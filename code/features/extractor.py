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
        
        # 4. Historical Engagement (BehaviourFeatures)
        engagement_feat = self._extract_historical_engagement(context)
        
        # 5. Relationship Strength (TrustFeatures)
        rel_strength_feat = self._extract_relationship_strength(context)
        
        # 6. Forward Risk (RiskFeatures)
        forward_risk_feat = self._extract_forward_risk(context)
        
        # Default fallbacks for remaining un-implemented features to satisfy schema validation
        sender_trust_feat = SenderTrustFeature(
            score=0.0,
            messages_read=0,
            replies_sent=0,
            is_group=False
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
        
        # Assemble nested structures
        trust = TrustFeatures(
            sender_trust=sender_trust_feat,
            business_trust=business_trust_feat,
            relationship_strength=rel_strength_feat
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
            historical_engagement=engagement_feat,
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
            parts = created_at.split()
            time_str = parts[-1] if parts else "00:00"
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

    def _extract_historical_engagement(self, context: UnifiedContext) -> HistoricalEngagementFeature:
        usr = context.user
        opened_30d = usr.messages_opened_30d if usr.messages_opened_30d is not None else 0
        replied_30d = usr.messages_replied_30d if usr.messages_replied_30d is not None else 0
        dismissed_30d = usr.notifications_dismissed_30d if usr.notifications_dismissed_30d is not None else 0
        
        total = opened_30d + replied_30d + dismissed_30d
        if total == 0:
            score = 0.5  # Cold start neutral fallback
        else:
            score = (opened_30d * 0.4 + replied_30d * 0.6) / total
            
        score = max(0.0, min(1.0, score))
        return HistoricalEngagementFeature(
            score=score,
            opened_30d=opened_30d,
            dismissed_30d=dismissed_30d,
            replied_30d=replied_30d
        )

    def _extract_relationship_strength(self, context: UnifiedContext) -> RelationshipStrengthFeature:
        sender_id = context.message.sender_user_id
        hist_msgs = context.historical_messages or []
        
        sender_msgs = [m for m in hist_msgs if m.sender_user_id == sender_id] if sender_id else []
        opened_count = sum(1 for m in sender_msgs if m.message_opened)
        replied_count = sum(1 for m in sender_msgs if m.message_replied)
        
        is_admin = False
        if context.sender and context.sender.role == "admin":
            is_admin = True
            
        total_msgs = len(sender_msgs)
        if total_msgs == 0:
            score = 0.2 if is_admin else 0.0
        else:
            base_ratio = (opened_count * 0.4 + replied_count * 0.6) / total_msgs
            admin_bonus = 0.2 if is_admin else 0.0
            score = min(1.0, base_ratio + admin_bonus)
            
        score = max(0.0, min(1.0, score))
        return RelationshipStrengthFeature(
            score=score,
            opened_count=opened_count,
            replied_count=replied_count,
            is_admin=is_admin
        )

    def _extract_forward_risk(self, context: UnifiedContext) -> ForwardRiskFeature:
        count = context.message.forwarded_count if context.message.forwarded_count is not None else 0
        is_high_risk = count >= 5
        return ForwardRiskFeature(
            is_high_risk=is_high_risk,
            forwarded_count=count
        )
