"""Validation test script for Sprint 1."""
import os
import sys

# Ensure correct python path to import packages from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.loader.data_loader import DataLoader
from code.context.context_builder import ContextBuilder

def run_tests():
    print("=== Step 1: Initializing DataLoader and Loading CSVs ===")
    loader = DataLoader()
    loader.load_all("dataset")
    
    # Print lengths of loaded DataFrames
    datasets = {
        "messages": loader._messages,
        "users": loader._users,
        "groups": loader._groups,
        "group_members": loader._group_members,
        "business_accounts": loader._business_accounts,
        "user_business_history": loader._user_business_history,
        "message_history": loader._message_history,
        "message_events": loader._message_events,
        "images": loader._images,
        "voice_notes": loader._voice_notes,
        "daily_notification_summary": loader._daily_notification_summary
    }
    for name, df in datasets.items():
        if df is not None:
            print(f"  {name}: {len(df)} rows")
        else:
            print(f"  {name}: Failed to load")

    context_builder = ContextBuilder(loader)

    print("\n=== Steps 2, 3 & 4: Build Context for First Message ===")
    first_msg_id = loader._messages.iloc[0]["message_id"]
    print(f"First message ID: {first_msg_id}")
    ctx = context_builder.build_context(first_msg_id)
    print(f"UnifiedContext populated:")
    print(f"  Metadata: {ctx.metadata}")
    print(f"  Message: {ctx.message}")
    print(f"  User: {ctx.user}")
    print(f"  Sender: {ctx.sender}")
    print(f"  Group: {ctx.group}")
    print(f"  Business: {ctx.business}")
    print(f"  Business History: {ctx.business_history}")
    print(f"  Message History (count): {len(ctx.interaction_history.historical_messages) if ctx.interaction_history else 0}")
    print(f"  Message Events (count): {len(ctx.interaction_history.historical_events) if ctx.interaction_history else 0}")
    print(f"  Notification Summary: {ctx.notification_summary}")
    print(f"  Media Metadata: {ctx.media_metadata}")

    print("\n=== Step 6: Build Context for different Conversation Types ===")
    conversation_types = ["personal", "group", "business"]
    for c_type in conversation_types:
        sample_rows = loader._messages[loader._messages["conversation_type"] == c_type]
        if not sample_rows.empty:
            msg_id = sample_rows.iloc[0]["message_id"]
            ctx_sample = context_builder.build_context(msg_id)
            print(f"  [SUCCESS] Found and built context for '{c_type}' message: {msg_id}")
        else:
            print(f"  [WARNING] No message found for '{c_type}' conversation type")

    print("\n=== Step 7: Build Context for Media Messages ===")
    for m_type in ["image", "voice"]:
        sample_rows = loader._messages[loader._messages["media_type"] == m_type]
        if not sample_rows.empty:
            msg_id = sample_rows.iloc[0]["message_id"]
            ctx_media = context_builder.build_context(msg_id)
            media_path = ctx_media.media_metadata.file_path if ctx_media.media_metadata else None
            print(f"  [SUCCESS] Built media context for '{m_type}' message {msg_id}. Path: {media_path}")
        else:
            print(f"  [WARNING] No message found with media_type == '{m_type}'")

    print("\n=== Step 8: Build Context for Edge Cases (Minimal Message) ===")
    # Find a message with no group, no business, no media, and minimal/no history
    minimal_msg_id = None
    for _, row in loader._messages.iterrows():
        # Check that it's personal, not business, and has no media
        if (row["conversation_type"] == "personal" and 
            (not row["group_id"] or str(row["group_id"]) == "nan" or row["group_id"] == "") and 
            (not row["business_id"] or str(row["business_id"]) == "nan" or row["business_id"] == "") and 
            (not row["media_id"] or str(row["media_id"]) == "nan" or row["media_id"] == "")):
            # Check history
            history_rows = loader.get_message_history(row["user_id"])
            if len(history_rows) == 0:
                minimal_msg_id = row["message_id"]
                break
    if not minimal_msg_id:
        # Fallback to any personal message with no media
        for _, row in loader._messages.iterrows():
            if (row["conversation_type"] == "personal" and 
                (not row["media_id"] or str(row["media_id"]) == "nan" or row["media_id"] == "")):
                minimal_msg_id = row["message_id"]
                break
    if minimal_msg_id:
        ctx_min = context_builder.build_context(minimal_msg_id)
        print(f"  [SUCCESS] Built minimal context for message {minimal_msg_id}")
        print(f"    group={ctx_min.group}, business={ctx_min.business}, media_metadata={ctx_min.media_metadata}, history_count={len(ctx_min.interaction_history.historical_messages) if ctx_min.interaction_history else 0}")
    else:
        print("  [WARNING] Could not find any minimal message sample.")

    print("\n=== Step 9: Stress Test ===")
    total_messages = len(loader._messages)
    success_count = 0
    for _, row in loader._messages.iterrows():
        try:
            ctx_stress = context_builder.build_context(row["message_id"])
            assert ctx_stress is not None
            success_count += 1
        except Exception as e:
            print(f"  [ERROR] Failed to build context for {row['message_id']}: {e}")
            raise e
    print(f"Stress test passed: {success_count} / {total_messages} messages processed successfully.")

if __name__ == "__main__":
    run_tests()
