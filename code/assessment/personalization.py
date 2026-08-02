from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult
from code.assessment.models import PersonalizationAssessment

class PersonalizationCalculator:
    """Calculates user personalization relevance and affinity from message context and understanding."""
    
    def calculate(self, context: UnifiedContext, understanding: UnderstandingResult) -> PersonalizationAssessment:
        """Returns default PersonalizationAssessment."""
        return PersonalizationAssessment()
