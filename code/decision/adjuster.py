"""ScoreAdjuster: Refines base notify / digest / mute scores using the EvidenceResult.

Applies fatigue/ignore penalties or high engagement boosts based on how
the user historically interacted with highly similar evidence messages.
"""

from typing import Optional, List
from code.context.models import UnifiedContext
from code.assessment.models import MessageAssessment
from code.evidence.models import EvidenceResult
from code.decision.models import DecisionScores


class ScoreAdjuster:
    """Applies contextual modifier deltas based on historical evidence."""

    def apply_adjustments(
        self,
        base_scores: DecisionScores,
        evidence: EvidenceResult,
        context: Optional[UnifiedContext] = None,
        assessment: Optional[MessageAssessment] = None,
        decision_trace: Optional[list] = None,
    ) -> DecisionScores:
        """Modify base scores using user actions from top evidence.

        Args:
            base_scores:    The DecisionScores object from BaseScorer.
            evidence:       EvidenceResult containing top matched historical items.
            context:        Optional UnifiedContext (compatible with prior scaffold).
            assessment:     Optional MessageAssessment (compatible with prior scaffold).
            decision_trace: Optional list to append audit logs to.

        Returns:
            A new/modified DecisionScores object with updated and clamped scores.
        """
        # Create a copy/mutable version of base scores to modify
        scores = DecisionScores(
            notify_score=base_scores.notify_score,
            digest_score=base_scores.digest_score,
            mute_score=base_scores.mute_score,
        )

        if not evidence or not evidence.top_evidence:
            if decision_trace is not None:
                decision_trace.append("evidence_adjustment: no evidence items available to adjust scores")
            return scores

        ignored_count = sum(1 for item in evidence.top_evidence if item.user_action == "ignored")
        opened_count = sum(1 for item in evidence.top_evidence if item.user_action == "opened")
        muted_count = sum(1 for item in evidence.top_evidence if item.user_action == "muted")

        # 1. Fatigue/Ignore Penalty
        if ignored_count > 0:
            old_notify = scores.notify_score
            scores.notify_score *= 0.6
            scores.digest_score += 0.2
            scores.mute_score += 0.2
            if decision_trace is not None:
                msg = (
                    f"evidence_adjustment: ignored penalty (ignored_count={ignored_count}) "
                    f"applied: notify_score scaled {old_notify:.3f} -> {scores.notify_score:.3f}, "
                    "digest/mute scores boosted"
                )
                decision_trace.append(msg)

        # 2. High Engagement Boost
        if opened_count > 0:
            old_notify = scores.notify_score
            scores.notify_score *= 1.3
            if decision_trace is not None:
                msg = (
                    f"evidence_adjustment: engagement boost (opened_count={opened_count}) "
                    f"applied: notify_score scaled {old_notify:.3f} -> {scores.notify_score:.3f}"
                )
                decision_trace.append(msg)

        # 3. Muted/Reported Penalty
        if muted_count > 0:
            old_notify = scores.notify_score
            scores.notify_score *= 0.4
            scores.mute_score += 0.3
            if decision_trace is not None:
                msg = (
                    f"evidence_adjustment: muted penalty (muted_count={muted_count}) "
                    f"applied: notify_score scaled {old_notify:.3f} -> {scores.notify_score:.3f}, "
                    "mute score boosted"
                )
                decision_trace.append(msg)

        # Clamp all adjusted scores to [0.0, 1.0]
        scores.notify_score = max(0.0, min(1.0, float(scores.notify_score)))
        scores.digest_score = max(0.0, min(1.0, float(scores.digest_score)))
        scores.mute_score = max(0.0, min(1.0, float(scores.mute_score)))

        return scores
