# Intelligent WhatsApp Message Prioritization System

## Overview

This project is an AI-powered WhatsApp message prioritization system developed for the HackerRank AI Hackathon.

Instead of treating every incoming message equally, the system analyzes message content, sender history, user behavior, and historical interactions to intelligently decide whether a message should:

- Notify the user immediately
- Be grouped into a digest
- Be muted

The system combines rule-based reasoning, machine learning style scoring, historical evidence retrieval, and Large Language Models (LLMs) to produce explainable and reliable decisions.

---

# Features

- AI-powered semantic message understanding
- Multimodal support
  - Text
  - Images
  - Voice Notes
- Feature extraction from sender, conversation, and message metadata
- Personalized assessment engine
- Historical evidence retrieval
- Explainable decision engine
- Hybrid LLM routing
  - Google Gemini
  - OpenRouter
- Automatic provider failover
- Model health tracking
- Response caching
- End-to-end evaluation pipeline

---

# Project Structure

```
code/
│
├── loader/
├── context/
├── features/
├── understanding/
├── assessment/
├── evidence/
├── decision/
├── output/
├── evaluation/
├── ai/
└── main.py

dataset/
├── messages.csv
├── output.csv
└── media/

tests/

scripts/
```

---

# System Pipeline

```
Messages
      │
      ▼
Data Loader
      │
      ▼
Context Builder
      │
      ▼
Feature Extraction
      │
      ▼
Semantic Understanding
(Text / Image / Voice)
      │
      ▼
Assessment Engine
      │
      ▼
Evidence Retrieval
      │
      ▼
Decision Engine
      │
      ▼
Output Generator
      │
      ▼
output.csv
```

---

# AI Architecture

The system uses a hybrid LLM routing layer.

Primary Provider

- Google Gemini

Automatic Failover

- OpenRouter

Supported fallback models include:

- Google Gemini Flash
- OpenAI GPT-4.1 Mini
- Anthropic Claude 3.5 Haiku

The router automatically switches providers when transient failures occur (rate limits, quota exhaustion, or temporary server errors).

---

# Setup Instructions

## 1. Clone the repository

```bash
git clone <repository-url>
cd <repository-folder>
```

---

## 2. Create a virtual environment

```bash
python3 -m venv .venv
```

Activate it

macOS/Linux

```bash
source .venv/bin/activate
```

Windows

```bash
.venv\Scripts\activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Create a `.env` file in the project root.

Example:

```env
LLM_PROVIDER=hybrid

PRIMARY_PROVIDER=gemini
SECONDARY_PROVIDER=openrouter

GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-2.5-flash

OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY

OPENROUTER_MODELS=google/gemini-2.5-flash,openai/gpt-4.1-mini,anthropic/claude-3.5-haiku

OPENROUTER_SITE_URL=http://localhost
OPENROUTER_APP_NAME=HackerRank Message Router
```

---

# Running the Project

Generate the submission file:

```bash
python code/main.py
```

This generates

```
dataset/output.csv
```

---

# Running Evaluation

```bash
python code/evaluation/main.py
```

Expected result:

```
"is_valid": true
```

---

# Running Tests

Run all tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Additional validation

```bash
python code/test_sprint1.py

python code/validate_understanding.py

python code/validate_assessment.py

python scripts/validate_llm_router.py
```

---

# Decision Strategy

Each message is processed through multiple stages:

1. Context construction
2. Feature extraction
3. Semantic understanding
4. Trust & risk assessment
5. Historical evidence retrieval
6. Decision scoring
7. Explainable action generation

The final action is one of:

- notify
- digest
- mute

along with:

- confidence score
- message type
- explanation
- supporting historical evidence

---

# Technologies Used

- Python
- Pydantic
- Pandas
- Google Gemini API
- OpenRouter API
- REST APIs
- JSON
- CSV

---

# Submission Outputs

The project produces:

- `dataset/output.csv` – Final prediction file
- Evaluation report
- Validation reports

---

# Authors

Developed as part of the HackerRank AI Hackathon.
