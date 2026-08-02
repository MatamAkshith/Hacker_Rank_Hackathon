import os
import sys
import unittest
import shutil
from unittest.mock import MagicMock, patch

# Ensure correct python path to import packages from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.context.models import (
    Recipient,
    UnifiedContext,
    Message,
    Business,
    BusinessContext,
    Participants,
    Conversation,
    HistoryContext,
    MediaContext,
    MediaSummary,
    ContextMetadata
)
from code.understanding.models import UnderstandingResult
from code.understanding.voice_processor import VoiceProcessor
from code.understanding.cache import MediaCache
from code.ai.gemini_client import GeminiClient

class TestVoiceProcessorLLM(unittest.TestCase):

    def setUp(self):
        self.test_cache_dir = "test_voice_cache"
        self.cache = MediaCache(base_dir=self.test_cache_dir)

    def tearDown(self):
        if os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir)

    def test_voice_processor_routes_to_gemini(self):
        """Verify that VoiceProcessor loads the prompt, specifies media path, and calls GeminiClient."""
        mock_client = MagicMock(spec=GeminiClient)
        
        expected_result = UnderstandingResult(
            summary="Mock voice summary",
            intent="promotional",
            message_type="promotional",
            urgency="low",
            entities=["Brand"],
            requires_attention=False,
            promotion_detected=True,
            payment_detected=False,
            event_detected=False,
            contains_media=True,
            processing_status="temporary"
        )
        mock_client.generate.return_value = expected_result
        
        # Build mock context
        recipient = Recipient(
            user_id="u_001",
            do_not_disturb_window="23:00-08:00",
            messages_opened_30d=0,
            messages_replied_30d=0,
            notifications_dismissed_30d=0,
            messages_reported_30d=0
        )
        
        message = Message(
            message_id="msg_001",
            user_id="u_001",
            conversation_type="personal",
            created_at="2026-07-30 22:19",
            media_type="voice",
            media_id="vn_001",
            forwarded_count=0
        )
        
        media_metadata = MediaSummary(
            media_id="vn_001",
            media_type="voice",
            file_path="media/audio/vn_001.mp3"
        )
        
        metadata = ContextMetadata(
            has_business_context=False,
            has_group_context=False,
            has_historical_evidence=False,
            media_needs_processing=False,
            missing_datasets=[]
        )
        
        context = UnifiedContext(
            recipient=recipient,
            participants=Participants(sender=None, group=None),
            conversation=Conversation(message=message),
            business=None,
            media=MediaContext(media_metadata=media_metadata),
            history=HistoryContext(interaction_history=None, notification_summary=None),
            metadata=metadata
        )
        
        # Instantiate processor with mock client
        processor = VoiceProcessor(cache=self.cache, gemini_client=mock_client)
        result = processor.process(context)
        
        # Verify result and overridden processing_status
        self.assertEqual(result.summary, "Mock voice summary")
        self.assertEqual(result.processing_status, "processed_via_gemini_voice")
        
        # Verify generate parameters
        mock_client.generate.assert_called_once()
        kwargs = mock_client.generate.call_args[1]
        
        # Assert system_instruction contains prompts loaded from voice.md
        self.assertIn("multimodal", kwargs["system_instruction"])
        self.assertIn("voice notes", kwargs["system_instruction"])
        
        # Assert media_path matches target audio path
        self.assertEqual(kwargs["media_path"], "media/audio/vn_001.mp3")

if __name__ == "__main__":
    unittest.main()
