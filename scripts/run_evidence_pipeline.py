"""End-to-end evidence pipeline execution script (Sprint 6.5).

Runs the full pipeline for all 110 messages in the mock dataset:
  DataLoader → ContextBuilder → FeatureExtractor → UnderstandingEngine
  → AssessmentEngine → RetrievalEngine

Outputs all 110 EvidenceResult objects to output/evidence_dump.json.
"""

import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.loader.data_loader import DataLoader
from code.context.context_builder import ContextBuilder
from code.features.extractor import FeatureExtractor
from code.understanding.understanding_engine import UnderstandingEngine
from code.assessment.assessment_engine import AssessmentEngine
from code.evidence.retrieval_engine import RetrievalEngine


def main():
    print("=== Initializing Data Loader and Pipeline Engines ===")
    loader = DataLoader()
    loader.load_all("dataset")

    context_builder    = ContextBuilder(loader)
    feature_extractor  = FeatureExtractor()
    understanding_engine = UnderstandingEngine()
    assessment_engine  = AssessmentEngine()
    retrieval_engine   = RetrievalEngine(loader)

    messages_df = loader._messages
    if messages_df is None or messages_df.empty:
        print("Error: No messages found in the dataset.")
        sys.exit(1)

    num_messages = len(messages_df)
    print(f"Loaded {num_messages} messages to process.\n")

    os.makedirs("output", exist_ok=True)
    output: dict = {}
    pass_count = 0
    error_count = 0

    for idx, row in messages_df.iterrows():
        msg_id = row["message_id"]
        pass_count += error_count  # recount below
        pass_count = idx + 1 - error_count  # running index
        print(f"Processing message {idx + 1}/{num_messages} (ID: {msg_id})...")

        try:
            context     = context_builder.build_context(msg_id)
            features    = feature_extractor.extract(context)
            understanding = understanding_engine.analyze(context)
            assessment  = assessment_engine.evaluate(context, understanding, features)
            evidence    = retrieval_engine.retrieve(context, assessment, understanding)

            output[msg_id] = evidence.model_dump()

        except Exception as e:
            error_count += 1
            print(f"  ERROR for {msg_id}: {e}")

    output_path = "output/evidence_dump.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    processed = num_messages - error_count
    print(f"\n=== Evidence Pipeline Run Complete ===")
    print(f"Successfully processed: {processed}/{num_messages}")
    print(f"Errors: {error_count}")
    print(f"Output written to: {output_path}")

    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
