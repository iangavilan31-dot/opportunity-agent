"""
Primary business sourcing via Google Maps (gosom/google-maps-scraper).

Runs the free MIT-licensed scraper binary in tools/ against every configured
niche x city and writes the project-root targets.csv that morning_batch already
prefers. Compared to the OpenStreetMap fallback this adds the two fields the
lead score was blind without: review_count and rating ("successful business +
neglected site" is the perfect prospect), plus a phone number for no-website
leads.

Deliberately does NOT pass the scraper's -email flag: website_signals.analyze()
already scrapes contact emails during analysis, and -email makes the scraper
re-crawl every site (3x slower for data we get anyway).

Etiquette/safety: concurrency stays low (-c 2) and volume is a few hundred
places a week from a home IP — far under the thresholds where Google Maps
scraping gets throttled. One niche/city failing is skipped, never fatal.

Run manually:   python source_maps.py [--fresh]
Auto:           web_targets.load_targets() refreshes when targets.csv is
                missing or older than SOURCING_REFRESH_DAYS.
"""
from __future__ import annotations

import csv
import os
import re
import subprocess
import sys
import tempfile
import time

import httpx

import config

_UA = "opportunity-agent-outreach/1.0 (+https://gavika.vercel.app; iangavilan31@gmail.com)"

_HERE = os.path.dirname(__file__)
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
SCRAPER_EXE = os.path.join(_ROOT, "tools", "google_maps_scraper.exe")
TARGETS_CSV = os.path.join(_ROOT, "targets.csv")

# Our category key -> Google Maps search term.
_NICHE_QUERY = {
    "barber":       "barber shop",
    "salon":        "hair salon",
    "dental":       "dentist",
    "medical":      "medical clinic",
    "restaurant":   "restaurant",
    "cafe":         "cafe",
    "plumbing":     "plumber",
    "hvac":         "hvac contractor",
    "roofing":      "roofing contractor",
    "landscaping":  "landscaping company",
    "gym":          "gym",
    "fitness":      "fitness studio",
    "law":          "law firm",
    "auto":         "auto repair shop",
    "electrician":  "electrician",
    "chiropractor": "chiropractor",
    "vet":          "veterinarian",
    "real_estate":  "real estate agency",
    "cleaning":     "cleaning service",
    "pet":          "pet groomer",
}

_CHAIN_HINTS = (
    "walmart", "walgreens", "cvs", "target", "costco", "petsmart", "petco",
    "banfield", "aspen dental", "midas", "firestone", "jiffy lube", "meineke",
    "great clips", "supercuts", "sport clips", "planet fitness", "anytime fitness",
    "la fitness", "starbucks", "dunkin", "mcdonald", "subway", "domino",
)


def scraper_available() -> bool:
    return os.path.exists(SCRAPER_EXE)


def _norm_key(name: str, website: str) -> tuple[str, str]:
    return (re.sub(r"\W+", "", (name or "").lower()), (website or "").lower())


def _row_from(place: dict, category: str, city: str) -> dict | None:
    name = (place.get("title") or "").strip()
    if not name:
        return None
    if any(ch in name.lower() for ch in _CHAIN_HINTS):
        return None  # nationals have corporate sites; never a prospect
    website = (place.get("website") or "").strip()
    try:
        rating = float(place.get("review_rating") or 0)
    except (TypeError, ValueError):
        rating = 0.0
    try:
        review_count = int(float(place.get("review_count") or 0))
    except (TypeError, ValueError):
        review_count = 0
    return {
        "company_name": name,
        "domain": website,
        "category": category,
        "city": city,
        "contact_email": (place.get("emails") or "").split(",")[0].strip(),
        "phone": (place.get("phone") or "").strip(),
        "rating": rating,
        "review_count": review_count,
    }


def _geo_points(city: str) -> list[str]:
    """City -> a small grid of 'lat,lng' points (center + quadrant midpoints).

    Fast mode returns up to ~21 places per query ordered by distance from the
    geo point, so a 5-point spread over the city bbox yields ~100 candidates
    per niche before dedup. Nominatim etiquette: 1 req/sec, real User-Agent.
    """
    try:
        with httpx.Client(timeout=30, headers={"User-Agent": _UA}) as c:
            r = c.get("https://nominatim.openstreetmap.org/search",
                      params={"q": city, "format": "json", "limit": 1})
        js = r.json()
        if not js:
            return []
        s, n = float(js[0]["boundingbox"][0]), float(js[0]["boundingbox"][1])
        w, e = float(js[0]["boundingbox"][2]), float(js[0]["boundingbox"][3])
        cy, cx = (s + n) / 2, (w + e) / 2
        qy, qx = (n - s) / 4, (e - w) / 4
        return [f"{cy:.5f},{cx:.5f}",
                f"{cy + qy:.5f},{cx - qx:.5f}", f"{cy + qy:.5f},{cx + qx:.5f}",
                f"{cy - qy:.5f},{cx - qx:.5f}", f"{cy - qy:.5f},{cx + qx:.5f}"]
    except Exception as e:
        print(f"[source_maps] nominatim failed for {city!r}: {e}")
        return []
    finally:
        time.sleep(1.1)


