"""
Autonomous draft sender — the machine presses Send, like a human would.

THE ACCOUNT LAW (read before enabling):
  This must NEVER run against the main personal Gmail. That address is Ian's
  whole identity (school, Cloudflare, Steam); the draft-only rule exists to
  keep it unburnable. Point this at a SACRIFICIAL ALT or (correct end state)
  a warmed Google Workspace inbox on a bought domain, via the profile env vars:
      GMAIL_TOKEN_PATH=gmail_token_alt.json
      GMAIL_READ_TOKEN_PATH=gmail_read_token_alt.json
      DB_PATH=alt.db
  Consumer-Gmail automation is also judged more harshly by Google than
  Workspace — one more reason the main account stays hands-only.

Why this exists: sending 10 emails in the same minute by hand (2026-07-09's
5:57 PM burst) is a worse bulk fingerprint than a machine sending one every
3-9 minutes inside business hours. Pacing is the point.

Safety by construction — every send must pass ALL gates:
  1. SEND_MODE=live       (default off; 'dry' prints the exact plan, sends nothing)
  2. postal_address set   (CAN-SPAM: no physical address, no commercial email)
  3. lead is APPROVED     (Ian's Queue-UI approval is the quality gate;
                           SEND_INCLUDE_QUEUED=true widens it deliberately)
  4. TO re-verified NOW   (is_trustworthy_email + verify_email at send time —
                           the jonpinhorn/Nunez class dies here, not in a bounce)
  5. live draft matched by RECIPIENT (never by stored id — ids go stale) and
     the draft's TO must equal the lead's verified email
  6. daily cap (SEND_DAILY_CAP, counted from the DB's sent-today)
  7. send window (SEND_WINDOW local hours) + 3-9 min jitter between sends
  8. bounce circuit-breaker: 2+ mailer-daemon messages today -> halt
  9. kill switch: a STOP_SENDING file beside this script halts before each send

Run:  python auto_send.py            # sends until cap/window/candidates end
      python auto_send.py --limit 5  # at most 5 this run
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import time
from datetime import datetime, timezone

import config
import gmail_drafts
import gmail_read
import verify_email
import website_signals
from db import Lead, SessionLocal, init_db
from settings_store import load_settings

STOP_FILE = os.path.join(os.path.dirname(__file__), "STOP_SENDING")


def _within_window() -> bool:
    try:
        lo, hi = (int(x) for x in str(config.SEND_WINDOW).split("-"))
    except Exception:
        lo, hi = 9, 17
    return lo <= datetime.now().hour < hi


def _sent_today(db) -> int:
    today = datetime.now(timezone.utc).date()
    return sum(1 for l in db.query(Lead)
               .filter(Lead.source == "website_autopilot",
                       Lead.sent_at.isnot(None)).all()
               if l.sent_at and l.sent_at.date() == today)


def run(limit: int | None = None) -> dict:
    mode = getattr(config, "SEND_MODE", "off")
    if mode not in ("dry", "live"):
        print("SEND_MODE=off — this tool does nothing until you set SEND_MODE=dry "
              "(print the plan) or SEND_MODE=live (actually send). Read the module "
              "docstring first: NEVER on the main personal Gmail.")
        return {"skipped": "SEND_MODE=off"}

    if not load_settings().get("postal_address", "").strip():
        if mode == "live":
            print("REFUSING: no postal address in Settings. CAN-SPAM requires a "
                  "physical mailing address in every commercial email — set it "
                  "(PO Box is fine), then re-run.")
            return {"skipped": "no postal_address"}
        print("WARNING: postal address unset — live mode will refuse until it's set.")

    if not gmail_drafts.is_configured():
        print("REFUSING: Gmail compose not configured for this profile "
              f"(token: {gmail_drafts.TOKEN_PATH}).")
        return {"skipped": "gmail not configured"}

    print(f"Mode: {mode.upper()} | token: {os.path.basename(gmail_drafts.TOKEN_PATH)} "
          f"| db: {config.DB_PATH} | cap: {config.SEND_DAILY_CAP}/day "
          f"| window: {config.SEND_WINDOW}h | gap: {config.SEND_GAP_MIN}-{config.SEND_GAP_MAX}m")

    # Bounce circuit-breaker (needs the read scope; skipped cleanly without it)
    if gmail_read.is_configured():
        bounces = gmail_read.count_messages("from:mailer-daemon newer_than:1d")
        if bounces >= 2:
            print(f"HALT: {bounces} bounce notices in the last day — the list has a "
                  "quality problem. Fix verification before sending more.")
            return {"halted": "bounces", "bounces": bounces}

    init_db()
    db = SessionLocal()
    sent = skipped = 0
    try:
        statuses = ["approved"] + (["queued"] if config.SEND_INCLUDE_QUEUED else [])
        leads = (db.query(Lead)
                   .filter(Lead.source == "website_autopilot",
                           Lead.status.in_(statuses),
                           Lead.contact_email.isnot(None),
                           Lead.contact_email != "",
                           Lead.notes.like("%gmail_draft:%"))
                   .order_by(Lead.automation_score.desc())
                   .all())
        budget = max(0, config.SEND_DAILY_CAP - _sent_today(db))
        if limit is not None:
            budget = min(budget, limit)
        print(f"{len(leads)} sendable leads ({'+'.join(statuses)}), "
              f"budget {budget} for today.")

        drafts = gmail_drafts.list_drafts_meta() or []
        by_to = {d["to"]: d["id"] for d in drafts if d["to"]}

        for lead in leads:
            if sent >= budget:
                print("Daily budget reached.")
                break
            if os.path.exists(STOP_FILE):
                print(f"HALT: {STOP_FILE} exists — kill switch.")
                break
            if not _within_window():
                print("Outside the send window — stopping.")
                break

            email = (lead.contact_email or "").strip().lower()
            # Gate 4: re-verify the recipient AT SEND TIME.
            if not website_signals.is_trustworthy_email(
                    email, lead.company_domain or "", name_hint=lead.company_name or ""):
                print(f"  skip {lead.company_name}: TO {email!r} no longer trusted")
                skipped += 1
                continue
            v = verify_email.verify(email)
            if not v["ok"]:
                print(f"  skip {lead.company_name}: {email} failed verify ({v['method']})")
                skipped += 1
                continue
            # Gate 5: the live draft, matched by recipient.
            draft_id = by_to.get(email)
            if not draft_id:
                print(f"  skip {lead.company_name}: no live draft addressed to {email}")
                skipped += 1
                continue

            if mode == "dry":
                print(f"  WOULD SEND -> {lead.company_name} <{email}> (draft {draft_id})")
                sent += 1
                continue

            if gmail_drafts.send_draft(draft_id):
                lead.status = "sent"
                lead.sent_at = datetime.now(timezone.utc)
                lead.last_action_at = lead.sent_at
                db.commit()
                by_to.pop(email, None)
                sent += 1
                print(f"  SENT -> {lead.company_name} <{email}>")
                gap = random.uniform(config.SEND_GAP_MIN, config.SEND_GAP_MAX) * 60
                print(f"  (waiting {gap/60:.1f} min)")
                time.sleep(gap)
            else:
                skipped += 1
    finally:
        db.close()
    out = {"mode": mode, "sent": sent, "skipped": skipped}
    print(out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="max sends this run (within the daily cap)")
    sys.exit(0 if run(limit=ap.parse_args().limit) is not None else 1)
