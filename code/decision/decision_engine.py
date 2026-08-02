"""DecisionEngine: Main orchestrator of the Decision module.

Takes the full set of upstream pipeline outputs and produces the final
routing action (notify / digest / mute) for an incoming message.

Sprint 7.1 — scaffold only. All sub-components are wired but not yet invoked.
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
        """Instantiate and wire all sub-components.

        Components are wired here but not yet invoked in decide().
        Full orchestration will be implemented in Sprint 7.2.
        """
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

        Sprint 7.1: Returns a safe scaffold default without invoking any
        sub-components. Full logic will be wired in Sprint 7.2.

        Args:
            features:      FeatureVector from the Feature Extraction stage.
            understanding: UnderstandingResult from the Understanding Engine.
            assessment:    MessageAssessment from the Assessment Engine.
            evidence:      EvidenceResult from the Evidence Retrieval Engine.

        Returns:
            A DecisionResult with action="unassigned" (scaffold default).
        """
        return DecisionResult()
