import os
import sys
import unittest

# Ensure correct python path to import packages from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.test_assessment_trust_risk import create_mock_features
from code.understanding.models import UnderstandingResult
from code.assessment.models import UrgencyAssessment, ImportanceAssessment, RiskAssessment
from code.assessment.personalization import PersonalizationCalculator
from code.assessment.attention import AttentionCalculator

class TestAssessmentPersonalizationAttention(unittest.TestCase):

    def test_highly_personalized_direct_message(self):
        """Case 1: 1-on-1 message with user's name extracted -> personalization_score >= 0.9."""
        features = create_mock_features(relationship_score=0.8)
        understanding = UnderstandingResult(
            summary="Hi John, are you coming?",
            intent="general",
            message_type="personal",
            urgency="low",
            entities=["John"],
            requires_attention=False,
            promotion_detected=False,
            payment_detected=False,
            event_detected=False,
            contains_media=False,
            processing_status="success"
        )
        
        calc = PersonalizationCalculator()
        personalization = calc.calculate(features, understanding)
        
        self.assertGreaterEqual(personalization.personalization_score, 0.9)
        self.assertEqual(personalization.user_relevance, "highly_relevant")
        self.assertTrue(any("name" in r.lower() for r in personalization.reasons))

    def test_mass_broadcast_promotion(self):
        """Case 2: Promo message from a business -> personalization_score <= 0.2."""
        features = create_mock_features()
        understanding = UnderstandingResult(
            summary="Save 20% storewide today!",
            intent="promotional",
            message_type="promotional",
            urgency="low",
            entities=[],
            requires_attention=False,
            promotion_detected=True,
            payment_detected=False,
            event_detected=False,
            contains_media=False,
            processing_status="success"
        )
        
        calc = PersonalizationCalculator()
        personalization = calc.calculate(features, understanding)
        
        self.assertLessEqual(personalization.personalization_score, 0.2)
        self.assertEqual(personalization.user_relevance, "low_relevance")

    def test_critical_alert_priority(self):
        """Case 3: High urgency + high importance + high personalization -> attention_score >= 0.9."""
        features = create_mock_features()
        understanding = UnderstandingResult(
            summary="Urgent security alert",
            intent="transactional",
            message_type="personal",
            urgency="high",
            entities=[],
            requires_attention=True,
            promotion_detected=False,
            payment_detected=False,
            event_detected=False,
            contains_media=False,
            processing_status="success"
        )
        
        urgency = UrgencyAssessment(urgency_score=0.9, time_sensitivity="high")
        importance = ImportanceAssessment(importance_score=0.9, value_category="critical")
        risk = RiskAssessment(risk_score=0.0, spam_probability=0.0, scam_probability=0.0, threat_level="none")
        
        calc = AttentionCalculator()
        attention = calc.calculate(features, understanding, urgency, importance, risk)
        
        self.assertGreaterEqual(attention.attention_score, 0.9)
        self.assertTrue(attention.attention_needed)

    def test_spam_suppression(self):
        """Case 4: High spam probability -> attention_score <= 0.1."""
        features = create_mock_features()
        understanding = UnderstandingResult(
            summary="Win cash promo",
            intent="promotional",
            message_type="promotional",
            urgency="low",
            entities=[],
            requires_attention=False,
            promotion_detected=True,
            payment_detected=False,
            event_detected=False,
            contains_media=False,
            processing_status="success"
        )
        
        urgency = UrgencyAssessment(urgency_score=0.3, time_sensitivity="low")
        importance = ImportanceAssessment(importance_score=0.2, value_category="promotional")
        risk = RiskAssessment(risk_score=0.8, spam_probability=0.8, scam_probability=0.0, threat_level="high")
        
        calc = AttentionCalculator()
        attention = calc.calculate(features, understanding, urgency, importance, risk)
        
        self.assertLessEqual(attention.attention_score, 0.1)
        self.assertFalse(attention.attention_needed)
        self.assertTrue(any("suppressed" in r.lower() for r in attention.reasons))

if __name__ == "__main__":
    unittest.main()
