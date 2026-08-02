import os
import sys
import unittest

# Ensure correct python path to import packages from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.loader.data_loader import DataLoader
from code.context.context_builder import ContextBuilder
from code.features.extractor import FeatureExtractor
from code.understanding.understanding_engine import UnderstandingEngine
from code.assessment.assessment_engine import AssessmentEngine
from code.assessment.models import (
    MessageAssessment,
    TrustAssessment,
    RiskAssessment,
    UrgencyAssessment,
    ImportanceAssessment,
    PersonalizationAssessment,
    AttentionAssessment
)

class TestAssessmentIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Load dataset and process first 10 messages through the entire pipeline
        cls.loader = DataLoader()
        cls.loader.load_all("dataset")
        cls.context_builder = ContextBuilder(cls.loader)
        cls.feature_extractor = FeatureExtractor()
        cls.understanding_engine = UnderstandingEngine()
        cls.assessment_engine = AssessmentEngine()
        
        cls.messages_sample = cls.loader._messages.head(10)
        cls.assessments = []
        
        for idx, row in cls.messages_sample.iterrows():
            msg_id = row["message_id"]
            context = cls.context_builder.build_context(msg_id)
            features = cls.feature_extractor.extract(context)
            understanding = cls.understanding_engine.analyze(context)
            assessment = cls.assessment_engine.evaluate(context, understanding, features)
            cls.assessments.append((msg_id, assessment))

    def test_end_to_end_assessment_integrity(self):
        """Verify the full pipeline output matches structure, type, and value constraints."""
        for msg_id, assessment in self.assessments:
            with self.subTest(msg_id=msg_id):
                # 1. Assert root assessment container properties
                self.assertIsInstance(assessment, MessageAssessment)
                self.assertEqual(assessment.status, "assessment_complete")
                self.assertTrue(0.0 <= assessment.overall_confidence <= 1.0)
                self.assertIsInstance(assessment.overall_confidence, float)
                self.assertTrue(-1.0 <= assessment.overall_score <= 1.0)
                self.assertIsInstance(assessment.overall_score, float)
                
                # 2. Assert sub-assessment presence and types
                self.assertIsInstance(assessment.trust, TrustAssessment)
                self.assertIsInstance(assessment.risk, RiskAssessment)
                self.assertIsInstance(assessment.urgency, UrgencyAssessment)
                self.assertIsInstance(assessment.importance, ImportanceAssessment)
                self.assertIsInstance(assessment.personalization, PersonalizationAssessment)
                self.assertIsInstance(assessment.attention, AttentionAssessment)
                
                # 3. Assert scores/probability values and types
                # Trust
                self.assertIsInstance(assessment.trust.trust_score, float)
                self.assertTrue(0.0 <= assessment.trust.trust_score <= 1.0)
                self.assertIsInstance(assessment.trust.is_verified, bool)
                
                # Risk
                self.assertIsInstance(assessment.risk.risk_score, float)
                self.assertTrue(0.0 <= assessment.risk.risk_score <= 1.0)
                self.assertIsInstance(assessment.risk.spam_probability, float)
                self.assertTrue(0.0 <= assessment.risk.spam_probability <= 1.0)
                self.assertIsInstance(assessment.risk.scam_probability, float)
                self.assertTrue(0.0 <= assessment.risk.scam_probability <= 1.0)
                self.assertIn(assessment.risk.threat_level, ["high", "medium", "low", "none"])
                
                # Urgency
                self.assertIsInstance(assessment.urgency.urgency_score, float)
                self.assertTrue(0.0 <= assessment.urgency.urgency_score <= 1.0)
                self.assertIn(assessment.urgency.time_sensitivity, ["high", "medium", "low"])
                
                # Importance
                self.assertIsInstance(assessment.importance.importance_score, float)
                self.assertTrue(0.0 <= assessment.importance.importance_score <= 1.0)
                self.assertIsInstance(assessment.importance.payment_probability, float)
                self.assertTrue(0.0 <= assessment.importance.payment_probability <= 1.0)
                self.assertIsInstance(assessment.importance.event_probability, float)
                self.assertTrue(0.0 <= assessment.importance.event_probability <= 1.0)
                self.assertIsInstance(assessment.importance.promotion_probability, float)
                self.assertTrue(0.0 <= assessment.importance.promotion_probability <= 1.0)
                self.assertIn(assessment.importance.value_category, ["critical", "informational", "promotional", "neutral"])
                
                # Personalization
                self.assertIsInstance(assessment.personalization.personalization_score, float)
                self.assertTrue(0.0 <= assessment.personalization.personalization_score <= 1.0)
                self.assertIsInstance(assessment.personalization.affinity_score, float)
                self.assertTrue(0.0 <= assessment.personalization.affinity_score <= 1.0)
                self.assertIn(assessment.personalization.user_relevance, ["highly_relevant", "general", "low_relevance"])
                
                # Attention
                self.assertIsInstance(assessment.attention.attention_score, float)
                self.assertTrue(0.0 <= assessment.attention.attention_score <= 1.0)
                self.assertIsInstance(assessment.attention.attention_needed, bool)
                self.assertIsInstance(assessment.attention.interruption_cost, float)
                self.assertTrue(0.0 <= assessment.attention.interruption_cost <= 1.0)
                
                # 4. Assert explainability reasons are present and contain text explanations
                for model_part in [
                    assessment.trust,
                    assessment.risk,
                    assessment.urgency,
                    assessment.importance,
                    assessment.personalization,
                    assessment.attention
                ]:
                    self.assertIsInstance(model_part.reasons, list)
                    self.assertGreaterEqual(len(model_part.reasons), 1, f"Failed explainability check on {model_part.__class__.__name__} for msg_id: {msg_id}")
                    for reason in model_part.reasons:
                        self.assertIsInstance(reason, str)
                        self.assertTrue(len(reason) > 0)

if __name__ == "__main__":
    unittest.main()
