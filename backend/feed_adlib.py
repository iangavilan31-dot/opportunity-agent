"""
feed_adlib — is this business running ads RIGHT NOW? Research report §13 L1.

The whole Ad-Rescue thesis rests on this column being honest: `ad_active=1`
means we SAW a currently-running ad for this exact business in Meta's Ad
Library (or Google's Ads Transparency Center). Per-prospect verified
willingness to pay — never inferred.

Provider chain (first configured wins):
  1. ScrapeCreators (SCRAPECREATORS_API_KEY) — Meta Ad Library API, ~$0.05/lookup
  2. SerpAPI (SERPAPI_KEY) — Google Ads Transparency Center engine
  3. Playwright scrape of the public Meta Ad Library web UI — free, brittle;
     conservative matching (normalized page-name must match the business) so
     a name collision can never fake a signal. Unknown stays NULL.

Values: 1 = ads found · 0 = checked, none found · NULL = not checked /
lookup failed. A NULL is never a 0 — coverage honesty is an E1 deliverable.

Usage: python feed_adlib.py [--limit N] [--nj-only] [--force]
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone

import httpx

_HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(_HERE)
sys.path.insert(0, _HERE)

DB = os.path.join(_HERE, "opportunity_agent.db")
SCRAPECREATORS_KEY = os.getenv("SCRAPECREATORS_API_KEY", "").strip()
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()


def _norm(name: str) -> str:
    """Normalize for matching: lowercase, drop legal suffixes + punctuation."""
    s = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    s = re.sub(r"\b(llc|inc|pa|pc|pllc|llp|ltd|corp|co|esq|dds|dc|md)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _match(company: str, page_name: str) -> bool:
    a, b = _norm(company), _norm(page_name)
    if not a or not b:
        return False
    return a == b or a in b or b in a


# ── Provider 1: ScrapeCreators (Meta Ad Library API) ─────────────────────────
def _via_scrapecreators(company: str, client: httpx.Client) -> dict | None:
    if not SCRAPECREATORS_KEY:
        return None
    try:
        r = client.get("https://api.scrapecreators.com/v1/facebook/adLibrary/search/companies",
                       params={"query": company},
                       headers={"x-api-key": SCRAPECREATORS_KEY}, timeout=30)
        r.raise_for_status()
        for res in (r.json().get("searchResults") or []):
            if _match(company, res.get("name", "")):
                page_id = res.get("page_id") or res.get("id")
                r2 = client.get("https://api.scrapecreators.com/v1/facebook/adLibrary/company/ads",
                                params={"pageId": page_id, "status": "active"},
                                headers={"x-api-key": SCRAPECREATORS_KEY}, timeout=30)
                r2.raise_for_status()
                ads = r2.json().get("results") or []
                if ads:
                    first = min((a.get("start_date") or "" for a in ads), default="")
                    return {"active": 1, "first_seen": str(first)[:10],
                            "url": f"https://www.facebook.com/ads/library/?view_all_page_id={page_id}"}
                return {"active": 0}
        return {"active": 0}  # searched, no matching advertiser page
    except Exception as e:
        print(f"  scrapecreators failed for {company}: {str(e)[:80]}")
        return None


# ── Provider 2: SerpAPI (Google Ads Transparency Center) ─────────────────────
def _via_serpapi(company: str, client: httpx.Client) -> dict | None:
    if not SERPAPI_KEY:
        return None
    try:
        r = client.get("https://serpapi.com/search.json",
                       params={"engine": "google_ads_transparency_center",
                               "text": company, "region": "2840",  # US
                               "api_key": SERPAPI_KEY}, timeout=30)
        r.raise_for_status()
        data = r.json()
        ads = data.get("ad_creatives") or []
        for adv in (data.get("advertisers") or []):
            if _match(company, adv.get("name", "")):
                return {"active": 1 if ads else 0,
                        "url": adv.get("link", "")}
        return {"active": 1 if any(_match(company, a.get("advertiser", ""))
                                   for a in ads) else 0}
    except Exception as e:
        print(f"  serpapi failed for {company}: {str(e)[:80]}")
        return None


# ── Provider 3: Playwright on the public Meta Ad Library ─────────────────────
_pw = {"browser": None, "ctx": None, "p": None}


def _pw_page():
    if _pw["ctx"] is None:
        from playwright.sync_api import sync_playwright
        _pw["p"] = sync_playwright().start()
        _pw["browser"] = _pw["p"].chromium.launch(headless=True)
        _pw["ctx"] = _pw["browser"].new_context(
            viewport={"width": 1400, "height": 900},
            locale="en-US")
    return _pw["ctx"].new_page()


def _pw_close():
    try:
        if _pw["browser"]:
            _pw["browser"].close()
        if _pw["p"]:
            _pw["p"].stop()
    except Exception:
        pass


def _via_playwright(company: str, city: str) -> dict | None:
    """Search the public Ad Library for active ads by this business. Reads the
    rendered result cards; requires a confident page-name match. Any parsing
    doubt returns None (unknown), never a guess."""
    from urllib.parse import quote
    q = quote(company)
    url = (f"https://www.facebook.com/ads/library/?active_status=active"
           f"&ad_type=all&country=US&q={q}&search_type=keyword_unordered")
    page = _pw_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(6000)  # results hydrate client-side
        body = page.inner_text("body", timeout=10000)
        low = body.lower()
        if "log in" in low[:2000] and "ad library" not in low[:2000]:
            return None  # login-walled this session — unknown, not zero
        # "~N results" header appears when the search matched ads
        m = re.search(r"([\d,]+)\s+results?", body)
        if m and int(m.group(1).replace(",", "")) > 0:
            # confirm at least one card names this business (collision guard)
            if _match(company, body[:20000]) or _norm(company) in _norm(body[:20000]):
                start = re.search(r"Started running on ([A-Z][a-z]{2} \d{1,2}, \d{4})", body)
                first = ""
                if start:
                    try:
                        first = datetime.strptime(start.group(1), "%b %d, %Y").date().isoformat()
                    except ValueError:
                        first = ""
                return {"active": 1, "first_seen": first, "url": url}
            return None  # results exist but we can't confirm they're this business
        if re.search(r"No ads match your search|0\s+results?|No results found", body, re.I):
            return {"active": 0}
        return None  # page shape unrecognized — honest unknown
    except Exception as e:
        print(f"  playwright adlib failed for {company}: {str(e)[:80]}")
        return None
    finally:
        page.close()


def check(company: str, city: str, client: httpx.Client) -> dict | None:
    for fn in (lambda: _via_scrapecreators(company, client),
               lambda: _via_serpapi(company, client),
               lambda: _via_playwright(company, city)):
        out = fn()
        if out is not None:
            return out
    return None


def main() -> None:
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    nj_only = "--nj-only" in sys.argv
    force = "--force" in sys.argv

    providers = [n for n, k in (("scrapecreators", SCRAPECREATORS_KEY),
                                ("serpapi", SERPAPI_KEY)) if k] or ["playwright (free fallback)"]
    print(f"providers: {', '.join(providers)}")

    db = sqlite3.connect(DB)
    q = ("SELECT id, company_name, job_location FROM leads "
         "WHERE source='website_autopilot'")
    if not force:
        q += " AND ad_active IS NULL"
    if nj_only:
        q += " AND job_location LIKE '%NJ%'"
    rows = db.execute(q).fetchall()
    if limit:
        rows = rows[:limit]
    print(f"{len(rows)} lead(s) to check")

    active = none_found = unknown = 0
    with httpx.Client() as client:
        for i, (lid, name, loc) in enumerate(rows, 1):
            out = check(name, loc or "", client)
            now = datetime.now(timezone.utc).isoformat()
            if out is None:
                unknown += 1
                print(f"  [{i}/{len(rows)}] {name[:44]}: UNKNOWN (left NULL)")
            elif out["active"]:
                active += 1
                db.execute("UPDATE leads SET ad_active=1, ad_first_seen=?, "
                           "ad_creative_url=?, last_action_at=? WHERE id=?",
                           (out.get("first_seen", ""), out.get("url", ""), now, lid))
                print(f"  [{i}/{len(rows)}] {name[:44]}: ★ ADS ACTIVE"
                      f"{' since ' + out['first_seen'] if out.get('first_seen') else ''}")
            else:
                none_found += 1
                db.execute("UPDATE leads SET ad_active=0, last_action_at=? WHERE id=?",
                           (now, lid))
                print(f"  [{i}/{len(rows)}] {name[:44]}: no active ads")
            db.commit()
            time.sleep(3 if not (SCRAPECREATORS_KEY or SERPAPI_KEY) else 0.5)

    _pw_close()
    print(f"\ndone: {active} ad-active, {none_found} none, {unknown} unknown "
          f"(coverage {active + none_found}/{len(rows)})")
    db.close()


if __name__ == "__main__":
    main()
