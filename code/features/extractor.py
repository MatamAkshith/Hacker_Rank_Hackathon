"""FeatureExtractor module."""
from datetime import datetime
from typing import Optional
from code.context.models import UnifiedContext
from code.features.models import (
    FeatureVector,
    TrustFeatures,
    UrgencyFeatures,
    RiskFeatures,
    BehaviourFeatures,
    SenderTrustFeature,
    BusinessTrustFeature,
    RelationshipStrengthFeature,
    UrgencyFeature,
    PromotionFeature,
    SpamRiskFeature,
    ScamRiskFeature,
    ForwardRiskFeature,
    HistoricalEngagementFeature,
    NotificationFatigueFeature,
    QuietHoursFeature
)

class FeatureExtractor:
    """Extracts a structured FeatureVector from a UnifiedContext."""
    
    def extract(self, context: UnifiedContext) -> FeatureVector:
        """Extracts and evaluates trust, urgency, risk, and behavioral features from context."""
        
        # 1. Quiet Hours (BehaviourFeatures)
        quiet_hours_feat = self._extract_quiet_hours(context)
        
        # 2. Business Trust (TrustFeatures)
        business_trust_feat = self._extract_business_trust(context)
        
        # 3. Notification Fatigue (BehaviourFeatures)
        fatigue_feat = self._extract_notification_fatigue(context)
        
        # 4. Default fallbacks for the rest of features to satisfy schema validation
        sender_trust_feat = SenderTrustFeature(
            score=0.0,
            messages_read=0,
            replies_sent=0,
            is_group=False
        )
        relationship_strength_feat = RelationshipStrengthFeature(
            score=0.0,
            opened_count=0,
            replied_count=0,
            is_admin=False
        )
        urgency_feat = UrgencyFeature(
            is_urgent=False,
            matched_keywords=[]
        )
        promotion_feat = PromotionFeature(
            score=0.0,
            matched_promo_keywords=[],
            is_retail_category=False
        )
        spam_risk_feat = SpamRiskFeature(
            score=0.0,
            user_reported_30d=0,
            forwarded_count=0
        )
        scam_risk_feat = ScamRiskFeature(
            score=0.0,
            matched_scam_keywords=[],
            verified_business=False
        )
        forward_risk_feat = ForwardRiskFeature(
            is_high_risk=False,
            forwarded_count=0
        )
        historical_engagement_feat = HistoricalEngagementFeature(
            score=0.0,
            opened_30d=0,
            dismissed_30d=0,
            replied_30d=0
        )
        
        # Assemble nested structures
        trust = TrustFeatures(
            sender_trust=sender_trust_feat,
            business_trust=business_trust_feat,
            relationship_strength=relationship_strength_feat
        )
        urgency = UrgencyFeatures(
            urgency=urgency_feat,
            promotion=promotion_feat
        )
        risk = RiskFeatures(
            spam_risk=spam_risk_feat,
            scam_risk=scam_risk_feat,
            forward_risk=forward_risk_feat
        )
        behaviour = BehaviourFeatures(
            historical_engagement=historical_engagement_feat,
            notification_fatigue=fatigue_feat,
            quiet_hours=quiet_hours_feat
        )
        
        return FeatureVector(
            trust=trust,
            urgency=urgency,
            risk=risk,
            behaviour=behaviour
        )

    def _extract_quiet_hours(self, context: UnifiedContext) -> QuietHoursFeature:
        msg = context.message
        usr = context.user
        dnd = usr.do_not_disturb_window
        created_at = msg.created_at
        
        if not dnd or "-" not in dnd:
            return QuietHoursFeature(is_quiet_hours=False, message_time="00:00")
            
        try:
            # Parse message time (supporting "YYYY-MM-DD HH:MM:SS" or just "HH:MM")
            parts = created_at.split()
            time_str = parts[-1] if parts else "00:00"
            # Keep only HH:MM if seconds are present
            time_parts = time_str.split(":")
            hh_mm_str = ":".join(time_parts[:2])
            
            msg_dt = datetime.strptime(hh_mm_str, "%H:%M")
            msg_minutes = msg_dt.hour * 60 + msg_dt.minute
            
            start_str, end_str = dnd.split("-")
            start_dt = datetime.strptime(start_str.strip(), "%H:%M")
            end_dt = datetime.strptime(end_str.strip(), "%H:%M")
            
            start_minutes = start_dt.hour * 60 + start_dt.minute
            end_minutes = end_dt.hour * 60 + end_dt.minute
            
            if start_minutes < end_minutes:
                is_quiet = start_minutes <= msg_minutes <= end_minutes
            else:  # Overnight crossing (e.g. 23:00 - 08:00)
                is_quiet = msg_minutes >= start_minutes or msg_minutes <= end_minutes
                
            return QuietHoursFeature(is_quiet_hours=is_quiet, message_time=hh_mm_str, dnd_window=dnd)
        except Exception:
            return QuietHoursFeature(is_quiet_hours=False, message_time="00:00", dnd_window=dnd)

    def _extract_business_trust(self, context: UnifiedContext) -> BusinessTrustFeature:
        biz = context.business
        if not biz:
            return BusinessTrustFeature(
                score=0.0,
                verified=False,
                domain_match=False,
                account_age_days=0,
                user_reports_30d=0
            )
            
        verified = bool(biz.verified)
        domain_match = False
        if biz.official_domain and biz.domain_used_by_sender:
            domain_match = biz.official_domain.strip().lower() == biz.domain_used_by_sender.strip().lower()
            
        account_age_days = biz.account_age_days if biz.account_age_days is not None else 0
        user_reports_30d = biz.user_reports_30d if biz.user_reports_30d is not None else 0
        
        verified_val = 1.0 if verified else 0.0
        domain_match_val = 1.0 if domain_match else 0.0
        normalized_age = min(account_age_days / 365.0, 1.0)
        normalized_reports = min(user_reports_30d / 10.0, 1.0)
        
        score = (verified_val * 0.4) + (domain_match_val * 0.3) + (normalized_age * 0.2) - (normalized_reports * 0.1)
        score = max(0.0, min(1.0, score))
        
        return BusinessTrustFeature(
            score=score,
            verified=verified,
            domain_match=domain_match,
            account_age_days=account_age_days,
            user_reports_30d=user_reports_30d
        )

    def _extract_notification_fatigue(self, context: UnifiedContext) -> NotificationFatigueFeature:
        summary = context.notification_summary
        if not summary:
            return NotificationFatigueFeature(score=0.0, sent_last_3d=0, dismissed_last_3d=0)
            
        try:
            # Sort by date descending to get most recent summaries
            sorted_summary = sorted(summary, key=lambda x: x.date, reverse=True)
            recent_3 = sorted_summary[:3]
            
            sent_last_3d = sum(n.notifications_sent for n in recent_3)
            dismissed_last_3d = sum(n.notifications_dismissed for n in recent_3)
            
            if sent_last_3d == 0:
                score = 0.0
            else:
                score = dismissed_last_3d / sent_last_3d
                
            score = max(0.0, min(1.0, score))
            return NotificationFatigueFeature(
                score=score,
                sent_last_3d=sent_last_3d,
                dismissed_last_3d=dismissed_last_3d
            )
        except Exception:
            return NotificationFatigueFeature(score=0.0, sent_last_3d=0, dismissed_last_3d=0)
