"""ActionSelector: Converts the final adjusted DecisionScores into the terminal
routing action ("notify", "digest", or "mute") along with a confidence score
and a human-readable reason.

To be fully implemented in Sprint 7.3.
"""

from code.decision.models import DecisionScores, DecisionResult


class ActionSelector:
    """Selects the winning routing action from a finalised DecisionScores vector."""

    def select_action(
        self,
        scores: DecisionScores,
        decision_trace: list,
    ) -> DecisionResult:
        """Convert the adjusted score vector into a terminal DecisionResult.

        To be implemented in Sprint 7.3.

        Args:
            scores:         Finalised DecisionScores after all adjustments.
            decision_trace: Mutable audit-log list accumulated by the engine.

        Returns:
            A DecisionResult with the chosen action, reason, and confidence.
        """
        raise NotImplementedError
