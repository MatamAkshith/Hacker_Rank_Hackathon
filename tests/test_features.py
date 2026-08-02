import os
import sys
import unittest

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
from code.features.extractor import FeatureExtractor

class TestFeatureRegression(unittest.TestCase):
    
    def setUp(self):
        """Set up a deterministic UnifiedContext for business trust regression testing."""
        metadata = ContextMetadata(
            has_business_context=True,
            has_group_context=False,
            has_historical_evidence=False,
            media_needs_processing=False,
            missing_datasets=[]
        )
        
        message = Message(
            message_id="msg_mock_001",
            user_id="u_mock_001",
            conversation_type="business",
            business_id="business_mock_001",
            created_at="2026-07-30 22:19",
            forwarded_count=0
        )
        
        recipient = Recipient(
            user_id="u_mock_001",
            do_not_disturb_window="23:00-08:00",
            messages_opened_30d=10,
            messages_replied_30d=5,
            notifications_dismissed_30d=2,
            messages_reported_30d=0
        )
        
        business = Business(
            business_id="business_mock_001",
            display_name="Mock Business",
            verified=True,
            official_domain="mock.com",
            domain_used_by_sender="mock.com",
            account_age_days=937,
            user_reports_30d=3
        )
        
        self.mock_business_context = UnifiedContext(
            recipient=recipient,
            participants=Participants(sender=None, group=None),
            conversation=Conversation(message=message),
            business=BusinessContext(profile=business, history=None),
            media=MediaContext(media_metadata=None),
            history=HistoryContext(interaction_history=None, notification_summary=None),
            metadata=metadata
        )

    def test_business_trust_regression(self):
        """Regression test asserting strict outputs of BusinessTrustFeature."""
        extractor = FeatureExtractor()
        feature_vector = extractor.extract(self.mock_business_context)
        result = feature_vector.trust.business_trust
        
        # 1. Assert score matches exactly with expected weights and normalized inputs
        self.assertAlmostEqual(result.score, 0.87, places=5)
        
        # 2. Assert confidence is 1.0 (all 5 core business trust fields populated)
        self.assertEqual(result.confidence, 1.0)
        
        # 3. Assert input_values matches expected dictionary of raw values
        expected_inputs = {
            "verified": True,
            "official_domain": "mock.com",
            "domain_used_by_sender": "mock.com",
            "account_age_days": 937,
            "user_reports_30d": 3
        }
        self.assertEqual(result.input_values, expected_inputs)
        
        # 4. Assert reason matches generated summary string
        self.assertEqual(result.reason, "verified business, domain matched, age: 937 days, 3 reports")
        
        # 5. Assert calculation_trace shows exact mathematical step sequence
        expected_trace = "(1.0 * 0.4) + (1.0 * 0.3) + (1.000 * 0.2) - (0.300 * 0.1)"
        self.assertEqual(result.calculation_trace, expected_trace)

if __name__ == "__main__":
    unittest.main()
