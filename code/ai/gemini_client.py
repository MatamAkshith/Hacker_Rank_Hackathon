"""GeminiClient: Unified entry point for LLM inference.

Acting as a provider-agnostic proxy. Slices requests between native Google Gemini
API (GeminiApiClient) or OpenRouter API (OpenRouterClient) depending on env config.
"""

from __future__ import annotations

import os
from typing import Optional, Type, TypeVar
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

# Track dotenv loading internally
_ENV_LOADED = False

T = TypeVar("T", bound=BaseModel)


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


class GeminiClient:
    """Provider-agnostic LLM Client Proxy.

    Delegates generate() requests to the active provider (Gemini or OpenRouter).
    The active provider is chosen via the LLM_PROVIDER env variable.
    """

    def __init__(self, model_name: Optional[str] = None):
        _ensure_dotenv_loaded()

        provider = os.environ.get("LLM_PROVIDER")
        gemini_key = os.environ.get("GEMINI_API_KEY")

        # 1. Default fallback: if no provider specified but GEMINI_API_KEY exists, use gemini
        if not provider:
            if gemini_key:
                provider = "gemini"
            else:
                raise ValueError(
                    "Configuration error: Neither LLM_PROVIDER nor GEMINI_API_KEY is configured in the environment."
                )

        provider = provider.lower().strip()

        # 2. Instantiate active provider delegate
        if provider == "gemini":
            print("[LLM INITIALIZATION] Active Provider: Google Gemini API")
            from code.ai.gemini_api_client import GeminiApiClient
            self.delegate = GeminiApiClient(model_name)
        elif provider == "openrouter":
            print("[LLM INITIALIZATION] Active Provider: OpenRouter API")
            from code.ai.openrouter_client import OpenRouterClient
            self.delegate = OpenRouterClient(model_name)
        else:
            raise ValueError(
                f"Configuration error: Unknown LLM_PROVIDER '{provider}'. Supported values: 'gemini', 'openrouter'"
            )

    def generate(
        self,
        system_instruction: str,
        prompt: str,
        response_model: Type[T],
        media_path: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> T:
        """Invokes generate on the active provider delegate."""
        return self.delegate.generate(
            system_instruction=system_instruction,
            prompt=prompt,
            response_model=response_model,
            media_path=media_path,
            mime_type=mime_type,
        )
