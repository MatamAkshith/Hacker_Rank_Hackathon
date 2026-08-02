from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult
from code.assessment.models import MessageAssessment
from code.evidence.models import EvidenceResult
from code.evidence.retriever import CandidateRetriever
from code.evidence.ranking import BaseRanker
from code.evidence.selectors import EvidenceSelector
from code.loader.data_loader import DataLoader


class RetrievalEngine:
    """Orchestrates the retriever, ranker, and selector to produce the final EvidenceResult."""

    def __init__(self, loader: DataLoader):
        """Initialise with a pre-loaded DataLoader shared across the pipeline.

        Args:
            loader: A DataLoader instance with all CSVs loaded via load_all().
        """
        self.retriever = CandidateRetriever(loader)
        self.ranker = BaseRanker()
        self.selector = EvidenceSelector()

    def retrieve(
        self,
        context: UnifiedContext,
        assessment: MessageAssessment,
        understanding: UnderstandingResult,
    ) -> EvidenceResult:
        """Retrieves and ranks historical evidence for the current message.

        Sprint 6.2: Calls CandidateRetriever to gather a raw candidate pool.
        Ranking and selection (Sprint 6.3) are not yet invoked — a safe
        default empty EvidenceResult is returned with a populated summary
        reflecting the candidate pool size.

        Args:
            context: The unified context for the current incoming message.
            assessment: The MessageAssessment from the AssessmentEngine.
            understanding: The UnderstandingResult from the UnderstandingEngine.

        Returns:
            An EvidenceResult with retrieval_status="retrieval_complete" and
            a summary of the candidates gathered, but empty top_evidence.
        """
        candidates = self.retriever.fetch_candidates(context)

        sources_used = set()
        for cand in candidates:
            for src in cand.get("_retrieval_sources", []):
                sources_used.add(src)

        summary = (
            f"Retrieved {len(candidates)} candidate(s) via strategies: "
            f"{', '.join(sorted(sources_used)) if sources_used else 'none'}. "
            "Ranking and selection pending (Sprint 6.3)."
        )

        return EvidenceResult(
            top_evidence=[],
            retrieval_summary=summary,
            retrieval_status="retrieval_complete",
        )
