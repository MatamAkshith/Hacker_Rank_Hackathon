import os
import re
from typing import Optional, List, Any
from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult
from code.understanding.processors.base import BaseProcessor
from code.ai.gemini_client import GeminiClient

class TextProcessor(BaseProcessor):
    """Processor to analyze and extract semantic meaning from raw text messages using GeminiClient or heuristics."""
    
    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini_client = gemini_client
        if self.gemini_client is None:
            try:
                self.gemini_client = GeminiClient()
            except ValueError:
                # Graceful fallback: keep client as None if GEMINI_API_KEY is not configured
                self.gemini_client = None

    def process(self, context: UnifiedContext, feature_vector: Optional[Any] = None) -> Optional[UnderstandingResult]:
        """Extracts semantic understanding from text context."""
        msg_text = context.conversation.message.message_text if context.conversation and context.conversation.message else ""
        if not msg_text:
            msg_text = ""
            
        if self.gemini_client is not None:
            try:
                return self._process_via_gemini(msg_text, context, feature_vector)
            except Exception:
                # Fallback to heuristics on API/call failures to ensure pipeline resiliency
                return self._process_via_heuristics(msg_text)
        else:
            return self._process_via_heuristics(msg_text)
        
    def _process_via_gemini(self, text: str, context: UnifiedContext, feature_vector: Optional[Any] = None) -> UnderstandingResult:
        """Sends raw text, context, and optional feature vector to Gemini LLM for structured semantic extraction."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.abspath(os.path.join(current_dir, "..", "ai", "prompts", "text.md"))
        
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_instruction = f.read()
        except Exception:
            system_instruction = "Act as a structured WhatsApp message semantic analyzer. Return valid JSON matching the UnderstandingResult schema."
            
        # Format the user prompt payload
        user_prompt = f"Message Text to analyze:\n\"\"\"\n{text}\n\"\"\"\n\n"
        
        # Append context metadata
        user_prompt += "Context Details:\n"
        if context.recipient:
            user_prompt += f"- Recipient DND: {context.recipient.do_not_disturb_window}\n"
        if context.business and context.business.profile:
            p = context.business.profile
            user_prompt += f"- Business Account: {p.display_name} (Category: {p.category}, Verified: {p.verified})\n"
            
        if feature_vector:
            user_prompt += f"\nPre-computed Feature Vector:\n{str(feature_vector)}\n"
            
        # Generate result using Gemini
        result = self.gemini_client.generate(
            system_instruction=system_instruction,
            prompt=user_prompt,
            response_model=UnderstandingResult
        )
        
        # Enforce strict processing status
        result.processing_status = "processed_via_gemini_text"
        return result

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
        raw_entities = re.findall(r'\b[A-Z][a-z]+\b', text)
        entities = list(dict.fromkeys(raw_entities))
        
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
