"""
Target sourcing for the website-selling track.

Priority order:
  1. targets.csv  (project root or backend/) — YOUR real prospect list.
  2. built-in seed set — realistic local businesses with pre-baked findings so
     the whole loop runs end-to-end with zero setup and zero network calls.

targets.csv columns (header row required, extras ignored):
    company_name,domain,category,city,contact_email

`domain` can be blank (that itself is the pitch: "no website"), a real domain
(gets LIVE-analyzed by website_signals), or a social URL. `category` should be
one of the keys in web_offer._CATEGORY (barber, dental, restaurant, hvac, law,
gym, ...); anything else falls back to a generic pitch.
"""
from __future__ import annotations

import csv
import hashlib
import os

import config

_HERE = os.path.dirname(__file__)
_CSV_CANDIDATES = [
    os.path.join(_HERE, "targets.csv"),
    os.path.join(_HERE, "..", "targets.csv"),
]


def target_id(company: str, domain: str) -> str:
    return hashlib.md5(f"web::{company}::{domain}".encode()).hexdigest()


def _baked(opportunity: int, headline: list[str], findings: list[dict],
           email: str = "", **extra) -> dict:
    """Construct a pre-analyzed signals dict for a seed entry (no network)."""
    d = {
        "reachable": True, "social_only": False, "https_ok": True,
        "mobile_friendly": True, "load_ms": None, "pagespeed": None,
        "title_ok": True, "meta_desc_ok": True, "builder": None,
        "copyright_year": None, "contact_email": email,
        "findings": findings, "headline_issues": headline,
        "opportunity_score": opportunity, "engine": "seed",
    }
    d.update(extra)
    return d


def _f(sev: str, code: str, msg: str) -> dict:
    return {"sev": sev, "code": code, "msg": msg}


