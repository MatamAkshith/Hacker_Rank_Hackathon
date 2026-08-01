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

    def load_all(self, data_dir: str):
        """Loads all CSVs from the dataset directory into private class attributes."""
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

    def _row_to_dict(self, df: pd.DataFrame, index_val: Any, col_name: str) -> Optional[Dict[str, Any]]:
        """Helper to find a row by index value and return it as a dictionary with native types."""
        rows = df[df[col_name] == index_val]
        if rows.empty:
            return None
        # Convert first matching row to dict, mapping NaN to None
        row_dict = rows.iloc[0].to_dict()
        return {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}

    def _rows_to_list(self, df: pd.DataFrame, index_val: Any, col_name: str) -> List[Dict[str, Any]]:
        """Helper to find all matching rows and return them as a list of dictionaries with native types."""
        rows = df[df[col_name] == index_val]
        res = []
        for _, r in rows.iterrows():
            row_dict = r.to_dict()
            res.append({k: (None if pd.isna(v) else v) for k, v in row_dict.items()})
        return res

    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Returns raw message dictionary matching message_id."""
        if self._messages is None:
            return None
        return self._row_to_dict(self._messages, message_id, "message_id")

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Returns raw user dictionary matching user_id."""
        if self._users is None:
            return None
        return self._row_to_dict(self._users, user_id, "user_id")

    def get_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Returns raw group dictionary matching group_id."""
        if self._groups is None:
            return None
        return self._row_to_dict(self._groups, group_id, "group_id")

    def get_business(self, business_id: str) -> Optional[Dict[str, Any]]:
        """Returns raw business dictionary matching business_id."""
        if self._business_accounts is None:
            return None
        return self._row_to_dict(self._business_accounts, business_id, "business_id")

    def get_group_members(self, group_id: str) -> List[Dict[str, Any]]:
        """Returns list of membership dictionaries for members of group_id."""
        if self._group_members is None:
            return []
        return self._rows_to_list(self._group_members, group_id, "group_id")

    def get_user_business_history(self, user_id: str, business_id: str) -> Optional[Dict[str, Any]]:
        """Returns business history dictionary between user_id and business_id."""
        if self._user_business_history is None:
            return None
        df = self._user_business_history
        rows = df[(df["user_id"] == user_id) & (df["business_id"] == business_id)]
        if rows.empty:
            return None
        row_dict = rows.iloc[0].to_dict()
        return {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}

    def get_message_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns message history list of dictionaries for user_id."""
        if self._message_history is None:
            return []
        return self._rows_to_list(self._message_history, user_id, "user_id")

    def get_message_events(self, message_ids: list) -> List[Dict[str, Any]]:
        """Returns list of message event dictionaries matching message_ids."""
        if self._message_events is None:
            return []
        df = self._message_events
        rows = df[df["message_id"].isin(message_ids)]
        res = []
        for _, r in rows.iterrows():
            row_dict = r.to_dict()
            res.append({k: (None if pd.isna(v) else v) for k, v in row_dict.items()})
        return res

    def get_notification_summary(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns daily notification summary logs for user_id."""
        if self._daily_notification_summary is None:
            return []
        return self._rows_to_list(self._daily_notification_summary, user_id, "user_id")

    def get_image(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Returns image dictionary matching media_id."""
        if self._images is None:
            return None
        return self._row_to_dict(self._images, media_id, "image_id")

    def get_voice(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Returns voice note dictionary matching media_id."""
        if self._voice_notes is None:
            return None
        return self._row_to_dict(self._voice_notes, media_id, "voice_note_id")
