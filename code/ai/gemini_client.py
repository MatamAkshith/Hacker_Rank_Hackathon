import base64
import json
import logging
import mimetypes
import os
import re
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Optional, Type, TypeVar
from pydantic import BaseModel
from code.ai.parser import safe_parse_json

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional until installed
    load_dotenv = None

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)

_ENV_LOADED = False

# Prefer Flash-class models; fall through when a model exhausts free-tier daily quota.
# Put aliases with remaining quota ahead of exhausted primary when needed via GEMINI_MODEL.
_DEFAULT_MODEL_CHAIN: List[str] = [
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
]


def _ensure_dotenv_loaded() -> None:
    """Load the repository-root ``.env`` once so GEMINI_API_KEY is available."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    if load_dotenv is not None:
        repo_root = Path(__file__).resolve().parents[2]
        load_dotenv(repo_root / ".env", override=False)
    _ENV_LOADED = True


def _retry_delay_seconds(error_body: str, attempt: int) -> float:
    """Extract RetryInfo delay from a Gemini error body, with exponential fallback."""
    match = re.search(r'"retryDelay"\s*:\s*"(\d+)(?:\.\d+)?s"', error_body)
    if match:
        return max(1.0, float(match.group(1)) + 1.0)
    return min(60.0, (2 ** attempt) * 5.0)


def _is_daily_quota_error(error_body: str) -> bool:
    return "PerDay" in error_body or "requestsPerDay" in error_body


class GeminiClient:
    """Client wrapper for Gemini API to invoke text/multimodal inference with retries and validation."""

    # Shared across instances so exhausted models are not retried within one process.
    _exhausted_models: set[str] = set()
    _last_request_at: float = 0.0
    _min_request_interval_seconds: float = 3.0

    def __init__(self, model_name: Optional[str] = None):
        _ensure_dotenv_loaded()
        env_model = os.environ.get("GEMINI_MODEL")
        primary = model_name or env_model or _DEFAULT_MODEL_CHAIN[0]
        self.model_chain = [primary] + [m for m in _DEFAULT_MODEL_CHAIN if m != primary]
        self.model_name = primary
        self.api_key = os.environ.get("GEMINI_API_KEY")

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please configure it in your environment."
            )

    def _pace_requests(self) -> None:
        """Simple client-side spacing to reduce per-minute 429s."""
        elapsed = time.time() - GeminiClient._last_request_at
        wait_for = self._min_request_interval_seconds - elapsed
        if wait_for > 0:
            time.sleep(wait_for)

    def _active_models(self) -> List[str]:
        return [m for m in self.model_chain if m not in GeminiClient._exhausted_models]

    def generate(
        self,
        system_instruction: str,
        prompt: str,
        response_model: Type[T],
        media_path: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> T:
        """Sends inference request to Gemini API and parses into response_model with retries."""

        parts = []
        if media_path and os.path.exists(media_path):
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(media_path)
            if not mime_type:
                if media_path.endswith(".mp3"):
                    mime_type = "audio/mpeg"
                elif media_path.endswith(".jpg") or media_path.endswith(".jpeg"):
                    mime_type = "image/jpeg"
                else:
                    mime_type = "application/octet-stream"

            with open(media_path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")

            parts.append(
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": b64_data,
                    }
                }
            )

        parts.append({"text": prompt})

        contents = [
            {
                "role": "user",
                "parts": parts,
            }
        ]

        models = self._active_models()
        if not models:
            raise ValueError(
                "All configured Gemini models have exhausted their free-tier daily quota."
            )

        last_error: Optional[Exception] = None
        for model_name in models:
            self.model_name = model_name
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent?key={self.api_key}"
            )
            max_attempts = 4
            for attempt in range(max_attempts):
                payload = {
                    "contents": contents,
                    "generationConfig": {
                        "temperature": 0.0,
                        "responseMimeType": "application/json",
                    },
                }
                if system_instruction:
                    payload["systemInstruction"] = {
                        "parts": [{"text": system_instruction}]
                    }

                raw_text = ""
                try:
                    self._pace_requests()
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=120) as response:
                        GeminiClient._last_request_at = time.time()
                        res_data = response.read().decode("utf-8")
                        res_json = json.loads(res_data)
                        raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                except urllib.error.HTTPError as e:
                    error_body = e.read().decode("utf-8") if e.fp else str(e)
                    GeminiClient._last_request_at = time.time()
                    if e.code == 429:
                        if _is_daily_quota_error(error_body):
                            logger.warning(
                                "Gemini daily quota exhausted for %s; switching model",
                                model_name,
                            )
                            GeminiClient._exhausted_models.add(model_name)
                            last_error = ValueError(
                                f"Gemini API request failed with status {e.code}. Details: {error_body}"
                            )
                            break  # try next model
                        if attempt < max_attempts - 1:
                            delay = _retry_delay_seconds(error_body, attempt)
                            logger.warning(
                                "Gemini rate-limited (429) on %s; retrying in %.1fs (attempt %d/%d)",
                                model_name,
                                delay,
                                attempt + 1,
                                max_attempts,
                            )
                            time.sleep(delay)
                            continue
                    last_error = ValueError(
                        f"Gemini API request failed with status {e.code}. Details: {error_body}"
                    )
                    if e.code in {404, 400}:
                        GeminiClient._exhausted_models.add(model_name)
                        break
                    raise last_error from e
                except Exception as e:
                    if attempt == max_attempts - 1:
                        last_error = ValueError(
                            f"Failed to request or parse response from Gemini API: {str(e)}"
                        )
                        break
                    time.sleep(min(20.0, (2 ** attempt) * 2.0))
                    continue

                try:
                    return safe_parse_json(raw_text, response_model)
                except ValueError as e:
                    if attempt == max_attempts - 1:
                        last_error = ValueError(
                            f"Failed to validate response against schema after {max_attempts} attempts. "
                            f"Last raw response: {raw_text}. Error: {str(e)}"
                        )
                        break

                    contents.append(
                        {
                            "role": "model",
                            "parts": [{"text": raw_text}],
                        }
                    )
                    contents.append(
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "text": (
                                        "Your output failed validation against the required schema. "
                                        "Please correct the output format and return valid JSON.\n"
                                        f"Error details: {str(e)}"
                                    )
                                }
                            ],
                        }
                    )

        if last_error is not None:
            raise last_error
        raise ValueError("Failed to generate valid schema response from Gemini.")
