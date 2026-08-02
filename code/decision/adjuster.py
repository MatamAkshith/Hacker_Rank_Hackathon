"""ScoreAdjuster: Applies contextual modifier deltas to the base DecisionScores
computed by BaseScorer (e.g., quiet-hour penalties, notification fatigue dampening,
user preference boosts).

To be fully implemented in Sprint 7.3.
"""

from code.context.models import UnifiedContext
from code.assessment.models import MessageAssessment
from code.decision.models import DecisionScores


class ScoreAdjuster:
    """Applies contextual modifier deltas to base DecisionScores."""

    def apply_adjustments(
        self,
        scores: DecisionScores,
        context: UnifiedContext,
        assessment: MessageAssessment,
    ) -> DecisionScores:
        """Modify the base scores with contextual signals.

        To be implemented in Sprint 7.3.

        Args:
            scores:     Base DecisionScores from BaseScorer.
            context:    UnifiedContext for the current message.
            assessment: MessageAssessment from the Assessment Engine.

        Returns:
            An updated DecisionScores object with all adjustments applied.
        """
        raise NotImplementedError
