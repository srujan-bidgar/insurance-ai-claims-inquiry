# Architecture - Claims Inquiry Concierge

## System Design

The system uses a linear three-agent pipeline with guarded handoffs. Each agent has a single,
well-scoped responsibility. No agent communicates with another directly - the orchestrator
controls all routing and carries state between stages.

This design prioritises:
- Auditability: every stage's input and output is logged separately
- Fail-safety: errors at any stage block delivery rather than pass through
- Compliance separation: validation (Agent 1) is decoupled from generation (Agent 2)
  and review (Agent 3), so no single prompt handles both creation and compliance

## Agent 1 — guardrailCheck

Model: Claude Haiku 4.5  
Rationale: The guardrail task produces three booleans. It does not require complex
reasoning — it requires fast, reliable classification. Haiku handles this at roughly
$0.001 per call with sub-second latency.

A regex pre-flight runs before the LLM call. Hard patterns (SSN format, PAN, card numbers,
VINs) are caught deterministically and for free. The LLM handles the ambiguous cases:
partial masking, distress detection, off-topic classification.

Alternatives considered:
- GPT-4o-mini: comparable cost and speed, viable alternative. Selected Haiku for
  consistency across the stack and slightly stronger instruction adherence.
- Rules-only (no LLM): insufficient for distress detection and off-topic classification,
  which require semantic understanding.

## Agent 2 — claimParser

Model: Claude Sonnet 4.6  
Rationale: This is the hardest task in the pipeline. The model must simultaneously:
classify intent across three categories, assign priority using nuanced injury/loss criteria,
estimate a plausible dollar figure, and draft a compliant natural language reply.

Haiku's output quality degrades noticeably on multi-constraint generation tasks. Testing
showed it occasionally dropped the required disclaimer or misclassified Medium/High priority.
Sonnet reliably produces valid JSON and handles the compliance constraints.

Alternatives considered:
- GPT-4o: comparable quality. Sonnet selected for stronger instruction adherence, which is the highest-stakes constraint in this system.
- Opus: overkill for this task, 1.67x the cost of Sonnet with no measurable quality gain
  on structured extraction.

Few-shot prompting: Four calibrated examples are included in the system prompt to anchor
priority scoring. Without examples, the model underestimates "High" priority cases.

## Agent 3 — safetyChecks

Model: Claude Haiku 4.5  
Rationale: Compliance review is a detection task , not a generation task. Haiku is well-suited. A deterministic string check on the required fisclaimer runs before the LLM call - this is the highest-frequency check and doesn't need a model.

On a compliance failure, the orchestrator passes a targeted correction note back to Agent 2
and retries once. If the second attempt also fails, the pipeline returns a safe fallback
response rather than delivering a non-compliant reply.

## Cost and Latency Tradeoffs

| Scenario | Est. cost | Est. P50 latency |
|---|---|---|
| Normal delivery (all 3 agents) | ~$0.007 | ~4–6s |
| PII block (regex only, no LLM) | ~$0.001 | <100ms |
| Compliance retry (4 agent calls) | ~$0.012 | ~7–9s |

The 5-second P50 target is achievable for standard cases. Compliance retries push latency
up but are expected to be infrequent (<5% of traffic based on prompt calibration).

Production optimisations not implemented in this pilot:
- Prompt caching on system prompts (90% input cost reduction on repeated calls)
- Async Agent 3 call (run compliance check while logging Agent 2 result)
- Batch API for non-real-time audit workflows (50% cost reduction)