from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")

class AIResponseWrapper(BaseModel, Generic[T]):
    """Generic wrapper for structured AI responses."""
    success: bool
    data: Optional[T] = None
    error_message: Optional[str] = None
