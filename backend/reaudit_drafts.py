"""
Re-audit unsent website-track drafts against the CURRENT analyzer and repair
their Gmail drafts in place.

Why this exists: a transient HTTPS fetch failure once put a false "Not Secure"
line into a real draft (2026-07-08). After any analyzer fix, run this to
re-verify every claim in every unsent draft:

  - findings changed but still pitch-worthy  -> regenerate copy, UPDATE the
    Gmail draft in place (same draft id) + refresh the DB lead
  - site now scores below the pitch threshold -> DELETE the Gmail draft and
    mark the lead rejected ("site fine on recheck")

Only touches leads still in queued/approved (i.e. drafts Ian hasn't sent).

Run:  python reaudit_drafts.py
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import config
import gmail_drafts
import web_offer
import website_signals
from db import Lead, SessionLocal, init_db
from settings_store import apply_signature, load_settings, web_profile


def run() -> dict:
    init_db()
    db = SessionLocal()
    settings = web_profile(load_settings())
    min_opp = getattr(config, "AUTOPILOT_MIN_OPPORTUNITY", 45)
    updated = rejected = unchanged = errors = 0
    try:
        leads = (db.query(Lead)
                   .filter(Lead.source == "website_autopilot",
                           Lead.status.in_(("queued", "approved")),
                           Lead.company_domain.isnot(None),
                           Lead.company_domain != "")
                   .all())
        print(f"Re-auditing {len(leads)} unsent website drafts...")
        for lead in leads:
            try:
                signals = website_signals.analyze(lead.company_domain)
                # Re-apply the trust-gap check using the Maps data captured at
                # sourcing time (stored in the old score_breakdown).
                try:
                    maps = (json.loads(lead.score_breakdown or "{}")).get("maps") or {}
                    website_signals.apply_trust_gap(
                        signals, maps.get("rating"), maps.get("review_count"))
                    if maps:
                        signals["maps"] = maps
                except Exception:
                    pass
            except Exception as e:
                print(f"  ! {lead.company_name}: analyze failed ({e}) — leaving as-is")
                errors += 1
                continue
            m = re.search(r"gmail_draft:([\w-]+)", lead.notes or "")
            draft_id = m.group(1) if m else None
            opportunity = int(signals.get("opportunity_score", 0))

            if opportunity < min_opp:
                # Site is actually fine — never should have been pitched.
                if draft_id:
                    gmail_drafts.delete_draft(draft_id)
                lead.status = "rejected"
                lead.score_reasoning = "site fine on recheck (re-audit)"
                lead.updated_at = datetime.now(timezone.utc)
                rejected += 1
                print(f"  - {lead.company_name}: opp {opportunity} < {min_opp} -> draft deleted, lead rejected")
                continue

            old_issues = lead.score_reasoning or ""
            # job_title stores the display NOUN ("Website — dental practice") —
            # reverse-map it to the category KEY the copy engine expects.
            noun = (lead.job_title or "").replace("Website — ", "").strip()
            category = next(
                (k for k, (n, _) in web_offer._CATEGORY.items() if n == noun),
                "generic")
            contact = (lead.contact_name or "").strip()
            if not contact:
                try:
                    import owner_name
                    contact = owner_name.find(lead.company_name,
                                              lead.company_domain) or ""
                    if contact:
                        lead.contact_name = contact
                except Exception:
                    contact = ""
            suite = web_offer.generate_website_suite(
                company_name=lead.company_name, city=lead.job_location or "",
                category=category, contact_name=contact, signals=signals)
            issues = signals.get("headline_issues", [])
            changed = "; ".join(issues) != old_issues

            lead.automation_score = opportunity
            lead.score_breakdown = json.dumps(signals)
            lead.pain_points = json.dumps([f["msg"] for f in signals.get("findings", [])])
            lead.score_reasoning = "; ".join(issues)
            lead.subject_line = suite["subject_line"]
            lead.email_body = suite["email_body"]
            lead.email_long = suite["email_long"]
            lead.mini_audit = suite["mini_audit"]
            lead.follow_up_1 = suite["follow_up_1"]
            lead.follow_up_2 = suite["follow_up_2"]
            lead.breakup_email = suite["breakup_email"]
            lead.objection_responses = json.dumps(suite["objection_responses"])
            lead.updated_at = datetime.now(timezone.utc)

            if draft_id and lead.contact_email:
                ok = gmail_drafts.update_draft(
                    draft_id, to=lead.contact_email, subject=suite["subject_line"],
                    body=apply_signature(suite["email_body"], settings))
                tag = "draft UPDATED" if ok else "draft update FAILED"
            else:
                tag = "no draft"
            if changed:
                updated += 1
                print(f"  * {lead.company_name}: claims changed -> {issues[0] if issues else '(none)'} | {tag}")
            else:
                unchanged += 1
                print(f"  = {lead.company_name}: claims re-verified unchanged | {tag}")
        db.commit()
    finally:
        db.close()
    summary = {"updated": updated, "unchanged": unchanged,
               "rejected": rejected, "errors": errors}
    print(summary)
    return summary


if __name__ == "__main__":
    run()
