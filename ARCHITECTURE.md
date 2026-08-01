# System Architecture Specification

This document details the modular system philosophy, unified architecture, processing pipeline, and reasoning modules for the WhatsApp Message Notification Router.

---

### Section 1: System Philosophy

The system is designed as a Personalized Notification Intelligence Engine rather than a simple message classifier. Instead of predicting labels directly from raw messages, it progressively builds contextual understanding, evaluates trust and risk, reasons over user-specific preferences and historical behavior, and produces an explainable routing decision supported by historical evidence.

---

### Section 2: Unified System Architecture Diagram

Below is the unified architectural design and flow of the notification engine:

```
                Incoming Message
                       │
                       ▼
                Context Builder
                       │
  ┌────────────────────┼────────────────────┐
  ▼                    ▼                    ▼
User Context        Sender Context      Media Context
│                    │                    │
└──────────────┬─────┴────────────────────┘
▼
Unified Context Object
▼
Feature Extraction
▼
Understanding Engine
▼
Risk Assessment Engine
▼
Notification Decision Engine
▼
Evidence & Confidence Layer
▼
output.csv
```

---

### Section 3: The Unified Context Object

The pipeline begins with establishing the recipient user's profile and general behavior, rather than solely examining the incoming message. The system aggregates metadata, relationships, and history into a **Unified Reasoning Context**:

```
Incoming Message

User Profile

Group Context

Business Context

Sender Context

Historical Messages

Message Events

Notification Summary

Media Summary
───────► Unified Reasoning Context
```

---

### Section 4: Feature Categories & Purpose

Calculated signals are grouped into four specialized categories to provide structured reasoning inputs:

1.  **Trust Features:** (Evaluates sender and channel legitimacy)
    *   *Sender Trust:* Historical reaction and reply frequency from the user.
    *   *Business Trust:* Official brand domain validation and sender profile age.
    *   *Relationship Strength:* Role of sender in group chats (e.g. admin vs member) and mutual conversation metrics.
2.  **Urgency Features:** (Measures time sensitivity and actionability)
    *   *Urgency:* Detected deadlines, schedules, or requests for immediate action.
    *   *Intent:* Goal-directed behavior in message text (e.g. coordinates meetings, updates circulars).
    *   *Payment Indicators:* Mentions of transaction alerts, utility bills, or pending fees.
3.  **Risk Features:** (Detects malice, noise, and spam)
    *   *Scam Indicators:* Mentions of codes, OTPs, wallet verification, or password inputs.
    *   *Spam Risk:* Unsolicited promotions, coupons, or messages from unsubscribed business accounts.
    *   *Forward Risk:* Messages forwarded multiple times containing chain letters or generic motivational greetings.
4.  **User Behaviour Features:** (Captures personalized recipient habits)
    *   *Historical Engagement:* The user's past actions (dismissed, read, reported) on similar categories.
    *   *Notification Fatigue:* Recipient's current daily count of notifications received vs dismissed.
    *   *Quiet Hours:* Timestamp comparison against user's DND settings.

---

### Section 5: The Safety Layer (Hard Override Pipeline)

The system passes all features through a strict safety evaluation chain that overrides personal preferences:

```
Safety Evaluation Chain:
Prompt Injection Detection
│
▼
Scam Detection
│
▼
OTP Fraud Detection
│
▼
Phishing Analysis
│
▼
Fake Verification Check
│
▼
Safety Override (Hard 'mute' if flagged)
```

*Rule: Safety Overrides Personalization. Any message flagged by the Safety Layer is immediately routed to `mute`, regardless of user engagement history.*

---

### Section 6: Decomposed 3-Stage Decision Engine & Rationale

Reasoning is broken down into three specialized sequential stages to avoid monolithic prompt failure:

*   **Stage 1: Understanding Engine** -> Determines what the message actually means (*Outputs: message_type, summary, urgency, intent*).
*   **Stage 2: Risk Assessment Engine** -> Determines whether the message is trustworthy (*Outputs: spam probability, scam indicators, sender trust, business trust, safety flags*).
*   **Stage 3: Notification Decision Engine** -> Determines whether the user should be interrupted right now (*Outputs: action [notify, digest, mute], reason, confidence, evidence*).

#### Why 3 Stages instead of a Monolithic Prompt?
1.  **Isolation of Concerns:** Prevents safety risks (e.g. prompt hijacking, scam details) from being diluted by user preference logic.
2.  **Deterministic Overrides:** Enables hard safety rules between Stage 2 and Stage 3 to ensure instant silencing of high-risk files.
3.  **Explainability & Debuggability:** Intermediate outputs from Stage 1 and Stage 2 can be logged and audited independently.

---

### Section 7: Explainability Flow

Traceability is maintained end-to-end throughout the reasoning cycle:

```
Features ──► Reasoning ──► Decision Reason ──► Historical Evidence ──► Confidence Calibration ──► Final Routing Prediction
```

---

### Section 8: Confidence Strategy

Numerical confidence is calculated and calibrated:

*   **Confidence Increases When:** Multiple feature signals agree (e.g., both DND checks and low-priority labels trigger digest), historical interactions strongly support the decision (e.g. repeated replies to work contacts), and sender trust is high.
*   **Confidence Decreases When:** Feature signals conflict, language is ambiguous, the sender is unknown, or historical context is scarce.

---

### Section 9: Future Scalability

The design is architected to support long-term production deployment:

*   **Real-time Stream Processing:** Capable of event-driven inference at high throughput.
*   **Online Personalization:** Supports incremental learning of user preferences without retraining from scratch.
*   **Modular Model Swapping:** The LLM/VLM backing reasoning stages can be upgraded without changing data contracts.
*   **Localization Support:** Structurally ready to handle multi-language messages and regional dialects.
