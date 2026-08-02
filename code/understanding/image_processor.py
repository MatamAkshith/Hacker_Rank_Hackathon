import os
from typing import Optional, Any
from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult
from code.understanding.processors.base import BaseProcessor
from code.understanding.cache import MediaCache
from code.ai.gemini_client import GeminiClient

class ImageProcessor(BaseProcessor):
    """Processor to analyze image attachments (OCR and visual description) using GeminiClient."""
    
    def __init__(self, cache: Optional[MediaCache] = None, gemini_client: Optional[GeminiClient] = None):
        self.cache = cache or MediaCache()
        self.gemini_client = gemini_client
        if self.gemini_client is None:
            try:
                self.gemini_client = GeminiClient()
            except ValueError:
                # Graceful fallback: keep client as None if GEMINI_API_KEY is not configured
                self.gemini_client = None
        
    def process(self, context: UnifiedContext) -> Optional[UnderstandingResult]:
        """Extracts semantic understanding from image context with caching."""
        media_id = None
        image_path = None
        if context.media and context.media.media_metadata:
            media_id = context.media.media_metadata.media_id
            image_path = context.media.media_metadata.file_path
            
        if not media_id:
            media_id = "unknown_image_id"
        if not image_path:
            image_path = "unknown_image_path"
            
        # 1. Check cache hit
        cached = self.cache.get("image", media_id)
        if cached:
            return cached
            
        # 2. Cache miss: route to Gemini Vision or placeholder fallback
        if self.gemini_client is not None:
            try:
                result = self._process_via_gemini_vision(image_path)
            except Exception:
                result = self._process_placeholder(image_path)
        else:
            result = self._process_placeholder(image_path)
            
        self.cache.set("image", media_id, result)
        return result
        
    def _process_via_gemini_vision(self, image_path: str) -> UnderstandingResult:
        """Sends image and system instructions to Gemini LLM for structured visual semantic extraction."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.abspath(os.path.join(current_dir, "..", "ai", "prompts", "image.md"))
        
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_instruction = f.read()
        except Exception:
            system_instruction = "Act as a WhatsApp image semantic analyzer. Return valid JSON matching the UnderstandingResult schema."
            
        user_prompt = "Perform OCR on the attached image and output the structured semantic details."
        
        # Invoke multimodal generate
        result = self.gemini_client.generate(
            system_instruction=system_instruction,
            prompt=user_prompt,
            response_model=UnderstandingResult,
            media_path=image_path
        )
        
        # Enforce strict processing status
        result.processing_status = "processed_via_gemini_vision"
        return result

    def _process_placeholder(self, image_path: str) -> UnderstandingResult:
        """Returns placeholder semantic representation for visual media."""
        return UnderstandingResult(
            summary=f"[Image Placeholder: {image_path}]",
            intent="general",
            message_type="personal",
            urgency="low",
            entities=[],
            requires_attention=False,
            promotion_detected=False,
            payment_detected=False,
            event_detected=False,
            contains_media=True,
            processing_status="placeholder_applied"
        )
