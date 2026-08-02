"""Validate confidence-based Gemini routing for text understanding.

Reports:
  - Total text messages
  - Gemini text calls
  - Heuristic-only messages
  - Cache hits
  - Estimated API reduction
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.ai.gemini_client import GeminiClient
from code.context.models import (
    ContextMetadata,
    Conversation,
    HistoryContext,
    MediaContext,
    Message,
    Participants,
    Recipient,
    UnifiedContext,
)
from code.understanding.cache import MediaCache
from code.understanding.models import UnderstandingResult
from code.understanding.text_processor import TextProcessor, _HEURISTIC_CONFIDENCE_THRESHOLD


def _build_context(message_id: str, message_text: str) -> UnifiedContext:
    recipient = Recipient(
        user_id="u_001",
        do_not_disturb_window="23:00-08:00",
        messages_opened_30d=0,
        messages_replied_30d=0,
        notifications_dismissed_30d=0,
        messages_reported_30d=0,
    )
    message = Message(
        message_id=message_id,
        user_id="u_001",
        conversation_type="personal",
        created_at="2026-07-30 22:19",
        message_text=message_text,
        forwarded_count=0,
    )
    metadata = ContextMetadata(
        has_business_context=False,
        has_group_context=False,
        has_historical_evidence=False,
        media_needs_processing=False,
        missing_datasets=[],
    )
    return UnifiedContext(
        recipient=recipient,
        participants=Participants(sender=None, group=None),
        conversation=Conversation(message=message),
        business=None,
        media=MediaContext(media_metadata=None),
        history=HistoryContext(interaction_history=None, notification_summary=None),
        metadata=metadata,
    )


# High-confidence promo/urgent text should stay on heuristics.
_HIGH_CONFIDENCE_TEXTS = [
    "URGENT: Flash sale up to 50% off storewide this weekend only!",
    "Please pay invoice INV-4421 amount due of Rs 1500 immediately.",
]

# Ambiguous / short / general text should route to Gemini when available.
# Avoid promo/payment keywords and the substring "hi" (matches inside "this").
_LOW_CONFIDENCE_TEXTS = [
    "Could you review the attached note sometime?",
    "ok",
    "hmm maybe later",
    "not sure what that means exactly",
]


class TestTextConfidenceRouting(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="text_routing_validate_")
        self.cache = MediaCache(base_dir=self._tmp)
        self.mock_client = MagicMock(spec=GeminiClient)
        self.mock_client.generate.return_value = UnderstandingResult(
            summary="Mock Gemini summary",
            intent="general",
            message_type="personal",
            urgency="low",
            entities=[],
            requires_attention=False,
            promotion_detected=False,
            payment_detected=False,
            event_detected=False,
            contains_media=False,
            processing_status="temporary",
        )
        self.processor = TextProcessor(cache=self.cache, gemini_client=self.mock_client)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_high_confidence_skips_gemini(self) -> None:
        context = _build_context("msg_hi", _HIGH_CONFIDENCE_TEXTS[0])
        heuristic = self.processor._process_via_heuristics(_HIGH_CONFIDENCE_TEXTS[0])
        confidence = self.processor._estimate_heuristic_confidence(
            heuristic, _HIGH_CONFIDENCE_TEXTS[0]
        )
        self.assertGreaterEqual(confidence, _HEURISTIC_CONFIDENCE_THRESHOLD)

        result = self.processor.process(context)
        self.assertEqual(self.mock_client.generate.call_count, 0)
        self.assertEqual(result.processing_status, "success")
        self.assertEqual(self.processor.routing_stats["heuristic_only"], 1)
        self.assertEqual(self.processor.routing_stats["gemini_calls"], 0)

    def test_low_confidence_calls_gemini_then_cache(self) -> None:
        text = _LOW_CONFIDENCE_TEXTS[0]
        context = _build_context("msg_lo", text)
        heuristic = self.processor._process_via_heuristics(text)
        confidence = self.processor._estimate_heuristic_confidence(heuristic, text)
        self.assertLess(confidence, _HEURISTIC_CONFIDENCE_THRESHOLD)

        first = self.processor.process(context)
        self.assertEqual(self.mock_client.generate.call_count, 1)
        self.assertEqual(first.processing_status, "processed_via_gemini_text")
        self.assertEqual(self.processor.routing_stats["gemini_calls"], 1)

        second = self.processor.process(context)
        self.assertEqual(self.mock_client.generate.call_count, 1)
        self.assertEqual(second.model_dump(), first.model_dump())
        self.assertEqual(self.processor.routing_stats["cache_hits"], 1)

    def test_routing_report_over_sample_corpus(self) -> None:
        texts = _HIGH_CONFIDENCE_TEXTS + _LOW_CONFIDENCE_TEXTS
        for idx, text in enumerate(texts):
            self.processor.process(_build_context(f"msg_{idx}", text))

        # Second pass should be entirely cache hits.
        for idx, text in enumerate(texts):
            self.processor.process(_build_context(f"msg_{idx}", text))

        total = len(texts) * 2
        stats = self.processor.routing_stats
        gemini_calls = stats["gemini_calls"]
        heuristic_only = stats["heuristic_only"]
        cache_hits = stats["cache_hits"]
        estimated_reduction = (
            round(100.0 * (1.0 - (gemini_calls / len(texts))), 1) if texts else 0.0
        )

        report = {
            "total_text_messages": total,
            "unique_text_messages": len(texts),
            "gemini_text_calls": gemini_calls,
            "heuristic_only_messages": heuristic_only,
            "cache_hits": cache_hits,
            "estimated_api_reduction_percent": estimated_reduction,
        }
        print("\nTEXT ROUTING REPORT")
        for key, value in report.items():
            print(f"  {key}: {value}")

        self.assertEqual(total, heuristic_only + gemini_calls + cache_hits)
        self.assertEqual(cache_hits, len(texts))
        self.assertEqual(gemini_calls, len(_LOW_CONFIDENCE_TEXTS))
        self.assertEqual(heuristic_only, len(_HIGH_CONFIDENCE_TEXTS))
        self.assertGreater(estimated_reduction, 0.0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    unittest.main()
