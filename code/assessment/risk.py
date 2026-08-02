from typing import Optional
from code.features.models import FeatureVector
from code.understanding.models import UnderstandingResult
from code.assessment.models import RiskAssessment, TrustAssessment

class RiskCalculator:
    """Calculates security, scam, and spam risk values from message context and understanding."""
    
    def calculate(
        self,
        features: FeatureVector,
        understanding: UnderstandingResult,
        trust_assessment: Optional[TrustAssessment] = None
    ) -> RiskAssessment:
        """Evaluates spam and scam probability and deduces threat level based on features and trust."""
        reasons = []
        trust_score = trust_assessment.trust_score if trust_assessment else 0.0
        
        # 1. Evaluate Spam Probability
        spam_base = 0.0
        if features.risk and features.risk.spam_risk:
            spam_base = features.risk.spam_risk.score
            
        spam_prob = spam_base
        if understanding.promotion_detected:
            spam_prob += 0.4
            reasons.append("Promotional material or marketing content detected")
            
        if features.behaviour and features.behaviour.notification_fatigue:
            fatigue_score = features.behaviour.notification_fatigue.score
            if fatigue_score > 0.5:
                spam_prob += 0.2
                reasons.append("High messaging frequency or notification fatigue signals")
                
        # Scale down spam risk slightly for trusted contacts
        spam_prob *= (1.0 - 0.3 * trust_score)
        spam_prob = max(0.0, min(1.0, spam_prob))
        
        # 2. Evaluate Scam Probability
        scam_base = 0.0
        if features.risk and features.risk.scam_risk:
            scam_base = features.risk.scam_risk.score
            
        scam_prob = scam_base
        if understanding.payment_detected:
            scam_prob += 0.5
            reasons.append("Financial payment or banking transaction keywords detected")
            
        # Scam risk is mitigated by sender trust, but amplified if unknown/low trust
        if trust_score >= 0.8:
            # Trusted sender strongly mitigates scam probability
            scam_prob *= (1.0 - trust_score)
        else:
            if understanding.payment_detected and trust_score < 0.3:
                scam_prob = max(scam_prob, 0.8)
                reasons.append("Critical transaction requested by an unknown or untrusted sender")
                
        scam_prob = max(0.0, min(1.0, scam_prob))
        
        # 3. Overall Risk blending
        risk_score = max(spam_prob, scam_prob)
        
        # 4. Determine Threat level
        if risk_score >= 0.70:
            threat_level = "high"
        elif risk_score >= 0.30:
            threat_level = "medium"
        elif risk_score >= 0.10:
            threat_level = "low"
        else:
            threat_level = "none"
            
        return RiskAssessment(
            risk_score=risk_score,
            spam_probability=spam_prob,
            scam_probability=scam_prob,
            threat_level=threat_level,
            reasons=reasons
        )
