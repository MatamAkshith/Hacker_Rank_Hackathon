import base64
import json
import mimetypes
import os
import urllib.request
import urllib.error
from typing import Optional, Type, TypeVar
from pydantic import BaseModel
from code.ai.parser import safe_parse_json

T = TypeVar("T", bound=BaseModel)

class GeminiClient:
    """Client wrapper for Gemini API to invoke text/multimodal inference with retries and validation."""
    
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.model_name = model_name
        self.api_key = os.environ.get("GEMINI_API_KEY")
        
        # Raise error if API key is not present
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set. Please configure it in your environment.")

    def generate(
        self,
        system_instruction: str,
        prompt: str,
        response_model: Type[T],
        media_path: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> T:
        """Sends inference request to Gemini API and parses into response_model with up to 3 retries."""
        
        # Prepare contents parts list
        parts = []
        if media_path and os.path.exists(media_path):
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(media_path)
            if not mime_type:
                if media_path.endswith(".mp3"):
                    mime_type = "audio/mp3"
                elif media_path.endswith(".jpg") or media_path.endswith(".jpeg"):
                    mime_type = "image/jpeg"
                else:
                    mime_type = "application/octet-stream"
                    
            with open(media_path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")
                
            parts.append({
                "inlineData": {
                    "mimeType": mime_type,
                    "data": b64_data
                }
            })
            
        parts.append({"text": prompt})
        
        # Initialize conversation turns list for auto-retry context accumulation
        contents = [
            {
                "role": "user",
                "parts": parts
            }
        ]
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        
        max_attempts = 3
        for attempt in range(max_attempts):
            payload = {
                "contents": contents,
                "generationConfig": {
                    "responseMimeType": "application/json"
                }
            }
            if system_instruction:
                payload["systemInstruction"] = {
                    "parts": [{"text": system_instruction}]
                }
                
            raw_text = ""
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req) as response:
                    res_data = response.read().decode("utf-8")
                    res_json = json.loads(res_data)
                    raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8") if e.fp else str(e)
                raise ValueError(f"Gemini API request failed with status {e.code}. Details: {error_body}") from e
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise ValueError(f"Failed to request or parse response from Gemini API: {str(e)}") from e
                continue
                
            # Attempt to parse and validate JSON response
            try:
                return safe_parse_json(raw_text, response_model)
            except ValueError as e:
                if attempt == max_attempts - 1:
                    raise ValueError(
                        f"Failed to validate response against schema after {max_attempts} attempts. "
                        f"Last raw response: {raw_text}. Error: {str(e)}"
                    ) from e
                    
                # Append failed model output and retry correction to conversation history
                contents.append({
                    "role": "model",
                    "parts": [{"text": raw_text}]
                })
                contents.append({
                    "role": "user",
                    "parts": [{
                        "text": (
                            f"Your output failed validation against the required schema. "
                            f"Please correct the output format and return valid JSON.\n"
                            f"Error details: {str(e)}"
                        )
                    }]
                })
                
        raise ValueError(f"Failed to generate valid schema response after {max_attempts} attempts.")
