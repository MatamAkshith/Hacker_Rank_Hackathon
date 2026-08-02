from typing import Optional, List
from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult
from code.understanding.text_processor import TextProcessor
from code.understanding.image_processor import ImageProcessor
from code.understanding.voice_processor import VoiceProcessor
from code.understanding.cache import MediaCache

class UnderstandingEngine:
    """Orchestrates text, image, and voice processors to construct UnifiedContext semantic understanding."""
    
    def __init__(self, cache: Optional[MediaCache] = None):
        self.cache = cache or MediaCache()
        self.text_processor = TextProcessor()
        self.image_processor = ImageProcessor(self.cache)
        self.voice_processor = VoiceProcessor(self.cache)

    def analyze(self, context: UnifiedContext) -> UnderstandingResult:
        """Processes the input context and returns the compiled semantic representation."""
        results: List[UnderstandingResult] = []
        
        # 1. Route to TextProcessor if message_text is present
        msg_text = context.conversation.message.message_text if context.conversation and context.conversation.message else ""
        if msg_text and msg_text.strip():
            text_res = self.text_processor.process(context)
            if text_res:
                results.append(text_res)
                
        # 2. Route to media processors if media is present
        media_type = context.conversation.message.media_type if context.conversation and context.conversation.message else None
        if media_type == "image":
            img_res = self.image_processor.process(context)
            if img_res:
                results.append(img_res)
        elif media_type == "voice":
            voice_res = self.voice_processor.process(context)
            if voice_res:
                results.append(voice_res)
                
        if not results:
            # Fallback safe default if no processors ran
            return UnderstandingResult(
                summary="Empty message",
                intent="general",
                message_type="personal",
                urgency="low",
                entities=[],
                requires_attention=False,
                promotion_detected=False,
                payment_detected=False,
                event_detected=False,
                contains_media=False,
                processing_status="empty_context"
            )
            
        # 3. Single Truth Convergence: Merge results if multiple exists
        merged = results[0]
        for next_res in results[1:]:
            merged = self._merge_results(merged, next_res)
            
        return merged

    def _merge_results(self, res1: UnderstandingResult, res2: UnderstandingResult) -> UnderstandingResult:
        """Merges two UnderstandingResult objects prioritizing first (usually text) for strings."""
        # Summaries concatenation
        summary = f"{res1.summary} | {res2.summary}"
        
        # Union entities (preserving order)
        seen = set(res1.entities)
        entities = list(res1.entities)
        for ent in res2.entities:
            if ent not in seen:
                entities.append(ent)
                seen.add(ent)
                
        # Urgency resolution
        urgency_priority = {"high": 3, "medium": 2, "low": 1}
        p1 = urgency_priority.get(res1.urgency.lower(), 1)
        p2 = urgency_priority.get(res2.urgency.lower(), 1)
        urgency = res1.urgency if p1 >= p2 else res2.urgency
        
        # Boolean operations (OR logic)
        requires_attention = res1.requires_attention or res2.requires_attention
        promotion_detected = res1.promotion_detected or res2.promotion_detected
        payment_detected = res1.payment_detected or res2.payment_detected
        event_detected = res1.event_detected or res2.event_detected
        contains_media = res1.contains_media or res2.contains_media
        
        # Intent and message_type hierarchy (res1/text preferred if populated)
        intent = res1.intent if res1.intent and res1.intent != "general" else (res2.intent or "general")
        message_type = res1.message_type if res1.message_type and res1.message_type != "personal" else (res2.message_type or "personal")
        
        return UnderstandingResult(
            summary=summary,
            intent=intent,
            message_type=message_type,
            urgency=urgency,
            entities=entities,
            requires_attention=requires_attention,
            promotion_detected=promotion_detected,
            payment_detected=payment_detected,
            event_detected=event_detected,
            contains_media=contains_media,
            processing_status="success"
        )
