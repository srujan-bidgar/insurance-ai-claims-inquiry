## Agent 3 — safetyChecks

import re
import json
import time
import anthropic

DISCLAIMER = (
    "All claims are subject to policy terms, coverage verification, and investigation. "
    "This is not a determination of coverage."
)

# Phrases that constitute coverage guarantees or denials
HARD_BLOCK_PHRASES = [
    r"\byour claim (is|has been) approved\b",
    r"\byou (will|are going to) receive \$",
    r"\bwe (will|are going to) pay\b",
    r"\bclaim (is|has been) denied\b",
    r"\bnot covered\b",
    r"\bguarantee(d)?\b",
    r"\bsettle(d|ment)? for \$",
    r"\bpayout (of|is) \$",
]

SAFETY_SYSTEM_PROMPT = """You are a compliance reviewer for an insurance carrier AI system.
Review the reply below and return a JSON object assessing three compliance rules.

RULE 1 — No coverage guarantee or denial:
Flag if the reply contains any of:
- Explicit approval ("your claim is approved", "you will receive $X")
- Explicit denial ("your claim is denied", "this is not covered")
- Any commitment to a specific payout amount or timeline

RULE 2 — No misleading or deceptive language:
Flag if the reply:
- Misrepresents policy terms
- Pressures the claimant to accept any amount
- Promises a specific processing speed
- Uses language designed to minimise or dismiss the claim

RULE 3 — Disclaimer present:
The reply MUST contain this exact phrase (or a close paraphrase):
"All claims are subject to policy terms, coverage verification, and investigation. This is not a determination of coverage."

Return ONLY valid JSON:
{
  "compliance_pass": <true if all three rules pass, false otherwise>,
  "violations": [<list of short violation descriptions, empty if none>]
}

No explanation outside the JSON.
"""

def _hard_phrase_check(reply: str) -> list:
    lower = reply.lower()
    found = []
    for pattern in HARD_BLOCK_PHRASES:
        if re.search(pattern, lower):
            found.append(f"Blocked phrase matched: '{pattern}'")
    return found


def run(reply: str, client: anthropic.Anthropic) -> dict:
    start = time.time()

    disclaimer_present = DISCLAIMER.lower() in reply.lower()

    hard_violations = _hard_phrase_check(reply)

    for attempt in range(2):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=120,
                system=SAFETY_SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": f"Review this reply:\n\n{reply}"
                }],
            )
            raw = response.content[0].text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw).strip()

            result = json.loads(raw)

            # Merging all hard violations into LLM result
            all_violations = result.get("violations", []) + hard_violations
            if not disclaimer_present:
                all_violations.append("Missing required disclaimer")

            compliance_pass = (
                result.get("compliance_pass", False)
                and not hard_violations
                and disclaimer_present
            )

            return {
                "compliance_pass": compliance_pass,
                "violations": all_violations,
                "disclaimer_present": disclaimer_present,
                "latency_ms": round((time.time() - start) * 1000, 1),
                "source": "llm",
            }

        except Exception as exc:
            if attempt == 1:
                return {
                    "compliance_pass": False,
                    "violations": [f"Compliance agent error: {str(exc)}"],
                    "disclaimer_present": disclaimer_present,
                    "latency_ms": round((time.time() - start) * 1000, 1),
                    "source": "fallback_block",
                }