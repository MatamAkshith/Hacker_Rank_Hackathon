"""ContextBuilder class to assemble UnifiedContext objects."""
from typing import Any, Dict, List, Optional
from code.loader.data_loader import DataLoader
from code.context.models import (
    User,
    Message,
    Sender,
    Group,
    Business,
    BusinessHistory,
    MediaSummary,
    HistoricalMessage,
    NotificationSummary,
    ContextMetadata,
    InteractionStatistics,
    InteractionHistory,
    UnifiedContext
)

class ContextBuilder:
    """Assembles the complete context required for a single message using raw data from DataLoader."""
    
    def __init__(self, loader: DataLoader):
        self.loader = loader

    def build_context(self, message_id: str) -> UnifiedContext:
        """Builds a typed UnifiedContext for the given message_id. Never returns None."""
        missing_datasets = []
        
        try:
            msg_dict = self.loader.get_message(message_id)
        except Exception:
            msg_dict = None

        if not msg_dict:
            missing_datasets.append("messages.csv")
            msg_dict = {
                "message_id": message_id,
                "user_id": "unknown_user",
                "conversation_type": "individual",
                "created_at": "1970-01-01 00:00:00"
            }
        
        user_id = msg_dict.get("user_id", "unknown_user")
        try:
            user_dict = self.loader.get_user(user_id)
        except Exception:
            user_dict = None

        if not user_dict:
            missing_datasets.append("users.csv")
            user_dict = {
                "user_id": user_id,
                "messages_opened_30d": 0,
                "messages_replied_30d": 0,
                "notifications_dismissed_30d": 0,
                "messages_reported_30d": 0
            }
        
        user = User(**user_dict)
        message = Message(**msg_dict)
        
        # 1. Fetch Sender (failsafe)
        sender = None
        sender_user_id = msg_dict.get("sender_user_id")
        if sender_user_id:
            try:
                sender_dict = {"sender_user_id": sender_user_id}
                if msg_dict.get("conversation_type") == "group" and msg_dict.get("group_id"):
                    members = self.loader.get_group_members(msg_dict["group_id"])
                    member_info = next((m for m in members if m.get("user_id") == sender_user_id), None)
                    if member_info:
                        sender_dict.update({
                            "role": member_info.get("role"),
                            "joined_at": member_info.get("joined_at"),
                            "messages_sent_30d": member_info.get("messages_sent_30d"),
                            "messages_read_30d": member_info.get("messages_read_30d"),
                            "replies_sent_30d": member_info.get("replies_sent_30d")
                        })
                sender = Sender(**sender_dict)
            except Exception:
                sender = Sender(sender_user_id=sender_user_id)
            
        # 2. Fetch Group (failsafe)
        group = None
        if msg_dict.get("conversation_type") == "group" and msg_dict.get("group_id"):
            group_id = msg_dict["group_id"]
            try:
                group_dict = self.loader.get_group(group_id)
                if not group_dict:
                    missing_datasets.append("groups.csv")
                else:
                    members = self.loader.get_group_members(group_id)
                    user_member = next((m for m in members if m.get("user_id") == user_id), None)
                    if user_member:
                        group_dict["group_muted_by_user"] = bool(user_member.get("group_muted_by_user"))
                    group = Group(**group_dict)
            except Exception:
                missing_datasets.append("groups.csv")
                
        # 3. Fetch Business profile and history (failsafe)
        business = None
        business_history = None
        if msg_dict.get("conversation_type") == "business" and msg_dict.get("business_id"):
            business_id = msg_dict["business_id"]
            try:
                biz_dict = self.loader.get_business(business_id)
                if not biz_dict:
                    missing_datasets.append("business_accounts.csv")
                
                biz_hist = self.loader.get_user_business_history(user_id, business_id)
                if biz_hist:
                    business_history = BusinessHistory(**biz_hist)
                else:
                    missing_datasets.append("user_business_history.csv")
                    
                if biz_dict:
                    if biz_hist:
                        biz_dict.update({
                            "why_user_knows_account": biz_hist.get("why_user_knows_account"),
                            "last_activity_at": biz_hist.get("last_activity_at"),
                            "allows_promotions": bool(biz_hist.get("allows_promotions")) if biz_hist.get("allows_promotions") is not None else None,
                            "promotions_opted_out_at": biz_hist.get("promotions_opted_out_at"),
                            "activity_count_180d": biz_hist.get("activity_count_180d"),
                            "messages_opened_30d": biz_hist.get("messages_opened_30d"),
                            "messages_dismissed_30d": biz_hist.get("messages_dismissed_30d"),
                            "messages_replied_30d": biz_hist.get("messages_replied_30d"),
                            "last_reply_at": biz_hist.get("last_reply_at")
                        })
                    biz_dict["verified"] = bool(biz_dict.get("verified"))
                    business = Business(**biz_dict)
            except Exception:
                missing_datasets.append("business_accounts.csv")

        # 4. Fetch Message History and corresponding Events (failsafe)
        historical_messages = []
        historical_events = []
        try:
            history_dicts = self.loader.get_message_history(user_id)
            if history_dicts:
                history_ids = [h["message_id"] for h in history_dicts]
                historical_events = self.loader.get_message_events(history_ids)
                events_map = {e["message_id"]: e for e in historical_events}
                
                for h in history_dicts:
                    h_id = h["message_id"]
                    evt = events_map.get(h_id, {})
                    hist_msg_dict = dict(h)
                    hist_msg_dict.update({
                        "message_opened": bool(evt.get("message_opened")) if evt.get("message_opened") is not None else None,
                        "message_replied": bool(evt.get("message_replied")) if evt.get("message_replied") is not None else None,
                        "reaction_time_minutes": evt.get("reaction_time_minutes"),
                        "notification_dismissed": bool(evt.get("notification_dismissed")) if evt.get("notification_dismissed") is not None else None,
                        "muted_after_message": bool(evt.get("muted_after_message")) if evt.get("muted_after_message") is not None else None,
                        "message_reported": bool(evt.get("message_reported")) if evt.get("message_reported") is not None else None,
                    })
                    historical_messages.append(HistoricalMessage(**hist_msg_dict))
        except Exception:
            missing_datasets.append("message_history.csv")

        # Construct unified InteractionHistory object
        interaction_history = None
        if historical_messages or historical_events:
            total_msgs = len(historical_messages)
            total_opened = sum(1 for m in historical_messages if m.message_opened)
            total_replied = sum(1 for m in historical_messages if m.message_replied)
            total_dismissed = sum(1 for m in historical_messages if m.notification_dismissed)
            
            open_rate = total_opened / total_msgs if total_msgs > 0 else 0.0
            reply_rate = total_replied / total_msgs if total_msgs > 0 else 0.0
            dismissal_rate = total_dismissed / total_msgs if total_msgs > 0 else 0.0
            
            interaction_history = InteractionHistory(
                historical_messages=historical_messages,
                historical_events=historical_events,
                interaction_statistics=InteractionStatistics(
                    total_messages=total_msgs,
                    total_opened=total_opened,
                    total_replied=total_replied,
                    total_dismissed=total_dismissed,
                    open_rate=open_rate,
                    reply_rate=reply_rate,
                    dismissal_rate=dismissal_rate
                )
            )

        # 5. Fetch Daily Notification summary and pre-aggregate (failsafe)
        notification_summary = None
        try:
            notif_dicts = self.loader.get_notification_summary(user_id)
            if notif_dicts:
                sorted_notifs = sorted(notif_dicts, key=lambda x: x.get("date", ""), reverse=True)
                total_sent = sum(n.get("notifications_sent", 0) for n in sorted_notifs)
                total_dismissed = sum(n.get("notifications_dismissed", 0) for n in sorted_notifs)
                num_days = len(sorted_notifs)
                
                avg_notifications = total_sent / num_days if num_days > 0 else 0.0
                avg_dismissals = total_dismissed / num_days if num_days > 0 else 0.0
                
                recent_3 = sorted_notifs[:3]
                sent_last_3d = sum(n.get("notifications_sent", 0) for n in recent_3)
                dismissed_last_3d = sum(n.get("notifications_dismissed", 0) for n in recent_3)
                fatigue_score = dismissed_last_3d / sent_last_3d if sent_last_3d > 0 else 0.0
                fatigue_score = max(0.0, min(1.0, fatigue_score))
                
                recent_avg = sent_last_3d / len(recent_3) if recent_3 else 0.0
                if recent_avg > avg_notifications * 1.2:
                    recent_trend = "spiking"
                elif recent_avg < avg_notifications * 0.8:
                    recent_trend = "declining"
                else:
                    recent_trend = "stable"
                    
                notification_summary = NotificationSummary(
                    fatigue_score=fatigue_score,
                    avg_notifications=avg_notifications,
                    avg_dismissals=avg_dismissals,
                    recent_trend=recent_trend,
                    sent_last_3d=sent_last_3d,
                    dismissed_last_3d=dismissed_last_3d
                )
            else:
                notification_summary = NotificationSummary(
                    fatigue_score=0.0,
                    avg_notifications=0.0,
                    avg_dismissals=0.0,
                    recent_trend="unknown",
                    sent_last_3d=0,
                    dismissed_last_3d=0
                )
        except Exception:
            missing_datasets.append("daily_notification_summary.csv")
        
        # 6. Fetch Media details (failsafe)
        media_metadata = None
        media_type = msg_dict.get("media_type")
        media_id = msg_dict.get("media_id")
        if media_id and media_type:
            try:
                if media_type == "image":
                    img_dict = self.loader.get_image(media_id)
                    if img_dict:
                        media_metadata = MediaSummary(
                            media_id=media_id,
                            media_type=media_type,
                            file_path=img_dict.get("file_path")
                        )
                    else:
                        missing_datasets.append("images.csv")
                elif media_type == "voice":
                    voice_dict = self.loader.get_voice(media_id)
                    if voice_dict:
                        media_metadata = MediaSummary(
                            media_id=media_id,
                            media_type=media_type,
                            file_path=voice_dict.get("file_path")
                        )
                    else:
                        missing_datasets.append("voice_notes.csv")
            except Exception:
                missing_datasets.append("images.csv" if media_type == "image" else "voice_notes.csv")

        # Evaluate ContextMetadata completeness
        has_business_context = business is not None
        has_group_context = group is not None
        has_historical_evidence = historical_messages is not None and len(historical_messages) > 0
        media_needs_processing = media_metadata is not None and media_type in ("image", "voice")
        
        has_media = bool(media_type)
        needs_ocr = media_type == "image"
        needs_asr = media_type == "voice"
        history_depth = len(historical_messages) if historical_messages else 0
        business_known = business_history is not None
        group_muted = bool(group.group_muted_by_user) if group is not None else False
        
        metadata = ContextMetadata(
            has_business_context=has_business_context,
            has_group_context=has_group_context,
            has_historical_evidence=has_historical_evidence,
            media_needs_processing=media_needs_processing,
            missing_datasets=missing_datasets,
            has_media=has_media,
            needs_ocr=needs_ocr,
            needs_asr=needs_asr,
            history_depth=history_depth,
            business_known=business_known,
            group_muted=group_muted
        )

        return UnifiedContext(
            metadata=metadata,
            message=message,
            user=user,
            sender=sender,
            group=group,
            business=business,
            business_history=business_history,
            interaction_history=interaction_history,
            notification_summary=notification_summary,
            media_metadata=media_metadata
        )
