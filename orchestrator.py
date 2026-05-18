import os
import time
import anthropic
from dotenv import load_dotenv

from agents import guardrail_check, claim_parser, safety_checks

load_dotenv()

MAX_COMPLIANCE_RETRIES = 1


def _make_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set. Add it to your .env file or export it."
        )
    return anthropic.Anthropic(api_key=api_key)


def process_message(message: str, client: anthropic.Anthropic = None) -> dict:
    if client is None:
        client = _make_client()

    pipeline_start = time.time()

    result = {
        "input": message,
        "guardrail": None,
        "parser": None,
        "compliance": None,
        "final_response": None,
        "pipeline_status": None,                                  
        "total_latency_ms": None,
    }

    # Agent 1 — guardrailCheck
    guardrail = guardrail_check.run(message, client)
    result["guardrail"] = guardrail

    if not guardrail.get("no_pii", False):
        result["pipeline_status"] = "blocked_pii"
        result["final_response"] = (
            "We noticed your message may contain sensitive personal information. "
            "For your security, please do not share full policy numbers, ID numbers, "
            "or financial details in chat. A representative will contact you securely. "
            + claim_parser.DISCLAIMER
        )
        result["total_latency_ms"] = round((time.time() - pipeline_start) * 1000, 1)
        return result

    if not guardrail.get("is_insurance_related", False):
        result["pipeline_status"] = "blocked_off_topic"
        result["final_response"] = (
            "It looks like your message may not be related to an insurance claim or coverage question. "
            "If you have a claims or coverage enquiry, please describe your situation and we will assist you."
        )
        result["total_latency_ms"] = round((time.time() - pipeline_start) * 1000, 1)
        return result

    
    if guardrail.get("needs_escalation", False):
        result["pipeline_status"] = "escalated"

    # Agent 2 — claimParser
    parsed = claim_parser.run(message, client)
    result["parser"] = parsed

    # Agent 3 — safetyChecks (with one retry)
    reply_text = parsed.get("summary_response", "")
    compliance = safety_checks.run(reply_text, client)
    result["compliance"] = compliance

    if not compliance.get("compliance_pass", False):
        violations_str = "; ".join(compliance.get("violations", ["unspecified violation"]))
        correction_note = (
            f"Your previous reply had compliance issues: {violations_str}. "
            "Rewrite it ensuring: no coverage guarantees, no settlement amounts, "
            "no denial language, and include the required disclaimer verbatim."
        )
        # Retry Agent 2 with correction
        parsed = claim_parser.run(message, client, correction_note=correction_note)
        result["parser"] = parsed

        # Re-check compliance
        reply_text = parsed.get("summary_response", "")
        compliance = safety_checks.run(reply_text, client)
        result["compliance"] = compliance

        if not compliance.get("compliance_pass", False):
            result["pipeline_status"] = "blocked_compliance"
            result["final_response"] = (
                "We received your enquiry and a representative will be in touch shortly. "
                + claim_parser.DISCLAIMER
            )
            result["total_latency_ms"] = round((time.time() - pipeline_start) * 1000, 1)
            return result


    # Result
    if result["pipeline_status"] != "escalated":
        result["pipeline_status"] = "delivered"

    result["final_response"] = reply_text
    result["total_latency_ms"] = round((time.time() - pipeline_start) * 1000, 1)
    return result

# CLI testing
if __name__ == "__main__":
    import json
    print("Claims Inquiry Concierge — manual test mode")
    print("Type a policyholder message and press Enter. Ctrl-C to quit.\n")
    client = _make_client()
    while True:
        try:
            msg = input("Policyholder: ").strip()
            if not msg:
                continue
            out = process_message(msg, client)
            print("\n--- Pipeline Result ---")
            print(json.dumps(out, indent=2))
            print()
        except KeyboardInterrupt:
            print("\nExiting.")
            break