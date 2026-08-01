"""Validation script for Sprint 2C/2D Feature Extraction."""
import os
import sys
import json

# Ensure correct python path to import packages from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.context.models import (
    Recipient,
    UnifiedContext,
    Message,
    Business,
    BusinessContext,
    Participants,
    Conversation,
    HistoryContext,
    MediaContext,
    NotificationSummary,
    ContextMetadata
)
from code.features.extractor import FeatureExtractor

def validate():
    # 1. Create a mocked ContextMetadata
    metadata = ContextMetadata(
        has_business_context=True,
        has_group_context=False,
        has_historical_evidence=False,
        media_needs_processing=False,
        missing_datasets=[]
    )
    
    # 2. Create a mocked Message (Quiet Hours test: created at 22:19)
    message = Message(
        message_id="msg_mock_001",
        user_id="u_mock_001",
        conversation_type="business",
        business_id="business_mock_001",
        created_at="2026-07-30 22:19",
        forwarded_count=0
    )
    
    # 3. Create a mocked Recipient (Quiet Hours DND window)
    recipient = Recipient(
        user_id="u_mock_001",
        do_not_disturb_window="23:00-08:00",
        messages_opened_30d=10,
        messages_replied_30d=5,
        notifications_dismissed_30d=2,
        messages_reported_30d=0
    )
    
    # 4. Create a mocked Business
    business = Business(
        business_id="business_mock_001",
        display_name="Mock Business",
        verified=True,
        official_domain="mock.com",
        domain_used_by_sender="mock.com",
        account_age_days=937,
        user_reports_30d=3
    )
    
    # 5. Create a mocked NotificationSummary
    notification_summary = NotificationSummary(
        fatigue_score=0.3333333333333333,
        avg_notifications=1.5,
        avg_dismissals=0.5,
        recent_trend="stable",
        sent_last_3d=3,
        dismissed_last_3d=1
    )
    
    # 6. Instantiate UnifiedContext using the domain objects
    context = UnifiedContext(
        recipient=recipient,
        participants=Participants(sender=None, group=None),
        conversation=Conversation(message=message),
        business=BusinessContext(profile=business, history=None),
        media=MediaContext(media_metadata=None),
        history=HistoryContext(interaction_history=None, notification_summary=notification_summary),
        metadata=metadata
    )
    
    # 7. Extract FeatureVector
    extractor = FeatureExtractor()
    feature_vector = extractor.extract(context)
    
    # 8. Print nicely formatted JSON
    print("=== FeatureVector Extracted JSON Output ===")
    dump_fn = getattr(feature_vector, "model_dump", None) or getattr(feature_vector, "dict", None)
    if dump_fn:
        print(json.dumps(dump_fn(), indent=2))
    else:
        print(feature_vector)

if __name__ == "__main__":
    validate()
