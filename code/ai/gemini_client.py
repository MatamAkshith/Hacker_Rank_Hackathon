"""GeminiClient: Unified LLM Client Router with automatic failover and health tracking.

Supports Gemini, OpenRouter, and Hybrid modes.
Handles transient errors (rate limit, quota, network timeouts) by falling back to
alternative models and providers, while propagating auth and parsing errors immediately.
"""

from __future__ import annotations

import os
import time
import urllib.error
from typing import List, Optional, Type, TypeVar, Dict
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

# Track dotenv loading internally
_ENV_LOADED = False

T = TypeVar("T", bound=BaseModel)

# ── Health Tracker (In-Memory) ────────────────────────────────────────────────
# Maps provider/model keys to the epoch timestamp when they become available again
_HEALTH_TRACKER: Dict[str, float] = {}


def _is_healthy(key: str) -> bool:
    now = time.time()
    blocked_until = _HEALTH_TRACKER.get(key, 0.0)
    return now >= blocked_until


def _mark_unhealthy(key: str, duration_seconds: float = 300.0) -> None:
    _HEALTH_TRACKER[key] = time.time() + duration_seconds


def _ensure_dotenv_loaded() -> None:
    """Load the repository-root ``.env`` once so configuration is available."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    if load_dotenv is not None:
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        load_dotenv(repo_root / ".env", override=False)
    _ENV_LOADED = True


def _parse_openrouter_models() -> List[str]:
    """Parse OPENROUTER_MODELS from environment variables cleanly."""
    raw_models = os.environ.get("OPENROUTER_MODELS", "")
    cleaned = raw_models.replace("\\", "").replace("\n", "").replace("\r", "")
    models = [m.strip() for m in cleaned.split(",") if m.strip()]
    return models if models else ["google/gemini-2.5-flash"]


def _is_retryable_error(e: Exception) -> bool:
    """Classifies whether an exception is transient/retryable (failover candidate)
    or terminal (authentication, schema validation, programming bug).
    """
    msg = str(e).lower()

    # Terminal: Schema validation and JSON parsing
    if any(term in msg for term in ("validation failed", "json parsing", "schema validation")):
        return False

    # Terminal: Bad API keys or access issues
    if any(term in msg for term in ("invalid api key", "api key not set", "status 401", "status 403")):
        return False

    # Transient: HTTP status code errors
    if any(status in msg for status in ("status 429", "status 500", "status 502", "status 503", "status 504")):
        return True

    # Transient: Quota / Resource exhaustion
    if any(term in msg for term in ("resource_exhausted", "quota", "exhausted", "rate limit", "requestsperday")):
        return True

    # Transient: Timeout or connection issues
    if any(term in msg for term in ("timeout", "connection", "rate-limited")):
        return True

    # Network exceptions
    if isinstance(e, (urllib.error.URLError, TimeoutError, ConnectionError)):
        return True

    return False


def _is_unhealthy_trigger(e: Exception) -> bool:
    """Checks if the exception warrants marking the model/provider unhealthy (quota/rate-limits)."""
    msg = str(e).lower()
    triggers = ["429", "quota", "resource_exhausted", "rate limit", "requestsperday"]
    return any(t in msg for t in triggers)


class GeminiClient:
    """Provider-agnostic LLM Router.

    Dynamically fails over between native Google Gemini and OpenRouter API models.
    Supports in-memory health tracking.
    """

    def __init__(self, model_name: Optional[str] = None):
        _ensure_dotenv_loaded()
        self.override_model_name = model_name

        provider = (os.environ.get("LLM_PROVIDER") or "").lower().strip()
        gemini_key = os.environ.get("GEMINI_API_KEY")

        # Fallback default if not specified
        if not provider:
            if gemini_key:
                provider = "gemini"
            else:
                raise ValueError(
                    "Configuration error: Neither LLM_PROVIDER nor GEMINI_API_KEY is configured in the environment."
                )

        if provider not in ("gemini", "openrouter", "hybrid"):
            raise ValueError(f"Configuration error: Unknown LLM_PROVIDER '{provider}'")

        if provider == "openrouter":
            or_key = os.environ.get("OPENROUTER_API_KEY")
            if not or_key:
                raise ValueError(
                    "Configuration error: OPENROUTER_API_KEY environment variable is not set. "
                    "Please configure it in your environment when using LLM_PROVIDER=openrouter."
                )

    @property
    def delegate(self):
        """Exposes the primary active delegate client (for backward-compatible unit tests)."""
        provider = (os.environ.get("LLM_PROVIDER") or "").lower().strip()
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if not provider:
            provider = "gemini" if gemini_key else "hybrid"

        if provider == "gemini" or provider == "hybrid":
            from code.ai.gemini_api_client import GeminiApiClient
            return GeminiApiClient(self.override_model_name)
        elif provider == "openrouter":
            from code.ai.openrouter_client import OpenRouterClient
            models = _parse_openrouter_models()
            return OpenRouterClient(models[0])
        return None

    def generate(
        self,
        system_instruction: str,
        prompt: str,
        response_model: Type[T],
        media_path: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> T:
        """Sends inference request to LLM, routing/failing over as configured."""
        provider = (os.environ.get("LLM_PROVIDER") or "").lower().strip()
        gemini_key = os.environ.get("GEMINI_API_KEY")

        # Fallback default if not specified
        if not provider:
            provider = "gemini" if gemini_key else "hybrid"

        if provider == "gemini":
            # Direct Gemini mode (Always use Gemini, raise errors directly)
            print("[LLM] Provider: Gemini")
            from code.ai.gemini_api_client import GeminiApiClient
            client = GeminiApiClient(self.override_model_name)
            return client.generate(system_instruction, prompt, response_model, media_path, mime_type)

        elif provider == "openrouter":
            # Direct OpenRouter mode with model list failover
            models = _parse_openrouter_models()
            last_error = None
            for idx, model in enumerate(models):
                if not _is_healthy(model):
                    continue

                print(f"[LLM] Trying model: {model}")
                try:
                    from code.ai.openrouter_client import OpenRouterClient
                    client = OpenRouterClient(model)
                    res = client.generate(system_instruction, prompt, response_model, media_path, mime_type)
                    print(f"[LLM] Success using: {model}")
                    return res
                except Exception as e:
                    last_error = e
                    if _is_retryable_error(e):
                        if _is_unhealthy_trigger(e):
                            _mark_unhealthy(model)
                        if idx < len(models) - 1:
                            print(f"[LLM] Model unavailable. Trying: {models[idx + 1]}")
                        continue
                    raise e
            if last_error:
                raise last_error
            raise ValueError("All configured OpenRouter models are currently unhealthy or exhausted.")

        elif provider == "hybrid":
            # Hybrid failover pipeline: Gemini -> OpenRouter Models
            gemini_healthy = _is_healthy("gemini")
            last_error = None

            if gemini_healthy:
                print("[LLM] Provider: Gemini")
                try:
                    from code.ai.gemini_api_client import GeminiApiClient
                    client = GeminiApiClient(self.override_model_name)
                    return client.generate(system_instruction, prompt, response_model, media_path, mime_type)
                except Exception as e:
                    last_error = e
                    if _is_retryable_error(e):
                        if _is_unhealthy_trigger(e):
                            _mark_unhealthy("gemini")
                        print("[LLM] Gemini rate limited.\nSwitching to OpenRouter.")
                    else:
                        raise e

            # Fallback to OpenRouter if Gemini is unhealthy or failed
            models = _parse_openrouter_models()
            for idx, model in enumerate(models):
                if not _is_healthy(model):
                    continue

                print(f"[LLM] Trying model:\n{model}")
                try:
                    from code.ai.openrouter_client import OpenRouterClient
                    client = OpenRouterClient(model)
                    res = client.generate(system_instruction, prompt, response_model, media_path, mime_type)
                    print(f"[LLM] Success using:\n{model}")
                    return res
                except Exception as e:
                    last_error = e
                    if _is_retryable_error(e):
                        if _is_unhealthy_trigger(e):
                            _mark_unhealthy(model)
                        if idx < len(models) - 1:
                            print(f"\n[LLM] Model unavailable.\n\nTrying:\n{models[idx + 1]}")
                        continue
                    raise e

            if last_error:
                raise last_error
            raise ValueError("All hybrid providers and models are currently unhealthy or exhausted.")

        else:
            raise ValueError(f"Unknown LLM_PROVIDER '{provider}'")
