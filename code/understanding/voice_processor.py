from typing import Optional
from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult

class VoiceProcessor:
    """Processor to analyze audio/voice attachments (ASR/transcription)."""
    
    def process(self, context: UnifiedContext) -> Optional[UnderstandingResult]:
        """Extracts semantic understanding from voice context."""
        pass
