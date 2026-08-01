"""ContextBuilder class to assemble UnifiedContext objects."""
from typing import Optional
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
    UnifiedContext
)

class ContextBuilder:
    """Assembles the complete context required for a single message using raw data from DataLoader."""
    
    def __init__(self, loader: DataLoader):
        self.loader = loader

    def build_context(self, message_id: str) -> Optional[UnifiedContext]:
        """Builds a typed UnifiedContext for the given message_id."""
        msg_dict = self.loader.get_message(message_id)
        if not msg_dict:
            return None
        
        user_id = msg_dict["user_id"]
        user_dict = self.loader.get_user(user_id)
        if not user_dict:
            return None
        user = User(**user_dict)
        
        # 1. Fetch Sender (if individual/group conversation has sender_user_id)
        sender = None
        sender_user_id = msg_dict.get("sender_user_id")
        if sender_user_id:
            sender_dict = {"sender_user_id": sender_user_id}
            # If group conversation, look up role and stats from group members
            if msg_dict.get("conversation_type") == "group" and msg_dict.get("group_id"):
                members = self.loader.get_group_members(msg_dict["group_id"])
                member_info = next((m for m in members if m["user_id"] == sender_user_id), None)
                if member_info:
                    sender_dict.update({
                        "role": member_info.get("role"),
                        "joined_at": member_info.get("joined_at"),
                        "messages_sent_30d": member_info.get("messages_sent_30d"),
                        "messages_read_30d": member_info.get("messages_read_30d"),
                        "replies_sent_30d": member_info.get("replies_sent_30d")
                    })
            sender = Sender(**sender_dict)
            
        # 2. Fetch Group and mute state (if group conversation)
        group = None
        if msg_dict.get("conversation_type") == "group" and msg_dict.get("group_id"):
            group_id = msg_dict["group_id"]
            group_dict = self.loader.get_group(group_id)
            if group_dict:
                members = self.loader.get_group_members(group_id)
                user_member = next((m for m in members if m["user_id"] == user_id), None)
                if user_member:
                    # Coerce muted integer flag to bool
                    group_dict["group_muted_by_user"] = bool(user_member.get("group_muted_by_user"))
                group = Group(**group_dict)
                
        # 3. Fetch Business profile and history (if business conversation)
        business = None
        if msg_dict.get("conversation_type") == "business" and msg_dict.get("business_id"):
            business_id = msg_dict["business_id"]
            biz_dict = self.loader.get_business(business_id)
            if biz_dict:
                biz_hist = self.loader.get_user_business_history(user_id, business_id)
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

        # 4. Fetch Message History and corresponding Events
        history_dicts = self.loader.get_message_history(user_id)
        history_ids = [h["message_id"] for h in history_dicts]
        event_dicts = self.loader.get_message_events(history_ids)
        events_map = {e["message_id"]: e for e in event_dicts}
        
        history = []
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
            history.append(HistoricalMessage(**hist_msg_dict))

        # 5. Fetch Daily Notification summary
        notif_dicts = self.loader.get_notification_summary(user_id)
        daily_summary = [NotificationSummary(**n) for n in notif_dicts]
        
        # 6. Fetch Media details
        media = None
        media_type = msg_dict.get("media_type")
        media_id = msg_dict.get("media_id")
        if media_id and media_type:
            if media_type == "image":
                img_dict = self.loader.get_image(media_id)
                if img_dict:
                    media = MediaSummary(
                        media_id=media_id,
                        media_type=media_type,
                        file_path=img_dict.get("file_path")
                    )
            elif media_type == "voice":
                voice_dict = self.loader.get_voice(media_id)
                if voice_dict:
                    media = MediaSummary(
                        media_id=media_id,
                        media_type=media_type,
                        file_path=voice_dict.get("file_path")
                    )

        return UnifiedContext(
            user=user,
            message=Message(**msg_dict),
            sender=sender,
            group=group,
            business=business,
            media=media,
            history=history,
            daily_summary=daily_summary
        )
