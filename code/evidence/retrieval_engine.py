from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult
from code.assessment.models import MessageAssessment
from code.evidence.models import EvidenceItem, EvidenceResult
from code.evidence.retriever import CandidateRetriever
from code.evidence.ranking import SimilarityRanker
from code.evidence.selectors import EvidenceSelector
from code.loader.data_loader import DataLoader

from typing import List


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
        """Execute the full evidence retrieval pipeline for the current message.

        Pipeline:
          1. CandidateRetriever  → broad structural pool
          2. SimilarityRanker    → multi-signal scored & sorted pool
          3. EvidenceSelector    → top-3 EvidenceItems with human-readable reasons

        Graceful empty-state:
          If the candidate pool is empty (new user, no history), returns a valid
          EvidenceResult with retrieval_status="no_history".

        Args:
            context:       The unified context for the current incoming message.
            assessment:    The MessageAssessment from the AssessmentEngine.
            understanding: The UnderstandingResult from the UnderstandingEngine.

        Returns:
            EvidenceResult with retrieval_status="success" (or "no_history"),
            top_evidence list of at most 3 EvidenceItems, and a human-readable
            retrieval_summary.
        """
        # Step 1: Gather broad candidate pool
        candidates = self.retriever.fetch_candidates(context)

        # Graceful no-history path
        if not candidates:
            return EvidenceResult(
                top_evidence=[],
                retrieval_summary="No historical messages found for this user.",
                retrieval_status="no_history",
            )

        # Step 2: Score and rank by multi-signal similarity
        ranked = self.ranker.rank_candidates(context, understanding, candidates)

        # Step 3: Select top-3 and map to EvidenceItems
        top_evidence: List[EvidenceItem] = self.selector.select_top(ranked, k=3)

        # Build a human-readable summary
        n = len(top_evidence)
        if n == 0:
            summary = (
                f"Evaluated {len(ranked)} historical candidate(s); "
                "none met the minimum relevance threshold."
            )
            status = "no_history"
        else:
            top_score = top_evidence[0].similarity_score
            strategies = sorted({
                src
                for c in ranked[:n]
                for src in c.get("_retrieval_sources", [])
            })
            strength = (
                "strong" if top_score >= 0.60
                else "moderate" if top_score >= 0.35
                else "weak"
            )
            summary = (
                f"Found {n} {strength} historical match{'es' if n > 1 else ''} "
                f"(top score: {top_score:.3f}). "
                f"Retrieval strategies: {', '.join(strategies)}."
            )
            status = "success"

        return EvidenceResult(
            top_evidence=top_evidence,
            retrieval_summary=summary,
            retrieval_status=status,
        )
