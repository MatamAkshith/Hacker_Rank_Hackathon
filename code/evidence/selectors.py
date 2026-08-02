from typing import List
from code.evidence.models import EvidenceItem

class EvidenceSelector:
    """Selects the top-K most relevant evidence items from a ranked candidate list."""
    
    def select_top(self, ranked_candidates: List[EvidenceItem], top_k: int = 5) -> List[EvidenceItem]:
        """Selects the top-K evidence items from the ranked list for use in the routing decision.
        
        To be implemented in Sprint 6.2 with actual selection logic.
        
        Args:
            ranked_candidates: Ranked list of EvidenceItems from the ranker.
            top_k: Maximum number of evidence items to return. Defaults to 5.
            
        Returns:
            A filtered list containing at most top_k EvidenceItems.
        """
        raise NotImplementedError
