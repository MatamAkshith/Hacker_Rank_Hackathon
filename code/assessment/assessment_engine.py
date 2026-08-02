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
        
        # Skeletons for other calculators accepting context/understanding for now
        urgency = self.urgency_calculator.calculate(context, understanding)
        importance = self.importance_calculator.calculate(context, understanding)
        personalization = self.personalization_calculator.calculate(context, understanding)
        attention = self.attention_calculator.calculate(context, understanding)
        
        # Aggregate overall score (higher is safer/better)
        overall_score = trust.trust_score - risk.risk_score
        
        return MessageAssessment(
            trust=trust,
            risk=risk,
            urgency=urgency,
            importance=importance,
            personalization=personalization,
            attention=attention,
            overall_score=overall_score,
            status="evaluated"
        )
