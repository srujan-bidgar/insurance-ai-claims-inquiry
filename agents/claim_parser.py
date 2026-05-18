## Agent 2 — claimParser

import re
import json
import time
import anthropic

DISCLAIMER = (
    "All claims are subject to policy terms, coverage verification, and investigation. "
    "This is not a determination of coverage."
)

PARSER_SYSTEM_PROMPT = f"""You are a claims intake specialist AI for an insurance carrier.
Your job is to read a policyholder's message and return a single valid JSON object.

ALLOWED INTENTS (pick exactly one):
- "Auto claim"
- "Home claim"
- "Coverage inquiry"

PRIORITY RULES (apply strictly):
- "Low"    — minor incident, no injuries, low estimated loss (under $2,000)
- "Medium" — moderate damage, no injuries, no ongoing risk ($2,000–$20,000)
- "High"   — significant loss, injuries reported, or active property exposure (over $20,000 or any injury)

REPLY RULES (for summary_response):
- Calm, neutral, professional tone
- Do NOT guarantee or deny coverage
- Do NOT commit to any settlement amount or payout timeline
- Do NOT mention protected characteristics (race, age, religion, disability, etc.)
- You MUST end every reply with exactly this disclaimer:
  "{DISCLAIMER}"

ESTIMATED LOSS AMOUNT:
- Provide a reasonable integer estimate in USD based on the incident described.
- If the message is a coverage inquiry with no loss, use 0.
- Use domain knowledge: minor fender-bender ~$1,500, roof damage ~$12,000, total loss vehicle ~$25,000.

OUTPUT FORMAT — return ONLY this JSON, no markdown, no extra text:
{{
  "intent": "<one of the three allowed intents>",
  "estimated_loss_amount": <integer>,
  "priority": "<Low | Medium | High>",
  "summary_response": "<your compliant reply including the disclaimer>"
}}

--- FEW-SHOT EXAMPLES ---

User: "A tree fell on my roof last night during the storm. There's a big hole and water is getting in."
Output: {{"intent": "Home claim", "estimated_loss_amount": 15000, "priority": "High", "summary_response": "We're sorry to hear about the storm damage to your home. We'll open a claim right away and connect you with a field adjuster who can assess the damage. In the meantime, if it's safe to do so, temporary tarping can help limit further water intrusion. {DISCLAIMER}"}}

User: "Someone scratched my car door in a parking lot yesterday. No other cars involved."
Output: {{"intent": "Auto claim", "estimated_loss_amount": 800, "priority": "Low", "summary_response": "Thank you for reporting this. We can open an auto claim and arrange a damage assessment at a time that works for you. A claims representative will be in touch shortly. {DISCLAIMER}"}}

User: "Does my policy cover flooding from a burst pipe? I'm not sure if that's different from flood insurance."
Output: {{"intent": "Coverage inquiry", "estimated_loss_amount": 0, "priority": "Low", "summary_response": "That's a great question. Coverage for water damage from a burst pipe is typically different from flood insurance, but the specifics depend on your individual policy terms. We recommend reviewing your policy documents or speaking with your agent for a precise answer. {DISCLAIMER}"}}

User: "There was a three-car accident on the highway. Two people were taken to hospital. My car is totalled."
Output: {{"intent": "Auto claim", "estimated_loss_amount": 35000, "priority": "High", "summary_response": "We're very sorry to hear about this serious accident. We're opening a priority claim immediately and a dedicated adjuster will contact you within 24 hours. Please seek any medical attention you need. {DISCLAIMER}"}}
---
"""

def run(message: str, client: anthropic.Anthropic, correction_note: str = "") -> dict:
    
    start = time.time()

    user_content = message
    if correction_note:
        user_content = f"{message}\n\n[SYSTEM NOTE — revise your previous reply: {correction_note}]"

    for attempt in range(2):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=400,
                system=PARSER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            raw = response.content[0].text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw).strip()

            result = json.loads(raw)

            # Validating intent
            allowed = {"Auto claim", "Home claim", "Coverage inquiry"}
            if result.get("intent") not in allowed:
                raise ValueError(f"Invalid intent: {result.get('intent')}")

            # Validating priority
            if result.get("priority") not in {"Low", "Medium", "High"}:
                raise ValueError(f"Invalid priority: {result.get('priority')}")

            # Hard-inject disclaimer / fail-safe for disclaimer
            reply = result.get("summary_response", "")
            if DISCLAIMER not in reply:
                result["summary_response"] = reply.rstrip() + " " + DISCLAIMER

            result["latency_ms"] = round((time.time() - start) * 1000, 1)
            result["source"] = "llm"
            return result

        except json.JSONDecodeError:
            if attempt == 0:
                # Retry 
                user_content = (
                    f"{message}\n\n"
                    "[SYSTEM NOTE — your previous response was not valid JSON. "
                    "Return ONLY the JSON object, no other text.]"
                )
                continue
            # If both attempts failed
            return {
                "intent": "Coverage inquiry",
                "estimated_loss_amount": 0,
                "priority": "Low",
                "summary_response": (
                    "We received your message but encountered a processing issue. "
                    "A representative will contact you shortly. "
                    + DISCLAIMER
                ),
                "latency_ms": round((time.time() - start) * 1000, 1),
                "source": "fallback",
            }

        except Exception as exc:
            return {
                "intent": "Coverage inquiry",
                "estimated_loss_amount": 0,
                "priority": "Low",
                "summary_response": (
                    "We received your message but encountered a processing issue. "
                    "A representative will contact you shortly. "
                    + DISCLAIMER
                ),
                "latency_ms": round((time.time() - start) * 1000, 1),
                "source": "fallback",
                "error": str(exc),
            }