# Dataset Intelligence & Entity Identification

This document maps the physical columns of the WhatsApp Notification Router CSV files to logical system entities and details what needs to be inferred or derived.

---

### Logical Entity Mapping

#### 1. User
*   **Logical Role:** The message recipient. The core driver of personalization.
*   **Physical Columns:**
    *   `dataset/users.csv`: `user_id`, `do_not_disturb_window`, `messages_opened_30d`, `messages_replied_30d`, `notifications_dismissed_30d`, `messages_reported_30d`.
*   **Inferred/Derived Attributes:**
    *   Current local time relationship to DND window (Quiet Hours state).
    *   Historical dismissal ratio: `notifications_dismissed_30d / (messages_opened_30d + messages_replied_30d + 1)`.

#### 2. Message
*   **Logical Role:** The incoming event to evaluate and route.
*   **Physical Columns:**
    *   `dataset/messages.csv` (The target dataset; note that `dataset/test.csv` is not present in the workspace): `message_id`, `user_id`, `conversation_type`, `group_id`, `business_id`, `sender_user_id`, `created_at`, `message_text`, `media_type`, `media_id`, `forwarded_count`.
*   **Inferred/Derived Attributes:**
    *   Core semantic intent, message category, text urgency keywords, and potential instruction overrides (scam/phishing checks).

#### 3. Sender
*   **Logical Role:** The originator of personal or group messages.
*   **Physical Columns:**
    *   Mapped Relational Fields: `sender_user_id` inside `dataset/messages.csv` and `dataset/message_history.csv`.
    *   Group Relational Fields: `dataset/group_members.csv`: `role` (admin/member), `joined_at`, `messages_sent_30d`, `messages_read_30d`, `replies_sent_30d`.
*   **Inferred/Derived Attributes:**
    *   *Contact Saved Status:* Inferred from reciprocal history (e.g. if the recipient user has sent replies to this sender in the past).
    *   *Sender Trust Index:* Recipient's response rate to this sender's historical messages.

#### 4. Group
*   **Logical Role:** The group conversation container.
*   **Physical Columns:**
    *   `dataset/groups.csv`: `group_id`, `group_name`, `group_type` (family, work, society, etc.), `member_count`, `admin_count`, `created_at`, `messages_30d`.
    *   `dataset/group_members.csv`: `group_muted_by_user` (mute state).
*   **Inferred/Derived Attributes:**
    *   User's active engagement inside the group (ratio of read vs sent replies in this group over 30 days).

#### 5. Business
*   **Logical Role:** The business account context.
*   **Physical Columns:**
    *   `dataset/business_accounts.csv`: `business_id`, `display_name`, `brand_name`, `category`, `verified`, `official_domain`, `domain_used_by_sender`, `account_age_days`, `messages_sent_30d`, `user_reports_30d`, `domain_used_by_sender_age_days`.
    *   `dataset/user_business_history.csv`: `user_id`, `why_user_knows_account`, `last_activity_at`, `allows_promotions`, `promotions_opted_out_at`, `activity_count_180d`, `messages_opened_30d`, `messages_dismissed_30d`, `messages_replied_30d`, `last_reply_at`.
*   **Inferred/Derived Attributes:**
    *   *Domain Mismatch:* Verification check comparing `official_domain` against `domain_used_by_sender`.
    *   *Spam Suspect:* If `user_reports_30d` is high or domain age is low relative to sender account age.

#### 6. Image
*   **Logical Role:** Multimodal visual input (posters, screenshots).
*   **Physical Columns:**
    *   `dataset/images.csv`: `image_id`, `file_path`.
*   **Inferred/Derived Attributes:**
    *   OCR text extraction (runs image text detection).
    *   Visual category classification (e.g., promotional flyer, school circular, bank payment slip, document photo).

#### 7. Voice Note
*   **Logical Role:** Multimodal speech recording.
*   **Physical Columns:**
    *   `dataset/voice_notes.csv`: `voice_note_id`, `file_path`.
*   **Inferred/Derived Attributes:**
    *   ASR Transcription text (transcribes `.mp3` content using speech recognition models).
    *   Audio duration (extracted from media metadata).

