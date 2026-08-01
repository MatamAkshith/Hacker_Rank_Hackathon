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
    *   Historical dismissal ratio inferred from user behavior metrics.

#### 2. Message
*   **Logical Role:** The incoming event to evaluate and route.
*   **Physical Columns:**
    *   `dataset/messages.csv` (the raw input dataset): `message_id`, `user_id`, `conversation_type`, `group_id`, `business_id`, `sender_user_id`, `created_at`, `message_text`, `media_type`, `media_id`, `forwarded_count`.
*   **Inferred/Derived Attributes:**
    *   Core semantic intent, message category, text urgency keywords, and potential instruction overrides (scam/phishing checks).

#### 3. Sender
*   **Logical Role:** The originator of personal or group messages.
*   **Physical Columns:**
    *   Mapped Relational Fields: `sender_user_id` inside `dataset/messages.csv` and `dataset/message_history.csv`.
    *   Group Relational Fields: `dataset/group_members.csv`: `role` (admin/member), `joined_at`, `messages_sent_30d`, `messages_read_30d`, `replies_sent_30d`.
*   **Inferred/Derived Attributes:**
    *   *Contact Saved Status:* Inferred from reciprocal history logs in the available datasets.
    *   *Sender Trust Index:* Derived from historical interaction and responsiveness logs between recipient and sender using the available datasets.

#### 4. Group
*   **Logical Role:** The group conversation container.
*   **Physical Columns:**
    *   `dataset/groups.csv`: `group_id`, `group_name`, `group_type` (family, work, society, etc.), `member_count`, `admin_count`, `created_at`, `messages_30d`.
    *   `dataset/group_members.csv`: `group_muted_by_user` (mute state).
*   **Inferred/Derived Attributes:**
    *   User's active engagement inside the group inferred from member role and read/reply metrics.

#### 5. Business
*   **Logical Role:** The business account context.
*   **Physical Columns:**
    *   `dataset/business_accounts.csv`: `business_id`, `display_name`, `brand_name`, `category`, `verified`, `official_domain`, `domain_used_by_sender`, `account_age_days`, `messages_sent_30d`, `user_reports_30d`, `domain_used_by_sender_age_days`.
    *   `dataset/user_business_history.csv`: `user_id`, `business_id`, `why_user_knows_account`, `last_activity_at`, `allows_promotions`, `promotions_opted_out_at`, `activity_count_180d`, `messages_opened_30d`, `messages_dismissed_30d`, `messages_replied_30d`, `last_reply_at`.
*   **Inferred/Derived Attributes:**
    *   *Domain Mismatch:* Verification check comparing official domains against sender domains.
    *   *Spam Suspect:* Derived from reports and domain registration ages.

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
    *   *fatigue levels:* Inferred from daily notification summary logs.

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

---

### Section 4: Feature Mapping

Below is the mapping for every feature extracted by the Feature Extractor, defining its source, type, and purpose:

**Sender Trust**
- *Source:* `users.csv`, `message_events.csv`, `message_history.csv`
- *Type:* Derived
- *Purpose:* Estimate whether the recipient trusts this sender.

**Business Verification (Business Trust)**
- *Source:* `business_accounts.csv`, `user_business_history.csv`
- *Type:* Direct / Derived
- *Purpose:* Determine the legitimacy of a business sender.

**Relationship Strength**
- *Source:* `message_history.csv`, `message_events.csv`, `groups.csv`
- *Type:* Derived
- *Purpose:* Quantify the closeness between sender and recipient to prioritize personal connections.

**Urgency**
- *Source:* `messages.csv`, `images.csv`, `voice_notes.csv`
- *Type:* Derived
- *Purpose:* Assess time-sensitivity and necessity of immediate interruption (e.g., emergencies, direct mentions).

**Promotion Score**
- *Source:* `messages.csv`, `images.csv`, `business_accounts.csv`
- *Type:* Derived
- *Purpose:* Detect marketing, sales, or promotional content typically routed to digest.

**Spam Risk**
- *Source:* `messages.csv`, `users.csv` (sender profile)
- *Type:* Derived
- *Purpose:* Identify low-value, unwanted, or repetitive noise.

**Forward Risk**
- *Source:* `messages.csv` (e.g., is_forwarded flag)
- *Type:* Direct / Derived
- *Purpose:* Detect viral, mass-forwarded, or chain-mail content which usually requires lower priority.

**Scam Indicators**
- *Source:* `messages.csv`, `images.csv`, `voice_notes.csv`
- *Type:* Derived
- *Purpose:* Identify phishing, OTP fraud, or safety threats to trigger the Safety Override (mute).

**Historical Engagement**
- *Source:* `message_events.csv`, `message_history.csv`
- *Type:* Derived
- *Purpose:* Measure user interaction with similar past messages or senders to predict current interest.

**Notification Fatigue**
- *Source:* `daily_notification_summary.csv`
- *Type:* Derived
- *Purpose:* Prevent overwhelming the user if they have received a high volume of notifications recently.

**Quiet Hours**
- *Source:* `users.csv` (user preferences)
- *Type:* Direct
- *Purpose:* Determine whether the notification should interrupt the user immediately based on time-of-day preferences.

---

### Section 5: Direct vs Derived Features

This section documents the distinction between features, noting that derived features represent the core implementation work of the Feature Extractor module.

#### Direct Features (Available directly from the dataset)
*   **DND window** (recipient user profile parameters)
*   **Forwarded count** (viral signal from message body metadata)
*   **Verified business** (business account verification status flag)
*   **Group muted** (mute flag configured in user-group preferences)
*   **Message timestamp** (raw timestamp parsed to check quiet hour ranges)
*   **Account age** (days since business sender profile creation)

