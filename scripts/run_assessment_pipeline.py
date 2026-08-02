import os
import sys
import json

# Ensure package paths are resolved from the workspace root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.loader.data_loader import DataLoader
from code.context.context_builder import ContextBuilder
from code.features.extractor import FeatureExtractor
from code.understanding.understanding_engine import UnderstandingEngine
from code.assessment.assessment_engine import AssessmentEngine

def main():
    print("=== Initializing Data Loader and Pipeline Engines ===")
    loader = DataLoader()
    loader.load_all("dataset")
    
    context_builder = ContextBuilder(loader)
    feature_extractor = FeatureExtractor()
    understanding_engine = UnderstandingEngine()
    assessment_engine = AssessmentEngine()
    
    messages_df = loader._messages
    if messages_df is None or messages_df.empty:
        print("Error: No messages found in the dataset.")
        sys.exit(1)
        
    num_messages = len(messages_df)
    print(f"Loaded {num_messages} messages to process.")
    
    assessments_dict = {}
    
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    processed_count = 0
    error_count = 0
    
    for idx, row in messages_df.iterrows():
        msg_id = row["message_id"]
        processed_count += 1
        print(f"Processing message {processed_count}/{num_messages} (ID: {msg_id})...")
        
        try:
            # 1. Build UnifiedContext
            context = context_builder.build_context(msg_id)
            
            # 2. Extract FeatureVector
            features = feature_extractor.extract(context)
            
            # 3. Extract UnderstandingResult
            understanding = understanding_engine.analyze(context)
            
            # 4. Synthesize MessageAssessment
            assessment = assessment_engine.evaluate(context, understanding, features)
            
            # 5. Serialize
            assessments_dict[msg_id] = assessment.model_dump()
            
        except Exception as e:
            error_count += 1
            print(f"ERROR processing message ID {msg_id}: {str(e)}")
            
    print(f"\nPipeline Run Complete. Successfully processed: {processed_count - error_count}/{num_messages} messages. Errors: {error_count}.")
    
    output_path = os.path.join(output_dir, "assessments_dump.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(assessments_dict, f, indent=2, ensure_ascii=False)
        
    print(f"Assessment pipeline output successfully written to: {output_path}")

if __name__ == "__main__":
    main()