# ── Built-in seed set: varied categories, cities, and real-world problems ──────
SEED_TARGETS = [
    {
        "company_name": "Fade Factory Barbershop", "domain": "", "category": "barber",
        "city": "Phoenix, AZ", "contact_email": "",
        "signals": _baked(95, ["you don't seem to have a website yet"],
                          [_f("high", "no_domain", "no website on file")]),
    },
    {
        "company_name": "Bella Vita Salon", "domain": "instagram.com/bellavitasalon",
        "category": "salon", "city": "Miami, FL", "contact_email": "",
        "signals": _baked(90, ["you're running on a social page with no real website"],
                          [_f("high", "social_only", "only a social-media page, no real website")]),
    },
    {
        "company_name": "Riverside Family Dental", "domain": "riversidefamilydental.example",
        "category": "dental", "city": "Sacramento, CA", "contact_email": "office@riversidefamilydental.example",
        "signals": _baked(70, ["no mobile version (missing responsive viewport)",
                               "copyright still says 2018"],
                          [_f("high", "no_mobile", "no mobile version (missing responsive viewport)"),
                           _f("med", "stale", "copyright still says 2018")],
                          email="office@riversidefamilydental.example", copyright_year=2018),
    },
    {
        "company_name": "Nonna's Trattoria", "domain": "nonnastrattoria.example",
        "category": "restaurant", "city": "Boston, MA", "contact_email": "hello@nonnastrattoria.example",
        "signals": _baked(60, ["shows 'Not Secure' in the browser (no HTTPS)",
                               "loads in ~5.8s (slow on phones)"],
                          [_f("high", "not_secure", "shows 'Not Secure' in the browser (no HTTPS)"),
                           _f("med", "midslow", "loads in ~5.8s (slow on phones)")],
                          email="hello@nonnastrattoria.example", https_ok=False, load_ms=5800),
    },
    {
        "company_name": "Rapid Response Plumbing", "domain": "rapidresponseplumbing.example",
        "category": "plumbing", "city": "Dallas, TX", "contact_email": "",
        "signals": _baked(85, ["no mobile version (missing responsive viewport)",
                               "shows 'Not Secure' in the browser (no HTTPS)"],
                          [_f("high", "no_mobile", "no mobile version (missing responsive viewport)"),
                           _f("high", "not_secure", "shows 'Not Secure' in the browser (no HTTPS)")],
                          mobile_friendly=False, https_ok=False),
    },
    {
        "company_name": "Peak Performance Auto", "domain": "peakperformanceauto.example",
        "category": "auto", "city": "Denver, CO", "contact_email": "service@peakperformanceauto.example",
        "signals": _baked(55, ["built on GoDaddy's builder", "no meta description (weaker search results)"],
                          [_f("med", "builder", "built on GoDaddy's builder"),
                           _f("low", "no_meta", "no meta description (weaker search results)")],
                          email="service@peakperformanceauto.example", builder="GoDaddy's builder"),
    },
    {
        "company_name": "Iron Temple Gym", "domain": "", "category": "gym",
        "city": "Austin, TX", "contact_email": "",
        "signals": _baked(95, ["you don't seem to have a website yet"],
                          [_f("high", "no_domain", "no website on file")]),
    },
    {
        "company_name": "Whitaker & Cole Law", "domain": "whitakercolelaw.example",
        "category": "law", "city": "Atlanta, GA", "contact_email": "intake@whitakercolelaw.example",
        "signals": _baked(52, ["loads in ~4.6s (slow on phones)", "copyright still says 2019"],
                          [_f("med", "midslow", "loads in ~4.6s (slow on phones)"),
                           _f("med", "stale", "copyright still says 2019")],
                          email="intake@whitakercolelaw.example", load_ms=4600, copyright_year=2019),
    },
    {
        "company_name": "Summit HVAC & Air", "domain": "facebook.com/summithvacair",
        "category": "hvac", "city": "Charlotte, NC", "contact_email": "",
        "signals": _baked(90, ["you're running on a social page with no real website"],
                          [_f("high", "social_only", "only a social-media page, no real website")]),
    },
    {
        "company_name": "Green Thumb Landscaping", "domain": "greenthumblandscaping.example",
        "category": "landscaping", "city": "Portland, OR", "contact_email": "",
        "signals": _baked(68, ["no mobile version (missing responsive viewport)",
                               "no page title (bad for Google)"],
                          [_f("high", "no_mobile", "no mobile version (missing responsive viewport)"),
                           _f("med", "no_title", "no page title (bad for Google)")],
                          mobile_friendly=False, title_ok=False),
    },
    {
        "company_name": "Corner Cup Cafe", "domain": "instagram.com/cornercupcafe",
        "category": "cafe", "city": "Nashville, TN", "contact_email": "",
        "signals": _baked(90, ["you're running on a social page with no real website"],
                          [_f("high", "social_only", "only a social-media page, no real website")]),
    },
    {
        "company_name": "Elite Roofing Pros", "domain": "eliteroofingpros.example",
        "category": "roofing", "city": "Tampa, FL", "contact_email": "office@eliteroofingpros.example",
        "signals": _baked(58, ["built on Wix", "loads in ~4.9s (slow on phones)"],
                          [_f("med", "builder", "built on Wix"),
                           _f("med", "midslow", "loads in ~4.9s (slow on phones)")],
                          email="office@eliteroofingpros.example", builder="Wix", load_ms=4900),
    },
    {
        "company_name": "Serenity Day Spa", "domain": "", "category": "salon",
        "city": "San Diego, CA", "contact_email": "",
        "signals": _baked(95, ["you don't seem to have a website yet"],
                          [_f("high", "no_domain", "no website on file")]),
    },
    {
        "company_name": "Momentum Fitness Studio", "domain": "momentumfitnessstudio.example",
        "category": "fitness", "city": "Chicago, IL", "contact_email": "hello@momentumfitnessstudio.example",
        "signals": _baked(62, ["shows 'Not Secure' in the browser (no HTTPS)",
                               "no meta description (weaker search results)"],
                          [_f("high", "not_secure", "shows 'Not Secure' in the browser (no HTTPS)"),
                           _f("low", "no_meta", "no meta description (weaker search results)")],
                          email="hello@momentumfitnessstudio.example", https_ok=False),
    },
    {
        "company_name": "Bright Smile Orthodontics", "domain": "brightsmileortho.example",
        "category": "dental", "city": "Seattle, WA", "contact_email": "front@brightsmileortho.example",
        "signals": _baked(66, ["no mobile version (missing responsive viewport)",
                               "loads in ~5.1s (slow on phones)"],
                          [_f("high", "no_mobile", "no mobile version (missing responsive viewport)"),
                           _f("med", "midslow", "loads in ~5.1s (slow on phones)")],
                          email="front@brightsmileortho.example", mobile_friendly=False, load_ms=5100),
    },
    {
        "company_name": "Old Town Auto Repair", "domain": "", "category": "auto",
        "city": "Kansas City, MO", "contact_email": "",
        "signals": _baked(95, ["you don't seem to have a website yet"],
                          [_f("high", "no_domain", "no website on file")]),
    },
    {
        "company_name": "Coastal Cleaning Co", "domain": "coastalcleaningco.example",
        "category": "cleaning", "city": "Jacksonville, FL", "contact_email": "info@coastalcleaningco.example",
        "signals": _baked(57, ["built on an old WordPress theme", "copyright still says 2020"],
                          [_f("med", "builder", "built on an old WordPress theme"),
                           _f("med", "stale", "copyright still says 2020")],
                          email="info@coastalcleaningco.example", builder="an old WordPress theme", copyright_year=2020),
    },
    {
        "company_name": "The Sharp Edge Barbers", "domain": "instagram.com/sharpedgebarbers",
        "category": "barber", "city": "Las Vegas, NV", "contact_email": "",
        "signals": _baked(90, ["you're running on a social page with no real website"],
                          [_f("high", "social_only", "only a social-media page, no real website")]),
    },
    {
        "company_name": "Harbor View Realty", "domain": "harborviewrealty.example",
        "category": "real_estate", "city": "Baltimore, MD", "contact_email": "team@harborviewrealty.example",
        "signals": _baked(54, ["loads in ~4.4s (slow on phones)", "no meta description (weaker search results)"],
                          [_f("med", "midslow", "loads in ~4.4s (slow on phones)"),
                           _f("low", "no_meta", "no meta description (weaker search results)")],
                          email="team@harborviewrealty.example", load_ms=4400),
    },
    {
        "company_name": "Paws & Claws Grooming", "domain": "", "category": "pet",
        "city": "Columbus, OH", "contact_email": "",
        "signals": _baked(95, ["you don't seem to have a website yet"],
                          [_f("high", "no_domain", "no website on file")]),
    },
]


