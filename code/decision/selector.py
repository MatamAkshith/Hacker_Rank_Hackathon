"""ActionSelector: Converts the final adjusted DecisionScores into the terminal
routing action ("notify", "digest", or "mute") along with a confidence score
and a human-readable reason.
"""

import math
from code.decision.models import DecisionScores, DecisionResult


class ActionSelector:
    """Selects the winning routing action from a finalised DecisionScores vector."""

    def select_action(
        self,
        scores: DecisionScores,
        decision_trace: list,
    ) -> DecisionResult:
        """Convert the adjusted score vector into a terminal DecisionResult.

        Uses Temperature Softmax (T=6.0) to derive a confidence score
        representing the relative strength of the winning action.

        Args:
            scores:         Finalised DecisionScores after all adjustments.
            decision_trace: Mutable audit-log list accumulated by the engine.

        Returns:
            A DecisionResult with the chosen action, reason, and confidence.
        """
        notify = scores.notify_score
        digest = scores.digest_score
        mute = scores.mute_score

        # 1. Determine the winning action
        if notify >= digest and notify >= mute:
            winner = "notify"
            winning_score = notify
            runner_up_score = max(digest, mute)
        elif digest >= notify and digest >= mute:
            winner = "digest"
            winning_score = digest
            runner_up_score = max(notify, mute)
        else:
            winner = "mute"
            winning_score = mute
            runner_up_score = max(notify, digest)

        # 2. Compute Temperature Softmax Confidence (T=6.7 matches the user example cases)
        T = 6.7
        try:
            e_notify = math.exp(T * notify)
            e_digest = math.exp(T * digest)
            e_mute   = math.exp(T * mute)
            total = e_notify + e_digest + e_mute
            confidence = (e_notify if winner == "notify" else e_digest if winner == "digest" else e_mute) / total
        except OverflowError:
            confidence = 1.0

        confidence = round(max(0.0, min(1.0, confidence)), 4)

        # 3. Formulate the explanation reason
        margin = winning_score - runner_up_score
        if margin < 0.1:
            comparison_phrase = f"marginally exceeded runner-up score ({runner_up_score:.2f})"
        elif margin > 0.5:
            comparison_phrase = f"significantly dominated runner-up score ({runner_up_score:.2f})"
        else:
            comparison_phrase = f"comfortably exceeded runner-up score ({runner_up_score:.2f})"

        reason = (
            f"Action selected: {winner}. "
            f"Winning score ({winning_score:.2f}) {comparison_phrase} "
            f"with a confidence of {confidence:.2f}."
        )

        # 4. Append audit log trace
        decision_trace.append(
            f"action_selector: selected='{winner}', confidence={confidence:.3f}, "
            f"notify={notify:.3f}, digest={digest:.3f}, mute={mute:.3f}"
        )

        return DecisionResult(
            action=winner,
            reason=reason,
            confidence=confidence,
            decision_trace=decision_trace,
        )
