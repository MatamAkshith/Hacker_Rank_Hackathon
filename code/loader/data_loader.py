"""DataLoader class to load and validate input CSV datasets."""
import os
import pandas as pd
from typing import Dict, List, Any, Optional

class DataLoader:
    """Loads and queries physical CSV datasets under a single-responsibility data retrieval API."""
    
    def __init__(self):
        self._users: Optional[pd.DataFrame] = None
        self._messages: Optional[pd.DataFrame] = None
        self._groups: Optional[pd.DataFrame] = None
        self._group_members: Optional[pd.DataFrame] = None
        self._business_accounts: Optional[pd.DataFrame] = None
        self._user_business_history: Optional[pd.DataFrame] = None
        self._message_history: Optional[pd.DataFrame] = None
        self._message_events: Optional[pd.DataFrame] = None
        self._images: Optional[pd.DataFrame] = None
        self._voice_notes: Optional[pd.DataFrame] = None
        self._daily_notification_summary: Optional[pd.DataFrame] = None

        # Private O(1) lookup dictionaries
        self._messages_idx: Dict[str, Dict[str, Any]] = {}
        self._users_idx: Dict[str, Dict[str, Any]] = {}
        self._groups_idx: Dict[str, Dict[str, Any]] = {}
        self._business_accounts_idx: Dict[str, Dict[str, Any]] = {}
        self._group_members_idx: Dict[str, List[Dict[str, Any]]] = {}
        self._user_business_history_idx: Dict[tuple, Dict[str, Any]] = {}
        self._message_history_idx: Dict[str, List[Dict[str, Any]]] = {}
        self._message_events_idx: Dict[str, Dict[str, Any]] = {}
        self._images_idx: Dict[str, Dict[str, Any]] = {}
        self._voice_notes_idx: Dict[str, Dict[str, Any]] = {}
        self._daily_notification_summary_idx: Dict[str, List[Dict[str, Any]]] = {}

    def _clean_dict(self, row: Any) -> dict:
        """Helper to convert nan values in dictionaries to None."""
        row_dict = row.to_dict() if hasattr(row, "to_dict") else dict(row)
        return {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}

    def load_all(self, data_dir: str):
        """Loads all CSVs from the dataset directory into memory and builds lookup indexes."""
        self._users = pd.read_csv(os.path.join(data_dir, "users.csv"))
        self._messages = pd.read_csv(os.path.join(data_dir, "messages.csv"))
        self._groups = pd.read_csv(os.path.join(data_dir, "groups.csv"))
        self._group_members = pd.read_csv(os.path.join(data_dir, "group_members.csv"))
        self._business_accounts = pd.read_csv(os.path.join(data_dir, "business_accounts.csv"))
        self._user_business_history = pd.read_csv(os.path.join(data_dir, "user_business_history.csv"))
        self._message_history = pd.read_csv(os.path.join(data_dir, "message_history.csv"))
        self._message_events = pd.read_csv(os.path.join(data_dir, "message_events.csv"))
        self._images = pd.read_csv(os.path.join(data_dir, "images.csv"))
        self._voice_notes = pd.read_csv(os.path.join(data_dir, "voice_notes.csv"))
        self._daily_notification_summary = pd.read_csv(os.path.join(data_dir, "daily_notification_summary.csv"))

        # Build message index by message_id
        if self._messages is not None:
            self._messages_idx = {
                str(r["message_id"]): self._clean_dict(r)
                for _, r in self._messages.iterrows()
            }

        # Build user index by user_id
        if self._users is not None:
            self._users_idx = {
                str(r["user_id"]): self._clean_dict(r)
                for _, r in self._users.iterrows()
            }

        # Build group index by group_id
        if self._groups is not None:
            self._groups_idx = {
                str(r["group_id"]): self._clean_dict(r)
                for _, r in self._groups.iterrows()
            }

        # Build business account index by business_id
        if self._business_accounts is not None:
            self._business_accounts_idx = {
                str(r["business_id"]): self._clean_dict(r)
                for _, r in self._business_accounts.iterrows()
            }

        # Build group members list by group_id
        if self._group_members is not None:
            self._group_members_idx = {}
            for _, r in self._group_members.iterrows():
                gid = str(r["group_id"])
                cleaned = self._clean_dict(r)
                if gid not in self._group_members_idx:
                    self._group_members_idx[gid] = []
                self._group_members_idx[gid].append(cleaned)

        # Build user business history index by (user_id, business_id)
        if self._user_business_history is not None:
            self._user_business_history_idx = {
                (str(r["user_id"]), str(r["business_id"])): self._clean_dict(r)
                for _, r in self._user_business_history.iterrows()
            }

        # Build message history list index by user_id
        if self._message_history is not None:
            self._message_history_idx = {}
            for _, r in self._message_history.iterrows():
                uid = str(r["user_id"])
                cleaned = self._clean_dict(r)
                if uid not in self._message_history_idx:
                    self._message_history_idx[uid] = []
                self._message_history_idx[uid].append(cleaned)

        # Build message events index by message_id
        if self._message_events is not None:
            self._message_events_idx = {
                str(r["message_id"]): self._clean_dict(r)
                for _, r in self._message_events.iterrows()
            }

        # Build images index by image_id
        if self._images is not None:
            self._images_idx = {
                str(r["image_id"]): self._clean_dict(r)
                for _, r in self._images.iterrows()
            }

        # Build voice notes index by voice_note_id
        if self._voice_notes is not None:
            self._voice_notes_idx = {
                str(r["voice_note_id"]): self._clean_dict(r)
                for _, r in self._voice_notes.iterrows()
            }

        # Build daily notification summary list index by user_id
        if self._daily_notification_summary is not None:
            self._daily_notification_summary_idx = {}
            for _, r in self._daily_notification_summary.iterrows():
                uid = str(r["user_id"])
                cleaned = self._clean_dict(r)
                if uid not in self._daily_notification_summary_idx:
                    self._daily_notification_summary_idx[uid] = []
                self._daily_notification_summary_idx[uid].append(cleaned)

    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Returns raw message dictionary matching message_id in O(1) time."""
        return self._messages_idx.get(str(message_id))

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Returns raw user dictionary matching user_id in O(1) time."""
        return self._users_idx.get(str(user_id))

    def get_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Returns raw group dictionary matching group_id in O(1) time."""
        return self._groups_idx.get(str(group_id))

    def get_business(self, business_id: str) -> Optional[Dict[str, Any]]:
        """Returns raw business dictionary matching business_id in O(1) time."""
        return self._business_accounts_idx.get(str(business_id))

    def get_group_members(self, group_id: str) -> List[Dict[str, Any]]:
        """Returns list of membership dictionaries for members of group_id in O(1) time."""
        return self._group_members_idx.get(str(group_id), [])

    def get_user_business_history(self, user_id: str, business_id: str) -> Optional[Dict[str, Any]]:
        """Returns business history dictionary between user_id and business_id in O(1) time."""
        return self._user_business_history_idx.get((str(user_id), str(business_id)))

    def get_message_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns message history list of dictionaries for user_id in O(1) time."""
        return self._message_history_idx.get(str(user_id), [])

    def get_message_events(self, message_ids: list) -> List[Dict[str, Any]]:
        """Returns list of message event dictionaries matching message_ids in O(M) time where M is len(message_ids)."""
        res = []
        for m_id in message_ids:
            evt = self._message_events_idx.get(str(m_id))
            if evt:
                res.append(evt)
        return res

    def get_notification_summary(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns daily notification summary logs for user_id in O(1) time."""
        return self._daily_notification_summary_idx.get(str(user_id), [])

    def get_image(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Returns image dictionary matching media_id in O(1) time."""
        return self._images_idx.get(str(media_id))

    def get_voice(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Returns voice note dictionary matching media_id in O(1) time."""
        return self._voice_notes_idx.get(str(media_id))
