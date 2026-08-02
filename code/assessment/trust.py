from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult
from code.assessment.models import TrustAssessment

class TrustCalculator:
    """Calculates sender and business trust values from message context and understanding."""
    
    def calculate(self, context: UnifiedContext, understanding: UnderstandingResult) -> TrustAssessment:
        """Returns default TrustAssessment."""
        return TrustAssessment()
