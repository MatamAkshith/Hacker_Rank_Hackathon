"""Unit tests for CandidateRetriever (Sprint 6.2)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.loader.data_loader import DataLoader
from code.context.context_builder import ContextBuilder
from code.evidence.retriever import CandidateRetriever


class TestCandidateRetriever(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.loader = DataLoader()
        cls.loader.load_all("dataset")
        cls.builder = ContextBuilder(cls.loader)
        cls.retriever = CandidateRetriever(cls.loader)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_and_fetch(self, msg_id: str):
        ctx = self.builder.build_context(msg_id)
        return ctx, self.retriever.fetch_candidates(ctx)

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_returns_list(self):
        """fetch_candidates must always return a list (never None)."""
        messages = self.loader._messages
        for _, row in messages.head(20).iterrows():
            _, candidates = self._build_and_fetch(row["message_id"])
            self.assertIsInstance(candidates, list)

    def test_pool_cap(self):
        """Total candidate pool must never exceed _CANDIDATE_POOL_LIMIT."""
        messages = self.loader._messages
        for _, row in messages.iterrows():
            _, candidates = self._build_and_fetch(row["message_id"])
            self.assertLessEqual(
                len(candidates),
                CandidateRetriever._CANDIDATE_POOL_LIMIT,
                f"Pool exceeded cap for {row['message_id']}"
            )

    def test_current_message_not_in_candidates(self):
        """The incoming message itself must not appear in its own candidate pool."""
        messages = self.loader._messages
        for _, row in messages.head(30).iterrows():
            msg_id = row["message_id"]
            _, candidates = self._build_and_fetch(msg_id)
            candidate_ids = [c.get("message_id") for c in candidates]
            self.assertNotIn(
                msg_id, candidate_ids,
                f"Incoming message {msg_id} found in its own candidate pool"
            )

    def test_retrieval_sources_annotation(self):
        """Every candidate must carry a non-empty _retrieval_sources list."""
        messages = self.loader._messages
        for _, row in messages.head(20).iterrows():
            _, candidates = self._build_and_fetch(row["message_id"])
            for cand in candidates:
                self.assertIn(
                    "_retrieval_sources", cand,
                    f"Missing _retrieval_sources on candidate {cand.get('message_id')}"
                )
                self.assertIsInstance(cand["_retrieval_sources"], list)
                self.assertGreater(
                    len(cand["_retrieval_sources"]), 0,
                    f"Empty _retrieval_sources on {cand.get('message_id')}"
                )

    def test_valid_strategy_labels(self):
        """_retrieval_sources must only contain known strategy labels."""
        known = {"same_sender", "same_business", "same_group", "conversation_type"}
        messages = self.loader._messages
        for _, row in messages.head(20).iterrows():
            _, candidates = self._build_and_fetch(row["message_id"])
            for cand in candidates:
                for src in cand.get("_retrieval_sources", []):
                    self.assertIn(src, known, f"Unknown strategy label '{src}'")

    def test_business_message_uses_business_strategy(self):
        """For a business-type message, at least some candidates should use 'same_business'."""
        messages = self.loader._messages
        biz_msgs = messages[messages["conversation_type"] == "business"]
        if biz_msgs.empty:
            self.skipTest("No business messages in dataset")

        found = False
        for _, row in biz_msgs.head(10).iterrows():
            _, candidates = self._build_and_fetch(row["message_id"])
            for cand in candidates:
                if "same_business" in cand.get("_retrieval_sources", []):
                    found = True
                    break
            if found:
                break
        self.assertTrue(found, "Expected at least one 'same_business' candidate for business messages")

    def test_group_message_uses_group_strategy(self):
        """For a group-type message, at least some candidates should use 'same_group'."""
        messages = self.loader._messages
        group_msgs = messages[messages["conversation_type"] == "group"]
        if group_msgs.empty:
            self.skipTest("No group messages in dataset")

        found = False
        for _, row in group_msgs.head(10).iterrows():
            _, candidates = self._build_and_fetch(row["message_id"])
            for cand in candidates:
                if "same_group" in cand.get("_retrieval_sources", []):
                    found = True
                    break
            if found:
                break
        self.assertTrue(found, "Expected at least one 'same_group' candidate for group messages")


if __name__ == "__main__":
    unittest.main()
