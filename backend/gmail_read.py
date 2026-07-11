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

import base64
import os
import re

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


# ── Auto-reply / vacation-responder detection ────────────────────────────────
# A message FROM a prospect is not necessarily a human reply: out-of-office and
# vacation responders (Gmail's own included) fire automatically the instant a
# cold email lands. Counting one as a reply is doubly wrong — it lies on the HUD
# AND stops the follow-up cadence to a lead who never actually engaged (and ~80%
# of cold replies come from follow-ups). RFC 3834 auto-responders set
# `Auto-Submitted: auto-replied`; Gmail's vacation responder does exactly that
# and prefixes the subject "Auto Response:" / "Automatic reply:".
_REPLY_HEADERS = ["Auto-Submitted", "X-Autoreply", "X-Autorespond",
                  "Precedence", "Subject"]
_AUTO_SUBJECT_RE = re.compile(
    r"(auto[\s-]?response|automatic reply|auto[\s-]?reply|out[\s-]?of[\s-]?office"
    r"|on vacation|currently (closed|away|unavailable)|away from (the )?office"
    r"|delivery status notification|undeliverable|mail delivery (failed|subsystem))",
    re.I)


def _is_auto_message(headers: dict[str, str]) -> bool:
    """True if a message looks machine-generated (auto-reply / OOO / bounce),
    so reply-detection can ignore it. Conservative: only flags on definitive
    signals, so a genuine human reply is never mistaken for an auto-reply."""
    auto = (headers.get("auto-submitted", "") or "").strip().lower()
    if auto and auto != "no":            # RFC 3834: auto-replied / auto-generated
        return True
    if headers.get("x-autoreply") or headers.get("x-autorespond"):
        return True
    if (headers.get("precedence", "") or "").strip().lower() == "auto_reply":
        return True
    if _AUTO_SUBJECT_RE.search(headers.get("subject", "") or ""):
        return True
    return False


def latest_human_reply_epoch_ms(email: str) -> int | None:
    """Epoch-ms of the most recent *human* message from `email` in the last 120
    days, skipping auto-responders / vacation notices / bounces. None if the only
    inbound mail from them is automated (or there is none). This is what reply
    detection must use — `latest_epoch_ms` counts auto-replies as replies."""
    svc = _get_service()
    if svc is None:
        return None
    ids = _list_ids(f"from:{email} newer_than:120d", max_results=10)
    newest = None
    for mid in ids:
        try:
            msg = svc.users().messages().get(
                userId="me", id=mid, format="metadata",
                metadataHeaders=_REPLY_HEADERS).execute()
        except Exception:
            continue
        hdrs = {h["name"].lower(): h.get("value", "")
                for h in msg.get("payload", {}).get("headers", [])}
        if _is_auto_message(hdrs):
            continue
        ts = int(msg.get("internalDate", 0))
        if newest is None or ts > newest:
            newest = ts
    return newest


def count_messages(query: str, cap: int = 10) -> int:
    """How many messages match a query, up to `cap` (cheap ids-only list).
    Used by auto_send's bounce circuit-breaker."""
    return len(_list_ids(query, max_results=cap))


def has_message(query: str) -> bool:
    """True if at least one message matches the query."""
    return bool(_list_ids(query, max_results=1))


# ── Bounce (delivery-failure) detection ──────────────────────────────────────
# A hard bounce is the single fastest way to get a Gmail account flagged, and a
# dead address keeps costing sends every time a follow-up fires at it. This reads
# the delivery-failure notices (DSNs) sitting in the inbox and pulls out which
# address failed and whether it's permanent — so the machine can blacklist it.
_RE_FINAL = re.compile(r"Final-Recipient:\s*rfc822;\s*<?([^>\s]+@[^>\s]+?)>?\s*$",
                       re.I | re.M)
_RE_FAILEDHDR = re.compile(r"X-Failed-Recipients:\s*<?([^>\s,]+@[^>\s,]+?)>?", re.I)
_RE_STATUS = re.compile(r"Status:\s*([245]\.\d+\.\d+)", re.I | re.M)
_HARD_PHRASES = (
    "does not exist", "user unknown", "no such user", "no such address",
    "couldn't be found", "could not be found", "address not found",
    "recipient not found", "mailbox unavailable", "mailbox not found",
    "no mailbox", "account that you tried to reach", "unrouteable address",
    "550 5.1.1", "550 5.1.0", "550 5.4.1")


def _decode_part(part) -> str:
    data = (part.get("body") or {}).get("data")
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode(
            "utf-8", "replace")
    except Exception:
        return ""


def _collect_dsn_text(payload) -> str:
    """Recursively gather the machine-readable delivery-status + human text/plain
    parts of a bounce message (skips the attached original message to avoid
    picking up our own From: address)."""
    parts_out = []
    mime = (payload.get("mimeType") or "").lower()
    if "delivery-status" in mime or mime == "text/plain":
        parts_out.append(_decode_part(payload))
    for p in payload.get("parts", []) or []:
        parts_out.append(_collect_dsn_text(p))
    return "\n".join(t for t in parts_out if t)


def list_bounces(newer_than_days: int = 30, cap: int = 40) -> list[dict]:
    """Parse delivery-failure notices into [{email, code, permanent, when}].
    `permanent` marks a hard bounce (5.x.x / 'address not found'); soft/temporary
    4.x failures are reported but flagged permanent=False so they aren't blocked.
    Read-only. Returns [] cleanly if read access isn't granted."""
    svc = _get_service()
    if svc is None:
        return []
    me = (account_email() or "").strip().lower()
    q1 = f"from:mailer-daemon newer_than:{newer_than_days}d"
    q2 = ('subject:("Delivery Status Notification" OR "Undelivered" OR '
          '"not delivered" OR "Mail delivery failed" OR "Address not found" OR '
          f'"returned mail" OR "failure notice") newer_than:{newer_than_days}d')
    ids, seen = [], set()
    for q in (q1, q2):
        for mid in _list_ids(q, max_results=cap):
            if mid not in seen:
                seen.add(mid)
                ids.append(mid)
    out = []
    for mid in ids[:cap]:
        try:
            msg = svc.users().messages().get(
                userId="me", id=mid, format="full").execute()
        except Exception:
            continue
        payload = msg.get("payload", {})
        text = _collect_dsn_text(payload)
        for h in payload.get("headers", []):
            if h.get("name", "").lower() == "x-failed-recipients":
                text += "\nX-Failed-Recipients: " + h.get("value", "")
        recips = _RE_FINAL.findall(text) or _RE_FAILEDHDR.findall(text)
        m = _RE_STATUS.search(text)
        status = m.group(1) if m else None
        low = text.lower()
        hard = bool((status and status.startswith("5"))
                    or any(p in low for p in _HARD_PHRASES))
        soft = bool(status and status.startswith("4")) or "temporar" in low \
            or "try again" in low
        when = int(msg.get("internalDate", 0))
        for r in dict.fromkeys(x.strip().lower() for x in recips):
            if "@" not in r or r == me:
                continue
            out.append({"email": r, "code": status or ("hard" if hard else "?"),
                        "permanent": hard and not soft, "when": when})
    return out


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
