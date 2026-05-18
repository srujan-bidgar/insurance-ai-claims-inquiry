# Claims Inquiry Concierge — Insurance AI

A 3-agent AI system that handles the first turn of a policyholder conversation.
Classifies the inquiry, returns structured output, and applies compliance and privacy checks.

## Architecture

```
Policyholder message
        │
        ▼
 [Agent 1] guardrailCheck   (Claude Haiku 4.5)
   - PII detection (regex + LLM)
   - Insurance relevance check
   - Distress / escalation detection
        │
        ├── PII found       → block
        ├── Off-topic       → redirect
        ├── Needs escalation→ flag + continue
        │
        ▼
 [Agent 2] claimParser      (Claude Sonnet 4.6)
   - Intent classification
   - Priority assignment
   - Loss estimation
   - Compliant reply drafting
        │
        ▼
 [Agent 3] safetyChecks     (Claude Haiku 4.5)
   - Coverage guarantee/denial check
   - Disclaimer presence check
   - Misleading language check
        │
        ├── Fail → retry Agent 2 with correction note (1 retry max)
        │
        ▼
   Compliant reply delivered
```

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo>
cd claims-ai
pip install -r requirements.txt
```

### 2. Set your API key

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Or export it in your shell:

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 3. Run a quick manual test

```bash
python orchestrator.py
```

Type any policyholder message and see the full pipeline output.

## Running the Evaluation

```bash
# Run all 18 cases
python eval/run_eval.py

# Run only adversarial and PII cases
python eval/run_eval.py --category adversarial pii_injection

# Run specific cases by ID
python eval/run_eval.py --id TC01 TC10 TC16
```

## Project Structure

```
claims-ai/
├── agents/
│   ├── guardrail_check.py   # Agent 1 — Intake Guardrails
│   ├── claim_parser.py      # Agent 2 — Inquiry Inference
│   └── safety_checks.py     # Agent 3 — Compliance
├── eval/
│   ├── test_cases.json      # 18 evaluation cases
│   └── run_eval.py          # Evaluation harness
├── docs/
│   ├── architecture.md      # Architecture rationale
│   └── exec_email.md        # Executive email to Head of Claims
├── orchestrator.py          # Pipeline orchestration
├── requirements.txt
└── README.md
```

## Model Selection Rationale

| Agent | Model | Reason |
|---|---|---|
| Guardrails | Haiku 4.5 ($1/$5 per MTok) | Boolean output, latency-critical, cheap. Regex pre-check handles obvious PII for free. |
| Parser | Sonnet 4.6 ($3/$15 per MTok) | Requires genuine NLU for intent, priority nuance, and safe reply drafting. |
| Compliance | Haiku 4.5 ($1/$5 per MTok) | Pattern classification task; string-based disclaimer check runs free before LLM call. |

Estimated cost per conversation: ~$0.007. Batch of 1,000 conversations: ~$7.