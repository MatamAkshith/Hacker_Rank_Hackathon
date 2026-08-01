# System Architecture Specification

This document details the modular system design, processing stages, and reasoning framework for the WhatsApp Message Notification Router.

---

### Section 1: High-Level Architecture

The system follows a modular AI pipeline where incoming WhatsApp messages are enriched with user, sender, group, business, media, and historical context before passing through multiple reasoning layers. Instead of classifying messages directly, the engine constructs contextual features, retrieves relevant historical evidence, evaluates safety and personalization, and finally produces a routing decision with confidence and supporting evidence.

---

### Section 2: Processing Pipeline

The processing pipeline is organized in the following sequential stages:

```
Incoming Message
│
▼
Data Loader
│
▼
Context Builder
│
▼
Media Understanding
│
▼
Feature Extraction
│
▼
Decision Engine
│
▼
Evidence Retrieval
│
▼
Confidence Calibration
│
▼
Output Generator
```

---

### Section 3: Module Responsibilities

Each module has a single-responsibility contract:

1.  **Data Loader:** Reads and validates all dataset files (`messages.csv`, `dataset/test.csv`, and media directories).
2.  **Context Builder:** Builds a unified context object combining:
    *   user
    *   sender
    *   group
    *   business
    *   message history
    *   notification statistics
3.  **Media Processor:** Processes text, image (posters/screenshots), and voice notes into a unified semantic/textual representation.
4.  **Feature Extractor:** Computes structured reasoning signals (inputs to the decision engine, not final model outputs):
    *   Sender Trust
    *   Business Trust
    *   Urgency
    *   Promotion Score
    *   Spam Risk
    *   Relationship Strength
    *   Forward Risk
    *   Notification Fatigue
    *   Quiet Hours
    *   Historical Engagement
    *   Scam Indicators
5.  **Decomposed Decision Engine:** (Decomposed into three specialized sequential stages to avoid monolithic prompt failure)
    *   **Stage 1: Understanding** -> Outputs: `message_type`, `summary`, `urgency`, `intent` ("What is this message actually about?")
    *   **Stage 2: Risk Assessment** -> Outputs: `spam probability`, `scam indicators`, `sender trust`, `business trust`, `safety flags` ("Can this message be trusted?")
    *   **Stage 3: Notification Decision** -> Outputs: `action` (`notify`, `digest`, `mute`), `reason`, `confidence`, `evidence` ("Should this user be interrupted?")
6.  **Evidence Retriever:** Finds historical messages (`evidence_message_ids`) that justify the decision to satisfy dataset schema requirements.
7.  **Confidence Estimator:** Assigns calibrated confidence scores based on:
    *   feature agreement
    *   ambiguity
    *   historical similarity
    *   safety overrides
8.  **Output Generator:** Formats and creates the schema-compliant `output.csv`.

---

### Section 4: Core Reasoning Principles

The system is guided by these exact five foundational principles:

1.  **Personalization First:** Every message is evaluated relative to the specific recipient.
2.  **Safety Overrides Personalization:** Clear scams, phishing, or safety risks are muted regardless of user engagement or preferences.
3.  **Historical Behaviour Matters:** Past interaction patterns strongly influence future routing choices.
4.  **Multimodal Consistency:** Text, images, and voice notes are unified into one common representation before reasoning.
5.  **Explainability:** Every decision must be fully explainable through structured features and historical evidence.

---

### Section 5: Data Flow

The flow of data proceeds as follows:

```
messages.csv
↓
context builder
↓
user profile
↓
history retrieval
↓
media summary
↓
feature vector
↓
reasoning
↓
prediction
```

---

### Section 6: Design Decisions & Justifications

Engineering design decisions and justifications:

1.  **Decision:** Rule-assisted LLM reasoning.
    *   **Why:** Pure prompting is inconsistent; pure rules lack flexibility. Hybrid reasoning combines the structural determinism of rules with the flexibility of LLMs.
2.  **Decision:** Feature extraction before reasoning.
    *   **Why:** Reduces prompt complexity while making decisions transparent and explainable.
3.  **Decision:** Separate evidence retrieval from decision engine.
    *   **Why:** Allows evidence selection algorithms to improve independently without affecting routing logic.
4.  **Decision:** Decomposed 3-Stage Decision Engine over a Monolithic Engine.
    *   **Why:** Makes the system easier to unit test, explain, evaluate, and extend than a single giant prompt.
