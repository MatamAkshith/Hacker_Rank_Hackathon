from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult
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

    def evaluate(self, context: UnifiedContext, understanding: UnderstandingResult) -> MessageAssessment:
        """Evaluates trust, risk, urgency, importance, personalization, and attention dimensions."""
        trust = self.trust_calculator.calculate(context, understanding)
        risk = self.risk_calculator.calculate(context, understanding)
        urgency = self.urgency_calculator.calculate(context, understanding)
        importance = self.importance_calculator.calculate(context, understanding)
        personalization = self.personalization_calculator.calculate(context, understanding)
        attention = self.attention_calculator.calculate(context, understanding)
        
        return MessageAssessment(
            trust=trust,
            risk=risk,
            urgency=urgency,
            importance=importance,
            personalization=personalization,
            attention=attention,
            overall_score=0.0,
            status="scaffold_complete"
        )
