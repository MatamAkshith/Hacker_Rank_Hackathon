"""BaseScorer: Computes the initial notify / digest / mute scores from
all available pipeline signals before contextual adjustments are applied.
"""

from typing import Optional
from code.features.models import FeatureVector
from code.understanding.models import UnderstandingResult
from code.assessment.models import MessageAssessment
from code.evidence.models import EvidenceResult
from code.decision.models import DecisionScores


class BaseScorer:
    """Calculates raw base scores for each routing action from pipeline signals."""

    def calculate_base_scores(
        self,
        assessment: MessageAssessment,
        features: Optional[FeatureVector] = None,
        understanding: Optional[UnderstandingResult] = None,
        evidence: Optional[EvidenceResult] = None,
    ) -> DecisionScores:
        """Derive the initial notify / digest / mute weight vector based on assessments.

        Args:
            assessment:    MessageAssessment containing sub-assessments.
            features:      Optional FeatureVector (ignored for base scoring).
            understanding: Optional UnderstandingResult (ignored for base scoring).
            evidence:      Optional EvidenceResult (ignored for base scoring).

        Returns:
            A DecisionScores object with raw scores clamped to [0.0, 1.0].
        """
        # 1. notify_score: Heavily weighted by attention, urgency, and personalization
        notify = (
            0.5 * assessment.attention.attention_score +
            0.3 * assessment.urgency.urgency_score +
            0.2 * assessment.personalization.personalization_score
        )

        # 2. digest_score: Heavily weighted by importance (when urgency is low), promo prob, and event prob
        is_urgency_low = (
            assessment.urgency.urgency_score < 0.4 or
            assessment.urgency.time_sensitivity == "low"
        )
        importance_factor = assessment.importance.importance_score if is_urgency_low else 0.0

        digest = (
            0.4 * importance_factor +
            0.3 * assessment.importance.promotion_probability +
            0.3 * assessment.importance.event_probability
        )

        # 3. mute_score: Heavily weighted by spam prob, low trust, and low personalization
        low_trust_factor = 1.0 - assessment.trust.trust_score
        low_personalization_factor = 1.0 - assessment.personalization.personalization_score

        mute = (
            0.5 * assessment.risk.spam_probability +
            0.3 * low_trust_factor +
            0.2 * low_personalization_factor
        )

        # Clamp all scores to [0.0, 1.0]
        notify_score = max(0.0, min(1.0, float(notify)))
        digest_score = max(0.0, min(1.0, float(digest)))
        mute_score = max(0.0, min(1.0, float(mute)))

        return DecisionScores(
            notify_score=notify_score,
            digest_score=digest_score,
            mute_score=mute_score,
        )
