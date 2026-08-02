"""DecisionEngine: Main orchestrator of the Decision module.

Sprint 7.2: Hard-rule short-circuit is now active. If a hard rule fires,
its DecisionResult is returned immediately. Otherwise the probabilistic
scoring pipeline placeholder is returned (scoring implemented in Sprint 7.3).
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

        Sprint 7.2 pipeline:
          1. HardRulesEvaluator — returns a terminal DecisionResult if any
             absolute rule fires, bypassing all downstream scoring.
          2. Scoring placeholder — returns a default 'unassigned' DecisionResult
             until BaseScorer / ScoreAdjuster / ActionSelector are implemented
             in Sprint 7.3.

        Args:
            features:      FeatureVector from the Feature Extraction stage.
            understanding: UnderstandingResult from the Understanding Engine.
            assessment:    MessageAssessment from the Assessment Engine.
            evidence:      EvidenceResult from the Evidence Retrieval Engine.

        Returns:
            A DecisionResult with a final action and confidence score.
        """
        # Step 1: Hard-rule short-circuit
        hard_rule_result = self.hard_rules.evaluate(
            features, understanding, assessment, evidence
        )
        if hard_rule_result is not None:
            return hard_rule_result

        # Steps 2-4: Probabilistic scoring (placeholder — Sprint 7.3)
        return DecisionResult()
