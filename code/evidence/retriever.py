from typing import List
from code.context.models import UnifiedContext
from code.evidence.models import EvidenceItem

class BaseRetriever:
    """Fetches candidate historical messages for evidence scoring against the current message context."""
    
    def fetch_candidates(self, context: UnifiedContext) -> List[EvidenceItem]:
        """Fetches a list of candidate historical messages to be ranked and evaluated.
        
        To be implemented in Sprint 6.2 with actual retrieval logic.
        
        Args:
            context: The unified context for the current incoming message.
            
        Returns:
            A list of raw candidate EvidenceItems before ranking.
        """
        raise NotImplementedError
