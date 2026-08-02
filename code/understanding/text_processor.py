import re
from typing import Optional, List
from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult

class TextProcessor:
    """Processor to analyze and extract semantic meaning from raw text messages using heuristics."""
    
    def process(self, context: UnifiedContext) -> Optional[UnderstandingResult]:
        """Extracts semantic understanding from text context."""
        msg_text = context.conversation.message.message_text if context.conversation and context.conversation.message else ""
        if not msg_text:
            msg_text = ""
        return self._process_via_heuristics(msg_text)
        
    def _process_via_heuristics(self, text: str) -> UnderstandingResult:
        """Heuristic analysis of raw text using regex and keyword matching."""
        text_lower = text.lower()
        
        # 1. Promotion detection
        promo_kws = ["sale", "discount", "off", "coupon", "promo", "deal", "offer", "save", "free", "cashback", "limited time"]
        promotion_detected = any(kw in text_lower for kw in promo_kws)
        
        # 2. Payment detection
        payment_kws = ["pay", "invoice", "payment", "bank", "card", "bill", "amount", "due", "transferred", "$", "otp", "recharge"]
        payment_detected = any(kw in text_lower for kw in payment_kws)
        
        # 3. Event detection
        event_kws = ["schedule", "meet", "appointment", "date", "party", "tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "calendar", "event"]
        event_detected = any(kw in text_lower for kw in event_kws)
        
        # 4. Urgency detection
        high_urgency_kws = ["urgent", "immediately", "asap", "deadline", "emergency", "blocked"]
        medium_urgency_kws = ["soon", "today", "important", "action required", "attention required"]
        
        if any(kw in text_lower for kw in high_urgency_kws):
            urgency = "high"
        elif any(kw in text_lower for kw in medium_urgency_kws):
            urgency = "medium"
        else:
            urgency = "low"
            
        # 5. Attention requirement
        attention_kws = ["reply", "verify", "action required", "confirm", "respond", "immediately", "please click", "action needed"]
        requires_attention = any(kw in text_lower for kw in attention_kws) or urgency in ("high", "medium")
        
        # 6. Intent and Message Type classification
        if promotion_detected:
            intent = "promotional"
            message_type = "promotional"
        elif payment_detected:
            intent = "transactional"
            message_type = "transactional"
        elif event_detected:
            intent = "scheduling"
            message_type = "personal"
        else:
            intent = "social" if any(kw in text_lower for kw in ["hello", "hi", "hey", "how are", "bye"]) else "general"
            message_type = "personal"
            
        # 7. Summary generation
        cleaned_text = text.strip().replace("\n", " ")
        summary = cleaned_text[:80] + "..." if len(cleaned_text) > 80 else cleaned_text
        if not summary:
            summary = "Empty message"
            
        # 8. Entity extraction
        # Simple heuristic to extract capitalized words (names, places, etc.)
        raw_entities = re.findall(r'\b[A-Z][a-z]+\b', text)
        entities = list(dict.fromkeys(raw_entities))  # Deduplicate
        
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
            contains_media=False,
            processing_status="success"
        )
        
    def _process_via_llm(self, text: str) -> Optional[UnderstandingResult]:
        """Placeholder stub for future LLM (e.g. Gemini API) semantic processing."""
        pass
