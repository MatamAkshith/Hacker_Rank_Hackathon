import json
import re
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

def safe_parse_json(text: str, schema: Type[T]) -> T:
    """Strips Markdown blocks, parses raw text JSON, and validates against the schema."""
    cleaned = text.strip()
    
    # Strip markdown code block wraps if present
    # Matches ```json <content> ``` or ``` <content> ```
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
        
    # Attempt JSON parsing
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON string format: {e.msg} at position {e.pos}. Raw: {cleaned}") from e
        
    # Validate against target Pydantic schema (compatible with Pydantic v1 and v2)
    try:
        if hasattr(schema, "model_validate"):
            return schema.model_validate(data)
        else:
            return schema.parse_obj(data)
    except Exception as e:
        raise ValueError(f"Pydantic schema validation failed: {str(e)}") from e
