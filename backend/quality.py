"""
Send-readiness quality check — evaluates a lead's outreach before it goes out
so quality control is instant. Returns a readiness level + specific warnings.

This is the "would I actually send this?" gate. It does NOT block sending
(the operator decides) — it just surfaces issues fast.
"""
import re

# Words/phrases that trip spam filters or read as salesy
SPAM_TRIGGERS = [
    "act now", "limited time", "click here", "buy now", "100% free",
    "risk-free", "guarantee", "guaranteed", "cash", "earn money",
    "make money", "no obligation", "winner", "congratulations",
    "urgent", "exclusive deal", "best price", "lowest price",
    "increase sales", "double your", "skyrocket", "revolutionary",
    "game-changing", "game changer", "cutting-edge", "synergy",
    "unlock", "supercharge", "10x ",
]

MAX_SUBJECT_LEN = 65
MAX_BODY_LEN = 1300  # chars for the initial email


def check_lead(lead) -> dict:
    """Return {level, warnings, blocking}. level: ready | warn | blocked."""
    warnings = []
    blocking = []

    email = (lead.contact_email or "").strip()
    name = (lead.contact_name or "").strip()
    subject = (lead.subject_line or "").strip()
    body = (lead.email_body or "").strip()

    # Blocking: can't actually send without a recipient
    if not email:
        blocking.append("No contact email — add one before sending")
    elif "@" not in email:
        blocking.append("Contact email looks invalid")

    # Warnings: weak personalization / deliverability risk
    if not name:
        warnings.append("No contact name — adding one (first name in the greeting) noticeably lifts replies")

    if not subject:
        blocking.append("Missing subject line")
    elif len(subject) > MAX_SUBJECT_LEN:
        warnings.append(f"Subject is long ({len(subject)} chars) — aim under {MAX_SUBJECT_LEN}")

    if not body:
        blocking.append("Missing email body")
    elif len(body) > MAX_BODY_LEN:
        warnings.append(f"Initial email is long ({len(body)} chars) — shorter usually replies better")

    # Spam-trigger scan (subject + body)
    haystack = f"{subject} {body}".lower()
    hits = sorted({t.strip() for t in SPAM_TRIGGERS if t in haystack})
    if hits:
        warnings.append(f"Possible spam-trigger wording: {', '.join(hits[:4])}")

    # Placeholder check — unfilled template tokens
    if "[your name]" in body.lower() and body.lower().count("[") > 1:
        warnings.append("Contains unfilled placeholders")

    if blocking:
        level = "blocked"
    elif warnings:
        level = "warn"
    else:
        level = "ready"

    return {"level": level, "warnings": warnings, "blocking": blocking}
