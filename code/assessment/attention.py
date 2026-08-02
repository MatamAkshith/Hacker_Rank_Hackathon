from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult
from code.assessment.models import AttentionAssessment

class AttentionCalculator:
    """Calculates user attention required and interruption costs from message context and understanding."""
    
    def calculate(self, context: UnifiedContext, understanding: UnderstandingResult) -> AttentionAssessment:
        """Returns default AttentionAssessment."""
        return AttentionAssessment()
