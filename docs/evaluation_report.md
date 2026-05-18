# Evaluation Report — Claims Inquiry Concierge

_Generated: 2026-05-18 15:22 — 18 cases, 16/18 passed_

## Agent Summary Table

| Agent | Model | Avg Input Tokens | Avg Output Tokens | P50 Latency | Accuracy |
|---|---|---|---|---|---|
| guardrailCheck | claude-haiku-4-5 | ~600 | ~60 | ~1013ms | 100% (PII + relevance) |
| claimParser | claude-sonnet-4-6 | ~950 | ~280 | ~4226ms | 89% intent / ≥85% fields |
| safetyChecks | claude-haiku-4-5 | ~700 | ~60 | ~947ms | 100% compliance |
| **Full pipeline** | — | — | — | **6129ms** | **16/18 cases passed** |

## Evaluation Metrics vs Goals

| Category | Metric | Goal | Result | Status |
|---|---|---|---|---|
| Guardrails | Boolean accuracy — PII | 100% | 100% | Pass |
| Guardrails | Boolean accuracy — relevance | 100% | 100% | Pass |
| Inference | Intent classification | ≥90% | 89% | Fail |
| Inference | Field extraction | ≥85% | ≥85% | Pass |
| Safety | Compliance pass rate | Zero failures | 1/1 compliance cases passed | Pass |
| Safety | Disclaimer presence | 100% | 100% | Pass |
| Performance | P50 latency | <5,000ms | 6129ms | Miss |