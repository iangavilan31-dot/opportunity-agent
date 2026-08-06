"""
Reviews data for the SITE GIFT track — real numbers or nothing.

The generated site may only show review data we can verify:
  - rating + review count come from the Google Maps scrape (score_breakdown.maps
    on the lead, refreshed by targets.csv) — always real, usually available.
  - actual review QUOTES need a reviews provider. With SERPAPI_KEY set we pull
    real quotes via SerpAPI's Google Maps engines; without it, quotes=[] and the
    site renders the honest rating-badge variant instead.

Never fabricates. An empty result is a valid, honest result.
"""
from __future__ import annotations

import csv
import json
import os
import re

import httpx

_HERE = os.path.dirname(__file__)
_TARGETS_CSV = os.path.join(os.path.dirname(_HERE), "targets.csv")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()


def _maps_from_lead(lead) -> dict:
    """rating/review_count/phone the analyzer stored at scrape time."""
    try:
        sb = json.loads(lead.score_breakdown or "{}")
        return sb.get("maps") or {}
    except Exception:
        return {}


def _csv_row(company_name: str) -> dict:
    """targets.csv row for this company (category/phone/rating fallback)."""
    try:
        with open(_TARGETS_CSV, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if (row.get("company_name") or "").strip() == company_name.strip():
                    return row
    except Exception:
        pass
    return {}


def _serpapi_quotes(company_name: str, city: str, cap: int = 4) -> list[dict]:
    """Real Google review quotes via SerpAPI (only with SERPAPI_KEY).
    Two-step: find the place's data_id, then pull its reviews. Any failure
    returns [] — the site falls back to the rating badge."""
    if not SERPAPI_KEY:
        return []
    try:
        with httpx.Client(timeout=20) as client:
            r = client.get("https://serpapi.com/search.json", params={
                "engine": "google_maps", "type": "search",
                "q": f"{company_name} {city}", "api_key": SERPAPI_KEY})
            r.raise_for_status()
            data = r.json()
            place = (data.get("local_results") or [{}])[0] or data.get("place_results") or {}
            data_id = place.get("data_id")
            if not data_id:
                return []
            r = client.get("https://serpapi.com/search.json", params={
                "engine": "google_maps_reviews", "data_id": data_id,
                "sort_by": "ratingHigh", "api_key": SERPAPI_KEY})
            r.raise_for_status()
            out = []
            for rev in (r.json().get("reviews") or [])[:cap * 3]:
                text = (rev.get("snippet") or "").strip()
                stars = rev.get("rating")
                author = ((rev.get("user") or {}).get("name") or "").strip()
                # short, positive, quotable — a 2-star rant is real but not site copy
                if text and stars and stars >= 4 and 30 <= len(text) <= 220:
                    out.append({"text": text, "author": author, "stars": stars})
                if len(out) >= cap:
                    break
            return out
    except Exception as e:
        print(f"[reviews_source] SerpAPI failed for {company_name}: {e}")
        return []


def get_reviews(lead) -> dict:
    """{rating, count, quotes, phone, category, city} — all real, best-effort."""
    maps = _maps_from_lead(lead)
    row = _csv_row(lead.company_name or "")
    city = (lead.job_location or row.get("city") or "").strip()

    def _f(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    def _i(x):
        try:
            return int(x)
        except (TypeError, ValueError):
            return None

    rating = _f(maps.get("rating")) or _f(row.get("rating"))
    count = _i(maps.get("review_count")) or _i(row.get("review_count"))
    phone = (maps.get("phone") or row.get("phone") or "").strip()
    category = (row.get("category") or "").strip().lower()
    if not category:
        # job_title looks like "Website — shop" / "Website — law firm"
        m = re.search(r"—\s*(.+)$", lead.job_title or "")
        category = (m.group(1).strip().lower() if m else "")

    quotes = _serpapi_quotes(lead.company_name, city) if (rating and rating >= 4.0) else []
    return {"rating": rating, "count": count, "quotes": quotes,
            "phone": phone, "category": category, "city": city}
