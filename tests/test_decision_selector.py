"""Unit tests for ActionSelector (Sprint 7.5)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.decision.models import DecisionScores, DecisionResult
from code.decision.selector import ActionSelector


class TestActionSelector(unittest.TestCase):

    def setUp(self):
        self.selector = ActionSelector()

    def test_example_marginal_winner(self):
        """Case 1: notify=0.62, digest=0.59, mute=0.12 -> notify with ~0.54 confidence."""
        scores = DecisionScores(notify_score=0.62, digest_score=0.59, mute_score=0.12)
        trace = []
        result = self.selector.select_action(scores, trace)

        self.assertEqual(result.action, "notify")
        # Assert math matches 0.54 case
        self.assertAlmostEqual(result.confidence, 0.54, places=2)
        self.assertTrue(len(result.decision_trace) > 0)
        self.assertIn("marginally", result.reason)

    def test_example_dominant_winner(self):
        """Case 2: notify=0.98, digest=0.15, mute=0.02 -> notify with ~0.99 confidence."""
        scores = DecisionScores(notify_score=0.98, digest_score=0.15, mute_score=0.02)
        trace = []
        result = self.selector.select_action(scores, trace)

        self.assertEqual(result.action, "notify")
        # Assert math matches 0.99 case
        self.assertAlmostEqual(result.confidence, 0.99, places=2)
        self.assertTrue(len(result.decision_trace) > 0)
        self.assertIn("dominated", result.reason)


if __name__ == "__main__":
    unittest.main()
