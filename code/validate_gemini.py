import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO

# Ensure correct python path to import packages from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pydantic import BaseModel, Field
from code.ai.parser import safe_parse_json
from code.ai.gemini_client import GeminiClient

class TestModel(BaseModel):
    name: str
    value: int

class TestGeminiInfrastructure(unittest.TestCase):

    def test_safe_parse_json_markdown_stripping(self):
        """Verify that markdown code blocks are safely stripped and parsed correctly."""
        markdown_text = """
```json
{
  "name": "Gemini",
  "value": 100
}
```
"""
        result = safe_parse_json(markdown_text, TestModel)
        self.assertEqual(result.name, "Gemini")
        self.assertEqual(result.value, 100)

    def test_safe_parse_json_raw(self):
        """Verify that raw JSON without markdown codeblocks is parsed correctly."""
        raw_text = '{"name": "Flash", "value": 200}'
        result = safe_parse_json(raw_text, TestModel)
        self.assertEqual(result.name, "Flash")
        self.assertEqual(result.value, 200)

    def test_safe_parse_json_validation_failure(self):
        """Verify that validation failures raise a ValueError."""
        invalid_data = '{"name": "Flash", "value": "not_an_int"}'
        with self.assertRaises(ValueError):
            safe_parse_json(invalid_data, TestModel)

    @patch("urllib.request.urlopen")
    def test_gemini_client_retry_logic(self, mock_urlopen):
        """Verify that GeminiClient automatically retries correction loop on parser errors."""
        # 1. Setup mock HTTP responses:
        # First call returns invalid schema JSON (missing required field 'value')
        response1 = MagicMock()
        response1.__enter__.return_value = response1
        response1.read.return_value = b'{"candidates": [{"content": {"parts": [{"text": "{\\"name\\": \\"FailedAttempt\\"}"}]}}]}'
        
        # Second call returns valid JSON conforming to TestModel schema
        response2 = MagicMock()
        response2.__enter__.return_value = response2
        response2.read.return_value = b'{"candidates": [{"content": {"parts": [{"text": "{\\"name\\": \\"Success\\", \\"value\\": 77}"}]}}]}'
        
        mock_urlopen.side_effect = [response1, response2]
        
        # Instantiate client with a temporary mock environment key
        with patch.dict(os.environ, {"GEMINI_API_KEY": "mock_api_key"}):
            client = GeminiClient(model_name="gemini-1.5-flash")
            result = client.generate(
                system_instruction="Instruction",
                prompt="User Prompt",
                response_model=TestModel
            )
            
            # Assert correct final parsed response
            self.assertEqual(result.name, "Success")
            self.assertEqual(result.value, 77)
            
            # Verify mock_urlopen was called exactly twice
            self.assertEqual(mock_urlopen.call_count, 2)

if __name__ == "__main__":
    unittest.main()
