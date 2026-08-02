import os
import json
from pathlib import Path
from typing import Optional
from code.understanding.models import UnderstandingResult

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CACHE_DIR = str(_REPO_ROOT / "cache")


class MediaCache:
    """Utility to store and retrieve processed semantic results locally."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or _DEFAULT_CACHE_DIR
        self.image_dir = os.path.join(self.base_dir, "images")
        self.voice_dir = os.path.join(self.base_dir, "voice")
        self.text_dir = os.path.join(self.base_dir, "text")

        # Create directories if they don't exist
        os.makedirs(self.image_dir, exist_ok=True)
        os.makedirs(self.voice_dir, exist_ok=True)
        os.makedirs(self.text_dir, exist_ok=True)

    def _get_path(self, media_type: str, media_id: str) -> str:
        """Helper to get path for cache file."""
        if media_type == "image":
            target_dir = self.image_dir
        elif media_type == "voice":
            target_dir = self.voice_dir
        elif media_type == "text":
            target_dir = self.text_dir
        else:
            raise ValueError(f"Unsupported cache media_type: {media_type}")
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
