"""DecisionEngine: Main orchestrator of the Decision module.

Sprint 7.3/7.4: Short-circuiting and base probabilistic scoring/adjustments
are now active. Adjustments write directly to the decision_trace audit log.
Action selection remains a scaffold placeholder.
"""

from code.features.models import FeatureVector
from code.understanding.models import UnderstandingResult
from code.assessment.models import MessageAssessment
from code.evidence.models import EvidenceResult
from code.decision.models import DecisionResult
from code.decision.hard_rules import HardRulesEvaluator
from code.decision.scorer import BaseScorer
from code.decision.adjuster import ScoreAdjuster
from code.decision.selector import ActionSelector


class DecisionEngine:
    """Orchestrates hard-rule evaluation, base scoring, contextual adjustment,
    and final action selection to produce a DecisionResult.
    """

    def __init__(self):
        """Instantiate and wire all sub-components."""
        self.hard_rules = HardRulesEvaluator()
        self.scorer     = BaseScorer()
        self.adjuster   = ScoreAdjuster()
        self.selector   = ActionSelector()

    def decide(
        self,
        features: FeatureVector,
        understanding: UnderstandingResult,
        assessment: MessageAssessment,
        evidence: EvidenceResult,
    ) -> DecisionResult:
        """Determine the final routing action for the current message.

        Args:
            features:      FeatureVector from the Feature Extraction stage.
            understanding: UnderstandingResult from the Understanding Engine.
            assessment:    MessageAssessment from the Assessment Engine.
            evidence:      EvidenceResult from the Evidence Retrieval Engine.

        Returns:
            A DecisionResult with the final routing decision and confidence.
        """
        # Step 1: Hard-rule short-circuit
        hard_rule_result = self.hard_rules.evaluate(
            features, understanding, assessment, evidence
        )
        if hard_rule_result is not None:
            return hard_rule_result

        # Audit trace log for base and adjusted scoring
        trace = []

        # Step 2: Base Scoring
        base_scores = self.scorer.calculate_base_scores(
            assessment, features, understanding, evidence
        )
        trace.append(
            f"base_scoring: notify_score={base_scores.notify_score:.3f}, "
            f"digest_score={base_scores.digest_score:.3f}, "
            f"mute_score={base_scores.mute_score:.3f}"
        )

        # Step 3: Evidence-Based Adjustment
        adjusted_scores = self.adjuster.apply_adjustments(
            base_scores, evidence, decision_trace=trace
        )

        # Step 4: Action Selection (Sprint 7.5)
        return self.selector.select_action(adjusted_scores, trace)
