"""
Contact finder — Hunter.io domain search.
Returns the most relevant decision-maker email for a given company domain.
Falls back gracefully if API key not configured or domain not found.
"""
import httpx
from typing import Optional
import config

HUNTER_URL = "https://api.hunter.io/v2/domain-search"

DECISION_MAKER_TITLES = [
    "founder", "co-founder", "ceo", "chief executive",
    "coo", "chief operating", "president",
    "owner", "director of operations", "head of operations",
    "vp of operations", "operations director", "managing director",
    "general manager",
]


def _rank_contact(email_data: dict) -> int:
    title = (email_data.get("position") or "").lower()
    score = 0
    for i, keyword in enumerate(DECISION_MAKER_TITLES):
        if keyword in title:
            score = len(DECISION_MAKER_TITLES) - i
            break
    if email_data.get("confidence", 0) > 80:
        score += 5
    return score


async def find_contact(domain: str) -> Optional[dict]:
    if not config.HUNTER_API_KEY or not domain:
        return None

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                HUNTER_URL,
                params={
                    "domain": domain,
                    "api_key": config.HUNTER_API_KEY,
                    "limit": 20,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            emails = (data.get("data") or {}).get("emails") or []
            if not emails:
                return None

            ranked = sorted(emails, key=_rank_contact, reverse=True)
            best = ranked[0]

            return {
                "contact_name": f"{best.get('first_name', '')} {best.get('last_name', '')}".strip(),
                "contact_title": best.get("position", ""),
                "contact_email": best.get("value", ""),
                "contact_source": "hunter.io",
            }

    except Exception as e:
        print(f"[contact_finder] Error for {domain}: {e}")
        return None