def _load_csv() -> list[dict]:
    for path in _CSV_CANDIDATES:
        if not os.path.exists(path):
            continue
        rows: list[dict] = []
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    name = (row.get("company_name") or row.get("name") or "").strip()
                    if not name:
                        continue
                    rows.append({
                        "company_name": name,
                        "domain": (row.get("domain") or row.get("website") or "").strip(),
                        "category": (row.get("category") or "generic").strip(),
                        "city": (row.get("city") or row.get("location") or "").strip(),
                        "contact_email": (row.get("contact_email") or row.get("email") or "").strip(),
                        "signals": None,  # force live analysis
                    })
        except Exception as e:
            print(f"[web_targets] failed to read {path}: {e}")
            return []
        if rows:
            print(f"[web_targets] loaded {len(rows)} targets from {path}")
            return rows
    return []


def load_targets(limit: int = 50) -> tuple[list[dict], str]:
    """Return (targets, source). Priority: targets.csv -> OpenStreetMap -> seed."""
    csv_targets = _load_csv()
    if csv_targets:
        return csv_targets[:limit], "csv"

    if getattr(config, "SOURCING_ENABLED", False):
        try:
            import sourcing
            live = sourcing.fetch(limit=limit)
            if live:
                print(f"[web_targets] sourced {len(live)} businesses from OpenStreetMap")
                return live[:limit], "osm"
            print("[web_targets] OpenStreetMap returned nothing; using seed set")
        except Exception as e:
            print(f"[web_targets] sourcing failed ({e}); using seed set")

    return SEED_TARGETS[:limit], "seed"