def _scrape_city(city: str, niches: list[str], depth: int, timeout_s: int) -> list[dict]:
    """Fast-mode scrape: no browser at all (the browser path trips Google's
    'unexpected page type' on headless-shell builds; fast mode is HTTP-only,
    ~0.5s per query, and returns every field we use). One invocation per
    (geo point, niche) so niche attribution is exact."""
    points = _geo_points(city)
    if not points:
        return []
    terms = [(n.lower(), _NICHE_QUERY[n.lower()]) for n in niches
             if _NICHE_QUERY.get(n.lower())]
    log_path = os.path.join(_HERE, "logs", "source_maps.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    deadline = time.time() + timeout_s

    rows: list[dict] = []
    with tempfile.TemporaryDirectory() as tmp, open(log_path, "ab") as lf:
        lf.write(f"\n=== {city} {time.strftime('%Y-%m-%d %H:%M')} (fast mode) ===\n".encode())
        for cat, term in terms:
            qfile = os.path.join(tmp, f"q_{cat}.txt")
            with open(qfile, "w", encoding="utf-8") as f:
                f.write(term)
            for geo in points:
                if time.time() > deadline:
                    print(f"[source_maps] {city}: hit the {timeout_s}s budget; keeping partial results")
                    return rows
                outfile = os.path.join(tmp, f"r_{cat}_{geo.replace(',', '_')}.csv")
                cmd = [SCRAPER_EXE, "-input", qfile, "-results", outfile,
                       "-fast-mode", "-geo", geo, "-zoom", "13",
                       "-exit-on-inactivity", "1m"]
                # Output goes to the log as raw bytes — decoding with the Windows
                # default codepage (cp1252) crashes on the banner's box chars.
                try:
                    lf.flush()
                    subprocess.run(cmd, cwd=_ROOT, timeout=180,
                                   stdout=lf, stderr=subprocess.STDOUT)
                except Exception as e:
                    print(f"[source_maps] {city}/{cat}@{geo}: scraper failed: {e}")
                    continue
                if not os.path.exists(outfile):
                    continue
                try:
                    with open(outfile, "r", encoding="utf-8-sig", newline="") as fh:
                        for place in csv.DictReader(fh):
                            row = _row_from(place, cat, city)
                            if row:
                                rows.append(row)
                except Exception as e:
                    print(f"[source_maps] {city}/{cat}: parse failed: {e}")
    return rows


def refresh(max_rows: int = 1500) -> int:
    """Scrape all configured cities x niches and (re)write targets.csv.
    Returns the number of rows written (0 = nothing scraped; old file kept)."""
    if not scraper_available():
        print(f"[source_maps] scraper binary missing: {SCRAPER_EXE}")
        return 0
    cities = getattr(config, "SOURCING_CITIES", [])
    niches = getattr(config, "SOURCING_NICHES", [])
    depth = getattr(config, "SOURCING_DEPTH", 2)
    timeout_s = getattr(config, "SOURCING_CITY_TIMEOUT_S", 1200)
    require_website = getattr(config, "SOURCING_REQUIRE_WEBSITE", False)

    all_rows: list[dict] = []
    seen: set = set()
    started = time.time()
    for city in cities:
        print(f"[source_maps] scraping {len(niches)} niches in {city} ...")
        for row in _scrape_city(city, niches, depth, timeout_s):
            if require_website and not row["domain"]:
                continue
            key = _norm_key(row["company_name"], row["domain"])
            if key in seen:
                continue
            seen.add(key)
            all_rows.append(row)
        if len(all_rows) >= max_rows:
            break

    if not all_rows:
        print("[source_maps] scrape produced 0 rows; keeping existing targets.csv")
        return 0

    all_rows = all_rows[:max_rows]
    fields = ["company_name", "domain", "category", "city", "contact_email",
              "phone", "rating", "review_count"]
    with open(TARGETS_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(all_rows)
    mins = (time.time() - started) / 60
    with_site = sum(1 for r in all_rows if r["domain"])
    print(f"[source_maps] wrote {len(all_rows)} businesses to targets.csv "
          f"({with_site} with a website, {len(all_rows) - with_site} without) in {mins:.1f} min")
    return len(all_rows)


def csv_age_days() -> float | None:
    if not os.path.exists(TARGETS_CSV):
        return None
    return (time.time() - os.path.getmtime(TARGETS_CSV)) / 86400


if __name__ == "__main__":
    fresh = "--fresh" in sys.argv
    age = csv_age_days()
    if not fresh and age is not None and age < getattr(config, "SOURCING_REFRESH_DAYS", 7):
        print(f"targets.csv is {age:.1f} days old (< refresh window). Use --fresh to force.")
    else:
        refresh()
