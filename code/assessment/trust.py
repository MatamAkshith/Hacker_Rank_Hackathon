from typing import Optional
from code.features.models import FeatureVector
from code.understanding.models import UnderstandingResult
from code.assessment.models import TrustAssessment

class TrustCalculator:
    """Calculates sender and business trust values from message context and understanding."""
    
    def calculate(self, features: FeatureVector, understanding: UnderstandingResult) -> TrustAssessment:
        """Evaluates sender trust score and verification status based on feature vector signals."""
        reasons = []
        is_verified = False
        
        # 1. Evaluate business verification and domain match
        biz_score = 0.0
        if features.trust and features.trust.business_trust:
            biz_score = features.trust.business_trust.score
            if getattr(features.trust.business_trust, "verified", False):
                is_verified = True
                reasons.append("Sender is a verified business")
            elif getattr(features.trust.business_trust, "domain_match", False):
                reasons.append("Sender matches verified business email domain")
                
        # 2. Evaluate sender relationship strength
        rel_score = 0.0
        if features.trust and features.trust.relationship_strength:
            rel_score = features.trust.relationship_strength.score
            if rel_score > 0.5:
                reasons.append("Strong historical relationship and interaction history")
            elif rel_score > 0.0:
                reasons.append("Sender has active interaction history")
                
        # 3. Evaluate historical user engagement
        eng_score = 0.0
        if features.behaviour and features.behaviour.historical_engagement:
            eng_score = features.behaviour.historical_engagement.score
            if eng_score > 0.5:
                reasons.append("User consistently engages with and replies to this sender")

        # 4. Calculate weighted trust score
        trust_score = (biz_score * 0.4) + (rel_score * 0.4) + (eng_score * 0.2)
        
        # Boost trust score if verified business and no high user report count
        if is_verified:
            reports = getattr(features.trust.business_trust, "user_reports_30d", 0) or 0
            if reports < 3:
                trust_score = max(trust_score, 0.85)
                
        if trust_score == 0.0:
            reasons.append("Unknown sender with no historical interaction records")
            
        trust_score = max(0.0, min(1.0, trust_score))
        
        return TrustAssessment(
            trust_score=trust_score,
            is_verified=is_verified,
            reasons=reasons
        )
