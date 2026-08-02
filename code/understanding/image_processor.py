from typing import Optional
from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult

class ImageProcessor:
    """Processor to analyze image attachments (OCR and visual description)."""
    
    def process(self, context: UnifiedContext) -> Optional[UnderstandingResult]:
        """Extracts semantic understanding from image context."""
        pass
