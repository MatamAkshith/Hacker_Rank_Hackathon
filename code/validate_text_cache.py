"""Validate text-understanding caching via the shared MediaCache architecture.

Demonstrates:
  1. First process() invokes Gemini (mocked).
  2. Second process() loads entirely from cache (Gemini not called).
  3. Both UnderstandingResult payloads are identical.
"""

from __future__ import annotations

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
from code.understanding.text_processor import TextProcessor


def _build_context(message_text: str = "Could you review the attached note sometime?") -> UnifiedContext:
    recipient = Recipient(
        user_id="u_001",
        do_not_disturb_window="23:00-08:00",
        messages_opened_30d=0,
        messages_replied_30d=0,
        notifications_dismissed_30d=0,
        messages_reported_30d=0,
    )
    message = Message(
        message_id="msg_cache_001",
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


class TestTextUnderstandingCache(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="text_cache_validate_")
        self.cache = MediaCache(base_dir=self._tmp)

        self.mock_client = MagicMock(spec=GeminiClient)
        self.mock_client.generate.return_value = UnderstandingResult(
            summary="Mock Gemini summary for sale poster",
            intent="promotional",
            message_type="promotional",
            urgency="medium",
            entities=["Brand"],
            requires_attention=True,
            promotion_detected=True,
            payment_detected=False,
            event_detected=False,
            contains_media=False,
            processing_status="temporary",
        )

        self.processor = TextProcessor(cache=self.cache, gemini_client=self.mock_client)
        self.context = _build_context()

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_first_run_invokes_gemini_second_run_uses_cache(self) -> None:
        first = self.processor.process(self.context)
        self.assertEqual(self.mock_client.generate.call_count, 1)
        self.assertEqual(first.processing_status, "processed_via_gemini_text")
        self.assertEqual(first.summary, "Mock Gemini summary for sale poster")

        # Fresh processor instance sharing the same on-disk cache.
        processor_again = TextProcessor(cache=self.cache, gemini_client=self.mock_client)
        second = processor_again.process(self.context)

        self.assertEqual(
            self.mock_client.generate.call_count,
            1,
            "Second run must not invoke Gemini when cache hit exists",
        )
        self.assertEqual(first.model_dump(), second.model_dump())

        cache_files = os.listdir(self.cache.text_dir)
        self.assertEqual(len(cache_files), 1)
        self.assertTrue(cache_files[0].endswith(".json"))

    def test_cache_key_is_deterministic_for_normalized_text(self) -> None:
        key_a = self.processor._cache_key("Hello   world\n")
        key_b = self.processor._cache_key("Hello world")
        self.assertEqual(key_a, key_b)
        self.assertEqual(len(key_a), 64)


if __name__ == "__main__":
    unittest.main()
