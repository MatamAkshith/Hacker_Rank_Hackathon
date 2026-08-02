"""Comprehensive integration tests for the Evidence Retrieval Pipeline (Sprint 6.5).

Validates the integrity of EvidenceResult outputs across a sample of messages,
asserting schema correctness, score bounds, reason explainability, and
graceful no_history handling.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.loader.data_loader import DataLoader
from code.context.context_builder import ContextBuilder
from code.features.extractor import FeatureExtractor
from code.understanding.understanding_engine import UnderstandingEngine
from code.assessment.assessment_engine import AssessmentEngine
from code.evidence.retrieval_engine import RetrievalEngine
from code.evidence.models import EvidenceResult, EvidenceItem
from code.evidence.selectors import EvidenceSelector


# ── Routing-decision keywords — must never appear in a reason string ──────────
_ROUTING_WORDS = {"notify", "mute", "digest", "block", "suppress", "alert", "ignore"}


class TestEvidencePipelineIntegration(unittest.TestCase):
    """End-to-end integration tests for the full evidence retrieval pipeline."""

    @classmethod
    def setUpClass(cls):
        cls.loader         = DataLoader()
        cls.loader.load_all("dataset")
        cls.builder        = ContextBuilder(cls.loader)
        cls.extractor      = FeatureExtractor()
        cls.understander   = UnderstandingEngine()
        cls.assessor       = AssessmentEngine()
        cls.engine         = RetrievalEngine(cls.loader)

        # Build results for the first 20 messages
        cls.results: list[tuple[str, EvidenceResult]] = []
        messages = cls.loader._messages
        for _, row in messages.head(20).iterrows():
            msg_id = row["message_id"]
            try:
                ctx   = cls.builder.build_context(msg_id)
                feats = cls.extractor.extract(ctx)
                und   = cls.understander.analyze(ctx)
                asmt  = cls.assessor.evaluate(ctx, und, feats)
                evid  = cls.engine.retrieve(ctx, asmt, und)
                cls.results.append((msg_id, evid))
            except Exception as e:
                raise AssertionError(f"Pipeline failed for {msg_id}: {e}")

    # ── Root container tests ─────────────────────────────────────────────────

    def test_returns_evidence_result(self):
        """retrieve() must always return an EvidenceResult instance."""
        for msg_id, result in self.results:
            with self.subTest(msg_id=msg_id):
                self.assertIsInstance(result, EvidenceResult)

    def test_retrieval_status_valid(self):
        """retrieval_status must be one of the three known terminal states."""
        valid_statuses = {"success", "no_history"}
        for msg_id, result in self.results:
            with self.subTest(msg_id=msg_id):
                self.assertIn(
                    result.retrieval_status, valid_statuses,
                    f"Unexpected status '{result.retrieval_status}' for {msg_id}"
                )

    def test_top_evidence_is_list(self):
        """top_evidence must always be a list."""
        for msg_id, result in self.results:
            with self.subTest(msg_id=msg_id):
                self.assertIsInstance(result.top_evidence, list)

    def test_top_evidence_max_three(self):
        """top_evidence must contain at most 3 EvidenceItems."""
        for msg_id, result in self.results:
            with self.subTest(msg_id=msg_id):
                self.assertLessEqual(
                    len(result.top_evidence), 3,
                    f"top_evidence exceeded 3 items for {msg_id}: {len(result.top_evidence)}"
                )

    def test_retrieval_summary_non_empty(self):
        """retrieval_summary must be a non-empty string."""
        for msg_id, result in self.results:
            with self.subTest(msg_id=msg_id):
                self.assertIsInstance(result.retrieval_summary, str)
                self.assertGreater(len(result.retrieval_summary.strip()), 0)

    def test_success_status_has_evidence_or_no_candidates(self):
        """'success' status implies at least one EvidenceItem was returned."""
        for msg_id, result in self.results:
            with self.subTest(msg_id=msg_id):
                if result.retrieval_status == "success":
                    self.assertGreater(
                        len(result.top_evidence), 0,
                        f"Status='success' but top_evidence is empty for {msg_id}"
                    )

    # ── EvidenceItem field tests ─────────────────────────────────────────────

    def test_evidence_item_types(self):
        """Every EvidenceItem must be an EvidenceItem instance."""
        for msg_id, result in self.results:
            for item in result.top_evidence:
                with self.subTest(msg_id=msg_id, item_id=item.message_id):
                    self.assertIsInstance(item, EvidenceItem)

    def test_message_id_non_empty(self):
        """EvidenceItem.message_id must be a non-empty string."""
        for msg_id, result in self.results:
            for item in result.top_evidence:
                with self.subTest(msg_id=msg_id):
                    self.assertIsInstance(item.message_id, str)
                    self.assertGreater(len(item.message_id.strip()), 0)

    def test_similarity_score_in_range(self):
        """EvidenceItem.similarity_score must be a float in [0.0, 1.0]."""
        for msg_id, result in self.results:
            for item in result.top_evidence:
                with self.subTest(msg_id=msg_id, item_id=item.message_id):
                    self.assertIsInstance(item.similarity_score, float)
                    self.assertGreaterEqual(item.similarity_score, 0.0)
                    self.assertLessEqual(item.similarity_score, 1.0)

    def test_reason_is_non_empty_string(self):
        """EvidenceItem.reason must be a non-empty explanatory string."""
        for msg_id, result in self.results:
            for item in result.top_evidence:
                with self.subTest(msg_id=msg_id, item_id=item.message_id):
                    self.assertIsInstance(item.reason, str)
                    self.assertGreater(
                        len(item.reason.strip()), 0,
                        f"Empty reason on evidence item {item.message_id} for {msg_id}"
                    )

    def test_matched_features_populated(self):
        """EvidenceItem.matched_features must be a non-empty list of strings."""
        for msg_id, result in self.results:
            for item in result.top_evidence:
                with self.subTest(msg_id=msg_id, item_id=item.message_id):
                    self.assertIsInstance(item.matched_features, list)
                    self.assertGreater(
                        len(item.matched_features), 0,
                        f"Empty matched_features on evidence {item.message_id} for {msg_id}"
                    )
                    for feat in item.matched_features:
                        self.assertIsInstance(feat, str)

    def test_reason_contains_no_routing_decisions(self):
        """reason must describe the match, not prescribe a routing action."""
        for msg_id, result in self.results:
            for item in result.top_evidence:
                with self.subTest(msg_id=msg_id, item_id=item.message_id):
                    reason_lower = item.reason.lower()
                    for bad_word in _ROUTING_WORDS:
                        self.assertNotIn(
                            bad_word, reason_lower,
                            f"Routing word '{bad_word}' found in reason for "
                            f"evidence {item.message_id}: '{item.reason}'"
                        )

    def test_similarity_above_threshold(self):
        """All selected items must be above the selector noise threshold (0.05)."""
        threshold = EvidenceSelector._MIN_SCORE_THRESHOLD
        for msg_id, result in self.results:
            for item in result.top_evidence:
                with self.subTest(msg_id=msg_id, item_id=item.message_id):
                    self.assertGreaterEqual(
                        item.similarity_score, threshold,
                        f"Evidence {item.message_id} for {msg_id} scored below "
                        f"threshold: {item.similarity_score}"
                    )

    def test_sorted_descending_by_score(self):
        """top_evidence must be ordered by descending similarity_score."""
        for msg_id, result in self.results:
            with self.subTest(msg_id=msg_id):
                scores = [i.similarity_score for i in result.top_evidence]
                self.assertEqual(
                    scores, sorted(scores, reverse=True),
                    f"top_evidence not sorted descending for {msg_id}: {scores}"
                )

    # ── Selector unit tests ──────────────────────────────────────────────────

    def test_selector_empty_input_returns_empty(self):
        """EvidenceSelector.select_top([]) must return []."""
        selector = EvidenceSelector()
        result = selector.select_top([], k=3)
        self.assertEqual(result, [])

    def test_selector_below_threshold_excluded(self):
        """Candidates below _MIN_SCORE_THRESHOLD must be excluded even if top-k."""
        selector = EvidenceSelector()
        low_cand = {
            "message_id": "low_001",
            "similarity_score": 0.01,  # Below 0.05 threshold
            "matched_features": ["structural:conv_type_match"],
            "_retrieval_sources": ["conversation_type"],
            "conversation_type": "business",
            "business_id": "biz_001",
        }
        result = selector.select_top([low_cand], k=3)
        self.assertEqual(result, [])

    def test_selector_k_respected(self):
        """select_top must return at most k items even when more are eligible."""
        selector = EvidenceSelector()
        candidates = [
            {
                "message_id": f"msg_{i:03d}",
                "similarity_score": 0.9 - i * 0.05,
                "matched_features": ["identity:same_business", "semantic:payment_match"],
                "_retrieval_sources": ["same_business"],
                "conversation_type": "business",
                "business_id": "biz_001",
            }
            for i in range(10)
        ]
        result = selector.select_top(candidates, k=3)
        self.assertLessEqual(len(result), 3)

    def test_no_history_graceful_return(self):
        """RetrievalEngine must return retrieval_status='no_history' for empty pools."""
        # Use a minimal mock context where the user has no history
        # We test this by checking that 'no_history' is a valid reachable state
        # by directly checking a message from a user whose history may be empty
        messages = self.loader._messages
        for _, row in messages.iterrows():
            uid = row["user_id"]
            history = self.loader.get_message_history(uid)
            if len(history) == 0:
                ctx   = self.builder.build_context(row["message_id"])
                feats = self.extractor.extract(ctx)
                und   = self.understander.analyze(ctx)
                asmt  = self.assessor.evaluate(ctx, und, feats)
                evid  = self.engine.retrieve(ctx, asmt, und)
                self.assertEqual(evid.retrieval_status, "no_history")
                self.assertEqual(evid.top_evidence, [])
                return  # One case verified is sufficient
        # If every user has history, pass vacuously
        self.skipTest("All users have historical messages — no_history path not exercisable")


if __name__ == "__main__":
    unittest.main()
