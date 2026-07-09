"""
Follow-up scheduler — day 0 / +3 / +10, the single biggest copy-side lift.

Research (2026-07-08 canon): follow-ups roughly double total replies; 3 touches
then stop. Every lead already carries follow_up_1 / follow_up_2 copy — this
module actually schedules it, with the same safety model as everything else:
it only creates Gmail DRAFTS; Ian reviews and sends.

How send-detection works with the compose-only OAuth scope (no re-auth needed):
a draft that disappeared from the Drafts folder was sent (or deliberately
deleted — either way, we move on). Reply-detection isn't possible with this
scope, so a prospect who replied could still get a follow-up draft — Ian is
the reply-handler and simply discards it. Marking a lead "replied" in the app
stops its sequence immediately.

Notes-field markers (append-only, survives everything):
    gmail_draft:<id>   initial email draft        (written by morning_batch)
    fu1_draft:<id>     follow-up 1 draft
    fu2_draft:<id>     follow-up 2 draft
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import config
import gmail_drafts
from db import Lead
from settings_store import apply_signature

_ACTIVE_STATUSES = ("queued", "approved", "sent")


def _marker(notes: str, key: str) -> str | None:
    m = re.search(rf"{key}:([\w-]+)", notes or "")
    return m.group(1) if m else None


def _now():
    return datetime.now(timezone.utc)


def _aware(dt):
    """SQLite round-trips datetimes naive; our writes are always UTC."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def process(db, log=print) -> dict:
    """Detect sends and draft due follow-ups. Returns a small summary dict."""
    if not getattr(config, "FOLLOWUP_ENABLED", True):
        return {"skipped": "disabled"}
    if not gmail_drafts.is_configured():
        return {"skipped": "gmail not configured"}

    current = gmail_drafts.list_draft_ids()
    if current is None:
        return {"skipped": "drafts list unavailable"}

    fu1_days = getattr(config, "FOLLOWUP_1_DAYS", 3)
    fu2_days = getattr(config, "FOLLOWUP_2_DAYS", 10)
    detected_sent = fu1_drafted = fu2_drafted = 0

    leads = (db.query(Lead)
               .filter(Lead.source == "website_autopilot",
                       Lead.status.in_(_ACTIVE_STATUSES),
                       Lead.notes.isnot(None),
                       Lead.notes.like("%gmail_draft:%"))
               .all())

    for lead in leads:
        notes = lead.notes or ""
        initial = _marker(notes, "gmail_draft")
        fu1 = _marker(notes, "fu1_draft")
        fu2 = _marker(notes, "fu2_draft")

        # ── Send detection: draft gone from Drafts = it went out ─────────────
        if lead.status in ("queued", "approved"):
            if initial and initial not in current:
                lead.status = "sent"
                lead.sent_at = lead.sent_at or _now()
                lead.last_action_at = _now()
                detected_sent += 1
            else:
                continue  # email 1 not sent yet — no follow-up business here

        if lead.status != "sent" or not lead.sent_at:
            continue
        days_out = (_now() - _aware(lead.sent_at)).days

        # Promote followup_stage when a follow-up draft has left the folder.
        if fu1 and fu1 not in current and (lead.followup_stage or 0) < 1:
            lead.followup_stage = 1
            lead.last_action_at = _now()
        if fu2 and fu2 not in current and (lead.followup_stage or 0) < 2:
            lead.followup_stage = 2
            lead.last_action_at = _now()

        # ── Draft follow-up 1 (day +3) ────────────────────────────────────────
        if not fu1 and days_out >= fu1_days and lead.contact_email and lead.follow_up_1:
            did = gmail_drafts.create_draft(
                to=lead.contact_email,
                subject=f"re: {lead.subject_line}",
                body=apply_signature(lead.follow_up_1))
            if did:
                lead.notes = f"{notes} fu1_draft:{did}".strip()
                fu1_drafted += 1
                log(f"  fu1 drafted -> {lead.company_name} ({days_out}d after send)")

        # ── Draft follow-up 2 (day +10, only after FU1 actually went out) ────
        elif (fu1 and not fu2 and (lead.followup_stage or 0) >= 1
              and days_out >= fu2_days and lead.contact_email and lead.follow_up_2):
            did = gmail_drafts.create_draft(
                to=lead.contact_email,
                subject=f"re: {lead.subject_line}",
                body=apply_signature(lead.follow_up_2))
            if did:
                lead.notes = f"{lead.notes} fu2_draft:{did}".strip()
                fu2_drafted += 1
                log(f"  fu2 drafted -> {lead.company_name} ({days_out}d after send)")

    db.commit()
    return {"sends_detected": detected_sent, "fu1_drafted": fu1_drafted,
            "fu2_drafted": fu2_drafted, "tracked": len(leads)}
