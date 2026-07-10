"""
One-shot: rewrite every machine-made draft currently in Gmail with
(1) a greeting if it's missing and (2) the multipart plain+HTML format so
recipients see flowing paragraphs instead of ~75-char hard-wrapped lines
(Ian, 2026-07-10 — issues 2 and 4 from the recipient-side screenshots).

Matches drafts to leads BY RECIPIENT ADDRESS, never by stored draft id
(Gmail re-creates edited drafts under a new id — see list_drafts_meta).
Drafts whose recipient isn't a lead in the DB are left untouched, so
personal drafts are safe by construction. Never sends anything.

Usage:  python fix_drafts_greeting_wrap.py [--dry]
"""
from __future__ import annotations

import base64
import sqlite3
import sys

import gmail_drafts
from email_templates import greeting_name

_HERE_DB = "opportunity_agent.db"


def _draft_plain_body(svc, draft_id: str) -> str | None:
    """Current text of a draft (handles both single-part and multipart)."""
    try:
        full = svc.users().drafts().get(
            userId="me", id=draft_id, format="full").execute()
        payload = (full.get("message", {}) or {}).get("payload", {})
        data = (payload.get("body") or {}).get("data")
        if not data:
            for p in payload.get("parts", []) or []:
                if p.get("mimeType") == "text/plain":
                    data = (p.get("body") or {}).get("data")
                    break
        if not data:
            return None
        return base64.urlsafe_b64decode(data.encode()).decode(
            "utf-8", "replace").replace("\r\n", "\n")
    except Exception as e:
        print(f"  ! could not read draft {draft_id}: {e}")
        return None


def _greeting_for(contact_name: str, company_name: str) -> str:
    # Same rule as web_offer/email_templates: real name wins; otherwise greet
    # the business by name ("Hi there" stays banned as a mass-send tell).
    if contact_name and contact_name.strip():
        return f"Hi {contact_name.strip().split()[0]},"
    return f"Hi {greeting_name(company_name)} team,"


def main() -> None:
    dry = "--dry" in sys.argv
    svc = gmail_drafts._get_service()
    if svc is None:
        print("Gmail not configured — aborting.")
        return

    drafts = gmail_drafts.list_drafts_meta()
    if drafts is None:
        print("Could not list drafts — aborting.")
        return
    print(f"{len(drafts)} draft(s) in Gmail. {'DRY RUN' if dry else 'LIVE'}\n")

    db = sqlite3.connect(_HERE_DB)
    leads = {}
    for email, name, company in db.execute(
            "SELECT contact_email, contact_name, company_name FROM leads "
            "WHERE contact_email IS NOT NULL AND contact_email != ''"):
        leads[email.strip().lower()] = (name or "", company or "")
    db.close()

    fixed = greeted = skipped = failed = 0
    for d in drafts:
        to, subject, did = d["to"], d["subject"], d["id"]
        if not to or to not in leads:
            skipped += 1
            print(f"- SKIP (not a lead): to={to or '(no recipient)'!r} subj={subject!r}")
            continue
        body = _draft_plain_body(svc, did)
        if not body or not body.strip():
            failed += 1
            print(f"- FAIL (empty/unreadable body): {to}")
            continue

        name, company = leads[to]
        new_body = body
        added_greeting = False
        first_line = body.lstrip().split("\n", 1)[0].lower()
        if not (first_line.startswith("hi ") or first_line.startswith("hey")
                or first_line.startswith("hello")):
            new_body = _greeting_for(name, company) + "\n\n" + body.lstrip("\n")
            added_greeting = True

        tag = "greeting + flow" if added_greeting else "flow only (already greets)"
        print(f"- {to}  [{tag}]")
        print(f"    opens: {new_body.lstrip().splitlines()[0][:78]!r}")
        if dry:
            fixed += 1
            greeted += int(added_greeting)
            continue
        if gmail_drafts.update_draft(did, to, subject, new_body):
            fixed += 1
            greeted += int(added_greeting)
        else:
            failed += 1

    print(f"\nDone: {fixed} rewritten ({greeted} got a greeting), "
          f"{skipped} skipped (not leads), {failed} failed.")


if __name__ == "__main__":
    main()
