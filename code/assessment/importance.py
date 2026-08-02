from typing import List
from code.features.models import FeatureVector
from code.understanding.models import UnderstandingResult
from code.assessment.models import ImportanceAssessment

class ImportanceCalculator:
    """Calculates message importance and category probabilities from message context and understanding."""
    
    def calculate(self, features: FeatureVector, understanding: UnderstandingResult) -> ImportanceAssessment:
        """Evaluates overall message importance score and category classification based on semantic content and relationships."""
        reasons = []
        
        # 1. Evaluate primary category probabilities
        payment_prob = 1.0 if getattr(understanding, "payment_detected", False) else 0.0
        event_prob = 1.0 if getattr(understanding, "event_detected", False) else 0.0
        promo_prob = 1.0 if getattr(understanding, "promotion_detected", False) else 0.0
        
        if payment_prob > 0:
            reasons.append("Billing invoice or transaction payment detected")
        if event_prob > 0:
            reasons.append("Calendar event, meeting, or scheduling details detected")
        if promo_prob > 0:
            reasons.append("Broadcast marketing material or promo deal detected")
            
        # 2. Base score from category signals (critical transactions > schedules > broadcast promos)
        importance_score = max(payment_prob * 0.90, event_prob * 0.75, promo_prob * 0.15)
        
        # Default neutral baseline if no direct category flags are present
        if importance_score == 0.0:
            importance_score = 0.25
            
        # 3. Apply relationship-strength boost to non-promotional messages
        if features.trust and features.trust.relationship_strength:
            rel_score = features.trust.relationship_strength.score
            if rel_score > 0.0 and promo_prob == 0.0:
                importance_score += rel_score * 0.2
                reasons.append("Sender has active relationship history")
                
        # 4. Limit range
        importance_score = max(0.0, min(1.0, importance_score))
        
        # Determine value category based on primary signal
        if payment_prob >= 0.8:
            value_category = "critical"
        elif event_prob >= 0.8:
            value_category = "informational"
        elif promo_prob >= 0.8:
            value_category = "promotional"
        else:
            value_category = "neutral"
            
        return ImportanceAssessment(
            importance_score=importance_score,
            value_category=value_category,
            payment_probability=payment_prob,
            event_probability=event_prob,
            promotion_probability=promo_prob,
            reasons=reasons
        )
