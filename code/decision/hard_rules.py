"""HardRulesEvaluator: Short-circuits the scoring pipeline when a definitive
routing action can be determined from a single, unambiguous rule (e.g., verified
scam detected → mute unconditionally).

To be fully implemented in Sprint 7.2.
"""

from typing import Optional

from code.features.models import FeatureVector
from code.understanding.models import UnderstandingResult
from code.assessment.models import MessageAssessment
from code.evidence.models import EvidenceResult
from code.decision.models import DecisionResult


class HardRulesEvaluator:
    """Evaluates high-confidence rule triggers that bypass scoring entirely.

    When a hard rule fires, it returns a terminal DecisionResult directly.
    When no rule fires, it returns None and the pipeline continues to scoring.
    """

    def evaluate(
        self,
        features: FeatureVector,
        understanding: UnderstandingResult,
        assessment: MessageAssessment,
        evidence: EvidenceResult,
    ) -> Optional[DecisionResult]:
        """Check all hard rules against the current message.

        To be implemented in Sprint 7.2.

        Args:
            features:     FeatureVector from the Feature Extraction stage.
            understanding: UnderstandingResult from the Understanding Engine.
            assessment:   MessageAssessment from the Assessment Engine.
            evidence:     EvidenceResult from the Retrieval Engine.

        Returns:
            A terminal DecisionResult if a hard rule fires, otherwise None.
        """
        raise NotImplementedError
