import os
import json
from typing import Optional
from code.understanding.models import UnderstandingResult

class MediaCache:
    """Utility to store and retrieve processed semantic results locally."""
    
    def __init__(self, base_dir: str = "cache"):
        self.base_dir = base_dir
        self.image_dir = os.path.join(base_dir, "images")
        self.voice_dir = os.path.join(base_dir, "voice")
        
        # Create directories if they don't exist
        os.makedirs(self.image_dir, exist_ok=True)
        os.makedirs(self.voice_dir, exist_ok=True)

    def _get_path(self, media_type: str, media_id: str) -> str:
        """Helper to get path for cache file."""
        target_dir = self.image_dir if media_type == "image" else self.voice_dir
        # Safe filename
        safe_id = "".join([c if c.isalnum() else "_" for c in media_id])
        return os.path.join(target_dir, f"{safe_id}.json")

    def get(self, media_type: str, media_id: str) -> Optional[UnderstandingResult]:
        """Loads and deserializes UnderstandingResult from cache if it exists."""
        cache_path = self._get_path(media_type, media_id)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return UnderstandingResult(**data)
            except Exception:
                return None
        return None

    def set(self, media_type: str, media_id: str, result: UnderstandingResult):
        """Serializes and saves UnderstandingResult to cache directory."""
        cache_path = self._get_path(media_type, media_id)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                data = result.dict() if hasattr(result, "dict") else result.model_dump()
                json.dump(data, f, indent=2)
        except Exception:
            pass
