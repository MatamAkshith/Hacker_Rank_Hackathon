"""Unit tests for SimilarityRanker (Sprint 6.3)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.loader.data_loader import DataLoader
from code.context.context_builder import ContextBuilder
from code.understanding.understanding_engine import UnderstandingEngine
from code.evidence.retriever import CandidateRetriever
from code.evidence.ranking import SimilarityRanker, _tokenize, _jaccard


class TestSimilarityRankerHelpers(unittest.TestCase):
    """Unit tests for pure helper functions."""

    def test_tokenize_basic(self):
        tokens = _tokenize("Hello World fo")
        self.assertIn("hello", tokens)
        self.assertIn("world", tokens)
        self.assertNotIn("fo", tokens)  # length 2 filtered (regex requires ≥3)

    def test_tokenize_none(self):
        self.assertEqual(_tokenize(None), set())

    def test_jaccard_identical(self):
        a = {"pay", "now", "urgent"}
        self.assertAlmostEqual(_jaccard(a, a), 1.0)

    def test_jaccard_disjoint(self):
        a = {"bank", "transfer"}
        b = {"holiday", "shopping"}
        self.assertAlmostEqual(_jaccard(a, b), 0.0)

    def test_jaccard_both_empty(self):
        self.assertAlmostEqual(_jaccard(set(), set()), 0.0)

    def test_jaccard_partial(self):
        a = {"pay", "bank", "urgent"}
        b = {"pay", "bank", "shop"}
        # intersection = {pay, bank}, union = {pay, bank, urgent, shop}
        self.assertAlmostEqual(_jaccard(a, b), 2 / 4)


class TestSimilarityRanker(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.loader = DataLoader()
        cls.loader.load_all("dataset")
        cls.builder     = ContextBuilder(cls.loader)
        cls.retriever   = CandidateRetriever(cls.loader)
        cls.ranker      = SimilarityRanker(cls.loader)
        cls.understand  = UnderstandingEngine()

    def _get_ranked(self, msg_id: str):
        ctx        = self.builder.build_context(msg_id)
        understand = self.understand.analyze(ctx)
        candidates = self.retriever.fetch_candidates(ctx)
        ranked     = self.ranker.rank_candidates(ctx, understand, candidates)
        return ctx, understand, ranked

    # ── Schema tests ──────────────────────────────────────────────────────────

    def test_returns_list(self):
        messages = self.loader._messages
        for _, row in messages.head(15).iterrows():
            _, _, ranked = self._get_ranked(row["message_id"])
            self.assertIsInstance(ranked, list)

    def test_similarity_score_in_range(self):
        """Every candidate's similarity_score must be in [0.0, 1.0]."""
        messages = self.loader._messages
        for _, row in messages.head(20).iterrows():
            _, _, ranked = self._get_ranked(row["message_id"])
            for cand in ranked:
                score = cand.get("similarity_score")
                self.assertIsNotNone(score, f"Missing similarity_score for {cand.get('message_id')}")
                self.assertIsInstance(score, float)
                self.assertGreaterEqual(score, 0.0)
                self.assertLessEqual(score, 1.0)

    def test_sorted_descending(self):
        """Ranked list must be sorted in descending order of similarity_score."""
        messages = self.loader._messages
        for _, row in messages.head(20).iterrows():
            _, _, ranked = self._get_ranked(row["message_id"])
            scores = [c["similarity_score"] for c in ranked]
            self.assertEqual(scores, sorted(scores, reverse=True),
                             f"Not sorted for msg {row['message_id']}")

    def test_matched_features_is_list(self):
        """Every candidate must have matched_features as a list of strings."""
        messages = self.loader._messages
        for _, row in messages.head(15).iterrows():
            _, _, ranked = self._get_ranked(row["message_id"])
            for cand in ranked:
                self.assertIn("matched_features", cand)
                self.assertIsInstance(cand["matched_features"], list)
                for feat in cand["matched_features"]:
                    self.assertIsInstance(feat, str)

    def test_feature_labels_have_prefix(self):
        """Every matched_feature label must carry a dimension prefix (e.g., 'identity:')."""
        known_prefixes = {"identity:", "semantic:", "structural:", "text:", "engagement:"}
        messages = self.loader._messages
        for _, row in messages.head(15).iterrows():
            _, _, ranked = self._get_ranked(row["message_id"])
            for cand in ranked:
                for feat in cand.get("matched_features", []):
                    has_prefix = any(feat.startswith(p) for p in known_prefixes)
                    self.assertTrue(has_prefix, f"Unknown feature label prefix: '{feat}'")

    # ── Semantic signal tests ──────────────────────────────────────────────────

    def test_business_message_top_candidate_shares_business(self):
        """For a business message, the top candidate should share identity with it."""
        messages = self.loader._messages
        biz_msgs = messages[messages["conversation_type"] == "business"]
        if biz_msgs.empty:
            self.skipTest("No business messages")

        for _, row in biz_msgs.head(10).iterrows():
            ctx, _, ranked = self._get_ranked(row["message_id"])
            if not ranked:
                continue
            top = ranked[0]
            # Top should have at least one identity signal
            identity_feats = [f for f in top.get("matched_features", []) if f.startswith("identity:")]
            self.assertGreater(len(identity_feats), 0,
                               f"Top ranked candidate for business msg {row['message_id']} "
                               f"has no identity feature: {top.get('matched_features')}")
            break  # One confirmed case is sufficient

    def test_weight_sum_correct(self):
        """Sanity-check: the sum of declared weights is exactly 1.0."""
        from code.evidence.ranking import (
            _W_IDENTITY, _W_SEMANTIC, _W_STRUCTURAL, _W_TEXT, _W_ENGAGEMENT
        )
        total = _W_IDENTITY + _W_SEMANTIC + _W_STRUCTURAL + _W_TEXT + _W_ENGAGEMENT
        self.assertAlmostEqual(total, 1.0, places=9)

    def test_reported_message_gets_zero_engagement(self):
        """A candidate flagged as reported must receive 0.0 from the engagement dimension."""
        # Build a synthetic candidate dict with reported=True
        ranker = self.ranker
        cand = {
            "message_id": "synth_001",
            "message_text": "please pay now",
            "message_reported": True,
            "message_opened": True,
            "message_replied": True,
            "notification_dismissed": False,
            "_retrieval_sources": ["conversation_type"],
        }
        features: list = []
        eng = ranker._engagement_signal(cand, features)
        self.assertAlmostEqual(eng, 0.0)
        self.assertNotIn("engagement:user_replied", features)

    def test_replied_message_gets_full_engagement(self):
        """A candidate the user replied to should receive 1.0 from engagement."""
        ranker = self.ranker
        cand = {
            "message_id": "synth_002",
            "message_text": "your otp is 1234",
            "message_reported": False,
            "message_opened": True,
            "message_replied": True,
            "notification_dismissed": False,
            "_retrieval_sources": ["same_business"],
        }
        features: list = []
        eng = ranker._engagement_signal(cand, features)
        self.assertAlmostEqual(eng, 1.0)
        self.assertIn("engagement:user_replied", features)


if __name__ == "__main__":
    unittest.main()
