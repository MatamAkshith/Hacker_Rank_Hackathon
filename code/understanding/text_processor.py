import hashlib
import logging
import os
import re
from typing import Any, Dict, Optional
from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult
from code.understanding.processors.base import BaseProcessor
from code.understanding.cache import MediaCache
from code.ai.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

# Bump when the text prompt contract or normalization rules change.
_TEXT_PROMPT_VERSION = "text_v1"
_HEURISTIC_CONFIDENCE_THRESHOLD = 0.85


class TextProcessor(BaseProcessor):
    """Processor to analyze and extract semantic meaning from raw text messages using GeminiClient or heuristics."""

    def __init__(
        self,
        cache: Optional[MediaCache] = None,
        gemini_client: Optional[GeminiClient] = None,
    ):
        self.cache = cache or MediaCache()
        self.gemini_client = gemini_client
        if self.gemini_client is None:
            try:
                self.gemini_client = GeminiClient()
            except ValueError:
                # Graceful fallback: keep client as None if GEMINI_API_KEY is not configured
                self.gemini_client = None
        self.routing_stats: Dict[str, int] = {
            "cache_hits": 0,
            "heuristic_only": 0,
            "gemini_calls": 0,
        }

    def process(self, context: UnifiedContext, feature_vector: Optional[Any] = None) -> Optional[UnderstandingResult]:
        """Extracts semantic understanding from text with cache + confidence-based Gemini routing."""
        msg_text = context.conversation.message.message_text if context.conversation and context.conversation.message else ""
        if not msg_text:
            msg_text = ""

        message_id = (
            context.conversation.message.message_id
            if context.conversation and context.conversation.message
            else "unknown"
        )

        cache_key = self._cache_key(msg_text, feature_vector)
        cached = self.cache.get("text", cache_key)
        if cached is not None:
            self.routing_stats["cache_hits"] += 1
            logger.info(
                "text_routing source=cache message_id=%s status=%s",
                message_id,
                getattr(cached, "processing_status", ""),
            )
            return cached

        heuristic = self._process_via_heuristics(msg_text)
        confidence = self._estimate_heuristic_confidence(heuristic, msg_text)

        if confidence >= _HEURISTIC_CONFIDENCE_THRESHOLD:
            self.routing_stats["heuristic_only"] += 1
            logger.info(
                "text_routing source=heuristic message_id=%s confidence=%.3f",
                message_id,
                confidence,
            )
            self.cache.set("text", cache_key, heuristic)
            return heuristic

        if self.gemini_client is not None:
            try:
                result = self._process_via_gemini(msg_text, context, feature_vector)
                self.routing_stats["gemini_calls"] += 1
                logger.info(
                    "text_routing source=gemini message_id=%s confidence=%.3f",
                    message_id,
                    confidence,
                )
            except Exception:
                # Fallback to heuristics on API/call failures to ensure pipeline resiliency
                logger.exception("Gemini text analysis failed; falling back to heuristics")
                result = heuristic
                self.routing_stats["heuristic_only"] += 1
                logger.info(
                    "text_routing source=heuristic message_id=%s confidence=%.3f reason=gemini_fallback",
                    message_id,
                    confidence,
                )
        else:
            result = heuristic
            self.routing_stats["heuristic_only"] += 1
            logger.info(
                "text_routing source=heuristic message_id=%s confidence=%.3f reason=no_gemini_client",
                message_id,
                confidence,
            )

        self.cache.set("text", cache_key, result)
        return result

    def _estimate_heuristic_confidence(self, result: UnderstandingResult, text: str) -> float:
        """Estimate confidence of the deterministic heuristic UnderstandingResult.

        Clear single-category signals with enough lexical evidence score high.
        Conflicting categories, tiny texts, or generic content score lower and
        are routed to Gemini when a client is available.
        """
        score = 0.40
        category_signals = sum(
            (
                bool(result.promotion_detected),
                bool(result.payment_detected),
                bool(result.event_detected),
            )
        )

        if category_signals == 1:
            score += 0.35
        elif category_signals >= 2:
            # Multiple overlapping labels are treated as ambiguous.
            score += 0.10
        elif result.intent == "social":
            score += 0.30
        elif result.intent == "general":
            score += 0.05
        else:
            score += 0.15

        if result.urgency == "high":
            score += 0.15
        elif result.urgency == "medium":
            score += 0.08

        words = len(self._normalize_text(text).split())
        if words >= 8:
            score += 0.10
        elif words <= 2:
            score -= 0.20

        if result.entities:
            score += 0.05

        return round(max(0.0, min(1.0, score)), 4)

    def _cache_key(self, text: str, feature_vector: Optional[Any] = None) -> str:
        """Deterministic SHA-256 key from normalized text, prompt version, and optional features."""
        normalized = self._normalize_text(text)
        prompt_version = self._prompt_version()
        payload = f"{prompt_version}\n{normalized}"
        if feature_vector is not None:
            payload = f"{payload}\n{str(feature_vector)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize whitespace for stable cache keys."""
        return " ".join((text or "").strip().split())

    def _prompt_version(self) -> str:
        """Combine a local version tag with a hash of the on-disk text prompt when available."""
        prompt_path = self._text_prompt_path()
        try:
            with open(prompt_path, "r", encoding="utf-8") as prompt_file:
                prompt_digest = hashlib.sha256(prompt_file.read().encode("utf-8")).hexdigest()[:16]
            return f"{_TEXT_PROMPT_VERSION}:{prompt_digest}"
        except Exception:
            return _TEXT_PROMPT_VERSION

    @staticmethod
    def _text_prompt_path() -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(current_dir, "..", "ai", "prompts", "text.md"))

    def _process_via_gemini(self, text: str, context: UnifiedContext, feature_vector: Optional[Any] = None) -> UnderstandingResult:
        """Sends raw text, context, and optional feature vector to Gemini LLM for structured semantic extraction."""
        prompt_path = self._text_prompt_path()

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
