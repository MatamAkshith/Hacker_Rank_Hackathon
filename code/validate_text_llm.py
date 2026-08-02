import os
import sys
import unittest
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
    ContextMetadata
)
from code.understanding.models import UnderstandingResult
from code.understanding.text_processor import TextProcessor
from code.ai.gemini_client import GeminiClient

class TestTextProcessorLLM(unittest.TestCase):

    def test_text_processor_routes_to_gemini(self):
        """Verify that TextProcessor loads the prompt, constructs the payload, and calls GeminiClient."""
        mock_client = MagicMock(spec=GeminiClient)
        
        expected_result = UnderstandingResult(
            summary="Mock summary",
            intent="promotional",
            message_type="promotional",
            urgency="low",
            entities=["Brand"],
            requires_attention=False,
            promotion_detected=True,
            payment_detected=False,
            event_detected=False,
            contains_media=False,
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
            message_text="Could you review the attached note sometime?",
            forwarded_count=0
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
            media=MediaContext(media_metadata=None),
            history=HistoryContext(interaction_history=None, notification_summary=None),
            metadata=metadata
        )
        
        # Instantiate processor with mock client
        processor = TextProcessor(gemini_client=mock_client)
        result = processor.process(context)
        
        # Verify result and overridden processing_status
        self.assertEqual(result.summary, "Mock summary")
        self.assertEqual(result.processing_status, "processed_via_gemini_text")
        
        # Verify generate parameters
        mock_client.generate.assert_called_once()
        kwargs = mock_client.generate.call_args[1]
        
        # Assert system_instruction contains prompts loaded from text.md
        self.assertIn("WhatsApp messages", kwargs["system_instruction"])
        
        # Assert prompt contains raw text and context DND window
        self.assertIn("Could you review the attached note sometime?", kwargs["prompt"])
        self.assertIn("23:00-08:00", kwargs["prompt"])

if __name__ == "__main__":
    unittest.main()
