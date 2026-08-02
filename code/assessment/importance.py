from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult
from code.assessment.models import ImportanceAssessment

class ImportanceCalculator:
    """Calculates message importance and value category from message context and understanding."""
    
    def calculate(self, context: UnifiedContext, understanding: UnderstandingResult) -> ImportanceAssessment:
        """Returns default ImportanceAssessment."""
        return ImportanceAssessment()
