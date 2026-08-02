from typing import List, Optional
from code.features.models import FeatureVector
from code.understanding.models import UnderstandingResult
from code.assessment.models import AttentionAssessment, UrgencyAssessment, ImportanceAssessment, RiskAssessment

class AttentionCalculator:
    """Calculates user attention required and interruption costs from message context and assessment details."""
    
    def calculate(
        self,
        features: FeatureVector,
        understanding: UnderstandingResult,
        urgency: UrgencyAssessment,
        importance: ImportanceAssessment,
        risk: RiskAssessment
    ) -> AttentionAssessment:
        """Synthesizes attention score and interruption costs based on urgency, importance, and security risks."""
        reasons = []
        
        # 1. Base attention score calculated as a blend of urgency and importance
        attention_score = (urgency.urgency_score * 0.5) + (importance.importance_score * 0.5)
        reasons.append(f"Base attention score blended from urgency ({urgency.urgency_score:.2f}) and importance ({importance.importance_score:.2f})")
        
        # 2. Risk evaluation overrides (Scam alert vs Spam suppression)
        attention_needed = False
        if risk.scam_probability >= 0.7:
            attention_score = max(attention_score, 0.95)
            attention_needed = True
            reasons.append("Critical alert: Potential scam/security threat requires immediate review")
        elif risk.spam_probability >= 0.7:
            attention_score = min(attention_score, 0.1)
            attention_needed = False
            reasons.append("Suppressed: High spam probability promotional content")
            
        # 3. Interruption cost evaluation based on quiet hours and notification fatigue
        interruption_cost = 0.2
        if features.behaviour and features.behaviour.quiet_hours:
            if getattr(features.behaviour.quiet_hours, "is_quiet_hours", False):
                interruption_cost += 0.6
                reasons.append("Elevated interruption cost: Recipient is currently in quiet/DND hours")
                
        if features.behaviour and features.behaviour.notification_fatigue:
            fatigue_score = features.behaviour.notification_fatigue.score
            if fatigue_score > 0.6:
                interruption_cost += 0.2
                reasons.append("Elevated interruption cost: High recipient notification fatigue detected")
                
        interruption_cost = max(0.0, min(1.0, interruption_cost))
        
        # 4. Decide attention_needed flag
        # Messages with attention_score >= 0.7 require attention, unless suppressed by spam
        if not (risk.spam_probability >= 0.7):
            if attention_score >= 0.70:
                attention_needed = True
                
        attention_score = max(0.0, min(1.0, attention_score))
        
        return AttentionAssessment(
            attention_score=attention_score,
            attention_needed=attention_needed,
            interruption_cost=interruption_cost,
            reasons=reasons
        )
