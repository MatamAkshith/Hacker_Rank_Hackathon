"""Validation script for Sprint 2C/2D Feature Extraction."""
import os
import sys
import json

# Ensure correct python path to import packages from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.context.models import (
    UnifiedContext,
    Message,
    User,
    Business,
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
    
    # 2. Create a mocked Message
    message = Message(
        message_id="msg_mock_001",
        user_id="u_mock_001",
        conversation_type="business",
        business_id="business_mock_001",
        created_at="2026-07-30 22:19",
        forwarded_count=0
    )
    
    # 3. Create a mocked User (Quiet Hours test: time 22:19 is OUTSIDE 23:00-08:00 DND)
    user = User(
        user_id="u_mock_001",
        do_not_disturb_window="23:00-08:00",
        messages_opened_30d=10,
        messages_replied_30d=5,
        notifications_dismissed_30d=2,
        messages_reported_30d=0
    )
    
    # 4. Create a mocked Business (Business Trust calculation:
    # verified=True, domain_match=True (official == sender), age=937 days, reports=3.
    # Score formula: 1.0*0.4 + 1.0*0.3 + min(937/365, 1.0)*0.2 - min(3/10, 1.0)*0.1 = 0.4 + 0.3 + 0.2 - 0.03 = 0.87)
    business = Business(
        business_id="business_mock_001",
        display_name="Mock Business",
        verified=True,
        official_domain="mock.com",
        domain_used_by_sender="mock.com",
        account_age_days=937,
        user_reports_30d=3
    )
    
    # 5. Create a mocked NotificationSummary (Notification Fatigue test:
    # sent: 1+2=3, dismissed: 0+1=1. Score: 1/3 = 0.3333333333333333)
    notification_summary = NotificationSummary(
        fatigue_score=0.3333333333333333,
        avg_notifications=1.5,
        avg_dismissals=0.5,
        recent_trend="stable",
        sent_last_3d=3,
        dismissed_last_3d=1
    )
    
    # 6. Instantiate UnifiedContext
    context = UnifiedContext(
        metadata=metadata,
        message=message,
        user=user,
        business=business,
        notification_summary=notification_summary
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
