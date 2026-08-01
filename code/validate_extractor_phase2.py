"""Validation script for Sprint 2 Phase 2 Feature Extraction."""
import os
import sys
import json

# Ensure correct python path to import packages from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.context.models import (
    Recipient,
    UnifiedContext,
    Message,
    Sender,
    HistoricalMessage,
    ContextMetadata,
    InteractionStatistics,
    InteractionHistory,
    Participants,
    Conversation,
    BusinessContext,
    MediaContext,
    HistoryContext
)
from code.features.extractor import FeatureExtractor

def validate():
    # 1. Create ContextMetadata
    metadata = ContextMetadata(
        has_business_context=False,
        has_group_context=True,
        has_historical_evidence=True,
        media_needs_processing=False,
        missing_datasets=[]
    )
    
    # 2. Create Message (Forwarded count = 7 -> Forward risk is_high_risk = True)
    message = Message(
        message_id="msg_phase2_001",
        user_id="u_phase2_recipient",
        conversation_type="group",
        group_id="g_phase2_001",
        sender_user_id="u_phase2_sender",
        created_at="2026-07-30 14:30",
        forwarded_count=7
    )
    
    # 3. Create Recipient
    recipient = Recipient(
        user_id="u_phase2_recipient",
        do_not_disturb_window="23:00-08:00",
        messages_opened_30d=10,
        messages_replied_30d=5,
        notifications_dismissed_30d=5,
        messages_reported_30d=0
    )
    
    # 4. Create Sender (role="admin")
    sender = Sender(
        sender_user_id="u_phase2_sender",
        role="admin"
    )
    
    # 5. Create Historical Messages from this sender (5 messages total: 4 opened, 2 replied)
    historical_messages = [
        HistoricalMessage(message_id="hist_1", user_id="u_phase2_recipient", conversation_type="group", sender_user_id="u_phase2_sender", created_at="2026-07-20 10:00", message_opened=True, message_replied=True),
        HistoricalMessage(message_id="hist_2", user_id="u_phase2_recipient", conversation_type="group", sender_user_id="u_phase2_sender", created_at="2026-07-21 11:00", message_opened=True, message_replied=True),
        HistoricalMessage(message_id="hist_3", user_id="u_phase2_recipient", conversation_type="group", sender_user_id="u_phase2_sender", created_at="2026-07-22 12:00", message_opened=True, message_replied=False),
        HistoricalMessage(message_id="hist_4", user_id="u_phase2_recipient", conversation_type="group", sender_user_id="u_phase2_sender", created_at="2026-07-23 13:00", message_opened=True, message_replied=False),
        HistoricalMessage(message_id="hist_5", user_id="u_phase2_recipient", conversation_type="group", sender_user_id="u_phase2_sender", created_at="2026-07-24 14:00", message_opened=False, message_replied=False)
    ]
    
    interaction_history = InteractionHistory(
        historical_messages=historical_messages,
        historical_events=[],
        interaction_statistics=InteractionStatistics(
            total_messages=5,
            total_opened=4,
            total_replied=2,
            total_dismissed=0,
            open_rate=0.8,
            reply_rate=0.4,
            dismissal_rate=0.0
        )
    )
    
    context = UnifiedContext(
        recipient=recipient,
        participants=Participants(sender=sender, group=None),
        conversation=Conversation(message=message),
        business=None,
        media=MediaContext(media_metadata=None),
        history=HistoryContext(interaction_history=interaction_history, notification_summary=None),
        metadata=metadata
    )
    
    extractor = FeatureExtractor()
    feature_vector = extractor.extract(context)
    
    print("=== Phase 2 FeatureVector Extracted JSON Output ===")
    dump_fn = getattr(feature_vector, "model_dump", None) or getattr(feature_vector, "dict", None)
    if dump_fn:
        print(json.dumps(dump_fn(), indent=2))
    else:
        print(feature_vector)

if __name__ == "__main__":
    validate()
