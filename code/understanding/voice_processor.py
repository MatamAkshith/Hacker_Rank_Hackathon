import logging
import os
from typing import Optional, Any
from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult
from code.understanding.processors.base import BaseProcessor
from code.understanding.cache import MediaCache
from code.ai.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class VoiceProcessor(BaseProcessor):
    """Processor to analyze audio/voice attachments (ASR/transcription) using GeminiClient."""
    
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
        """Extracts semantic understanding from voice context with caching."""
        media_id = None
        voice_path = None
        if context.media and context.media.media_metadata:
            media_id = context.media.media_metadata.media_id
            voice_path = context.media.media_metadata.file_path
            
        if not media_id:
            media_id = "unknown_voice_id"
        if not voice_path:
            voice_path = "unknown_voice_path"
            
        # 1. Check cache hit (ignore stale placeholders when Gemini is available)
        cached = self.cache.get("voice", media_id)
        if cached and not (
            self.gemini_client is not None
            and getattr(cached, "processing_status", "") == "placeholder_applied"
        ):
            return cached
            
        # 2. Cache miss: route to Gemini Voice or placeholder fallback
        if self.gemini_client is not None:
            try:
                result = self._process_via_transcription(voice_path)
            except Exception:
                logger.exception("Gemini audio failed for media_id=%s path=%s", media_id, voice_path)
                result = self._process_placeholder(voice_path)
        else:
            result = self._process_placeholder(voice_path)
            
        # Do not persist placeholder failures when Gemini is configured; allow retries.
        if result.processing_status != "placeholder_applied" or self.gemini_client is None:
            self.cache.set("voice", media_id, result)
        return result
        
    def _process_via_transcription(self, voice_path: str) -> UnderstandingResult:
        """Sends audio voice file and system instructions to Gemini LLM for native transcription and extraction."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.abspath(os.path.join(current_dir, "..", "ai", "prompts", "voice.md"))
        
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_instruction = f.read()
        except Exception:
            system_instruction = "Act as a WhatsApp audio semantic analyzer. Return valid JSON matching the UnderstandingResult schema."
            
        user_prompt = "Transcribe the attached voice note natively and output the structured semantic details."
        
        # Invoke audio generate
        result = self.gemini_client.generate(
            system_instruction=system_instruction,
            prompt=user_prompt,
            response_model=UnderstandingResult,
            media_path=voice_path
        )
        
        # Enforce strict processing status
        result.processing_status = "processed_via_gemini_voice"
        return result

    def _process_placeholder(self, voice_path: str) -> UnderstandingResult:
        """Returns placeholder semantic representation for audio media."""
        return UnderstandingResult(
            summary=f"[Voice Placeholder: {voice_path}]",
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
