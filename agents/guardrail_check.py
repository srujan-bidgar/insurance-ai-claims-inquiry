## Agent 1 — guardrailCheck

import re
import json
import time
import anthropic

# Hard PII patterns — regex pre-flight 
PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b",           "SSN"),
    (r"\b\d{4}\s\d{4}\s\d{4}\b",          "Aadhaar"),
    (r"\b[A-Z]{5}\d{4}[A-Z]\b",           "PAN"),
    (r"\b\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b", "card_number"),
    (r"\b[A-HJ-NPR-Z0-9]{17}\b",          "VIN"),
]

# Keywords to determine insurance relevance.
INSURANCE_KEYWORDS = {
    "claim", "claims", "policy", "coverage", "insur", "accident", "damage",
    "adjuster", "deductible", "premium", "collision", "flood", "fire", "theft",
    "roof", "vehicle", "car", "home", "house", "property", "loss", "repair",
    "hospital", "injury", "injuries", "totalled", "totaled", "liability",
}


def _regex_pii_check(message: str) -> tuple:
    upper = message.upper()
    found = []
    for pattern, label in PII_PATTERNS:
        target = upper if label in ("PAN", "VIN") else message
        if re.search(pattern, target):
            found.append(label)
    return bool(found), found


def _keyword_insurance_check(message: str) -> bool:
    lower = message.lower()
    return any(kw in lower for kw in INSURANCE_KEYWORDS)


GUARDRAIL_SYSTEM_PROMPT = """You are a guardrail agent for an insurance claims intake system.
Analyse the policyholder message and return a JSON object with exactly three boolean fields.

is_insurance_related: true if the message concerns claims (auto/home/property), coverage questions, or policy administration. False for anything unrelated.

no_pii: false if the message contains unmasked sensitive identifiers such as full SSN, Aadhaar, PAN, full policy/claim numbers, bank/card numbers, driver's license, or VIN. Partial masking like ****-4321 is acceptable (set to true). True if no unmasked identifiers are present.

needs_escalation: true ONLY if the message suggests active self-harm threats, severe ongoing distress (catastrophic loss in progress right now), or an active safety emergency (fire in progress, injuries happening now). False for past events, general frustration, or urgency.

Return ONLY valid JSON. No explanation, no markdown fences, no extra keys.
Example: {"is_insurance_related": true, "no_pii": true, "needs_escalation": false}
"""


def run(message: str, client: anthropic.Anthropic) -> dict:
    """
    Runs the guardrail check. Returns dict with guardrail fields plus metadata.
    Fail-safe: on any error, blocks the message rather than passing it through.
    """
    start = time.time()

    has_pii, pii_types = _regex_pii_check(message)
    if has_pii:
        is_insurance = _keyword_insurance_check(message)
        return {
            "is_insurance_related": is_insurance,
            "no_pii": False,
            "needs_escalation": False,
            "pii_types_detected": pii_types,
            "source": "regex_block",
            "latency_ms": round((time.time() - start) * 1000, 1),
        }

    
    for attempt in range(2):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=80,
                system=GUARDRAIL_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": message}],
            )
            raw = response.content[0].text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw).strip()

            result = json.loads(raw)
            for key in ("is_insurance_related", "no_pii", "needs_escalation"):
                if key not in result:
                    raise ValueError(f"Missing key in LLM response: {key}")

            result["pii_types_detected"] = []
            result["source"] = "llm"
            result["latency_ms"] = round((time.time() - start) * 1000, 1)
            return result

        except Exception as exc:
            if attempt == 1:
                return {
                    "is_insurance_related": False,
                    "no_pii": False,
                    "needs_escalation": False,
                    "pii_types_detected": [],
                    "source": "fallback_block",
                    "error": str(exc),
                    "latency_ms": round((time.time() - start) * 1000, 1),
                }