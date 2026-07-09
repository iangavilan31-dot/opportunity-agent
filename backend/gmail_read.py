"""
Gmail READ access — lets the machine see what actually happened: which drafts
you sent, and who replied.

Why a separate module (and a separate token) from gmail_drafts.py:
  - gmail_drafts.py uses the `gmail.compose` scope — create/update drafts only.
    That scope CANNOT read your inbox, so it can't tell a real reply from
    silence. Reply tracking today is whatever you marked by hand.
  - This module adds `gmail.readonly` (read-only, never sends, never modifies),
    stored in its OWN token (gmail_read_token.json). Your draft creation keeps
    working untouched whether or not you grant read access.

One-time setup (grant read access):
    python gmail_read.py        # opens your browser, asks to allow read-only
                                # -> writes backend/gmail_read_token.json
After that the HUD's "Sync Gmail" button works headlessly.

Everything degrades gracefully: no token / libs / API error -> is_configured()
is False and callers just skip reply detection.
"""
from __future__ import annotations

import os

# Reuse the SAME OAuth client (Desktop app) as gmail_drafts — only the scope and
# the token file differ.
from gmail_drafts import CREDENTIALS_PATH  # noqa: E402

_HERE = os.path.dirname(__file__)
# Overridable for multi-account profiles (see gmail_drafts.TOKEN_PATH).
READ_TOKEN_PATH = (os.getenv("GMAIL_READ_TOKEN_PATH")
                   or os.path.join(_HERE, "gmail_read_token.json"))
READ_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

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
    """True if we can read Gmail headlessly right now (read token exists)."""
    return _LIBS and os.path.exists(READ_TOKEN_PATH)


def _load_creds(interactive: bool = False):
    creds = None
    if os.path.exists(READ_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(READ_TOKEN_PATH, READ_SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(READ_TOKEN_PATH, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            return creds
        except Exception:
            pass
    if interactive:
        if not os.path.exists(CREDENTIALS_PATH):
            raise FileNotFoundError(
                f"Missing {CREDENTIALS_PATH}. Download an OAuth Desktop client from "
                f"Google Cloud (see GMAIL_SETUP.md).")
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, READ_SCOPES)
        creds = flow.run_local_server(port=0)
        with open(READ_TOKEN_PATH, "w", encoding="utf-8") as f:
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


def _list_ids(query: str, max_results: int = 5) -> list[str]:
    svc = _get_service()
    if svc is None:
        return []
    try:
        resp = svc.users().messages().list(
            userId="me", q=query, maxResults=max_results).execute()
        return [m["id"] for m in resp.get("messages", [])]
    except Exception as e:
        print(f"[gmail_read] list failed ({query!r}): {e}")
        return []


def latest_epoch_ms(query: str) -> int | None:
    """Epoch-ms of the most recent message matching a Gmail search query, or None
    if there are no matches. `internalDate` is returned by messages.get on any
    format, so a cheap 'minimal' fetch is enough."""
    svc = _get_service()
    if svc is None:
        return None
    ids = _list_ids(query, max_results=5)
    newest = None
    for mid in ids:
        try:
            msg = svc.users().messages().get(
                userId="me", id=mid, format="minimal").execute()
            ts = int(msg.get("internalDate", 0))
            if newest is None or ts > newest:
                newest = ts
        except Exception:
            continue
    return newest


def has_message(query: str) -> bool:
    """True if at least one message matches the query."""
    return bool(_list_ids(query, max_results=1))


def account_email() -> str:
    """The signed-in address (nice for the HUD to confirm which inbox)."""
    svc = _get_service()
    if svc is None:
        return ""
    try:
        return svc.users().getProfile(userId="me").execute().get("emailAddress", "")
    except Exception:
        return ""


def authorize():
    """Run interactively once to grant READ access (opens a browser)."""
    if not _LIBS:
        print("Google API libraries not installed. Run: pip install -r requirements.txt")
        return
    creds = _load_creds(interactive=True)
    if creds:
        print(f"Read access granted. Token saved to {READ_TOKEN_PATH}. "
              f"The HUD 'Sync Gmail' button can now detect real sends + replies.")


if __name__ == "__main__":
    authorize()
