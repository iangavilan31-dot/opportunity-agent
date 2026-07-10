"""
Follow-up scheduler — day 0 / +3 / +10, the single biggest copy-side lift.

Research (2026-07-08 canon): follow-ups roughly double total replies; 3 touches
then stop. Every lead already carries follow_up_1 / follow_up_2 copy — this
module actually schedules it, with the same safety model as everything else:
it only creates Gmail DRAFTS; Ian reviews and sends.

Send-detection is delegated to gmail_sync.reconcile (recipient/Sent-folder
based). Draft IDs are NOT usable for it: the Gmail web UI re-creates a draft
under a new id the moment a human edits it, so "id vanished" just means Ian
touched the draft — the old id-based check was silently marking edited-but-
unsent drafts as sent, which would follow up on people who were never emailed.
Reply-detection runs in reconcile too (read scope); a lead marked "replied"
drops out of the sequence immediately.

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
from settings_store import apply_signature, web_profile

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

    # Reconcile first: TO/Sent-folder-based send + reply detection (draft ids
    # are unstable, see module docstring). Everything below trusts lead.status.
    import gmail_sync
    rec = gmail_sync.reconcile(db, log=log)

    drafts = gmail_drafts.list_drafts_meta()
    if drafts is None:
        return {"skipped": "drafts list unavailable"}
    # Live follow-up drafts per recipient: ours are the only drafts addressed
    # to the prospect with an "re:" subject. Zero left = the follow-up went out.
    live_re: dict[str, int] = {}
    for d in drafts:
        if d["to"] and (d["subject"] or "").lower().startswith("re:"):
            live_re[d["to"]] = live_re.get(d["to"], 0) + 1

    fu1_days = getattr(config, "FOLLOWUP_1_DAYS", 3)
    fu2_days = getattr(config, "FOLLOWUP_2_DAYS", 10)
    fu1_drafted = fu2_drafted = 0

    leads = (db.query(Lead)
               .filter(Lead.source == "website_autopilot",
                       Lead.status.in_(_ACTIVE_STATUSES),
                       Lead.notes.isnot(None),
                       Lead.notes.like("%gmail_draft:%"))
               .all())

    for lead in leads:
        notes = lead.notes or ""
        fu1 = _marker(notes, "fu1_draft")
        fu2 = _marker(notes, "fu2_draft")

        if lead.status != "sent" or not lead.sent_at:
            continue  # email 1 not confirmed out -> no follow-up business here
        days_out = (_now() - _aware(lead.sent_at)).days

        # Promote followup_stage when no follow-up draft remains for this
        # recipient (an edited draft keeps its TO + "re:" subject, so it still
        # counts as pending — only an actual send/delete empties the folder).
        email = (lead.contact_email or "").strip().lower()
        pending_re = live_re.get(email, 0) if email else 0
        if fu1 and pending_re == 0 and (lead.followup_stage or 0) < 1:
            lead.followup_stage = 1
            lead.last_action_at = _now()
        if fu2 and pending_re == 0 and (lead.followup_stage or 0) < 2:
            lead.followup_stage = 2
            lead.last_action_at = _now()

        # ── Draft follow-up 1 (day +3) ────────────────────────────────────────
        if not fu1 and days_out >= fu1_days and lead.contact_email and lead.follow_up_1:
            did = gmail_drafts.create_draft(
                to=lead.contact_email,
                subject=f"Re: {lead.subject_line}",
                body=apply_signature(lead.follow_up_1, web_profile()))
            if did:
                lead.notes = f"{notes} fu1_draft:{did}".strip()
                fu1_drafted += 1
                log(f"  fu1 drafted -> {lead.company_name} ({days_out}d after send)")

        # ── Draft follow-up 2 (day +10, only after FU1 actually went out) ────
        elif (fu1 and not fu2 and (lead.followup_stage or 0) >= 1
              and days_out >= fu2_days and lead.contact_email and lead.follow_up_2):
            did = gmail_drafts.create_draft(
                to=lead.contact_email,
                subject=f"Re: {lead.subject_line}",
                body=apply_signature(lead.follow_up_2, web_profile()))
            if did:
                lead.notes = f"{lead.notes} fu2_draft:{did}".strip()
                fu2_drafted += 1
                log(f"  fu2 drafted -> {lead.company_name} ({days_out}d after send)")

    db.commit()
    return {"sends_detected": rec.get("sent_detected", 0),
            "replies_detected": rec.get("replies_detected", 0),
            "fu1_drafted": fu1_drafted,
            "fu2_drafted": fu2_drafted, "tracked": len(leads)}
