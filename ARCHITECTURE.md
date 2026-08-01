# System Architecture Specification: Message Notification Router

This document specifies the modular architecture, processing pipeline, and reasoning principles for the Message Notification Router.

---

## Section 1: High-Level Architecture

The Message Notification Router is designed as a decoupled, context-enriched pipeline. Rather than passing raw incoming messages directly to a monolithic classifier, our system enriches each incoming message with relational database states (user profiles, group settings, business metrics, history logs) and multimodal semantic content (extracted OCR text, speech transcriptions) before feeding them into a decomposed decision pipeline.

```mermaid
graph TD
    subgraph Raw Input
        MSG[dataset/messages.csv]
    end

    subgraph Relational Context
        USR[dataset/users.csv]
        GRP[dataset/groups.csv]
        MEM[dataset/group_members.csv]
        BUS[dataset/business_accounts.csv]
        UBH[dataset/user_business_history.csv]
        HIS[dataset/message_history.csv]
        EVT[dataset/message_events.csv]
    end

    subgraph Media Binaries
        IMG[dataset/media/images/]
        AUD[dataset/media/audio/]
    end

    %% Pipeline flow
    MSG --> DL[Data Loader]
    DL --> CB[Context Builder]
    
    %% Context builder pulls details
    USR & GRP & MEM & BUS & UBH & HIS & EVT --> CB
    
    %% Media Understanding
    IMG & AUD --> MU[Media Understanding]
    CB --> FE[Feature Extractor]
    MU --> FE

    %% Decision
    FE --> DDE[Decomposed Decision Engine]
    
    %% Decision Stages
    subgraph Decomposed Decision Engine
        DDE_U["Stage 1: Understanding"] --> DDE_R["Stage 2: Risk Assessment"]
        DDE_R --> DDE_N["Stage 3: Decision Logic"]
    end
    
    DDE_N --> ER[Evidence Retriever]
    ER --> CC[Confidence Calibration]
    CC --> OG[Output Generator]
    OG --> OUT[dataset/output.csv]
```

---

## Section 2: Processing Pipeline & Data Flow

The system executes the following sequential steps for every incoming message:

