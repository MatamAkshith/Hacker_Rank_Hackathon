from typing import List
from code.evidence.models import EvidenceItem
from code.assessment.models import MessageAssessment
from code.understanding.models import UnderstandingResult

class BaseRanker:
    """Scores and ranks candidate evidence items by relevance to the current message assessment."""
    
    def rank_candidates(
        self,
        candidates: List[EvidenceItem],
        assessment: MessageAssessment,
        understanding: UnderstandingResult
    ) -> List[EvidenceItem]:
        """Ranks evidence candidates by computing similarity and relevance scores.
        
        To be implemented in Sprint 6.2 with actual ranking logic.
        
        Args:
            candidates: Raw candidate EvidenceItems returned by the retriever.
            assessment: The MessageAssessment for the current message.
            understanding: The UnderstandingResult for the current message.
            
        Returns:
            A reordered/scored list of EvidenceItems sorted by relevance.
        """
        raise NotImplementedError
