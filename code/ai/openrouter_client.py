"""OpenRouterClient: Client wrapper for OpenRouter API.

Implements the identical generate interface as GeminiClient for seamless,
provider-agnostic usage.
"""

import base64
import json
import logging
import mimetypes
import os
import time
import urllib.request
import urllib.error
from typing import Optional, Type, TypeVar
from pydantic import BaseModel
from code.ai.parser import safe_parse_json

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Client wrapper for OpenRouter API to invoke text/multimodal inference."""

    def __init__(self, model_name: Optional[str] = None):
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable is not set. "
                "Please configure it in your environment when using LLM_PROVIDER=openrouter."
            )

        env_model = os.environ.get("OPENROUTER_MODEL")
        self.model_name = model_name or env_model or "google/gemini-2.5-flash"

        self.site_url = os.environ.get("OPENROUTER_SITE_URL", "http://localhost")
        self.app_name = os.environ.get("OPENROUTER_APP_NAME", "HackerRank Message Router")

    def generate(
        self,
        system_instruction: str,
        prompt: str,
        response_model: Type[T],
        media_path: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> T:
        """Sends inference request to OpenRouter API and parses into response_model with retries."""
        url = "https://openrouter.ai/api/v1/chat/completions"

        # Prepare messages in OpenAI compatible format
        messages = []
        if system_instruction:
            messages.append({
                "role": "system",
                "content": system_instruction
            })

        user_content = []

        # Handle media attachments
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

            # OpenAI format for visual media: image_url
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{b64_data}"
                }
            })

        user_content.append({
            "type": "text",
            "text": prompt
        })

        messages.append({
            "role": "user",
            "content": user_content
        })

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.0,
            "response_format": {
                "type": "json_object"
            }
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
        }

        max_attempts = 4
        last_error = None
        for attempt in range(max_attempts):
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=120) as response:
                    res_data = response.read().decode("utf-8")
                    res_json = json.loads(res_data)
                    raw_text = res_json["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8") if e.fp else str(e)
                last_error = ValueError(f"OpenRouter API request failed with status {e.code}. Details: {error_body}")
                if e.code == 429:
                    time.sleep(min(30.0, (2 ** attempt) * 3.0))
                    continue
                raise last_error from e
            except Exception as e:
                if attempt == max_attempts - 1:
                    last_error = ValueError(f"Failed to request or parse response from OpenRouter API: {str(e)}")
                    break
                time.sleep(min(20.0, (2 ** attempt) * 2.0))
                continue

            try:
                return safe_parse_json(raw_text, response_model)
            except ValueError as e:
                if attempt == max_attempts - 1:
                    last_error = ValueError(
                        f"Failed to validate OpenRouter response against schema. Raw response: {raw_text}. Error: {str(e)}"
                    )
                    break
                # Resubmit with warning
                messages.append({
                    "role": "assistant",
                    "content": raw_text
                })
                messages.append({
                    "role": "user",
                    "content": (
                        "Your output failed validation against the required schema. "
                        "Please correct the output format and return valid JSON.\n"
                        f"Error details: {str(e)}"
                    )
                })
                payload["messages"] = messages

        if last_error is not None:
            raise last_error
        raise ValueError("Failed to generate valid schema response from OpenRouter.")
