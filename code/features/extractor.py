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
        
        # 7. Sender Trust (TrustFeatures)
        sender_trust_feat = self._extract_sender_trust(context)
        
        # 8. Urgency (UrgencyFeatures)
        urgency_feat = self._extract_urgency(context)
        
        # 9. Promotion Score (UrgencyFeatures)
        promotion_feat = self._extract_promotion(context)
        
        # 10. Spam Risk (RiskFeatures)
        spam_risk_feat = self._extract_spam_risk(context)
        
        # 11. Scam Risk (RiskFeatures)
        scam_risk_feat = self._extract_scam_risk(context)
        
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
        msg = context.conversation.message
        usr = context.recipient
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
        biz = context.business.profile if context.business else None
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
        summary = context.history.notification_summary if context.history else None
        if not summary:
            return NotificationFatigueFeature(score=0.0, sent_last_3d=0, dismissed_last_3d=0)
            
        return NotificationFatigueFeature(
            score=summary.fatigue_score,
            sent_last_3d=summary.sent_last_3d,
            dismissed_last_3d=summary.dismissed_last_3d
        )

    def _extract_historical_engagement(self, context: UnifiedContext) -> HistoricalEngagementFeature:
        history = context.history.interaction_history if context.history else None
        if history and history.interaction_statistics and history.interaction_statistics.total_messages > 0:
            stats = history.interaction_statistics
            opened_30d = stats.total_opened
            replied_30d = stats.total_replied
            dismissed_30d = stats.total_dismissed
            total = stats.total_messages
        else:
            usr = context.recipient
            opened_30d = usr.messages_opened_30d if usr.messages_opened_30d is not None else 0
            replied_30d = usr.messages_replied_30d if usr.messages_replied_30d is not None else 0
            dismissed_30d = usr.notifications_dismissed_30d if usr.notifications_dismissed_30d is not None else 0
            total = opened_30d + replied_30d + dismissed_30d
            
        if total == 0:
            score = 0.5
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
        sender_id = context.conversation.message.sender_user_id
        history = context.history.interaction_history if context.history else None
        hist_msgs = history.historical_messages if history else []
        
        sender_msgs = [m for m in hist_msgs if m.sender_user_id == sender_id] if sender_id else []
        opened_count = sum(1 for m in sender_msgs if m.message_opened)
        replied_count = sum(1 for m in sender_msgs if m.message_replied)
        
        is_admin = False
        if context.participants and context.participants.sender and context.participants.sender.role == "admin":
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
        count = context.conversation.message.forwarded_count if context.conversation.message.forwarded_count is not None else 0
        is_high_risk = count >= 5
        return ForwardRiskFeature(
            is_high_risk=is_high_risk,
            forwarded_count=count
        )

    def _extract_sender_trust(self, context: UnifiedContext) -> SenderTrustFeature:
        is_group = context.conversation.message.conversation_type == "group"
        sender = context.participants.sender if context.participants else None
        if is_group and sender:
            read_count = sender.messages_read_30d or 0
            replies_count = sender.replies_sent_30d or 0
            score = replies_count / (read_count + 1) if read_count >= 0 else 0.0
        elif context.recipient:
            opened = context.recipient.messages_opened_30d or 0
            replied = context.recipient.messages_replied_30d or 0
            score = replied / (opened + 1) if opened >= 0 else 0.0
            read_count = opened
            replies_count = replied
        else:
            read_count = 0
            replies_count = 0
            score = 0.0
            
        score = max(0.0, min(1.0, score))
        return SenderTrustFeature(
            score=score,
            messages_read=read_count,
            replies_sent=replies_count,
            is_group=is_group
        )

    def _extract_urgency(self, context: UnifiedContext) -> UrgencyFeature:
        text = (context.conversation.message.message_text or "").lower()
        urgency_keywords = ["urgent", "immediately", "asap", "due by", "expires", "deadline", "action required", "attention required", "important update"]
        matched = [kw for kw in urgency_keywords if kw in text]
        return UrgencyFeature(
            is_urgent=len(matched) > 0,
            matched_keywords=matched
        )

    def _extract_promotion(self, context: UnifiedContext) -> PromotionFeature:
        text = (context.conversation.message.message_text or "").lower()
        promo_keywords = ["sale", "discount", "off", "coupon", "promo", "deal", "limited time", "buy now", "free shipping", "cashback", "offer", "save"]
        matched_promo = [kw for kw in promo_keywords if kw in text]
        
        is_retail = False
        biz = context.business.profile if context.business else None
        if biz and biz.category:
            cat = biz.category.lower()
            is_retail = any(c in cat for c in ["shopping", "retail", "e-commerce", "marketing", "store"])
            
        kw_score = min(len(matched_promo) * 0.35, 0.7)
        cat_score = 0.3 if is_retail else 0.0
        score = min(1.0, kw_score + cat_score)
        
        return PromotionFeature(
            score=score,
            matched_promo_keywords=matched_promo,
            is_retail_category=is_retail
        )

    def _extract_spam_risk(self, context: UnifiedContext) -> SpamRiskFeature:
        user_reported = 0
        biz = context.business.profile if context.business else None
        if biz and biz.user_reports_30d is not None:
            user_reported = biz.user_reports_30d
        elif context.recipient and context.recipient.messages_reported_30d is not None:
            user_reported = context.recipient.messages_reported_30d
            
        forwarded_count = context.conversation.message.forwarded_count if context.conversation.message.forwarded_count is not None else 0
        
        report_score = min(user_reported / 10.0, 0.6)
        fwd_score = 0.4 if forwarded_count >= 5 else (0.2 if forwarded_count > 0 else 0.0)
        score = min(1.0, report_score + fwd_score)
        
        return SpamRiskFeature(
            score=score,
            user_reported_30d=user_reported,
            forwarded_count=forwarded_count
        )

    def _extract_scam_risk(self, context: UnifiedContext) -> ScamRiskFeature:
        text = (context.conversation.message.message_text or "").lower()
        scam_keywords = ["otp", "login code", "verify pin", "pay reattempt fee", "release package", "scan qr", "bank account blocked", "urgent action required", "winner", "lottery", "claim reward", "transfer money"]
        matched_scam = [kw for kw in scam_keywords if kw in text]
        
        biz = context.business.profile if context.business else None
        verified_business = bool(biz and biz.verified)
        
        scam_kw_score = min(len(matched_scam) * 0.4, 0.8)
        unverified_penalty = 0.2 if (biz and not verified_business) or (not biz and matched_scam) else 0.0
        
        raw_score = min(1.0, scam_kw_score + unverified_penalty)
        if verified_business:
            raw_score = raw_score * 0.5
            
        score = max(0.0, min(1.0, raw_score))
        return ScamRiskFeature(
            score=score,
            matched_scam_keywords=matched_scam,
            verified_business=verified_business
        )