#### Derived Features (Need reasoning or aggregation)
*   **Sender Trust:** Inferred from historical interaction and responsiveness logs between recipient and sender using the available datasets.
*   **Spam Risk:** Derived from structural noise signals and unsolicited text patterns identified across historical messages and user reports.
*   **Relationship Strength:** Inferred from contextual closeness, message exchanges, and mutual group participations present in the source logs.
*   **Notification Fatigue:** Inferred from the user's recent daily counts of notifications sent versus dismissed in history.
*   **Promotion Preference:** Inferred from the recipient's opt-out settings and history of interaction with similar marketing campaigns.
*   **Scam Probability:** Inferred from authentication checks, domain usage checks, and textual or visual indicators of risk.
*   **User Engagement Score:** Inferred from user engagement trends with specific groups or message categories over time.

---

### Section 6: Evidence Mapping

This section documents exactly what counts as valid evidence to satisfy the `evidence_message_ids` requirement. This dictates what the Evidence Retriever must search for to justify the decisions made by the router:

#### Example 1: Promotion Avoidance
- *Behavior:* Previous similar promotion ignored
- *Current Message:* Promotion
- *Decision:* Mute
- *Evidence:* Previous promotion IDs

#### Example 2: Urgent Engagement
- *Behavior:* Previous payment reminder opened
- *Current Message:* Payment reminder
- *Decision:* Notify
- *Evidence:* Previous payment reminder IDs

#### Example 3: Safety Risk
- *Behavior:* Repeated scam reported
- *Current Message:* Scam
- *Decision:* Mute
- *Evidence:* Reported scam IDs

---

### Section 7: Personalization Signals

Below is the list of fields and behavioral dimensions that influence the personalization layers:
*   **Messages opened:** Recipient's history of opening notifications from this sender/group.
*   **Replies:** User replies to historical messages indicating direct relationship.
*   **Dismissals:** Dismissed notification counts indicating lower relevance.
*   **Reports:** User reported spam/scam logs indicating explicit muting preference.
*   **Promotion opt-out:** Timestamps of promotional opt-outs from specific businesses.
*   **Group mute status:** Muted state flags from member mappings.
*   **Relationship history:** Type and frequency of historical interactions.
*   **Activity count:** Interaction metrics over 180 days.
*   **Daily notification load:** Measures the volume of recent interruptions.

---

### Section 8: Safety Signals

Below is the list of fields and threat dimensions that contribute to the Safety Layer evaluation:
*   **Business verification:** Checked status of the business account.
*   **Domain mismatch:** Unofficial domain mismatch check.
*   **User reports:** Sum of user reports for a business or contact in the past 30 days.
*   **Forwarded count:** Measures potential viral spam threat.
*   **Unknown sender:** Sender not present in conversation/relationship history.
*   **OTP requests:** Text checking for "OTP", "login code", "verification pin".
*   **QR/payment requests:** Checks for transaction links, "pay small fee", "scan QR".
*   **Phishing language:** Urgency phrases pushing for credentials.
*   **Scam keywords:** Fraud alert filters (e.g. account reactivation, expiration warning).

---

### Section 9: Implementation Priority Matrix

Below is the roadmap and priority order for implementing modules:

| Priority | Module | Depends On |
| :--- | :--- | :--- |
| 1 | Data Loader | None |
| 2 | Context Builder | Loader |
| 3 | Media Processor | Loader |
| 4 | Feature Extractor | Context + Media |
| 5 | Understanding Engine | Features |
| 6 | Risk Assessment | Understanding |
| 7 | Notification Decision | Risk |
| 8 | Evidence Retriever | Decision |
| 9 | Confidence Estimator | Decision + Evidence |
| 10 | Output Generator | Everything |

---

### Feature Dictionary

Below is the comprehensive Feature Dictionary referencing all metrics extracted from raw datasets:

| Feature | Description | Source Dataset(s) | Type | Used By Module(s) |
| :--- | :--- | :--- | :--- | :--- |
| Quiet Hours | DND window preference | `users.csv` | Direct | Decision Engine |
| Sender Trust | Inferred historical reliability of sender | history + events | Derived | Risk Assessment |
| Scam Probability | Inferred likelihood of fraud/phishing | message + business | Derived | Safety Layer |
| Notification Fatigue | Inferred recent interruption load | daily summary | Derived | Decision Engine |
| Business Trust | Inferred legitimacy of a business sender | `business_accounts.csv`, `user_business_history.csv` | Direct / Derived | Risk Assessment |
| Relationship Strength | Inferred closeness between sender and recipient | `message_history.csv`, `message_events.csv`, `groups.csv` | Derived | Decision Engine |
| Urgency | Inferred time-sensitivity of current message | `messages.csv`, `images.csv`, `voice_notes.csv` | Derived | Decision Engine |
| Promotion Score | Inferred marketing/sales/promotional content | `messages.csv`, `images.csv`, `business_accounts.csv` | Derived | Decision Engine |
| Spam Risk | Inferred low-value, unwanted, or repetitive noise | `messages.csv`, `users.csv` | Derived | Risk Assessment |
| Forward Risk | Inferred mass-forwarded chain content | `messages.csv` | Direct / Derived | Decision Engine |
| Historical Engagement | Inferred recipient response on similar past messages | `message_events.csv`, `message_history.csv` | Derived | Decision Engine |

---

### Entity Ownership

This section defines the hierarchical object relationships for the Context Builder to maintain clean object scope boundaries:

*   **`User` owns:**
    *   `Notification Preferences`
    *   `History`
    *   `Business Preferences`
    *   `Daily Summary`
*   **`Message` belongs to:**
    *   `User`
    *   `Group`
    *   `Business`
    *   `Media`






