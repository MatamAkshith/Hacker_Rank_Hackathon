import os
import sys
import unittest

# Ensure correct python path to import packages from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.features.models import (
    FeatureVector, TrustFeatures, UrgencyFeatures, RiskFeatures, BehaviourFeatures,
    SenderTrustFeature, BusinessTrustFeature, RelationshipStrengthFeature,
    UrgencyFeature, PromotionFeature, SpamRiskFeature, ScamRiskFeature, ForwardRiskFeature,
    HistoricalEngagementFeature, NotificationFatigueFeature, QuietHoursFeature
)
from code.understanding.models import UnderstandingResult
from code.assessment.trust import TrustCalculator
from code.assessment.risk import RiskCalculator

def make_base_feature(score=0.0):
    return {
        "score": score,
        "confidence": 1.0,
        "input_values": {},
        "reason": "mock",
        "calculation_trace": "mock"
    }

def create_mock_features(
    business_trust_score=0.0,
    verified=False,
    relationship_score=0.0,
    engagement_score=0.0,
    spam_risk_score=0.0,
    scam_risk_score=0.0,
    fatigue_score=0.0
):
    sender_trust = SenderTrustFeature(messages_read=0, replies_sent=0, is_group=False, **make_base_feature())
    
    business_trust = BusinessTrustFeature(
        verified=verified,
        domain_match=False,
        account_age_days=0,
        user_reports_30d=0,
        **make_base_feature(score=business_trust_score)
    )
    
    relationship_strength = RelationshipStrengthFeature(
        opened_count=0,
        replied_count=0,
        is_admin=False,
        **make_base_feature(score=relationship_score)
    )
    
    urgency = UrgencyFeature(is_urgent=False, matched_keywords=[], **make_base_feature())
    promotion = PromotionFeature(matched_promo_keywords=[], is_retail_category=False, **make_base_feature())
    
    spam_risk = SpamRiskFeature(user_reported_30d=0, forwarded_count=0, **make_base_feature(score=spam_risk_score))
    scam_risk = ScamRiskFeature(matched_scam_keywords=[], verified_business=verified, **make_base_feature(score=scam_risk_score))
    forward_risk = ForwardRiskFeature(is_high_risk=False, forwarded_count=0, **make_base_feature())
    
    historical_engagement = HistoricalEngagementFeature(
        opened_30d=0,
        dismissed_30d=0,
        replied_30d=0,
        **make_base_feature(score=engagement_score)
    )
    
    notification_fatigue = NotificationFatigueFeature(
        sent_last_3d=0,
        dismissed_last_3d=0,
        **make_base_feature(score=fatigue_score)
    )
    
    quiet_hours = QuietHoursFeature(is_quiet_hours=False, message_time="12:00", **make_base_feature())
    
    return FeatureVector(
        trust=TrustFeatures(
            sender_trust=sender_trust,
            business_trust=business_trust,
            relationship_strength=relationship_strength
        ),
        urgency=UrgencyFeatures(
            urgency=urgency,
            promotion=promotion
        ),
        risk=RiskFeatures(
            spam_risk=spam_risk,
            scam_risk=scam_risk,
            forward_risk=forward_risk
        ),
        behaviour=BehaviourFeatures(
            historical_engagement=historical_engagement,
            notification_fatigue=notification_fatigue,
            quiet_hours=quiet_hours
        )
    )

class TestAssessmentTrustRisk(unittest.TestCase):

    def test_verified_business_reputation(self):
        """Case 1: High business trust / verified Contact -> high trust score and low risk score."""
        features = create_mock_features(business_trust_score=0.8, verified=True)
        understanding = UnderstandingResult(
            summary="Receipt details",
            intent="transactional",
            message_type="transactional",
            urgency="low",
            entities=[],
            requires_attention=False,
            promotion_detected=False,
            payment_detected=False,
            event_detected=False,
            contains_media=False,
            processing_status="success"
        )
        
        trust_calc = TrustCalculator()
        risk_calc = RiskCalculator()
        
        trust = trust_calc.calculate(features, understanding)
        risk = risk_calc.calculate(features, understanding, trust)
        
        self.assertTrue(trust.is_verified)
        self.assertGreaterEqual(trust.trust_score, 0.85)
        self.assertLess(risk.risk_score, 0.2)

    def test_obvious_payment_scam(self):
        """Case 2: Unknown sender + payment_detected -> high scam probability and high overall risk."""
        features = create_mock_features(business_trust_score=0.0, relationship_score=0.0, scam_risk_score=0.2)
        understanding = UnderstandingResult(
            summary="Send money immediately",
            intent="transactional",
            message_type="transactional",
            urgency="high",
            entities=[],
            requires_attention=True,
            promotion_detected=False,
            payment_detected=True,
            event_detected=False,
            contains_media=False,
            processing_status="success"
        )
        
        trust_calc = TrustCalculator()
        risk_calc = RiskCalculator()
        
        trust = trust_calc.calculate(features, understanding)
        risk = risk_calc.calculate(features, understanding, trust)
        
        self.assertLess(trust.trust_score, 0.3)
        self.assertGreaterEqual(risk.scam_probability, 0.8)
        self.assertGreaterEqual(risk.risk_score, 0.8)

    def test_spammy_promotion(self):
        """Case 3: promotion_detected + notification fatigue -> high spam probability."""
        features = create_mock_features(spam_risk_score=0.3, fatigue_score=0.6)
        understanding = UnderstandingResult(
            summary="Flash sale offer",
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
        
        trust_calc = TrustCalculator()
        risk_calc = RiskCalculator()
        
        trust = trust_calc.calculate(features, understanding)
        risk = risk_calc.calculate(features, understanding, trust)
        
        self.assertGreaterEqual(risk.spam_probability, 0.7)
        self.assertEqual(risk.risk_score, risk.spam_probability)

if __name__ == "__main__":
    unittest.main()
