"""
Contact enrichment — the bridge from "company" to "a real decision-maker's
verified inbox". This is the make-or-break step of the money loop.

Chain:  Apollo (find the PERSON by title)  →  Hunter (domain fallback)
        →  simulation (when no keys, so the loop runs end-to-end)
        →  verification (mandatory before send)
        →  lead-confidence score + sendability flag.

Honest by design: simulated contacts are labelled "simulated" and flagged so you
never mistake them for real, verified people. Add APOLLO_API_KEY (free 10k/mo)
to switch to real discovery; add VERIFIER_API_KEY for real verification.
"""
import re
import hashlib
import httpx
from typing import Optional
import config

# Decision-maker titles in priority order (SMB → the owner usually is the buyer)
DECISION_MAKER_TITLES = [
    "founder", "co-founder", "owner", "ceo", "chief executive", "president",
    "coo", "chief operating", "managing partner", "managing director",
    "operations director", "director of operations", "head of operations",
    "vp of operations", "practice manager", "office manager",
    "operations manager", "general manager", "recruiting lead", "principal",
]

ROLE_ACCOUNTS = {"info", "support", "admin", "hello", "contact", "sales",
                 "team", "office", "help", "billing", "careers", "jobs"}

_FIRST = ["Sarah", "James", "Maria", "David", "Jennifer", "Michael", "Lisa",
          "Robert", "Emily", "Daniel", "Ashley", "Chris", "Jessica", "Matt",
          "Amanda", "Brian", "Nicole", "Kevin", "Rachel", "Eric", "Laura",
          "Steven", "Megan", "Jason", "Stephanie", "Mark", "Karen", "Paul"]
_LAST = ["Patel", "Chen", "Garcia", "Johnson", "Martinez", "Reyes", "Nguyen",
         "Williams", "Brown", "Lee", "Rodriguez", "Davis", "Lopez", "Wilson",
         "Anderson", "Taylor", "Moore", "Kim", "Walker", "Hall", "Torres",
         "Murphy", "Bennett", "Foster", "Sullivan", "Coleman", "Hughes"]

_TITLE_BY_SIZE = {
    "micro": ["Founder", "Owner"],
    "small": ["Owner", "Founder", "Operations Manager"],
    "mid": ["Operations Director", "Director of Operations", "General Manager"],
    "large": ["VP of Operations", "Head of Operations"],
}


def _h(seed: str) -> int:
    return int(hashlib.md5(seed.encode()).hexdigest(), 16)


def _title_rank(title: str) -> int:
    t = (title or "").lower()
    for i, kw in enumerate(DECISION_MAKER_TITLES):
        if kw in t:
            return len(DECISION_MAKER_TITLES) - i
    return 0


def _title_points(title: str) -> int:
    """0-30 based on how senior/buyer-like the title is."""
    t = (title or "").lower()
    if any(k in t for k in ["founder", "owner", "ceo", "president", "principal"]):
        return 30
    if any(k in t for k in ["coo", "chief operating", "managing", "operations director", "director of operations", "head of operations", "vp of operations"]):
        return 25
    if any(k in t for k in ["practice manager", "office manager", "operations manager", "general manager", "recruiting lead"]):
        return 18
    return 6


# ── Discovery providers ──────────────────────────────────────────────────────

async def _apollo_find(domain: str, company: str) -> Optional[dict]:
    if not config.APOLLO_API_KEY or not domain:
        return None
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.apollo.io/v1/mixed_people/search",
                headers={"Content-Type": "application/json",
                         "Cache-Control": "no-cache",
                         "X-Api-Key": config.APOLLO_API_KEY},
                json={
                    "q_organization_domains": domain,
                    "person_titles": ["founder", "owner", "ceo", "coo",
                                       "operations manager", "office manager",
                                       "practice manager", "director of operations"],
                    "page": 1, "per_page": 10,
                },
            )
            resp.raise_for_status()
            people = resp.json().get("people", []) or []
            if not people:
                return None
            best = max(people, key=lambda p: _title_rank(p.get("title", "")))
            return {
                "contact_name": (best.get("name")
                                 or f"{best.get('first_name','')} {best.get('last_name','')}").strip(),
                "contact_title": best.get("title", ""),
                "contact_email": best.get("email", "") or "",
                "contact_source": "apollo",
                "provider_confidence": 90 if best.get("email") else 55,
            }
    except Exception as e:
        print(f"[enrich] Apollo error {domain}: {e}")
        return None


