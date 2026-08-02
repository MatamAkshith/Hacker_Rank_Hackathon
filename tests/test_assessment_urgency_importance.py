import os
import sys
import unittest

# Ensure correct python path to import packages from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.test_assessment_trust_risk import create_mock_features
from code.understanding.models import UnderstandingResult
from code.assessment.urgency import UrgencyCalculator
from code.assessment.importance import ImportanceCalculator

class TestAssessmentUrgencyImportance(unittest.TestCase):

    def test_high_urgency_action_request(self):
        """Case 1: Message with urgency='high' and requires_attention=True -> urgency_score >= 0.8."""
        features = create_mock_features()
        understanding = UnderstandingResult(
            summary="Emergency meeting now",
            intent="scheduling",
            message_type="personal",
            urgency="high",
            entities=["now"],
            requires_attention=True,
            promotion_detected=False,
            payment_detected=False,
            event_detected=True,
            contains_media=False,
            processing_status="success"
        )
        
        calc = UrgencyCalculator()
        urgency = calc.calculate(features, understanding)
        
        self.assertGreaterEqual(urgency.urgency_score, 0.8)
        self.assertEqual(urgency.time_sensitivity, "high")
        self.assertTrue(any("attention" in r.lower() for r in urgency.reasons))

    def test_payment_invoice_importance(self):
        """Case 2: payment_detected=True -> payment_probability >= 0.85 and high importance_score."""
        features = create_mock_features(relationship_score=0.4)
        understanding = UnderstandingResult(
            summary="Your monthly electricity bill is due",
            intent="transactional",
            message_type="transactional",
            urgency="medium",
            entities=[],
            requires_attention=True,
            promotion_detected=False,
            payment_detected=True,
            event_detected=False,
            contains_media=False,
            processing_status="success"
        )
        
        calc = ImportanceCalculator()
        importance = calc.calculate(features, understanding)
        
        self.assertGreaterEqual(importance.payment_probability, 0.85)
        self.assertGreaterEqual(importance.importance_score, 0.8)
        self.assertEqual(importance.value_category, "critical")

    def test_calendar_event_importance(self):
        """Case 3: event_detected=True -> event_probability >= 0.8."""
        features = create_mock_features(relationship_score=0.3)
        understanding = UnderstandingResult(
            summary="Dentist appointment tomorrow at 10 AM",
            intent="scheduling",
            message_type="personal",
            urgency="low",
            entities=["tomorrow", "10 AM"],
            requires_attention=False,
            promotion_detected=False,
            payment_detected=False,
            event_detected=True,
            contains_media=False,
            processing_status="success"
        )
        
        calc = ImportanceCalculator()
        importance = calc.calculate(features, understanding)
        
        self.assertGreaterEqual(importance.event_probability, 0.8)
        self.assertGreaterEqual(importance.importance_score, 0.7)
        self.assertEqual(importance.value_category, "informational")

    def test_low_importance_promotion(self):
        """Case 4: promotion_detected=True -> high promotion_probability, low importance_score."""
        features = create_mock_features()
        understanding = UnderstandingResult(
            summary="Flash sale 50% discount",
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
        
        calc = ImportanceCalculator()
        importance = calc.calculate(features, understanding)
        
        self.assertGreaterEqual(importance.promotion_probability, 0.8)
        self.assertLessEqual(importance.importance_score, 0.3)
        self.assertEqual(importance.value_category, "promotional")

if __name__ == "__main__":
    unittest.main()
