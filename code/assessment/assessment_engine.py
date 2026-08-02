from typing import Optional
from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult
from code.features.models import FeatureVector
from code.features.extractor import FeatureExtractor
from code.assessment.models import MessageAssessment
from code.assessment.trust import TrustCalculator
from code.assessment.risk import RiskCalculator
from code.assessment.urgency import UrgencyCalculator
from code.assessment.importance import ImportanceCalculator
from code.assessment.personalization import PersonalizationCalculator
from code.assessment.attention import AttentionCalculator

class AssessmentEngine:
    """Orchestrates different calculators to evaluate incoming messages across multiple dimensions."""
    
    def __init__(self):
        self.trust_calculator = TrustCalculator()
        self.risk_calculator = RiskCalculator()
        self.urgency_calculator = UrgencyCalculator()
        self.importance_calculator = ImportanceCalculator()
        self.personalization_calculator = PersonalizationCalculator()
        self.attention_calculator = AttentionCalculator()

    def evaluate(
        self,
        context: UnifiedContext,
        understanding: UnderstandingResult,
        features: Optional[FeatureVector] = None
    ) -> MessageAssessment:
        """Evaluates trust, risk, urgency, importance, personalization, and attention dimensions."""
        if features is None:
            features = FeatureExtractor().extract(context)
            
        trust = self.trust_calculator.calculate(features, understanding)
        risk = self.risk_calculator.calculate(features, understanding, trust)
        
        # Calculators accepting features and understanding
        urgency = self.urgency_calculator.calculate(features, understanding)
        importance = self.importance_calculator.calculate(features, understanding)
        personalization = self.personalization_calculator.calculate(features, understanding)
        attention = self.attention_calculator.calculate(
            features, understanding, urgency, importance, risk
        )
        
        # Calculate overall confidence based on data completeness and processing status
        has_history = False
        if features.trust and features.trust.sender_trust:
            has_history = features.trust.sender_trust.score > 0.0 or features.trust.sender_trust.messages_read > 0
            
        status = getattr(understanding, "processing_status", "") or ""
        
        if status == "placeholder_applied":
            overall_confidence = 0.75
        elif not has_history:
            overall_confidence = 0.60
        else:
            overall_confidence = 0.95
            
        # Aggregate overall score
        overall_score = (trust.trust_score * 0.2) + (importance.importance_score * 0.3) + \
                        (urgency.urgency_score * 0.2) + (personalization.personalization_score * 0.3) - risk.risk_score
                        
        return MessageAssessment(
            trust=trust,
            risk=risk,
            urgency=urgency,
            importance=importance,
            personalization=personalization,
            attention=attention,
            overall_score=overall_score,
            overall_confidence=overall_confidence,
            status="assessment_complete"
        )
