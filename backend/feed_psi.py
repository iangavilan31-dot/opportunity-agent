"""
feed_psi — batch PageSpeed (mobile) over the lead DB. Research report §13 L1.

The burning_ads finding is `ad_active AND psi_mobile < 40`: this feed supplies
the second half. Free Google API; PAGESPEED_API_KEY (already a config option)
raises the quota to 25k/day, but the feed runs keyless at a polite pace too.

Honest by construction: psi_mobile is only ever a real Lighthouse score from
Google's API — a failed lookup stays NULL (never guessed). Re-runs skip leads
checked in the last REFRESH_DAYS.

Usage: python feed_psi.py [--limit N] [--force]
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

import httpx

_HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(_HERE)
sys.path.insert(0, _HERE)
import config

DB = os.path.join(_HERE, "opportunity_agent.db")
API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
KEY = getattr(config, "PAGESPEED_API_KEY", "") or os.getenv("PAGESPEED_API_KEY", "")
REFRESH_DAYS = 30


def _domain_of(lead_row) -> str | None:
    """A real, reachable site per the analyzer's own verdict — social pages
    and dead domains are the other machines' inventory, not PSI targets."""
    sb_raw = lead_row["score_breakdown"]
    try:
        sb = json.loads(sb_raw or "{}")
    except Exception:
        return None
    domain = (sb.get("domain") or "").strip()
    if not domain or sb.get("social_only") or not sb.get("reachable", False):
        return None
    return domain


def psi_mobile_score(url: str, client: httpx.Client) -> int | None:
    params = {"url": url, "strategy": "mobile", "category": "performance"}
    if KEY:
        params["key"] = KEY
    try:
        r = client.get(API, params=params, timeout=90)
        if r.status_code == 429:
            print("  quota pressure (429) — backing off 30s")
            time.sleep(30)
            r = client.get(API, params=params, timeout=90)
        r.raise_for_status()
        score = r.json()["lighthouseResult"]["categories"]["performance"]["score"]
        return round(score * 100)
    except Exception as e:
        print(f"  psi failed for {url}: {str(e)[:90]}")
        return None


def main() -> None:
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    force = "--force" in sys.argv

    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        "SELECT id, company_name, score_breakdown, psi_mobile, psi_checked_at "
        "FROM leads WHERE source='website_autopilot'").fetchall()

    todo = []
    for r in rows:
        if not force and r["psi_checked_at"]:
            age = (datetime.now(timezone.utc)
                   - datetime.fromisoformat(r["psi_checked_at"]))
            if age.days < REFRESH_DAYS:
                continue
        domain = _domain_of(r)
        if domain:
            todo.append((r["id"], r["company_name"], domain))
    if limit:
        todo = todo[:limit]
    print(f"{len(todo)} lead(s) to check (key={'yes' if KEY else 'no — polite pace'})")

    checked = scored = 0
    with httpx.Client(follow_redirects=True) as client:
        for lid, name, domain in todo:
            url = domain if domain.startswith("http") else f"https://{domain}"
            score = psi_mobile_score(url, client)
            checked += 1
            now = datetime.now(timezone.utc).isoformat()
            if score is not None:
                scored += 1
                db.execute("UPDATE leads SET psi_mobile=?, psi_checked_at=? WHERE id=?",
                           (score, now, lid))
                flag = " <— SLOW" if score < 40 else ""
                print(f"  [{checked}/{len(todo)}] {name[:40]}: {score}{flag}")
            else:
                db.execute("UPDATE leads SET psi_checked_at=? WHERE id=?", (now, lid))
            db.commit()
            if not KEY:
                time.sleep(2.5)  # keyless quota is soft; stay polite

    slow = db.execute("SELECT COUNT(*) FROM leads WHERE psi_mobile < 40").fetchone()[0]
    print(f"\ndone: {scored}/{checked} scored; {slow} lead(s) under PSI 40 total")
    db.close()


if __name__ == "__main__":
    main()
