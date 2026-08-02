"""Unit tests for BaseScorer and ScoreAdjuster (Sprint 7.3 & 7.4)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.decision.scorer import BaseScorer
from code.decision.adjuster import ScoreAdjuster
from code.decision.models import DecisionScores
from code.evidence.models import EvidenceResult, EvidenceItem
from code.assessment.models import (
    MessageAssessment,
    RiskAssessment,
    TrustAssessment,
    UrgencyAssessment,
    ImportanceAssessment,
    PersonalizationAssessment,
    AttentionAssessment,
)


def _build_assessment(
    attention_score: float = 0.0,
    urgency_score: float = 0.0,
    personalization_score: float = 0.0,
    importance_score: float = 0.0,
    promotion_probability: float = 0.0,
    event_probability: float = 0.0,
    spam_probability: float = 0.0,
    trust_score: float = 0.5,
    time_sensitivity: str = "low",
) -> MessageAssessment:
    """Helper to construct configurable MessageAssessment objects."""
    return MessageAssessment(
        risk=RiskAssessment(
            risk_score=0.0,
            spam_probability=spam_probability,
            scam_probability=0.0,
            threat_level="none",
        ),
        trust=TrustAssessment(
            trust_score=trust_score,
            is_verified=False,
        ),
        urgency=UrgencyAssessment(
            urgency_score=urgency_score,
            time_sensitivity=time_sensitivity,
        ),
        importance=ImportanceAssessment(
            importance_score=importance_score,
            payment_probability=0.0,
            event_probability=event_probability,
            promotion_probability=promotion_probability,
            value_category="neutral",
        ),
        personalization=PersonalizationAssessment(
            personalization_score=personalization_score,
            affinity_score=0.0,
            user_relevance="general",
        ),
        attention=AttentionAssessment(
            attention_score=attention_score,
            attention_needed=False,
            interruption_cost=0.0,
        ),
        overall_score=0.0,
        overall_confidence=0.5,
        status="assessment_complete",
    )


class TestBaseScorer(unittest.TestCase):

    def setUp(self):
        self.scorer = BaseScorer()

    def test_high_urgency_base_score(self):
        """High urgency and attention message must favor notify_score over digest_score."""
        asmt = _build_assessment(
            attention_score=0.9,
            urgency_score=0.8,
            personalization_score=0.7,
            importance_score=0.3,
            time_sensitivity="high",
        )
        scores = self.scorer.calculate_base_scores(asmt)

        self.assertGreater(scores.notify_score, scores.digest_score)
        # Verify clamp logic
        self.assertTrue(0.0 <= scores.notify_score <= 1.0)
        self.assertTrue(0.0 <= scores.digest_score <= 1.0)
        self.assertTrue(0.0 <= scores.mute_score <= 1.0)

    def test_promo_base_score(self):
        """Low urgency promotional message must favor digest_score over notify_score."""
        asmt = _build_assessment(
            attention_score=0.1,
            urgency_score=0.1,
            personalization_score=0.2,
            importance_score=0.8,
            promotion_probability=0.9,
            time_sensitivity="low",
        )
        scores = self.scorer.calculate_base_scores(asmt)

        self.assertGreater(scores.digest_score, scores.notify_score)


class TestScoreAdjuster(unittest.TestCase):

    def setUp(self):
        self.adjuster = ScoreAdjuster()

    def test_adjustment_penalty_on_ignored_history(self):
        """Ignore evidence penalty must drop notify_score significantly."""
        base_scores = DecisionScores(notify_score=0.8, digest_score=0.3, mute_score=0.2)

        # Mock evidence showing user ignored the last 3 similar promos
        evidence = EvidenceResult(
            top_evidence=[
                EvidenceItem(message_id="m1", similarity_score=0.9, user_action="ignored"),
                EvidenceItem(message_id="m2", similarity_score=0.8, user_action="ignored"),
                EvidenceItem(message_id="m3", similarity_score=0.7, user_action="ignored"),
            ],
            retrieval_summary="Found ignored history.",
            retrieval_status="success",
        )

        trace = []
        adjusted = self.adjuster.apply_adjustments(base_scores, evidence, decision_trace=trace)

        # Base score 0.8 * 0.6 = 0.48
        self.assertAlmostEqual(adjusted.notify_score, 0.48)
        self.assertGreater(adjusted.digest_score, base_scores.digest_score)
        self.assertGreater(adjusted.mute_score, base_scores.mute_score)
        self.assertTrue(len(trace) > 0)

    def test_adjustment_boost_on_engaged_history(self):
        """Engagement evidence boost must raise notify_score."""
        base_scores = DecisionScores(notify_score=0.6, digest_score=0.2, mute_score=0.1)

        # Mock evidence showing user opened similar messages
        evidence = EvidenceResult(
            top_evidence=[
                EvidenceItem(message_id="m4", similarity_score=0.9, user_action="opened"),
            ],
            retrieval_summary="Found engaged history.",
            retrieval_status="success",
        )

        trace = []
        adjusted = self.adjuster.apply_adjustments(base_scores, evidence, decision_trace=trace)

        # Base score 0.6 * 1.3 = 0.78
        self.assertAlmostEqual(adjusted.notify_score, 0.78)
        self.assertTrue(len(trace) > 0)

    def test_scores_clamped_strictly(self):
        """Adjusted scores must remain strictly within [0.0, 1.0]."""
        base_scores = DecisionScores(notify_score=0.9, digest_score=0.9, mute_score=0.9)

        evidence = EvidenceResult(
            top_evidence=[
                EvidenceItem(message_id="m5", similarity_score=0.9, user_action="opened"),
            ],
            retrieval_summary="engaged",
            retrieval_status="success",
        )

        # 0.9 * 1.3 = 1.17 -> should be clamped to 1.0
        adjusted = self.adjuster.apply_adjustments(base_scores, evidence)
        self.assertEqual(adjusted.notify_score, 1.0)
        self.assertTrue(0.0 <= adjusted.digest_score <= 1.0)
        self.assertTrue(0.0 <= adjusted.mute_score <= 1.0)


if __name__ == "__main__":
    unittest.main()
