from typing import List
from code.features.models import FeatureVector
from code.understanding.models import UnderstandingResult
from code.assessment.models import PersonalizationAssessment

class PersonalizationCalculator:
    """Calculates user personalization relevance and affinity from message context and understanding."""
    
    def calculate(self, features: FeatureVector, understanding: UnderstandingResult) -> PersonalizationAssessment:
        """Evaluates message personalization targeting score and category based on sender and content targeting signals."""
        reasons = []
        
        # 1. Base personalization score based on conversation format and promo flags
        is_group = False
        if features.trust and features.trust.sender_trust:
            is_group = getattr(features.trust.sender_trust, "is_group", False)
            
        is_promo = getattr(understanding, "promotion_detected", False)
        
        if is_group:
            personalization_score = 0.4
            reasons.append("Group chat message with lower direct individual targeting")
        elif is_promo:
            personalization_score = 0.15
            reasons.append("Mass broadcast marketing or promotional message")
        else:
            personalization_score = 0.8
            reasons.append("Direct 1-on-1 message channel")
            
        # 2. Apply interaction affinity boost
        rel_score = 0.0
        if features.trust and features.trust.relationship_strength:
            rel_score = features.trust.relationship_strength.score
            if rel_score > 0.6:
                personalization_score += 0.1
                reasons.append("High sender interaction affinity and relationship strength")
                
        # 3. Check for specific recipient names or direct addressing
        has_personal_entity = False
        for ent in getattr(understanding, "entities", []) or []:
            # Capitalized words in non-promo direct context usually imply recipient targeting
            if ent.istitle() and not is_promo:
                has_personal_entity = True
                
        if has_personal_entity:
            personalization_score += 0.15
            reasons.append("Direct name address detected in content")
            
        # 4. Limit range
        personalization_score = max(0.0, min(1.0, personalization_score))
        
        # Classify user relevance category
        if personalization_score >= 0.75:
            user_relevance = "highly_relevant"
        elif personalization_score >= 0.35:
            user_relevance = "general"
        else:
            user_relevance = "low_relevance"
            
        return PersonalizationAssessment(
            personalization_score=personalization_score,
            affinity_score=rel_score,
            user_relevance=user_relevance,
            reasons=reasons
        )
