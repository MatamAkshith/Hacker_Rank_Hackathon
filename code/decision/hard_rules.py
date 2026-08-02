"""HardRulesEvaluator: Short-circuits the Decision pipeline when a definitive,
deterministic routing action can be concluded from a single unambiguous rule.

Rules are evaluated strictly in priority order — security/safety rules come
first so a malicious message can never game a later positive rule (e.g., using
a Direct Mention to escape a Scam block).

Priority order:
  1. Scam Prevention      → mute   (security — highest priority)
  2. Blocked Sender        → mute   (user preference — overrides everything positive)
  3. Critical Banking Alert → notify (high-value positive override)
  4. Direct Mention Override → notify (user-attention positive override)

If no rule fires, returns None and the probabilistic pipeline takes over.
"""

from typing import List, Optional

from code.features.models import FeatureVector
from code.understanding.models import UnderstandingResult
from code.assessment.models import MessageAssessment
from code.evidence.models import EvidenceResult
from code.decision.models import DecisionResult

# ── Thresholds (named constants for readability and future tunability) ────────
_SCAM_PROB_THRESHOLD        = 0.85   # Rule 1: scam probability hard floor
_PAYMENT_PROB_THRESHOLD     = 0.80   # Rule 3: payment probability requirement
_URGENCY_SCORE_THRESHOLD    = 0.80   # Rule 3: urgency score requirement
_MENTION_PERSONAL_THRESHOLD = 0.80   # Rule 4: personalization score for direct mention


class HardRulesEvaluator:
    """Evaluates high-confidence rule triggers that bypass scoring entirely.

    Returns a terminal DecisionResult immediately when any rule fires.
    Returns None when no rule matches, allowing the scoring pipeline to proceed.
    """

    def evaluate(
        self,
        features: FeatureVector,
        understanding: UnderstandingResult,
        assessment: MessageAssessment,
        evidence: EvidenceResult,
    ) -> Optional[DecisionResult]:
        """Evaluate all hard rules in priority order.

        Args:
            features:      FeatureVector from the Feature Extraction stage.
            understanding: UnderstandingResult from the Understanding Engine.
            assessment:    MessageAssessment from the Assessment Engine.
            evidence:      EvidenceResult from the Evidence Retrieval Engine.

        Returns:
            A terminal DecisionResult (confidence=1.0) if any hard rule fires,
            otherwise None to allow probabilistic scoring to continue.
        """
        # Rule 1 — Scam Prevention (MUTE) ────────────────────────────────────
        result = self._rule_scam_prevention(assessment)
        if result is not None:
            return result

        # Rule 2 — Blocked Sender (MUTE) ─────────────────────────────────────
        result = self._rule_blocked_sender(features)
        if result is not None:
            return result

        # Rule 3 — Critical Banking Alert (NOTIFY) ───────────────────────────
        result = self._rule_critical_banking_alert(assessment)
        if result is not None:
            return result

        # Rule 4 — Direct Mention Override (NOTIFY) ──────────────────────────
        result = self._rule_direct_mention_override(features, assessment)
        if result is not None:
            return result

        return None

    # ── Rule implementations ─────────────────────────────────────────────────

    def _rule_scam_prevention(
        self, assessment: MessageAssessment
    ) -> Optional[DecisionResult]:
        """Rule 1: Mute messages with a high probability of being scams.

        Triggers when:
          - assessment.risk.scam_probability > 0.85, OR
          - assessment.risk.threat_level == "high"
        """
        triggered = (
            assessment.risk.scam_probability > _SCAM_PROB_THRESHOLD
            or assessment.risk.threat_level == "high"
        )
        if not triggered:
            return None

        trace: List[str] = [
            f"hard_rule:scam_prevention fired "
            f"(scam_probability={assessment.risk.scam_probability:.3f}, "
            f"threat_level='{assessment.risk.threat_level}')"
        ]
        return DecisionResult(
            action="mute",
            reason="High probability of scam or malicious intent.",
            confidence=1.0,
            decision_trace=trace,
        )

    def _rule_blocked_sender(
        self, features: FeatureVector
    ) -> Optional[DecisionResult]:
        """Rule 2: Mute messages from senders explicitly blocked by the user.

        Triggers when:
          - features.is_blocked == True
        """
        if not features.is_blocked:
            return None

        trace: List[str] = [
            "hard_rule:blocked_sender fired (features.is_blocked=True)"
        ]
        return DecisionResult(
            action="mute",
            reason="Sender is explicitly blocked by the user.",
            confidence=1.0,
            decision_trace=trace,
        )

    def _rule_critical_banking_alert(
        self, assessment: MessageAssessment
    ) -> Optional[DecisionResult]:
        """Rule 3: Notify immediately for urgent payment alerts from verified sources.

        Triggers when ALL of the following are true:
          - assessment.trust.is_verified == True
          - assessment.importance.payment_probability > 0.80
          - assessment.urgency.urgency_score > 0.80
        """
        triggered = (
            assessment.trust.is_verified
            and assessment.importance.payment_probability > _PAYMENT_PROB_THRESHOLD
            and assessment.urgency.urgency_score > _URGENCY_SCORE_THRESHOLD
        )
        if not triggered:
            return None

        trace: List[str] = [
            f"hard_rule:critical_banking_alert fired "
            f"(is_verified={assessment.trust.is_verified}, "
            f"payment_probability={assessment.importance.payment_probability:.3f}, "
            f"urgency_score={assessment.urgency.urgency_score:.3f})"
        ]
        return DecisionResult(
            action="notify",
            reason="Urgent payment/banking notification from a verified source.",
            confidence=1.0,
            decision_trace=trace,
        )

    def _rule_direct_mention_override(
        self,
        features: FeatureVector,
        assessment: MessageAssessment,
    ) -> Optional[DecisionResult]:
        """Rule 4: Notify when user is directly mentioned in a muted group.

        Triggers when ALL of the following are true:
          - features.group_is_muted == True
          - assessment.personalization.personalization_score > 0.80
        """
        triggered = (
            features.group_is_muted
            and assessment.personalization.personalization_score > _MENTION_PERSONAL_THRESHOLD
        )
        if not triggered:
            return None

        trace: List[str] = [
            f"hard_rule:direct_mention_override fired "
            f"(group_is_muted={features.group_is_muted}, "
            f"personalization_score={assessment.personalization.personalization_score:.3f})"
        ]
        return DecisionResult(
            action="notify",
            reason="User was directly mentioned despite the group being muted.",
            confidence=1.0,
            decision_trace=trace,
        )
