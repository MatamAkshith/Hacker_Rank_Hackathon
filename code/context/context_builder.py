"""ContextBuilder class to assemble UnifiedContext objects."""
from typing import Any, Dict, List, Optional
from code.loader.data_loader import DataLoader
from code.context.models import (
    User,
    Message,
    Sender,
    Group,
    Business,
    MediaSummary,
    HistoricalMessage,
    NotificationSummary,
    ContextMetadata,
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
                    business_history = [biz_hist]
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

        # 5. Fetch Daily Notification summary (failsafe)
        notification_summary = None
        try:
            notif_dicts = self.loader.get_notification_summary(user_id)
            if notif_dicts:
                notification_summary = [NotificationSummary(**n) for n in notif_dicts]
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
        has_historical_evidence = len(historical_messages) > 0
        media_needs_processing = media_metadata is not None and media_type in ("image", "voice")
        
        metadata = ContextMetadata(
            has_business_context=has_business_context,
            has_group_context=has_group_context,
            has_historical_evidence=has_historical_evidence,
            media_needs_processing=media_needs_processing,
            missing_datasets=missing_datasets
        )

        return UnifiedContext(
            metadata=metadata,
            message=message,
            user=user,
            sender=sender,
            group=group,
            business=business,
            business_history=business_history,
            historical_messages=historical_messages,
            historical_events=historical_events,
            notification_summary=notification_summary,
            media_metadata=media_metadata
        )
