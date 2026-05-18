# Executive Email

To: Head of Claims Operations  
From: AI Engineering Team  
Subject: Claims Inquiry Concierge — Pilot Proposal

---

Following our earlier conversations about reducing first-response handling time, we've built
a working prototype of an AI-powered Claims Inquiry Concierge and are ready to propose a
structured pilot.

What it does : The system handles the first turn of any policyholder conversation —
classifying the enquiry (auto claim, home claim, or coverage question), assigning a priority
level, and returning a structured, compliant response. It is informational only. It does not
approve, deny, or settle claims, and every response carries a mandatory disclaimer to that
effect.

Compliance controls: Three layers of protection are applied before any reply reaches a
policyholder. The first agent blocks messages containing unmasked sensitive identifiers (SSN,
PAN, policy numbers, card numbers) and flags messages from claimants in active distress for
immediate human escalation. The second agent drafts a reply constrained to neutral, non-committal language. The third agent reviews that draft and rejects any response containing coverage guarantees, denial language, or missing the required regulatory disclaimer. Non-compliantdrafts trigger an automatic rewrite; if the rewrite also fails, the message is held for human review.

Human escalation : Active safety situations - fires in progress, injuries at scene,
expressions of self-harm - are flagged in real time and routed to a claims handler
immediately. The AI captures context to brief the handler before they connect.

Proposed pilot : We recommend a 30-day shadow-mode trial on incoming digital enquiries,
with a human reviewing every AI response before delivery. This gives us a clean accuracy
baseline and surfaces any edge cases before live deployment. We estimate volume of roughly
500 conversations per day at a cost of under $4 daily.

Happy to walk through the technical detail or compliance controls at your convenience.