async def _hunter_find(domain: str) -> Optional[dict]:
    if not config.HUNTER_API_KEY or not domain:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.hunter.io/v2/domain-search",
                params={"domain": domain, "api_key": config.HUNTER_API_KEY, "limit": 20},
            )
            resp.raise_for_status()
            emails = (resp.json().get("data") or {}).get("emails") or []
            if not emails:
                return None
            best = max(emails, key=lambda e: _title_rank(e.get("position", "")) * 10 + (e.get("confidence", 0)))
            return {
                "contact_name": f"{best.get('first_name','')} {best.get('last_name','')}".strip(),
                "contact_title": best.get("position", ""),
                "contact_email": best.get("value", ""),
                "contact_source": "hunter",
                "provider_confidence": best.get("confidence", 50),
            }
    except Exception as e:
        print(f"[enrich] Hunter error {domain}: {e}")
        return None


def _simulate_find(domain: str, company: str, company_size: str, decision_maker_profile: str) -> Optional[dict]:
    """Plausible decision-maker so the loop runs end-to-end with no keys.
    Deterministic per company. Clearly labelled 'simulated'."""
    if not domain:
        return None
    seed = _h(company or domain)
    first = _FIRST[seed % len(_FIRST)]
    last = _LAST[(seed // 7) % len(_LAST)]

    size_key = "small"
    for k in ("micro", "small", "mid", "large"):
        if company_size and k in company_size:
            size_key = k
            break
    # Use a clean single title from the size pool. The niche decision_maker_profile
    # is a description ("founder or owner") — too messy for a real title line.
    titles = _TITLE_BY_SIZE.get(size_key, ["Owner"])
    title = titles[seed % len(titles)]

    # SMB founders commonly use first@domain; bigger orgs first.last@domain
    if size_key in ("micro", "small"):
        local = first.lower()
    else:
        local = f"{first.lower()}.{last.lower()}"
    email = f"{local}@{domain}"

    return {
        "contact_name": f"{first} {last}",
        "contact_title": title,
        "contact_email": email,
        "contact_source": "simulated",
        "provider_confidence": 70 + (seed % 12),  # 70-81
    }


# ── Verification ─────────────────────────────────────────────────────────────

async def _verify(email: str, source: str) -> dict:
    """Return {status, score} — status in valid|risky|invalid|unknown."""
    if not email or "@" not in email:
        return {"status": "invalid", "score": 0}

    local, _, domain = email.partition("@")
    if local.lower() in ROLE_ACCOUNTS:
        # Deliverable but not a person — treat as risky for personalized outreach
        return {"status": "risky", "score": 40}

    # Real verifier (MillionVerifier-style) when configured
    if config.VERIFIER_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://api.millionverifier.com/api/v3/",
                    params={"api": config.VERIFIER_API_KEY, "email": email},
                )
                resp.raise_for_status()
                r = resp.json()
                result = (r.get("result") or "").lower()  # ok|catch_all|unknown|invalid
                mapping = {"ok": ("valid", 95), "catch_all": ("risky", 60),
                           "unknown": ("unknown", 50), "invalid": ("invalid", 0)}
                status, score = mapping.get(result, ("unknown", 50))
                return {"status": status, "score": score}
        except Exception as e:
            print(f"[enrich] Verifier error {email}: {e}")

    # Heuristic fallback: syntax + simulated confidence (no real SMTP check)
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return {"status": "invalid", "score": 0}
    if source == "simulated":
        # Honest: we generated it, so it's a plausible pattern, not verified.
        return {"status": "unverified", "score": 65}
    return {"status": "unknown", "score": 55}


# ── Orchestration + scoring ──────────────────────────────────────────────────

def _lead_confidence(title: str, provider_conf: int, verify_score: int) -> int:
    title_pts = _title_points(title)                 # 0-30
    source_pts = round((provider_conf or 0) * 0.40)  # 0-40
    verify_pts = round((verify_score or 0) * 0.30)    # 0-30
    return max(0, min(100, title_pts + source_pts + verify_pts))


def _sendability(email: str, verify_status: str, confidence: int) -> str:
    if not email or verify_status == "invalid":
        return "blocked"
    if verify_status == "valid" and confidence >= 70:
        return "ready"
    if verify_status in ("valid", "unverified", "unknown", "risky") and confidence >= 55:
        return "review"
    return "risky"


async def enrich(company_name: str, domain: str, company_size: str = "",
                 decision_maker_profile: str = "") -> Optional[dict]:
    """Full chain → contact dict with confidence + sendability, or None."""
    found = (await _apollo_find(domain, company_name)
             or await _hunter_find(domain)
             or _simulate_find(domain, company_name, company_size, decision_maker_profile))
    if not found:
        return None

    verification = await _verify(found["contact_email"], found["contact_source"])
    confidence = _lead_confidence(found["contact_title"],
                                  found.get("provider_confidence", 50),
                                  verification["score"])
    sendability = _sendability(found["contact_email"], verification["status"], confidence)

    return {
        **found,
        "contact_verified": verification["status"],
        "verification_score": verification["score"],
        "contact_confidence": confidence,
        "sendability": sendability,
    }
