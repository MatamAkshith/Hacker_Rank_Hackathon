"""Validation script for Sprint 2 Phase 3 Feature Extraction."""
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
    ContextMetadata
)
from code.features.extractor import FeatureExtractor

def validate():
    extractor = FeatureExtractor()
    
    # 1. Normal Message Case
    normal_context = UnifiedContext(
        metadata=ContextMetadata(
            has_business_context=False,
            has_group_context=False,
            has_historical_evidence=False,
            media_needs_processing=False,
            missing_datasets=[]
        ),
        message=Message(
            message_id="msg_normal",
            user_id="u_101",
            conversation_type="personal",
            created_at="2026-07-30 14:00",
            message_text="Hey! Are we still meeting for lunch today at 1 PM?",
            forwarded_count=0
        ),
        user=User(
            user_id="u_101",
            do_not_disturb_window="23:00-08:00",
            messages_opened_30d=20,
            messages_replied_30d=15,
            notifications_dismissed_30d=2,
            messages_reported_30d=0
        )
    )

    # 2. Promotional Message Case
    promo_context = UnifiedContext(
        metadata=ContextMetadata(
            has_business_context=True,
            has_group_context=False,
            has_historical_evidence=False,
            media_needs_processing=False,
            missing_datasets=[]
        ),
        message=Message(
            message_id="msg_promo",
            user_id="u_102",
            conversation_type="business",
            business_id="biz_fashion",
            created_at="2026-07-30 16:00",
            message_text="Flash Sale! Get 50% off on all summer items with coupon SAVE50. Limited time deal, buy now!",
            forwarded_count=0
        ),
        user=User(
            user_id="u_102",
            do_not_disturb_window="23:00-08:00",
            messages_opened_30d=5,
            messages_replied_30d=0,
            notifications_dismissed_30d=10,
            messages_reported_30d=0
        ),
        business=Business(
            business_id="biz_fashion",
            display_name="Fashion Store",
            category="shopping retail",
            verified=True,
            official_domain="fashion.com",
            domain_used_by_sender="fashion.com",
            account_age_days=500,
            user_reports_30d=0
        )
    )

    # 3. High-Risk Phishing / Scam Message Case
    scam_context = UnifiedContext(
        metadata=ContextMetadata(
            has_business_context=False,
            has_group_context=False,
            has_historical_evidence=False,
            media_needs_processing=False,
            missing_datasets=[]
        ),
        message=Message(
            message_id="msg_scam",
            user_id="u_103",
            conversation_type="personal",
            created_at="2026-07-30 02:30",
            message_text="URGENT: Your bank account blocked! Share your login code and OTP immediately to verify pin or pay reattempt fee.",
            forwarded_count=8
        ),
        user=User(
            user_id="u_103",
            do_not_disturb_window="23:00-08:00",
            messages_opened_30d=2,
            messages_replied_30d=0,
            notifications_dismissed_30d=1,
            messages_reported_30d=5
        )
    )

    cases = [
        ("Normal Personal Message", normal_context),
        ("Promotional E-Commerce Message", promo_context),
        ("High-Risk Phishing/Scam Message", scam_context)
    ]

    for title, ctx in cases:
        print(f"\n==========================================")
        print(f"  {title}")
        print(f"==========================================")
        fv = extractor.extract(ctx)
        dump_fn = getattr(fv, "model_dump", None) or getattr(fv, "dict", None)
        print(json.dumps(dump_fn(), indent=2))

if __name__ == "__main__":
    validate()
