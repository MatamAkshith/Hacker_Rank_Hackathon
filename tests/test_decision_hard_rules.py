"""Unit tests for HardRulesEvaluator and DecisionEngine short-circuit (Sprint 7.2).

Tests cover all four hard rules plus the pass-through (None) case, including
priority ordering (security rules first) and trace annotation.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.decision.hard_rules import (
    HardRulesEvaluator,
    _SCAM_PROB_THRESHOLD,
    _PAYMENT_PROB_THRESHOLD,
    _URGENCY_SCORE_THRESHOLD,
    _MENTION_PERSONAL_THRESHOLD,
)
from code.decision.decision_engine import DecisionEngine
from code.decision.models import DecisionResult
from code.assessment.models import (
    MessageAssessment,
    RiskAssessment,
    TrustAssessment,
    UrgencyAssessment,
    ImportanceAssessment,
    PersonalizationAssessment,
    AttentionAssessment,
)
from code.evidence.models import EvidenceResult
from code.understanding.models import UnderstandingResult


# ── Shared mock builders ──────────────────────────────────────────────────────

def _safe_assessment(**overrides) -> MessageAssessment:
    """Build a default-safe (no rules trigger) MessageAssessment."""
    base = MessageAssessment(
        risk=RiskAssessment(
            risk_score=0.0,
            scam_probability=0.0,
            spam_probability=0.0,
            threat_level="none",
            reasons=["safe baseline"],
        ),
        trust=TrustAssessment(
            trust_score=0.5,
            is_verified=False,
            reasons=["baseline"],
        ),
        urgency=UrgencyAssessment(
            urgency_score=0.2,
            time_sensitivity="low",
            reasons=["baseline"],
        ),
        importance=ImportanceAssessment(
            importance_score=0.2,
            payment_probability=0.1,
            event_probability=0.0,
            promotion_probability=0.0,
            value_category="neutral",
            reasons=["baseline"],
        ),
        personalization=PersonalizationAssessment(
            personalization_score=0.1,
            affinity_score=0.1,
            user_relevance="general",
            reasons=["baseline"],
        ),
        attention=AttentionAssessment(
            attention_score=0.2,
            attention_needed=False,
            interruption_cost=0.2,
            reasons=["baseline"],
        ),
        overall_score=0.0,
        overall_confidence=0.5,
        status="assessment_complete",
    )
    # Apply overrides at the top level (action, etc.) — not used here
    return base


def _safe_features():
    """Import FeatureVector lazily to avoid circular issues, return a minimal one."""
    from code.loader.data_loader import DataLoader
    from code.context.context_builder import ContextBuilder
    from code.features.extractor import FeatureExtractor

    loader = DataLoader()
    loader.load_all("dataset")
    builder = ContextBuilder(loader)
    extractor = FeatureExtractor()
    ctx = builder.build_context("msg_023")
    return extractor.extract(ctx)


def _safe_understanding() -> UnderstandingResult:
    return UnderstandingResult(
        summary="A generic safe message.",
        intent="informational",
        message_type="personal",
        urgency="low",
        entities=[],
        requires_attention=False,
        promotion_detected=False,
        payment_detected=False,
        event_detected=False,
        contains_media=False,
        processing_status="heuristics",
    )


def _safe_evidence() -> EvidenceResult:
    return EvidenceResult(
        top_evidence=[],
        retrieval_summary="No evidence.",
        retrieval_status="no_history",
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestHardRulesEvaluator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.evaluator = HardRulesEvaluator()
        cls.features  = _safe_features()
        cls.understanding = _safe_understanding()
        cls.evidence  = _safe_evidence()

    # ── Rule 1: Scam Prevention ───────────────────────────────────────────────

    def test_scam_high_probability_triggers_mute(self):
        """scam_probability > threshold → mute with confidence=1.0."""
        assessment = _safe_assessment()
        assessment.risk.scam_probability = _SCAM_PROB_THRESHOLD + 0.01
        result = self.evaluator.evaluate(
            self.features, self.understanding, assessment, self.evidence
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.action, "mute")
        self.assertAlmostEqual(result.confidence, 1.0)
        self.assertIn("scam_prevention", result.decision_trace[0])

    def test_scam_high_threat_level_triggers_mute(self):
        """threat_level='high' → mute regardless of scam_probability."""
        assessment = _safe_assessment()
        assessment.risk.scam_probability = 0.0
        assessment.risk.threat_level = "high"
        result = self.evaluator.evaluate(
            self.features, self.understanding, assessment, self.evidence
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.action, "mute")

    def test_scam_below_threshold_does_not_trigger(self):
        """scam_probability exactly at threshold → no trigger (rule is strictly >)."""
        assessment = _safe_assessment()
        assessment.risk.scam_probability = _SCAM_PROB_THRESHOLD  # Equal, not above
        result = self.evaluator.evaluate(
            self.features, self.understanding, assessment, self.evidence
        )
        # Rule 1 should not fire (strictly >)
        if result is not None:
            self.assertNotEqual(result.decision_trace[0].split(":")[1].split(" ")[0],
                                "scam_prevention")

    # ── Rule 2: Blocked Sender ───────────────────────────────────────────────

    def test_blocked_sender_triggers_mute(self):
        """is_blocked=True → mute with confidence=1.0."""
        from code.features.models import FeatureVector
        blocked_features = self.features.model_copy(update={"is_blocked": True})
        assessment = _safe_assessment()
        result = self.evaluator.evaluate(
            blocked_features, self.understanding, assessment, self.evidence
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.action, "mute")
        self.assertAlmostEqual(result.confidence, 1.0)
        self.assertIn("blocked_sender", result.decision_trace[0])

    def test_not_blocked_does_not_trigger(self):
        """is_blocked=False → rule 2 does not fire."""
        features = self.features.model_copy(update={"is_blocked": False})
        assessment = _safe_assessment()
        result = self.evaluator.evaluate(
            features, self.understanding, assessment, self.evidence
        )
        # If result is not None, it must be from a different rule
        if result is not None:
            self.assertNotIn("blocked_sender", result.decision_trace[0])

    # ── Rule 3: Critical Banking Alert ──────────────────────────────────────

    def test_critical_banking_alert_triggers_notify(self):
        """Verified + high payment + high urgency → notify with confidence=1.0."""
        assessment = _safe_assessment()
        assessment.trust.is_verified = True
        assessment.importance.payment_probability = _PAYMENT_PROB_THRESHOLD + 0.01
        assessment.urgency.urgency_score = _URGENCY_SCORE_THRESHOLD + 0.01
        result = self.evaluator.evaluate(
            self.features, self.understanding, assessment, self.evidence
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.action, "notify")
        self.assertAlmostEqual(result.confidence, 1.0)
        self.assertIn("critical_banking_alert", result.decision_trace[0])

    def test_banking_alert_without_verified_does_not_trigger(self):
        """Rule 3 requires is_verified=True; unverified sender must not trigger."""
        assessment = _safe_assessment()
        assessment.trust.is_verified = False
        assessment.importance.payment_probability = 0.95
        assessment.urgency.urgency_score = 0.95
        result = self.evaluator.evaluate(
            self.features, self.understanding, assessment, self.evidence
        )
        if result is not None:
            self.assertNotIn("critical_banking_alert", result.decision_trace[0])

    def test_banking_alert_low_urgency_does_not_trigger(self):
        """Rule 3 requires urgency_score > threshold; low urgency must not trigger."""
        assessment = _safe_assessment()
        assessment.trust.is_verified = True
        assessment.importance.payment_probability = 0.95
        assessment.urgency.urgency_score = 0.50  # Below 0.80
        result = self.evaluator.evaluate(
            self.features, self.understanding, assessment, self.evidence
        )
        if result is not None:
            self.assertNotIn("critical_banking_alert", result.decision_trace[0])

    # ── Rule 4: Direct Mention Override ─────────────────────────────────────

    def test_direct_mention_in_muted_group_triggers_notify(self):
        """group_is_muted + high personalization → notify with confidence=1.0."""
        muted_features = self.features.model_copy(update={"group_is_muted": True})
        assessment = _safe_assessment()
        assessment.personalization.personalization_score = _MENTION_PERSONAL_THRESHOLD + 0.01
        result = self.evaluator.evaluate(
            muted_features, self.understanding, assessment, self.evidence
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.action, "notify")
        self.assertAlmostEqual(result.confidence, 1.0)
        self.assertIn("direct_mention_override", result.decision_trace[0])

    def test_mention_not_muted_group_does_not_trigger(self):
        """Rule 4 requires group_is_muted=True; unmuted group must not trigger."""
        not_muted = self.features.model_copy(update={"group_is_muted": False})
        assessment = _safe_assessment()
        assessment.personalization.personalization_score = 0.99
        result = self.evaluator.evaluate(
            not_muted, self.understanding, assessment, self.evidence
        )
        if result is not None:
            self.assertNotIn("direct_mention_override", result.decision_trace[0])

    # ── Pass-through ─────────────────────────────────────────────────────────

    def test_pass_through_safe_message_returns_none(self):
        """A generic safe message must trigger no hard rules → None returned."""
        assessment = _safe_assessment()
        result = self.evaluator.evaluate(
            self.features, self.understanding, assessment, self.evidence
        )
        self.assertIsNone(result)

    # ── Priority ordering ────────────────────────────────────────────────────

    def test_scam_beats_direct_mention(self):
        """A scam in a muted group with high personalization → mute wins over notify.

        Validates that security rules (Rule 1) execute before positive rules (Rule 4).
        """
        muted_features = self.features.model_copy(update={"group_is_muted": True})
        assessment = _safe_assessment()
        assessment.risk.scam_probability = 0.99  # Triggers Rule 1
        assessment.personalization.personalization_score = 0.95  # Would trigger Rule 4
        result = self.evaluator.evaluate(
            muted_features, self.understanding, assessment, self.evidence
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.action, "mute",
                         "Scam rule must take precedence over direct-mention notify")
        self.assertIn("scam_prevention", result.decision_trace[0])

    def test_blocked_beats_critical_banking(self):
        """Blocked sender + critical banking alert → mute wins over notify.

        Validates that Rule 2 (blocked) executes before Rule 3 (banking).
        """
        blocked_features = self.features.model_copy(update={"is_blocked": True})
        assessment = _safe_assessment()
        assessment.trust.is_verified = True
        assessment.importance.payment_probability = 0.95
        assessment.urgency.urgency_score = 0.95
        result = self.evaluator.evaluate(
            blocked_features, self.understanding, assessment, self.evidence
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.action, "mute",
                         "Blocked sender must take precedence over banking alert notify")
        self.assertIn("blocked_sender", result.decision_trace[0])

    # ── DecisionResult schema ────────────────────────────────────────────────

    def test_hard_rule_result_has_non_empty_reason(self):
        """Every hard-rule DecisionResult must have a non-empty reason string."""
        assessment = _safe_assessment()
        assessment.risk.scam_probability = 0.99
        result = self.evaluator.evaluate(
            self.features, self.understanding, assessment, self.evidence
        )
        self.assertIsNotNone(result)
        self.assertIsInstance(result.reason, str)
        self.assertGreater(len(result.reason.strip()), 0)

    def test_hard_rule_result_has_trace(self):
        """decision_trace must be a non-empty list when a hard rule fires."""
        assessment = _safe_assessment()
        assessment.risk.scam_probability = 0.99
        result = self.evaluator.evaluate(
            self.features, self.understanding, assessment, self.evidence
        )
        self.assertIsNotNone(result)
        self.assertIsInstance(result.decision_trace, list)
        self.assertGreater(len(result.decision_trace), 0)


class TestDecisionEngineShortCircuit(unittest.TestCase):
    """Verify DecisionEngine returns hard-rule results immediately."""

    @classmethod
    def setUpClass(cls):
        cls.engine = DecisionEngine()
        cls.features = _safe_features()
        cls.understanding = _safe_understanding()
        cls.evidence = _safe_evidence()

    def test_scam_message_short_circuits_to_mute(self):
        """DecisionEngine must return mute without reaching the scoring stage."""
        assessment = _safe_assessment()
        assessment.risk.scam_probability = 0.99
        result = self.engine.decide(
            self.features, self.understanding, assessment, self.evidence
        )
        self.assertIsInstance(result, DecisionResult)
        self.assertEqual(result.action, "mute")
        self.assertAlmostEqual(result.confidence, 1.0)

    def test_safe_message_falls_through_to_scaffold_default(self):
        """Safe message → hard rules return None → engine returns a valid terminal action."""
        assessment = _safe_assessment()
        result = self.engine.decide(
            self.features, self.understanding, assessment, self.evidence
        )
        self.assertIsInstance(result, DecisionResult)
        self.assertIn(result.action, ("notify", "digest", "mute"),
                      "Non-hard-rule messages must result in a valid routing decision action")


if __name__ == "__main__":
    unittest.main()