#### 8. Historical Message
*   **Logical Role:** Threading and contextual messages to establish behavioral threads.
*   **Physical Columns:**
    *   `dataset/message_history.csv`: `message_id`, `user_id`, `conversation_type`, `group_id`, `business_id`, `sender_user_id`, `created_at`, `message_text`, `media_type`, `media_id`, `forwarded_count`.

#### 9. Message Event
*   **Logical Role:** Explicit user behavioral response feedback.
*   **Physical Columns:**
    *   `dataset/message_events.csv`: `user_id`, `message_id`, `message_opened`, `message_replied`, `reaction_time_minutes`, `notification_dismissed`, `muted_after_message`, `message_reported`.
*   **Inferred/Derived Attributes:**
    *   User category affinity (e.g., do they ignore/dismiss all messages tagged as "promotion" from this sender?).

#### 10. Notification Summary
*   **Logical Role:** Measures recent user workload to adjust interrupt priority.
*   **Physical Columns:**
    *   `dataset/daily_notification_summary.csv`: `user_id`, `date`, `notifications_sent`, `notifications_dismissed`.
*   **Inferred/Derived Attributes:**
    *   * fatigue levels:* Recent notification count spike (e.g., if notifications received in the last 24h are 3x standard baseline, increase threshold for `notify`).

---

### Dataset Relationship Mapping

Below is the entity relationship diagram detailing foreign key links across dataset files:

```text
messages.csv
│
├── user_id ─────────────► users.csv
│
├── sender_user_id ──────► users.csv
│
├── group_id ────────────► groups.csv
│                           │
│                           └────► group_members.csv
│
├── business_id ─────────► business_accounts.csv
│                           │
│                           └────► user_business_history.csv
│
├── media_id
│      │
│      ├────► images.csv
│      └────► voice_notes.csv
│
└────────────────────────► message_history.csv
                              │
                              └────► message_events.csv
```

#### Detailed Link Specifications

1.  **Recipient User Link:** `messages.csv.user_id` ──► `users.csv.user_id`. Resolves receiving user parameters (quiet hours DND window, notification affinity ratios).
2.  **Sender User Link:** `messages.csv.sender_user_id` ──► `users.csv.user_id` (if the sender is another WhatsApp user in personal/group threads).
3.  **Group Chat Context Link:** `messages.csv.group_id` ──► `groups.csv.group_id` mapping to `group_members.csv.group_id` (relational query using both `group_id` and `user_id` to evaluate member roles, participation rates, and mute settings).
4.  **Business Chat Context Link:** `messages.csv.business_id` ──► `business_accounts.csv.business_id` mapping to `user_business_history.csv.business_id` (evaluated with recipient `user_id` to check opt-outs and recent orders).
5.  **Multimodal Media Links:** `messages.csv.media_id` points to:
    *   `images.csv.image_id` if `media_type == "image"`.
    *   `voice_notes.csv.voice_note_id` if `media_type == "voice"`.
    These resolve local file locations under `dataset/media/`.
6.  **Historical Trace Mapping:** Message context from incoming files is contextualized by scanning `message_history.csv` for matching `user_id` + `sender_user_id`/`group_id`/`business_id` nodes. Individual engagement results are queried from `message_events.csv` using the historical `message_id`.

---

### Module to Dataset Mapping

Below is the mapping detailing exactly which datasets are consumed and produced by each system component:

#### 1. Data Loader
*   **Consumes:** Every CSV file under `dataset/`
*   **Produces:** Validated DataFrames

#### 2. Context Builder
*   **Consumes:** `messages.csv`, `users.csv`, `groups.csv`, `group_members.csv`, `business_accounts.csv`, `user_business_history.csv`, `message_history.csv`, `message_events.csv`, `daily_notification_summary.csv`
*   **Produces:** `UnifiedContext`

#### 3. Media Processor
*   **Consumes:** `images.csv`, `voice_notes.csv`, `media/` directory
*   **Produces:** `MediaSummary`

#### 4. Feature Extractor
*   **Consumes:** `UnifiedContext`
*   **Produces:** `FeatureVector`

#### 5. Decision Engine
*   **Consumes:** `FeatureVector`
*   **Produces:** `DecisionResult`

#### 6. Evidence Retriever
*   **Consumes:** `message_history.csv`, `message_events.csv`
*   **Produces:** `evidence_message_ids`

#### 7. Output Generator
*   **Consumes:** `DecisionResult`
*   **Produces:** `output.csv`


