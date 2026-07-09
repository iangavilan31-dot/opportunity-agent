"""
Free pre-draft email verification.

Bounces (not volume) are what get small Gmail senders flagged — complaint/bounce
RATE on a tiny denominator is the real account risk at 10-20 sends/day. This
kills the obvious hard bounces before a draft is ever created:

  1. syntax check (free, instant)
  2. domain MX lookup via dnspython (free, cached per domain)
  3. optional MillionVerifier API when VERIFIER_API_KEY is set (their free
     credits; graceful fallback to the MX verdict on any error)

Home-box SMTP probing is deliberately NOT attempted: residential ISPs block
outbound port 25, so it can't work from this machine (verified 2026-07-08).
"""
from __future__ import annotations

import re

import httpx

import config

_SYNTAX = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_mx_cache: dict[str, bool] = {}

# MillionVerifier can silently run dry (returns result:'error', credits:0) and
# then verification quietly degrades to MX-only — which proves the DOMAIN takes
# mail, NOT that the mailbox exists (this is how info@nunezheatingandcooling.com
# bounced). Surface it LOUDLY the first time so Ian knows real mailbox
# verification is off and can decide to top up.
_credit_warning_shown = False
verifier_out_of_credits = False


def verifier_status() -> dict:
    """Cheap probe of the MillionVerifier key so callers/UI can tell Ian whether
    real mailbox verification is live or we're on MX-only. Never raises."""
    key = getattr(config, "VERIFIER_API_KEY", "")
    if not key:
        return {"configured": False, "ok": False, "credits": None,
                "message": "No VERIFIER_API_KEY set — MX-only (domain accepts mail, mailbox unverified)."}
    try:
        with httpx.Client(timeout=15) as c:
            r = c.get("https://api.millionverifier.com/api/v3/credits.json",
                      params={"api": key})
        data = r.json()
        credits = data.get("credits")
        if isinstance(credits, (int, float)) and credits <= 0:
            return {"configured": True, "ok": False, "credits": credits,
                    "message": "MillionVerifier is OUT OF CREDITS — on MX-only. Top up or accept domain-match."}
        return {"configured": True, "ok": True, "credits": credits,
                "message": f"MillionVerifier live ({credits} credits)."}
    except Exception as e:
        return {"configured": True, "ok": False, "credits": None,
                "message": f"MillionVerifier unreachable ({type(e).__name__}) — on MX-only."}

try:
    import dns.resolver
    _DNS = True
except Exception:
    _DNS = False


def _has_mx(domain: str) -> bool | None:
    """True/False = definitive; None = couldn't check (offline etc.)."""
    domain = domain.lower()
    if domain in _mx_cache:
        return _mx_cache[domain]
    if not _DNS:
        return None
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = resolver.lifetime = 5.0
        try:
            answers = resolver.resolve(domain, "MX")
            ok = len(answers) > 0
        except (dns.resolver.NoAnswer,):
            # No MX record — an A record can still receive mail (rare but legal).
            try:
                resolver.resolve(domain, "A")
                ok = True
            except Exception:
                ok = False
        except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
            ok = False
        _mx_cache[domain] = ok
        return ok
    except Exception:
        return None  # resolver problem / offline — don't block the batch


def _millionverifier(email: str) -> str | None:
    """Returns 'valid'|'risky'|'invalid' or None when unavailable."""
    key = getattr(config, "VERIFIER_API_KEY", "")
    if not key:
        return None
    try:
        with httpx.Client(timeout=15) as c:
            r = c.get("https://api.millionverifier.com/api/v3/",
                      params={"api": key, "email": email, "timeout": 10})
        data = r.json()
        result = (data.get("result") or "").lower()
        if result == "ok":
            return "valid"
        if result in ("invalid", "disposable"):
            return "invalid"
        if result in ("catch_all", "unknown"):
            return "risky"
        # Anything else = the API refused (out of credits / error). Warn ONCE.
        global _credit_warning_shown, verifier_out_of_credits
        credits = data.get("credits")
        if result == "error" or credits == 0:
            verifier_out_of_credits = True
            if not _credit_warning_shown:
                _credit_warning_shown = True
                print("[verify_email] !! MillionVerifier unavailable "
                      f"(result={result!r}, credits={credits}, error={data.get('error')!r}). "
                      "Verification is now MX-ONLY: it confirms the domain accepts mail, "
                      "NOT that the mailbox exists. Top up at millionverifier.com or accept "
                      "domain-match. (This is the class of bug behind the recent bounces.)")
    except Exception:
        pass
    return None


def verify(email: str) -> dict:
    """Returns {ok, level, method}. ok=False means: do NOT draft to this address."""
    email = (email or "").strip().lower()
    if not email or not _SYNTAX.match(email):
        return {"ok": False, "level": "invalid", "method": "syntax"}

    domain = email.split("@", 1)[1]
    mx = _has_mx(domain)
    if mx is False:
        return {"ok": False, "level": "invalid", "method": "mx"}

    api = _millionverifier(email)
    if api == "invalid":
        return {"ok": False, "level": "invalid", "method": "api"}
    if api == "valid":
        return {"ok": True, "level": "valid", "method": "api"}
    if api == "risky":
        return {"ok": True, "level": "risky", "method": "api"}

    # MX ok (or unknowable) and no API verdict: good enough at this volume.
    level = "risky" if mx is None else "valid"
    return {"ok": True, "level": level, "method": "mx"}
