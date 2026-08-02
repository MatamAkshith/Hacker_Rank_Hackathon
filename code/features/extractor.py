"""FeatureExtractor module."""
from datetime import datetime
from typing import Optional
from config.feature_weights import (
    BUSINESS_TRUST_ACCOUNT_AGE_NORMALIZER_DAYS,
    BUSINESS_TRUST_ACCOUNT_AGE_WEIGHT,
    BUSINESS_TRUST_DOMAIN_MATCH_WEIGHT,
    BUSINESS_TRUST_REPORTS_NORMALIZER,
    BUSINESS_TRUST_REPORTS_PENALTY_WEIGHT,
    BUSINESS_TRUST_VERIFIED_WEIGHT,
    FORWARD_HIGH_RISK_THRESHOLD,
    HISTORICAL_ENGAGEMENT_COLD_START_SCORE,
    HISTORICAL_ENGAGEMENT_OPENED_WEIGHT,
    HISTORICAL_ENGAGEMENT_REPLIED_WEIGHT,
    PROMOTION_KEYWORD_SCORE_CAP,
    PROMOTION_KEYWORD_WEIGHT,
    PROMOTION_RETAIL_CATEGORY_WEIGHT,
    RELATIONSHIP_ADMIN_BONUS,
    RELATIONSHIP_COLD_START_ADMIN_SCORE,
    RELATIONSHIP_OPENED_WEIGHT,
    RELATIONSHIP_REPLIED_WEIGHT,
    SCAM_KEYWORD_SCORE_CAP,
    SCAM_KEYWORD_WEIGHT,
    SCAM_UNVERIFIED_PENALTY,
    SCAM_VERIFIED_BUSINESS_MULTIPLIER,
    SENDER_TRUST_DENOMINATOR_SMOOTHING,
    SPAM_HIGH_FORWARD_WEIGHT,
    SPAM_LOW_FORWARD_WEIGHT,
    SPAM_REPORT_SCORE_CAP,
    SPAM_REPORTS_NORMALIZER,
)
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
        
        input_values = {
            "do_not_disturb_window": dnd,
            "created_at": created_at
        }
        
        confidence = 1.0 if dnd else 0.5
        
        if not dnd or "-" not in dnd:
            return QuietHoursFeature(
                score=0.0,
                confidence=confidence,
                input_values=input_values,
                reason="DND window not set",
                calculation_trace="0.0 (DND window not set)",
                is_quiet_hours=False,
                message_time="00:00",
                dnd_window=dnd
            )
            
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
                
            score = 1.0 if is_quiet else 0.0
            reason = f"Message time {hh_mm_str} is in DND window {dnd}" if is_quiet else f"Message time {hh_mm_str} is outside DND window {dnd}"
            trace = f"1.0 (quiet)" if is_quiet else f"0.0 (not quiet)"
            return QuietHoursFeature(
                score=score,
                confidence=1.0,
                input_values=input_values,
                reason=reason,
                calculation_trace=trace,
                is_quiet_hours=is_quiet,
                message_time=hh_mm_str,
                dnd_window=dnd
            )
        except Exception as e:
            return QuietHoursFeature(
                score=0.0,
                confidence=0.5,
                input_values=input_values,
                reason=f"Failed to parse time/DND: {str(e)}",
                calculation_trace="0.0 (exception)",
                is_quiet_hours=False,
                message_time="00:00",
                dnd_window=dnd
            )

    def _extract_business_trust(self, context: UnifiedContext) -> BusinessTrustFeature:
        biz = context.business.profile if context.business else None
        
        input_values = {
            "verified": biz.verified if biz else None,
            "official_domain": biz.official_domain if biz else None,
            "domain_used_by_sender": biz.domain_used_by_sender if biz else None,
            "account_age_days": biz.account_age_days if biz else None,
            "user_reports_30d": biz.user_reports_30d if biz else None
        }
        
        if not biz:
            return BusinessTrustFeature(
                score=0.0,
                confidence=0.0,
                input_values=input_values,
                reason="Not a business account or missing business profile",
                calculation_trace="0.0 (No business)",
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
        normalized_age = min(account_age_days / BUSINESS_TRUST_ACCOUNT_AGE_NORMALIZER_DAYS, 1.0)
        normalized_reports = min(user_reports_30d / BUSINESS_TRUST_REPORTS_NORMALIZER, 1.0)
        
        score = (
            (verified_val * BUSINESS_TRUST_VERIFIED_WEIGHT)
            + (domain_match_val * BUSINESS_TRUST_DOMAIN_MATCH_WEIGHT)
            + (normalized_age * BUSINESS_TRUST_ACCOUNT_AGE_WEIGHT)
            - (normalized_reports * BUSINESS_TRUST_REPORTS_PENALTY_WEIGHT)
        )
        score = max(0.0, min(1.0, score))
        
        trace = (
            f"({verified_val} * {BUSINESS_TRUST_VERIFIED_WEIGHT}) + "
            f"({domain_match_val} * {BUSINESS_TRUST_DOMAIN_MATCH_WEIGHT}) + "
            f"({normalized_age:.3f} * {BUSINESS_TRUST_ACCOUNT_AGE_WEIGHT}) - "
            f"({normalized_reports:.3f} * {BUSINESS_TRUST_REPORTS_PENALTY_WEIGHT})"
        )
        
        reasons = []
        if verified:
            reasons.append("verified business")
        if domain_match:
            reasons.append("domain matched")
        if account_age_days > 0:
            reasons.append(f"age: {account_age_days} days")
        if user_reports_30d > 0:
            reasons.append(f"{user_reports_30d} reports")
        reason = ", ".join(reasons) if reasons else "no specific signals"
        
        return BusinessTrustFeature(
            score=score,
            confidence=1.0,
            input_values=input_values,
            reason=reason,
            calculation_trace=trace,
            verified=verified,
            domain_match=domain_match,
            account_age_days=account_age_days,
            user_reports_30d=user_reports_30d
        )

    def _extract_notification_fatigue(self, context: UnifiedContext) -> NotificationFatigueFeature:
        summary = context.history.notification_summary if context.history else None
        
        input_values = {
            "fatigue_score": summary.fatigue_score if summary else None,
            "sent_last_3d": summary.sent_last_3d if summary else None,
            "dismissed_last_3d": summary.dismissed_last_3d if summary else None
        }
        
        if not summary:
            return NotificationFatigueFeature(
                score=0.0,
                confidence=0.0,
                input_values=input_values,
                reason="No notification summary available",
                calculation_trace="0.0 (No history)",
                sent_last_3d=0,
                dismissed_last_3d=0
            )
            
        trace = f"{summary.fatigue_score:.3f} (direct fatigue_score from NotificationSummary)"
        reason = f"Fatigue score {summary.fatigue_score:.2f} based on {summary.dismissed_last_3d} dismissals out of {summary.sent_last_3d} sent in last 3 days"
        
        return NotificationFatigueFeature(
            score=summary.fatigue_score,
            confidence=1.0,
            input_values=input_values,
            reason=reason,
            calculation_trace=trace,
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
            source = "interaction_statistics"
        else:
            usr = context.recipient
            opened_30d = usr.messages_opened_30d if usr.messages_opened_30d is not None else 0
            replied_30d = usr.messages_replied_30d if usr.messages_replied_30d is not None else 0
            dismissed_30d = usr.notifications_dismissed_30d if usr.notifications_dismissed_30d is not None else 0
            total = opened_30d + replied_30d + dismissed_30d
            source = "recipient_profile"
            
        input_values = {
            "opened_30d": opened_30d,
            "replied_30d": replied_30d,
            "dismissed_30d": dismissed_30d,
            "total_messages": total,
            "source": source
        }
        
        if total == 0:
            score = HISTORICAL_ENGAGEMENT_COLD_START_SCORE
            trace = f"{HISTORICAL_ENGAGEMENT_COLD_START_SCORE} (cold start default)"
            reason = "No historical engagement logs; using cold start default score"
            confidence = 0.5
        else:
            score = (
                opened_30d * HISTORICAL_ENGAGEMENT_OPENED_WEIGHT
                + replied_30d * HISTORICAL_ENGAGEMENT_REPLIED_WEIGHT
            ) / total
            score = max(0.0, min(1.0, score))
            trace = f"({opened_30d} * {HISTORICAL_ENGAGEMENT_OPENED_WEIGHT} + {replied_30d} * {HISTORICAL_ENGAGEMENT_REPLIED_WEIGHT}) / {total}"
            reason = f"Historical engagement score {score:.2f} computed from {source} (opened={opened_30d}, replied={replied_30d}, total={total})"
            confidence = 1.0
            
        return HistoricalEngagementFeature(
            score=score,
            confidence=confidence,
            input_values=input_values,
            reason=reason,
            calculation_trace=trace,
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
        
        input_values = {
            "sender_user_id": sender_id,
            "sender_messages_count": total_msgs,
            "opened_count": opened_count,
            "replied_count": replied_count,
            "is_admin": is_admin
        }
        
        if total_msgs == 0:
            score = RELATIONSHIP_COLD_START_ADMIN_SCORE if is_admin else 0.0
            trace = f"{RELATIONSHIP_COLD_START_ADMIN_SCORE if is_admin else 0.0} (cold start)"
            reason = "No sender interaction history; using cold start"
            confidence = 0.5
        else:
            base_ratio = (
                opened_count * RELATIONSHIP_OPENED_WEIGHT
                + replied_count * RELATIONSHIP_REPLIED_WEIGHT
            ) / total_msgs
            admin_bonus = RELATIONSHIP_ADMIN_BONUS if is_admin else 0.0
            score = min(1.0, base_ratio + admin_bonus)
            score = max(0.0, min(1.0, score))
            trace = f"min(1.0, ({opened_count} * {RELATIONSHIP_OPENED_WEIGHT} + {replied_count} * {RELATIONSHIP_REPLIED_WEIGHT}) / {total_msgs} + {admin_bonus})"
            reason = f"Relationship strength {score:.2f} based on {total_msgs} messages from sender (opened={opened_count}, replied={replied_count}, is_admin={is_admin})"
            confidence = 1.0
            
        return RelationshipStrengthFeature(
            score=score,
            confidence=confidence,
            input_values=input_values,
            reason=reason,
            calculation_trace=trace,
            opened_count=opened_count,
            replied_count=replied_count,
            is_admin=is_admin
        )

    def _extract_forward_risk(self, context: UnifiedContext) -> ForwardRiskFeature:
        count = context.conversation.message.forwarded_count if context.conversation.message.forwarded_count is not None else 0
        is_high_risk = count >= FORWARD_HIGH_RISK_THRESHOLD
        
        input_values = {
            "forwarded_count": count
        }
        
        score = 1.0 if is_high_risk else (count / FORWARD_HIGH_RISK_THRESHOLD)
        score = max(0.0, min(1.0, score))
        
        trace = f"1.0 (high risk: {count} >= {FORWARD_HIGH_RISK_THRESHOLD})" if is_high_risk else f"{count} / {FORWARD_HIGH_RISK_THRESHOLD}"
        reason = f"Message forwarded {count} times (high risk)" if is_high_risk else f"Message forwarded {count} times"
        
        return ForwardRiskFeature(
            score=score,
            confidence=1.0,
            input_values=input_values,
            reason=reason,
            calculation_trace=trace,
            is_high_risk=is_high_risk,
            forwarded_count=count
        )

    def _extract_sender_trust(self, context: UnifiedContext) -> SenderTrustFeature:
        is_group = context.conversation.message.conversation_type == "group"
        sender = context.participants.sender if context.participants else None
        
        if is_group and sender:
            read_count = sender.messages_read_30d or 0
            replies_count = sender.replies_sent_30d or 0
            score = (
                replies_count / (read_count + SENDER_TRUST_DENOMINATOR_SMOOTHING)
                if read_count >= 0
                else 0.0
            )
            source = "sender_profile"
        elif context.recipient:
            opened = context.recipient.messages_opened_30d or 0
            replied = context.recipient.messages_replied_30d or 0
            score = (
                replied / (opened + SENDER_TRUST_DENOMINATOR_SMOOTHING)
                if opened >= 0
                else 0.0
            )
            read_count = opened
            replies_count = replied
            source = "recipient_profile"
        else:
            read_count = 0
            replies_count = 0
            score = 0.0
            source = "none"
            
        score = max(0.0, min(1.0, score))
        
        input_values = {
            "is_group": is_group,
            "read_count": read_count,
            "replies_count": replies_count,
            "source": source
        }
        
        trace = f"{replies_count} / ({read_count} + {SENDER_TRUST_DENOMINATOR_SMOOTHING})"
        reason = f"Sender trust {score:.2f} computed from {source} (read/opened={read_count}, replies={replies_count})"
        confidence = 1.0 if source != "none" else 0.0
        
        return SenderTrustFeature(
            score=score,
            confidence=confidence,
            input_values=input_values,
            reason=reason,
            calculation_trace=trace,
            messages_read=read_count,
            replies_sent=replies_count,
            is_group=is_group
        )

    def _extract_urgency(self, context: UnifiedContext) -> UrgencyFeature:
        text = (context.conversation.message.message_text or "").lower()
        urgency_keywords = ["urgent", "immediately", "asap", "due by", "expires", "deadline", "action required", "attention required", "important update"]
        matched = [kw for kw in urgency_keywords if kw in text]
        is_urgent = len(matched) > 0
        
        input_values = {
            "message_text": text,
            "urgency_keywords": urgency_keywords
        }
        
        score = 1.0 if is_urgent else 0.0
        trace = f"1.0 (matched keywords: {matched})" if is_urgent else "0.0 (no matching keywords)"
        reason = f"Urgency keywords matched: {matched}" if is_urgent else "No urgency keywords matched"
        confidence = 1.0 if text else 0.5
        
        return UrgencyFeature(
            score=score,
            confidence=confidence,
            input_values=input_values,
            reason=reason,
            calculation_trace=trace,
            is_urgent=is_urgent,
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
            
        kw_score = min(
            len(matched_promo) * PROMOTION_KEYWORD_WEIGHT,
            PROMOTION_KEYWORD_SCORE_CAP,
        )
        cat_score = PROMOTION_RETAIL_CATEGORY_WEIGHT if is_retail else 0.0
        score = min(1.0, kw_score + cat_score)
        
        input_values = {
            "message_text": text,
            "promo_keywords_count": len(matched_promo),
            "is_retail_category": is_retail
        }
        
        trace = f"min(1.0, min(len({matched_promo}) * {PROMOTION_KEYWORD_WEIGHT}, {PROMOTION_KEYWORD_SCORE_CAP}) + {cat_score})"
        reason = f"Promotion score {score:.2f} based on keywords {matched_promo} and retail category = {is_retail}"
        confidence = 1.0 if text else 0.5
        
        return PromotionFeature(
            score=score,
            confidence=confidence,
            input_values=input_values,
            reason=reason,
            calculation_trace=trace,
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
        
        report_score = min(user_reported / SPAM_REPORTS_NORMALIZER, SPAM_REPORT_SCORE_CAP)
        fwd_score = (
            SPAM_HIGH_FORWARD_WEIGHT
            if forwarded_count >= FORWARD_HIGH_RISK_THRESHOLD
            else (SPAM_LOW_FORWARD_WEIGHT if forwarded_count > 0 else 0.0)
        )
        score = min(1.0, report_score + fwd_score)
        
        input_values = {
            "user_reported_30d": user_reported,
            "forwarded_count": forwarded_count
        }
        
        trace = f"min(1.0, min({user_reported} / {SPAM_REPORTS_NORMALIZER}, {SPAM_REPORT_SCORE_CAP}) + {fwd_score})"
        reason = f"Spam risk {score:.2f} calculated from {user_reported} user reports and {forwarded_count} forwards"
        confidence = 1.0
        
        return SpamRiskFeature(
            score=score,
            confidence=confidence,
            input_values=input_values,
            reason=reason,
            calculation_trace=trace,
            user_reported_30d=user_reported,
            forwarded_count=forwarded_count
        )

    def _extract_scam_risk(self, context: UnifiedContext) -> ScamRiskFeature:
        text = (context.conversation.message.message_text or "").lower()
        scam_keywords = ["otp", "login code", "verify pin", "pay reattempt fee", "release package", "scan qr", "bank account blocked", "urgent action required", "winner", "lottery", "claim reward", "transfer money"]
        matched_scam = [kw for kw in scam_keywords if kw in text]
        
        biz = context.business.profile if context.business else None
        verified_business = bool(biz and biz.verified)
        
        scam_kw_score = min(
            len(matched_scam) * SCAM_KEYWORD_WEIGHT,
            SCAM_KEYWORD_SCORE_CAP,
        )
        unverified_penalty = (
            SCAM_UNVERIFIED_PENALTY
            if (biz and not verified_business) or (not biz and matched_scam)
            else 0.0
        )
        
        raw_score = min(1.0, scam_kw_score + unverified_penalty)
        if verified_business:
            raw_score = raw_score * SCAM_VERIFIED_BUSINESS_MULTIPLIER
            
        score = max(0.0, min(1.0, raw_score))
        
        input_values = {
            "message_text": text,
            "matched_scam_keywords_count": len(matched_scam),
            "verified_business": verified_business
        }
        
        trace_steps = f"min(1.0, min(len({matched_scam}) * {SCAM_KEYWORD_WEIGHT}, {SCAM_KEYWORD_SCORE_CAP}) + {unverified_penalty})"
        if verified_business:
            trace = f"({trace_steps}) * {SCAM_VERIFIED_BUSINESS_MULTIPLIER}"
        else:
            trace = trace_steps
            
        reason = f"Scam risk {score:.2f} based on keywords {matched_scam} and verified_business={verified_business}"
        confidence = 1.0 if text else 0.5
        
        return ScamRiskFeature(
            score=score,
            confidence=confidence,
            input_values=input_values,
            reason=reason,
            calculation_trace=trace,
            matched_scam_keywords=matched_scam,
            verified_business=verified_business
        )
