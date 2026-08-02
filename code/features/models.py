"""Models defining features and computation lineages (explainability)."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class BaseFeature(BaseModel):
    """Base model for all features to enforce consistent programmatic analysis and explainability."""
    score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    input_values: Dict[str, Any]
    reason: str
    calculation_trace: str

class SenderTrustFeature(BaseFeature):
    messages_read: int
    replies_sent: int
    is_group: bool

class BusinessTrustFeature(BaseFeature):
    verified: bool
    domain_match: bool
    account_age_days: int
    user_reports_30d: int

class RelationshipStrengthFeature(BaseFeature):
    opened_count: int
    replied_count: int
    is_admin: bool

class UrgencyFeature(BaseFeature):
    is_urgent: bool
    matched_keywords: List[str]

class PromotionFeature(BaseFeature):
    matched_promo_keywords: List[str]
    is_retail_category: bool

class SpamRiskFeature(BaseFeature):
    user_reported_30d: int
    forwarded_count: int

class ScamRiskFeature(BaseFeature):
    matched_scam_keywords: List[str]
    verified_business: bool

class ForwardRiskFeature(BaseFeature):
    is_high_risk: bool
    forwarded_count: int

class HistoricalEngagementFeature(BaseFeature):
    opened_30d: int
    dismissed_30d: int
    replied_30d: int

class NotificationFatigueFeature(BaseFeature):
    sent_last_3d: int
    dismissed_last_3d: int

class QuietHoursFeature(BaseFeature):
    is_quiet_hours: bool
    message_time: str
    dnd_window: Optional[str] = None

class TrustFeatures(BaseModel):
    sender_trust: SenderTrustFeature
    business_trust: BusinessTrustFeature
    relationship_strength: RelationshipStrengthFeature

class UrgencyFeatures(BaseModel):
    urgency: UrgencyFeature
    promotion: PromotionFeature

class RiskFeatures(BaseModel):
    spam_risk: SpamRiskFeature
    scam_risk: ScamRiskFeature
    forward_risk: ForwardRiskFeature

class BehaviourFeatures(BaseModel):
    historical_engagement: HistoricalEngagementFeature
    notification_fatigue: NotificationFatigueFeature
    quiet_hours: QuietHoursFeature

class FeatureVector(BaseModel):
    """Parent FeatureVector composed of structured, explainable subgroups."""
    trust: TrustFeatures
    urgency: UrgencyFeatures
    risk: RiskFeatures
    behaviour: BehaviourFeatures
    
    # Placeholders for future media processing sprints
    semantic_summary: Optional[str] = None
    image_summary: Optional[str] = None
    voice_summary: Optional[str] = None
