"""Pipeline validation script for Sprint 7.1 — Decision Engine scaffold.

Chains the full upstream pipeline for all 110 messages, passes outputs
into DecisionEngine.decide(), and asserts that every message returns a
valid default DecisionResult with action="unassigned".
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.loader.data_loader import DataLoader
from code.context.context_builder import ContextBuilder
from code.features.extractor import FeatureExtractor
from code.understanding.understanding_engine import UnderstandingEngine
from code.assessment.assessment_engine import AssessmentEngine
from code.evidence.retrieval_engine import RetrievalEngine
from code.decision.decision_engine import DecisionEngine
from code.decision.models import DecisionResult


def main():
    print("=== Initializing Data Loader and Pipeline Engines ===")
    loader = DataLoader()
    loader.load_all("dataset")

    context_builder      = ContextBuilder(loader)
    feature_extractor    = FeatureExtractor()
    understanding_engine = UnderstandingEngine()
    assessment_engine    = AssessmentEngine()
    retrieval_engine     = RetrievalEngine(loader)
    decision_engine      = DecisionEngine()

    messages_df = loader._messages
    if messages_df is None or messages_df.empty:
        print("Error: No messages found in the dataset.")
        sys.exit(1)

    num_messages = len(messages_df)
    print(f"Loaded {num_messages} messages to process.\n")

    pass_count  = 0
    error_count = 0

    for idx, row in messages_df.iterrows():
        msg_id = row["message_id"]
        print(f"Processing message {idx + 1}/{num_messages} (ID: {msg_id})...")

        try:
            context       = context_builder.build_context(msg_id)
            features      = feature_extractor.extract(context)
            understanding = understanding_engine.analyze(context)
            assessment    = assessment_engine.evaluate(context, understanding, features)
            evidence      = retrieval_engine.retrieve(context, assessment, understanding)
            decision      = decision_engine.decide(features, understanding, assessment, evidence)

            # ── Assertions ────────────────────────────────────────────────────
            assert isinstance(decision, DecisionResult), \
                f"Expected DecisionResult, got {type(decision)}"
            assert decision.action in ("notify", "mute", "digest", "unassigned"), \
                f"Unexpected action '{decision.action}' for {msg_id}"
            assert isinstance(decision.confidence, float), \
                "confidence must be a float"
            assert 0.0 <= decision.confidence <= 1.0, \
                f"confidence out of range: {decision.confidence}"
            assert isinstance(decision.decision_trace, list), \
                "decision_trace must be a list"

            pass_count += 1

        except Exception as e:
            error_count += 1
            print(f"  ERROR for {msg_id}: {e}")

    print(f"\n=== Decision Scaffold Validation Complete ===")
    print(f"Passed: {pass_count}/{num_messages}")
    print(f"Failed: {error_count}/{num_messages}")

    if error_count == 0:
        print("All assertions passed. Decision scaffold is wired correctly.")
    else:
        print("Some assertions failed. Review errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
