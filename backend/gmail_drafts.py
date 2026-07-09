"""
Gmail drafts — put finished emails straight into your Gmail Drafts folder.

This CREATES DRAFTS ONLY. It never sends. Drafts don't touch spam filters or any
sending quota, so this is completely ban-safe: every morning your best emails are
sitting in Gmail, To/subject/body filled, and all you do is open Gmail and hit Send.

One-time setup (see GMAIL_SETUP.md):
  1. Make a Google Cloud project, enable the Gmail API, create an OAuth client
     (Desktop app), download it to  backend/gmail_credentials.json
  2. Run once to authorize (opens your browser):  python gmail_drafts.py
     -> writes backend/gmail_token.json; after that the 9 AM task runs headless.

Degrades gracefully: if the google libraries aren't installed or you haven't
authorized yet, is_configured() returns False and morning_batch just skips draft
creation (leads still queue with one-click Gmail compose links).
"""
from __future__ import annotations

import base64
import os
import re
from email.mime.text import MIMEText

_HERE = os.path.dirname(__file__)
CREDENTIALS_PATH = os.path.join(_HERE, "gmail_credentials.json")
TOKEN_PATH = os.path.join(_HERE, "gmail_token.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    _LIBS = True
except Exception:
    _LIBS = False


def libs_available() -> bool:
    return _LIBS


def is_configured() -> bool:
    """True if we can create drafts headlessly right now (authorized token exists)."""
    return _LIBS and os.path.exists(TOKEN_PATH)


def _load_creds(interactive: bool = False):
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_PATH, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            return creds
        except Exception:
            pass
    if interactive:
        if not os.path.exists(CREDENTIALS_PATH):
            raise FileNotFoundError(
                f"Missing {CREDENTIALS_PATH}. Download an OAuth Desktop client from "
                f"Google Cloud (see GMAIL_SETUP.md).")
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        return creds
    return None


_service = None


def _get_service():
    global _service
    if _service is not None:
        return _service
    if not _LIBS:
        return None
    creds = _load_creds(interactive=False)
    if not creds:
        return None
    _service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return _service


def create_draft(to: str, subject: str, body: str, from_name: str = "") -> str | None:
    """Create a Gmail draft. Returns the draft id, or None on failure/not-configured."""
    svc = _get_service()
    if svc is None:
        return None
    try:
        # Last mile before Gmail: subjects skip apply_signature, so scrub
        # AI-tell punctuation here for everything that ships.
        from settings_store import humanize
        msg = MIMEText(humanize(body), _charset="utf-8")
        if to:
            msg["To"] = to
        msg["Subject"] = humanize(subject)
        if from_name:
            # Gmail overrides From with the account address; the display name still shows.
            msg["From"] = from_name
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        draft = svc.users().drafts().create(
            userId="me", body={"message": {"raw": raw}}).execute()
        return draft.get("id")
    except Exception as e:
        print(f"[gmail_drafts] create_draft failed for {to}: {e}")
        return None


def update_draft(draft_id: str, to: str, subject: str, body: str) -> bool:
    """Replace an existing draft's message in place (same draft id)."""
    svc = _get_service()
    if svc is None:
        return False
    try:
        from settings_store import humanize
        msg = MIMEText(humanize(body), _charset="utf-8")
        if to:
            msg["To"] = to
        msg["Subject"] = humanize(subject)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        svc.users().drafts().update(
            userId="me", id=draft_id, body={"message": {"raw": raw}}).execute()
        return True
    except Exception as e:
        print(f"[gmail_drafts] update_draft {draft_id} failed: {e}")
        return False


def delete_draft(draft_id: str) -> bool:
    svc = _get_service()
    if svc is None:
        return False
    try:
        svc.users().drafts().delete(userId="me", id=draft_id).execute()
        return True
    except Exception as e:
        print(f"[gmail_drafts] delete_draft {draft_id} failed: {e}")
        return False


def list_draft_ids() -> set[str] | None:
    """All current draft ids in the account (None = not configured / API failure).
    Used to detect sends: a draft that vanished from Drafts was sent (or deleted)."""
    svc = _get_service()
    if svc is None:
        return None
    ids: set[str] = set()
    try:
        token = None
        while True:
            resp = svc.users().drafts().list(
                userId="me", maxResults=500, pageToken=token).execute()
            for d in resp.get("drafts", []):
                ids.add(d.get("id"))
            token = resp.get("nextPageToken")
            if not token:
                return ids
    except Exception as e:
        print(f"[gmail_drafts] list_draft_ids failed: {e}")
        return None


def list_drafts_meta() -> list[dict] | None:
    """[{id, to, subject}] for every current draft (None = not configured/failed).

    Draft IDs are NOT stable: the Gmail web UI silently re-creates a draft
    (new id) the moment a human edits it, so every id we stored goes stale as
    soon as Ian reviews a draft. This is why 17/17 update_draft calls failed
    with 'Message not a draft' on 2026-07-09. The recipient + subject are the
    stable keys for re-linking a lead to its live draft."""
    svc = _get_service()
    if svc is None:
        return None
    out: list[dict] = []
    try:
        token = None
        while True:
            resp = svc.users().drafts().list(
                userId="me", maxResults=500, pageToken=token).execute()
            for d in resp.get("drafts", []):
                try:
                    full = svc.users().drafts().get(
                        userId="me", id=d["id"], format="metadata").execute()
                    headers = (full.get("message", {}) or {}).get(
                        "payload", {}).get("headers", [])
                    hmap = {h["name"].lower(): h.get("value", "") for h in headers}
                    m = re.search(r"[\w.+\-]+@[\w.\-]+", hmap.get("to", ""))
                    out.append({"id": d["id"],
                                "to": m.group(0).lower() if m else "",
                                "subject": hmap.get("subject", "")})
                except Exception:
                    continue
            token = resp.get("nextPageToken")
            if not token:
                return out
    except Exception as e:
        print(f"[gmail_drafts] list_drafts_meta failed: {e}")
        return None


def authorize():
    """Run interactively once to grant access (opens a browser)."""
    if not _LIBS:
        print("Google API libraries not installed. Run: pip install -r requirements.txt")
        return
    creds = _load_creds(interactive=True)
    if creds:
        print(f"Authorized. Token saved to {TOKEN_PATH}. The 9 AM task can now create drafts.")


if __name__ == "__main__":
    authorize()
