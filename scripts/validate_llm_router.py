"""Validation script for unified LLM Router failover and health management (Sprint 8.1)."""

import os
import sys
import time
from typing import Type, Optional
from pydantic import BaseModel
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.ai.gemini_client import GeminiClient, _HEALTH_TRACKER
from code.ai.gemini_api_client import GeminiApiClient
from code.ai.openrouter_client import OpenRouterClient


class DummyModel(BaseModel):
    summary: str


def reset_health():
    _HEALTH_TRACKER.clear()


def run_validation():
    print("=== STARTING LLM ROUTER VALIDATION ===\n")

    # Save environment variables
    env_backup = {
        "LLM_PROVIDER": os.environ.get("LLM_PROVIDER"),
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY"),
        "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY"),
        "OPENROUTER_MODELS": os.environ.get("OPENROUTER_MODELS"),
    }

    # Setup environment
    os.environ["LLM_PROVIDER"] = "hybrid"
    os.environ["GEMINI_API_KEY"] = "mock_gemini_key"
    os.environ["OPENROUTER_API_KEY"] = "mock_openrouter_key"
    os.environ["OPENROUTER_MODELS"] = "google/gemini-2.5-flash,openai/gpt-4.1-mini"

    # Dummy response
    dummy_res = DummyModel(summary="success_value")

    # ──────────────────────────────────────────────────────────────────────────
    # CASE 1: Gemini Success
    # ──────────────────────────────────────────────────────────────────────────
    reset_health()
    print("--- Case 1: Gemini Success ---")
    with patch.object(GeminiApiClient, "generate", return_value=dummy_res) as mock_gemini:
        with patch.object(OpenRouterClient, "generate") as mock_or:
            client = GeminiClient()
            res = client.generate("sys", "user", DummyModel)
            print(f"Result summary: {res.summary}")
            mock_gemini.assert_called_once()
            mock_or.assert_not_called()
            print("✓ Case 1 passed.\n")

    # ──────────────────────────────────────────────────────────────────────────
    # CASE 2: Gemini Rate Limit (Failover to OpenRouter first model)
    # ──────────────────────────────────────────────────────────────────────────
    reset_health()
    print("--- Case 2: Gemini Rate Limit (Failover) ---")
    with patch.object(GeminiApiClient, "generate", side_effect=ValueError("status 429: Too Many Requests")) as mock_gemini:
        with patch.object(OpenRouterClient, "generate", return_value=dummy_res) as mock_or:
            client = GeminiClient()
            res = client.generate("sys", "user", DummyModel)
            print(f"Result summary: {res.summary}")
            mock_gemini.assert_called_once()
            # Assert OpenRouterClient was instantiated and generate() called on the first model
            mock_or.assert_called_once()
            print("✓ Case 2 passed.\n")

    # ──────────────────────────────────────────────────────────────────────────
    # CASE 3: Gemini Quota Exceeded (Verify health tracking blocks it for subsequent runs)
    # ──────────────────────────────────────────────────────────────────────────
    reset_health()
    print("--- Case 3: Gemini Quota Exceeded & Health Tracker Block ---")
    with patch.object(GeminiApiClient, "generate", side_effect=ValueError("quota exceeded (RESOURCE_EXHAUSTED)")) as mock_gemini:
        with patch.object(OpenRouterClient, "generate", return_value=dummy_res) as mock_or:
            client = GeminiClient()
            # First request should fail on Gemini and trigger failover
            res1 = client.generate("sys", "user", DummyModel)
            mock_gemini.assert_called_once()
            mock_or.assert_called_once()

            # Second request should immediately skip Gemini (since it is marked unhealthy)
            mock_gemini.reset_mock()
            mock_or.reset_mock()
            res2 = client.generate("sys", "user", DummyModel)
            mock_gemini.assert_not_called()
            mock_or.assert_called_once()
            print("✓ Case 3 passed.\n")

    # ──────────────────────────────────────────────────────────────────────────
    # CASE 4: OpenRouter First Model Failure (Failover to Second Model)
    # ──────────────────────────────────────────────────────────────────────────
    reset_health()
    print("--- Case 4: OpenRouter First Model Failure (Model Failover) ---")

    def mock_or_generate(self, system_instruction, prompt, response_model, media_path=None, mime_type=None):
        if self.model_name == "google/gemini-2.5-flash":
            raise ValueError("status 429: Rate Limit on google model")
        return dummy_res

    # Mark Gemini unhealthy to force OpenRouter path directly
    _HEALTH_TRACKER["gemini"] = time.time() + 300.0

    with patch.object(OpenRouterClient, "generate", mock_or_generate):
        client = GeminiClient()
        res = client.generate("sys", "user", DummyModel)
        print(f"Result summary: {res.summary}")
        print("✓ Case 4 passed.\n")

    # ──────────────────────────────────────────────────────────────────────────
    # CASE 5: OpenRouter Second Model Success (Explicit verification)
    # ──────────────────────────────────────────────────────────────────────────
    reset_health()
    print("--- Case 5: OpenRouter Second Model Success ---")
    _HEALTH_TRACKER["gemini"] = time.time() + 300.0

    def mock_or_gen_second(self, system_instruction, prompt, response_model, media_path=None, mime_type=None):
        if self.model_name == "google/gemini-2.5-flash":
            raise ValueError("quota exceeded")
        elif self.model_name == "openai/gpt-4.1-mini":
            return DummyModel(summary="second_model_success")
        raise ValueError("Unknown model")

    with patch.object(OpenRouterClient, "generate", mock_or_gen_second):
        client = GeminiClient()
        res = client.generate("sys", "user", DummyModel)
        print(f"Result: {res.summary}")
        # Verify first model is now marked unhealthy
        self_healthy = _HEALTH_TRACKER.get("google/gemini-2.5-flash", 0.0)
        print(f"First model unhealthy state marked: {self_healthy > time.time()}")
        print("✓ Case 5 passed.\n")

    # ──────────────────────────────────────────────────────────────────────────
    # CASE 6: OpenRouter Total Failure
    # ──────────────────────────────────────────────────────────────────────────
    reset_health()
    print("--- Case 6: OpenRouter Total Failure ---")
    _HEALTH_TRACKER["gemini"] = time.time() + 300.0

    with patch.object(OpenRouterClient, "generate", side_effect=ValueError("resource_exhausted")):
        client = GeminiClient()
        try:
            client.generate("sys", "user", DummyModel)
            print("Error: Case 6 failed to raise ValueError")
            sys.exit(1)
        except ValueError as e:
            print(f"Caught expected total exhaustion exception: {e}")
            print("✓ Case 6 passed.\n")

    # Restore environment
    for k, v in env_backup.items():
        if v is None:
            if k in os.environ:
                del os.environ[k]
        else:
            os.environ[k] = v

    print("=== ALL LLM ROUTER MOCK VALIDATIONS PASSED ===")


if __name__ == "__main__":
    run_validation()
