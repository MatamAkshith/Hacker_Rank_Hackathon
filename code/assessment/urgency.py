from typing import List
from code.features.models import FeatureVector
from code.understanding.models import UnderstandingResult
from code.assessment.models import UrgencyAssessment

class UrgencyCalculator:
    """Calculates message urgency values from message context and understanding."""
    
    def calculate(self, features: FeatureVector, understanding: UnderstandingResult) -> UrgencyAssessment:
        """Evaluates message urgency score and time sensitivity category based on semantic signals."""
        reasons = []
        
        # 1. Base score from understanding.urgency
        base_urgency = (understanding.urgency or "low").lower()
        if base_urgency == "high":
            urgency_score = 0.8
            reasons.append("High semantic urgency explicitly identified in message content")
        elif base_urgency == "medium":
            urgency_score = 0.5
            reasons.append("Medium semantic urgency identified in message content")
        else:
            urgency_score = 0.1
            
        # 2. Boost if requires_attention is True
        if understanding.requires_attention:
            urgency_score += 0.15
            reasons.append("Contains call-to-action requiring prompt recipient attention")
            
        # 3. Check for highly time-sensitive terms/entities
        has_urgent_entity = False
        for ent in getattr(understanding, "entities", []) or []:
            ent_lower = ent.lower()
            if any(term in ent_lower for term in ["asap", "immediately", "urgent", "now", "deadline", "today", "tomorrow"]):
                has_urgent_entity = True
                
        if has_urgent_entity:
            urgency_score += 0.1
            reasons.append("Explicit immediate or highly time-sensitive entities detected")
            
        # 4. Limit range
        urgency_score = max(0.0, min(1.0, urgency_score))
        
        # Determine time sensitivity category based on final blended score
        if urgency_score >= 0.7:
            time_sensitivity = "high"
        elif urgency_score >= 0.3:
            time_sensitivity = "medium"
        else:
            time_sensitivity = "low"
            
        return UrgencyAssessment(
            urgency_score=urgency_score,
            time_sensitivity=time_sensitivity,
            reasons=reasons
        )
