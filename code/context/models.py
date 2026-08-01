from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class User(BaseModel):
    user_id: str
    do_not_disturb_window: Optional[str] = None
    messages_opened_30d: int
    messages_replied_30d: int
    notifications_dismissed_30d: int
    messages_reported_30d: int

class Message(BaseModel):
    message_id: str
    user_id: str
    conversation_type: str
    group_id: Optional[str] = None
    business_id: Optional[str] = None
    sender_user_id: Optional[str] = None
    created_at: str
    message_text: Optional[str] = None
    media_type: Optional[str] = None
    media_id: Optional[str] = None
    forwarded_count: Optional[int] = None

class Sender(BaseModel):
    sender_user_id: str
    role: Optional[str] = None
    joined_at: Optional[str] = None
    messages_sent_30d: Optional[int] = None
    messages_read_30d: Optional[int] = None
    replies_sent_30d: Optional[int] = None

class Group(BaseModel):
    group_id: str
    group_name: str
    group_type: str
    member_count: int
    admin_count: int
    created_at: str
    messages_30d: int
    group_muted_by_user: Optional[bool] = None

class Business(BaseModel):
    business_id: str
    display_name: str
    brand_name: Optional[str] = None
    category: Optional[str] = None
    verified: bool
    official_domain: Optional[str] = None
    domain_used_by_sender: Optional[str] = None
    account_age_days: Optional[int] = None
    messages_sent_30d: Optional[int] = None
    user_reports_30d: Optional[int] = None
    domain_used_by_sender_age_days: Optional[int] = None
    
    # Mapped user business interaction history
    why_user_knows_account: Optional[str] = None
    last_activity_at: Optional[str] = None
    allows_promotions: Optional[bool] = None
    promotions_opted_out_at: Optional[str] = None
    activity_count_180d: Optional[int] = None
    messages_opened_30d: Optional[int] = None
    messages_dismissed_30d: Optional[int] = None
    messages_replied_30d: Optional[int] = None
    last_reply_at: Optional[str] = None

class MediaSummary(BaseModel):
    media_id: str
    media_type: str
    file_path: Optional[str] = None
    ocr_text: Optional[str] = None
    asr_transcript: Optional[str] = None
    media_category: Optional[str] = None
    audio_duration_seconds: Optional[float] = None

class HistoricalMessage(BaseModel):
    message_id: str
    user_id: str
    conversation_type: str
    group_id: Optional[str] = None
    business_id: Optional[str] = None
    sender_user_id: Optional[str] = None
    created_at: str
    message_text: Optional[str] = None
    media_type: Optional[str] = None
    media_id: Optional[str] = None
    forwarded_count: Optional[int] = None
    
    # Event metadata (message_events.csv)
    message_opened: Optional[bool] = None
    message_replied: Optional[bool] = None
    reaction_time_minutes: Optional[float] = None
    notification_dismissed: Optional[bool] = None
    muted_after_message: Optional[bool] = None
    message_reported: Optional[bool] = None

class NotificationSummary(BaseModel):
    user_id: str
    date: str
    notifications_sent: int
    notifications_dismissed: int

class ContextMetadata(BaseModel):
    has_business_context: bool
    has_group_context: bool
    has_historical_evidence: bool
    media_needs_processing: bool
    missing_datasets: List[str]

class UnifiedContext(BaseModel):
    metadata: ContextMetadata
    message: Message
    user: User
    sender: Optional[Sender] = None
    group: Optional[Group] = None
    business: Optional[Business] = None
    business_history: Optional[List[Dict[str, Any]]] = None
    historical_messages: List[HistoricalMessage] = []
    historical_events: List[Dict[str, Any]] = []
    notification_summary: Optional[List[NotificationSummary]] = None
    media_metadata: Optional[MediaSummary] = None
