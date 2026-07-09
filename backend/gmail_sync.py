"""
Gmail sync — make the pipeline's status reflect what ACTUALLY happened in Gmail,
so the HUD shows reality instead of whatever was last marked by hand.

Two reconciliations, each degrading gracefully on its own:

  1. SENT  — a draft that left your Drafts folder went out. Uses the existing
             compose scope (gmail_drafts.list_draft_ids); NO extra permission.
  2. REPLIED — searches your inbox for a message FROM each prospect we emailed.
             Needs the read scope (gmail_read / gmail_read_token.json). Skipped
             cleanly, with a flag, if you haven't granted read access yet.

Safe by construction: it only READS Gmail and flips lead statuses in the local
DB. It never sends and never deletes anything in Gmail.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import gmail_drafts
import gmail_read
from db import Lead

_EMAILED_STATUSES = ("queued", "approved", "sent")
_TERMINAL = ("replied", "meeting", "closed", "rejected")


def _now():
    return datetime.now(timezone.utc)


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _marker(notes: str, key: str) -> str | None:
    m = re.search(rf"{key}:([\w-]+)", notes or "")
    return m.group(1) if m else None


def status() -> dict:
    """What Gmail connections do we have? Drives the HUD's connection banner."""
    compose_ok = gmail_drafts.is_configured()
    read_ok = gmail_read.is_configured()
    acct = gmail_read.account_email() if read_ok else ""
    if not gmail_drafts.libs_available():
        msg = "Google API libraries not installed."
    elif not compose_ok:
        msg = "Gmail not connected — drafts can't be created yet."
    elif not read_ok:
        msg = ("Read access not granted — sends are tracked, but replies aren't. "
               "Run  python gmail_read.py  once to connect (read-only).")
    else:
        msg = f"Connected{f' as {acct}' if acct else ''} — sends + replies tracked."
    return {"compose_ok": compose_ok, "read_ok": read_ok,
            "account": acct, "message": msg}


def reconcile(db, log=print) -> dict:
    """Flip lead statuses to match Gmail. Returns a summary + the reply list."""
    out = {"sent_detected": 0, "replies_detected": 0, "checked": 0,
           "read_authorized": gmail_read.is_configured(),
           "compose_authorized": gmail_drafts.is_configured(),
           "replies": []}

    website = (db.query(Lead)
                 .filter(Lead.source == "website_autopilot",
                         Lead.notes.isnot(None),
                         Lead.notes.like("%gmail_draft:%"))
                 .all())

    # ── 1) SENT: a draft that vanished from Drafts was sent ──────────────────
    current = gmail_drafts.list_draft_ids() if gmail_drafts.is_configured() else None
    if current is not None:
        for lead in website:
            if lead.status not in ("queued", "approved"):
                continue
            did = _marker(lead.notes, "gmail_draft")
            if did and did not in current:
                lead.status = "sent"
                lead.sent_at = lead.sent_at or _now()
                lead.last_action_at = _now()
                out["sent_detected"] += 1
                log(f"  sent: {lead.company_name}")

    # ── 2) REPLIED: an inbound message from a prospect we emailed ────────────
    if gmail_read.is_configured():
        for lead in website:
            email = (lead.contact_email or "").strip().lower()
            if not email or lead.status in _TERMINAL:
                continue
            if lead.status not in _EMAILED_STATUSES:
                continue
            out["checked"] += 1
            epoch = gmail_read.latest_epoch_ms(f'from:{email} newer_than:120d')
            if not epoch:
                continue
            when = datetime.fromtimestamp(epoch / 1000.0, tz=timezone.utc)
            # Only count it as a reply if it arrived after we emailed them (when
            # we know the send time). Cold prospects don't email us first.
            sent_at = _aware(lead.sent_at)
            if sent_at and when <= sent_at:
                continue
            lead.status = "replied"
            lead.replied_at = when
            lead.sent_at = lead.sent_at or when
            lead.last_action_at = _now()
            out["replies_detected"] += 1
            out["replies"].append({"company": lead.company_name, "email": email,
                                    "when": when.isoformat()})
            log(f"  REPLY: {lead.company_name} <{email}>")

    db.commit()
    return out
