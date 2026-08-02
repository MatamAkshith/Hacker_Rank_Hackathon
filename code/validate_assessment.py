import os
import sys
import unittest

# Ensure correct python path to import packages from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.context.models import (
    Recipient,
    UnifiedContext,
    Message,
    Participants,
    Conversation,
    HistoryContext,
    MediaContext,
    ContextMetadata
)
from code.understanding.models import UnderstandingResult
from code.assessment.models import MessageAssessment
from code.assessment.assessment_engine import AssessmentEngine

class TestMessageAssessmentScaffold(unittest.TestCase):

    def test_assessment_scaffold_returns_defaults(self):
        """Verify that AssessmentEngine initializes and returns MessageAssessment with scaffold defaults."""
        engine = AssessmentEngine()
        
        # Build minimal context
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
            message_text="Hello world",
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
        
        # Build minimal understanding
        understanding = UnderstandingResult(
            summary="Hello world",
            intent="social",
            message_type="personal",
            urgency="low",
            entities=[],
            requires_attention=False,
            promotion_detected=False,
            payment_detected=False,
            event_detected=False,
            contains_media=False,
            processing_status="success"
        )
        from tests.test_assessment_trust_risk import create_mock_features
        assessment = engine.evaluate(context, understanding, features=create_mock_features())
        
        # Assert base data contract types and status
        self.assertIsInstance(assessment, MessageAssessment)
        self.assertEqual(assessment.status, "assessment_complete")
        
        # Assert default values inside component sub-assessments
        self.assertEqual(assessment.trust.trust_score, 0.0)
        self.assertFalse(assessment.trust.is_verified)
        
        self.assertEqual(assessment.risk.risk_score, 0.0)
        self.assertEqual(assessment.risk.threat_level, "none")
        
        self.assertEqual(assessment.urgency.urgency_score, 0.1)
        self.assertEqual(assessment.urgency.time_sensitivity, "low")
        
        self.assertEqual(assessment.importance.importance_score, 0.25)
        self.assertEqual(assessment.importance.value_category, "neutral")
        
        self.assertEqual(assessment.personalization.personalization_score, 0.8)
        self.assertEqual(assessment.personalization.user_relevance, "highly_relevant")
        
        self.assertFalse(assessment.attention.attention_needed)
        self.assertEqual(assessment.attention.attention_score, 0.175)
        self.assertEqual(assessment.attention.interruption_cost, 0.2)
        
        self.assertAlmostEqual(assessment.overall_score, 0.335)
        self.assertEqual(assessment.overall_confidence, 0.6)

if __name__ == "__main__":
    unittest.main()
