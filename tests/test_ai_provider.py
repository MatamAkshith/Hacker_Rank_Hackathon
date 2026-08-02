"""Unit tests for provider-agnostic GeminiClient configuration (OpenRouter support)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.ai.gemini_client import GeminiClient


class TestAIProviderDelegation(unittest.TestCase):

    def setUp(self):
        # Backup environment variables
        self.env_backup = {
            "LLM_PROVIDER": os.environ.get("LLM_PROVIDER"),
            "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY"),
            "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY"),
            "OPENROUTER_MODEL": os.environ.get("OPENROUTER_MODEL"),
        }

    def tearDown(self):
        # Restore environment variables
        for k, v in self.env_backup.items():
            if v is None:
                if k in os.environ:
                    del os.environ[k]
            else:
                os.environ[k] = v

    def test_default_gemini_without_provider_selection(self):
        """Should delegate to GeminiApiClient if no provider specified but GEMINI_API_KEY is present."""
        os.environ["GEMINI_API_KEY"] = "mock_gemini_key"
        if "LLM_PROVIDER" in os.environ:
            del os.environ["LLM_PROVIDER"]

        client = GeminiClient()
        from code.ai.gemini_api_client import GeminiApiClient
        self.assertIsInstance(client.delegate, GeminiApiClient)

    def test_explicit_gemini_provider(self):
        """Should delegate to GeminiApiClient when LLM_PROVIDER=gemini."""
        os.environ["LLM_PROVIDER"] = "gemini"
        os.environ["GEMINI_API_KEY"] = "mock_gemini_key"

        client = GeminiClient()
        from code.ai.gemini_api_client import GeminiApiClient
        self.assertIsInstance(client.delegate, GeminiApiClient)

    def test_explicit_openrouter_provider(self):
        """Should delegate to OpenRouterClient when LLM_PROVIDER=openrouter."""
        os.environ["LLM_PROVIDER"] = "openrouter"
        os.environ["OPENROUTER_API_KEY"] = "mock_openrouter_key"
        os.environ["OPENROUTER_MODEL"] = "google/gemini-2.5-flash"

        client = GeminiClient()
        from code.ai.openrouter_client import OpenRouterClient
        self.assertIsInstance(client.delegate, OpenRouterClient)
        self.assertEqual(client.delegate.model_name, "google/gemini-2.5-flash")

    def test_missing_config_raises_error(self):
        """Should raise ValueError if required variables are missing."""
        if "LLM_PROVIDER" in os.environ:
            del os.environ["LLM_PROVIDER"]
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        if "OPENROUTER_API_KEY" in os.environ:
            del os.environ["OPENROUTER_API_KEY"]

        with self.assertRaises(ValueError):
            GeminiClient()

    def test_missing_openrouter_key_raises_error(self):
        """Should raise ValueError when openrouter chosen but no key set."""
        os.environ["LLM_PROVIDER"] = "openrouter"
        if "OPENROUTER_API_KEY" in os.environ:
            del os.environ["OPENROUTER_API_KEY"]

        with self.assertRaises(ValueError):
            GeminiClient()


if __name__ == "__main__":
    unittest.main()
