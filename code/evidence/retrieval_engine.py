from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult
from code.assessment.models import MessageAssessment
from code.evidence.models import EvidenceResult
from code.evidence.retriever import CandidateRetriever
from code.evidence.ranking import SimilarityRanker
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
        self.ranker    = SimilarityRanker(loader)
        self.selector  = EvidenceSelector()

    def retrieve(
        self,
        context: UnifiedContext,
        assessment: MessageAssessment,
        understanding: UnderstandingResult,
    ) -> EvidenceResult:
        """Retrieves and ranks historical evidence for the current message.

        Sprint 6.3: CandidateRetriever gathers the raw pool; SimilarityRanker
        scores and sorts candidates.  EvidenceSelector (Sprint 6.4) is not yet
        invoked — a safe default empty top_evidence is returned with a summary
        that surfaces the ranked pool size and top score.

        Args:
            context:       The unified context for the current incoming message.
            assessment:    The MessageAssessment from the AssessmentEngine.
            understanding: The UnderstandingResult from the UnderstandingEngine.

        Returns:
            EvidenceResult with retrieval_status="ranking_complete", an empty
            top_evidence list, and a human-readable retrieval_summary.
        """
        # Step 1: Retrieve broad candidate pool
        candidates = self.retriever.fetch_candidates(context)

        # Step 2: Rank candidates by multi-signal similarity
        ranked = self.ranker.rank_candidates(context, understanding, candidates)

        # Summarise ranked pool for inspection (selection pending Sprint 6.4)
        top_score  = ranked[0]["similarity_score"] if ranked else 0.0
        strategies = sorted({
            src
            for c in ranked
            for src in c.get("_retrieval_sources", [])
        })
        summary = (
            f"Ranked {len(ranked)} candidate(s). "
            f"Top similarity_score: {top_score:.3f}. "
            f"Retrieval strategies used: {', '.join(strategies) if strategies else 'none'}. "
            "Evidence selection pending (Sprint 6.4)."
        )

        return EvidenceResult(
            top_evidence=[],
            retrieval_summary=summary,
            retrieval_status="ranking_complete",
        )
