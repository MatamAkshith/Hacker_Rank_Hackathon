"""BaseScorer: Computes the initial notify / digest / mute scores from
all available pipeline signals before contextual adjustments are applied.

To be fully implemented in Sprint 7.2.
"""

from code.features.models import FeatureVector
from code.understanding.models import UnderstandingResult
from code.assessment.models import MessageAssessment
from code.evidence.models import EvidenceResult
from code.decision.models import DecisionScores


class BaseScorer:
    """Calculates raw base scores for each routing action from pipeline signals."""

    def calculate_base_scores(
        self,
        features: FeatureVector,
        understanding: UnderstandingResult,
        assessment: MessageAssessment,
        evidence: EvidenceResult,
    ) -> DecisionScores:
        """Derive the initial notify / digest / mute weight vector.

        To be implemented in Sprint 7.2.

        Args:
            features:     FeatureVector from the Feature Extraction stage.
            understanding: UnderstandingResult from the Understanding Engine.
            assessment:   MessageAssessment from the Assessment Engine.
            evidence:     EvidenceResult from the Retrieval Engine.

        Returns:
            A DecisionScores object with the raw score for each action.
        """
        raise NotImplementedError
