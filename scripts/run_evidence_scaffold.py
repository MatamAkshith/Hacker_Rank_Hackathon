import os
import sys

# Ensure package paths are resolved from the workspace root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.loader.data_loader import DataLoader
from code.context.context_builder import ContextBuilder
from code.features.extractor import FeatureExtractor
from code.understanding.understanding_engine import UnderstandingEngine
from code.assessment.assessment_engine import AssessmentEngine
from code.evidence.retrieval_engine import RetrievalEngine
from code.evidence.models import EvidenceResult

def main():
    print("=== Initializing Data Loader and Pipeline Engines ===")
    loader = DataLoader()
    loader.load_all("dataset")
    
    context_builder = ContextBuilder(loader)
    feature_extractor = FeatureExtractor()
    understanding_engine = UnderstandingEngine()
    assessment_engine = AssessmentEngine()
    retrieval_engine = RetrievalEngine(loader)
    
    messages_df = loader._messages
    if messages_df is None or messages_df.empty:
        print("Error: No messages found in the dataset.")
        sys.exit(1)
        
    num_messages = len(messages_df)
    print(f"Loaded {num_messages} messages to process.\n")
    
    pass_count = 0
    fail_count = 0
    
    for idx, row in messages_df.iterrows():
        msg_id = row["message_id"]
        print(f"Processing message {pass_count + fail_count + 1}/{num_messages} (ID: {msg_id})...")
        
        try:
            # Build context and run assessment pipeline
            context = context_builder.build_context(msg_id)
            features = feature_extractor.extract(context)
            understanding = understanding_engine.analyze(context)
            assessment = assessment_engine.evaluate(context, understanding, features)
            
            # Run Evidence Retrieval Engine
            evidence = retrieval_engine.retrieve(context, assessment, understanding)
            
            # Assertions
            assert isinstance(evidence, EvidenceResult), f"Expected EvidenceResult, got {type(evidence)}"
            assert evidence.retrieval_status == "retrieval_complete", \
                f"Expected retrieval_status='retrieval_complete', got '{evidence.retrieval_status}'"
            assert isinstance(evidence.top_evidence, list), "top_evidence must be a list"
            
            pass_count += 1
            
        except Exception as e:
            fail_count += 1
            print(f"  ERROR for message {msg_id}: {str(e)}")
            
    print(f"\n=== Evidence Scaffold Validation Complete ===")
    print(f"Passed: {pass_count}/{num_messages}")
    print(f"Failed: {fail_count}/{num_messages}")
    
    if fail_count == 0:
        print("All assertions passed. Evidence scaffold is wired correctly.")
    else:
        print("Some assertions failed. Review errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