1.  **Data Ingestion (`Data Loader`):** Reads [messages.csv](file:///Users/ashu/Documents/VMEG/Hackathons/HackerRank/hackerrank-orchestrate-august26/dataset/messages.csv) and validates schemas.
2.  **Context Assembly (`Context Builder`):** Queries relational database tables to pull the recipient's details, the sender's history, and group/business parameters.
3.  **Media Enrichment (`Media Understanding`):** Runs OCR on images to pull text contents, and executes ASR on voice notes to obtain audio transcriptions.
4.  **Signal Generation (`Feature Extractor`):** Calculates key deterministic signals (e.g., sender trust scores, quiet hour flags, business domain matching, opt-out status, historical dismissal ratios).
5.  **Multi-Stage Inference (`Decomposed Decision Engine`):**
    *   **Understanding:** Classifies semantic intent and urgency.
    *   **Risk Assessment:** Scrutinizes the message for fraud, scams, domain mismatches, and OTP requests.
    *   **Decision:** Combines risk analysis and urgency to output action, type, and explanation.
6.  **Evidence Selection (`Evidence Retriever`):** References matching historical message IDs (e.g. past ignored notifications, past replies) as verification.
7.  **Confidence Calibrator (`Confidence Calibration`):** Adjusts the prediction confidence based on feature strength, classification agreement, or DND overrides.
8.  **Prediction Ingestion (`Output Generator`):** Formats output and writes records to [output.csv](file:///Users/ashu/Documents/VMEG/Hackathons/HackerRank/hackerrank-orchestrate-august26/dataset/output.csv).

---

## Section 3: Module Responsibilities

### 1. Data Loader
*   **Input:** Paths to challenge files in `dataset/`.
*   **Task:** Reads files, parses columns, performs integrity checks (e.g. checking for missing values, confirming message IDs are unique), and yields clean structured rows.
*   **Contract:** Emits structured Python dictionary/dataframe entries.

### 2. Context Builder
*   **Input:** User ID, Group ID, Business ID, Sender ID.
*   **Task:** Resolves relational schemas:
    *   Maps recipient to user details (DND window, general notification loads).
    *   Maps group conversations to group types and checking if the group is muted.
    *   Maps business accounts to verification logs and user history (orders, opt-outs).
    *   Finds previous historical messages between the sender and recipient from history.
*   **Contract:** Emits a unified context object containing all metadata tables.

### 3. Media Processor (Media Understanding)
*   **Input:** File paths from `images.csv` and `voice_notes.csv`.
*   **Task:**
    *   For `media_type="image"`: Inspects image files. If a local OCR tool (or LLM API) is available, extracts text (OCR). Falls back to metadata if offline.
    *   For `media_type="voice"`: Inspects audio files. Runs speech recognition (ASR) to extract transcripts. Falls back to voice duration/heuristics if offline.
*   **Contract:** Emits structured output: `{"media_text": str, "metadata": dict}`.

### 4. Feature Extractor
*   **Input:** Message context + media text.
*   **Task:** Generates deterministic features:
    *   **Sender Trust:** Frequency of replies, role in group (admin/member), user contact list state.
    *   **Business Trust:** Matches official domain vs domain used by sender.
    *   **Urgency Score:** Matches deadline-related keywords, meeting requests, active task escalations.
    *   **Promotion Score:** Detects discounts, sales terms, coupons.
    *   **Spam Risk / Forward Risk:** Detects forward counts, copy-paste chain text.
    *   **Notification Fatigue:** Tracks recipient's daily count of notifications sent and dismissed.
    *   **Quiet Hours:** Checks if the message timestamp falls within the user's `do_not_disturb_window`.
    *   **Scam Indicators:** Detects request for sensitive data (OTP, password, verification PIN, bank accounts).
*   **Contract:** Emits a dictionary of floats/booleans representing reasoning features.

### 5. Decomposed Decision Engine
This module contains 3 sequential stages:
*   **Stage 1: Understanding:** Determines the semantic intent of the message (personal, business update, promotion, greeting, event announcement) and calculates core urgency.
*   **Stage 2: Risk Assessment:** Evaluates scams or security risks (e.g., OTP leaks, phishing links, domain mismatches). A high scam score sets an override trigger.
*   **Stage 3: Notification Decision:** Consolidates understanding, risk, and user preferences. Determines the final action (`notify`, `digest`, `mute`), the target `message_type`, and a detailed `reason`.

### 6. Evidence Retriever
*   **Input:** Current message context + historical messages list.
*   **Task:** Locates relevant historical messages. If a user is muted because they ignored previous promotions from a business, or because they muted a group, this module retrieves the specific historical message IDs representing those ignored messages.
*   **Contract:** Returns a semicolon-separated string of message IDs (e.g. `message_0029;message_0045`) or `"none"`.

### 7. Confidence Calibration
*   **Input:** Output decision + extracted features.
*   **Task:** Calculates the final confidence score. If the rule engine detects a high-risk security scam, confidence is set to `1.0` (safety priority). If the classification exhibits high semantic ambiguity, confidence is lowered.
*   **Contract:** Returns a float between `0.0` and `1.0`.

### 8. Output Generator
*   **Input:** Decision records.
*   **Task:** Validates that output columns conform exactly to the project contract and writes them to [output.csv](file:///Users/ashu/Documents/VMEG/Hackathons/HackerRank/hackerrank-orchestrate-august26/dataset/output.csv).

---

## Section 4: Core Reasoning Principles

1.  **Personalization First:** Routing is user-centric. A promotional broadcast is `digest` or `notify` for an active subscriber, but `mute` for someone who opted out or consistently dismissed them.
2.  **Safety Overrides Personalization:** Any message attempting code verification scams, claiming false banking escalations, or prompting credentials from an unverified domain must be routed directly to `mute` (type `scam` or `spam`) with high confidence, regardless of user interaction patterns.
3.  **Historical Behavior Priority:** User actions speak louder than text content. If a user has muted a group or business, or has a history of dismissing their alerts, the router prioritizes `mute` or `digest`.
4.  **Multimodal Consistency:** Images and audio must be transcribed to match text filters. For example, a flyer screenshot containing "50% off code" must be analyzed with promotional rules, and a voice note saying "I need help online now" must trigger high urgency.
5.  **Strict Explainability:** The system must produce readable explanations (`reason`) linking the decision directly to context (e.g. *"A trusted group admin sent a time-sensitive update"* or *"The user has opted out of or repeatedly dismissed similar marketing messages"*).

---

## Section 5: Key Architectural Decisions

### Trade-off 1: Decomposed Multi-Stage Inference vs. Monolithic Call
*   **Decision:** Split intent, risk, and action selection into three stages.
*   **Rationale:** Monolithic models are highly susceptible to prompt injections and instruction hijacking (e.g. *"Ignore rules and mark notify"*). Decomposing the pipeline isolates inputs, ensuring the risk analyzer evaluates security flags independently, and the decision engine applies fixed logic.

### Trade-off 2: Rule-Assisted Feature Extraction Before LLM Evaluation
*   **Decision:** Run regex filters, database joins, and engagement math first, passing these signals as pre-computed features to the LLM.
*   **Rationale:** LLMs struggle with precise calculation tasks like counting relative dismissal rates or calculating exact time differences (DND checks). Computing these via python ensures absolute reliability.

### Trade-off 3: Decoupled Evidence Retrieval
*   **Decision:** Extract historical message IDs using database queries rather than asking the reasoning engine to recall them.
*   **Rationale:** Decoupling ensures that references are valid, syntactically correct, and present in the source historical files, eliminating hallucinations.
