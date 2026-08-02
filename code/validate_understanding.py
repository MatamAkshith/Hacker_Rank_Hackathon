import os
import sys
import unittest
import shutil

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
from code.understanding.understanding_engine import UnderstandingEngine
from code.understanding.cache import MediaCache

class TestUnderstandingFramework(unittest.TestCase):
    
    def setUp(self):
        """Set up cache directory and engine."""
        self.test_cache_dir = "test_cache"
        self.cache = MediaCache(base_dir=self.test_cache_dir)
        
        # Temporarily disable GEMINI_API_KEY and prevent disk dotenv reloading
        self.api_key_backup = os.environ.get("GEMINI_API_KEY")
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
            
        import code.ai.gemini_client
        self.dotenv_backup = code.ai.gemini_client._ENV_LOADED
        code.ai.gemini_client._ENV_LOADED = True
            
        self.engine = UnderstandingEngine(cache=self.cache)
        
        # Build base metadata
        self.metadata = ContextMetadata(
            has_business_context=False,
            has_group_context=False,
            has_historical_evidence=False,
            media_needs_processing=False,
            missing_datasets=[]
        )
        
        # Build recipient
        self.recipient = Recipient(
            user_id="u_test_001",
            messages_opened_30d=0,
            messages_replied_30d=0,
            notifications_dismissed_30d=0,
            messages_reported_30d=0
        )

    def tearDown(self):
        """Cleanup test cache directory."""
        if os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir)
            
        import code.ai.gemini_client
        code.ai.gemini_client._ENV_LOADED = self.dotenv_backup
        if self.api_key_backup is not None:
            os.environ["GEMINI_API_KEY"] = self.api_key_backup

    def test_text_only_understanding(self):
        """Verify that TextProcessor correctly analyzes raw text and returns expected semantic features."""
        message = Message(
            message_id="msg_text_001",
            user_id="u_test_001",
            conversation_type="personal",
            created_at="2026-07-30 22:19",
            message_text="Hey John! Are we still scheduled to meet tomorrow at 3pm for our appointment?",
            forwarded_count=0
        )
        
        context = UnifiedContext(
            recipient=self.recipient,
            participants=Participants(sender=None, group=None),
            conversation=Conversation(message=message),
            business=None,
            media=MediaContext(media_metadata=None),
            history=HistoryContext(interaction_history=None, notification_summary=None),
            metadata=self.metadata
        )
        
        res = self.engine.analyze(context)
        
        # Verify heuristic intent & urgency detection
        self.assertEqual(res.intent, "scheduling")
        self.assertEqual(res.message_type, "personal")
        self.assertEqual(res.urgency, "low")
        self.assertTrue(res.event_detected)
        self.assertFalse(res.promotion_detected)
        self.assertIn("John", res.entities)

    def test_multimodal_caching_and_merging(self):
        """Verify caching mechanism on visual media and merging rules on multi-format (Text + Image)."""
        media_id = "img_mock_999"
        file_path = "media/images/mock_sale.jpg"
        
        message = Message(
            message_id="msg_multimodal_001",
            user_id="u_test_001",
            conversation_type="business",
            business_id="biz_mock_001",
            created_at="2026-07-30 22:19",
            message_text="URGENT: Flash sale up to 50% off!",
            media_type="image",
            media_id=media_id,
            forwarded_count=0
        )
        
        media_metadata = MediaSummary(
            media_id=media_id,
            media_type="image",
            file_path=file_path
        )
        
        context = UnifiedContext(
            recipient=self.recipient,
            participants=Participants(sender=None, group=None),
            conversation=Conversation(message=message),
            business=None,
            media=MediaContext(media_metadata=media_metadata),
            history=HistoryContext(interaction_history=None, notification_summary=None),
            metadata=self.metadata
        )
        
        # 1. Run engine - should trigger both text and image processors and merge them
        res_first = self.engine.analyze(context)
        
        # Verify text heuristics + image placeholders merged
        self.assertEqual(res_first.urgency, "high")  # High urgency from "URGENT" text
        self.assertTrue(res_first.promotion_detected)  # True from "sale" keyword
        self.assertTrue(res_first.contains_media)  # True from image placeholder
        self.assertIn("Flash sale up to 50% off!", res_first.summary)
        self.assertIn(file_path, res_first.summary)
        
        # 2. Check that the image processor cached the result
        cache_file = os.path.join(self.test_cache_dir, "images", f"{media_id}.json")
        self.assertTrue(os.path.exists(cache_file), "Cache file was not created on cache miss")
        
        # 3. Modify cached file manually to simulate cache hit verification
        with open(cache_file, "r") as f:
            cached_data = json.load(f)
        cached_data["summary"] = "CACHED_IMAGE_RESULT"
        with open(cache_file, "w") as f:
            json.dump(cached_data, f)
            
        # 4. Run engine again - should hit cache for image and merge with new text analysis
        res_second = self.engine.analyze(context)
        self.assertIn("CACHED_IMAGE_RESULT", res_second.summary, "Engine did not use cached image result")

if __name__ == "__main__":
    import json
    unittest.main()
