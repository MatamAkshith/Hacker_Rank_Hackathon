from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult
from code.assessment.models import UrgencyAssessment

class UrgencyCalculator:
    """Calculates message urgency values from message context and understanding."""
    
    def calculate(self, context: UnifiedContext, understanding: UnderstandingResult) -> UrgencyAssessment:
        """Returns default UrgencyAssessment."""
        return UrgencyAssessment()
