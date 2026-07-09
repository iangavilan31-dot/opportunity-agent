"""
Free business sourcing via OpenStreetMap (Nominatim + Overpass).

No API key, no credit card, $0. For each (niche x city) it asks OpenStreetMap for
matching local businesses and returns target dicts shaped exactly like a
targets.csv row: {company_name, domain, category, city, contact_email, signals}.

Domain + email come from OSM tags when present; the analyzer scrapes any missing
email off the live site. Coverage varies by area and is lower than Google Places,
but it is genuinely free. A "no website" result is a valid lead too (best pitch).

Etiquette: Nominatim asks for <=1 req/sec and a real User-Agent; Overpass is a
shared free service, so queries are bounded and spaced. Everything is guarded —
a failure for one city/niche is skipped, never fatal.
"""
from __future__ import annotations

import re
import time

import httpx

import config

_UA = "opportunity-agent-outreach/1.0 (+https://gavika.pages.dev; iangavilan31@gmail.com)"
_NOMINATIM = "https://nominatim.openstreetmap.org/search"
_OVERPASS = "https://overpass-api.de/api/interpreter"

# Our category -> OpenStreetMap tag selectors (key, value).
_NICHE_OSM = {
    "barber":       [("shop", "hairdresser")],
    "salon":        [("shop", "beauty"), ("shop", "hairdresser")],
    "dental":       [("amenity", "dentist"), ("healthcare", "dentist")],
    "medical":      [("amenity", "doctors"), ("amenity", "clinic")],
    "restaurant":   [("amenity", "restaurant")],
    "cafe":         [("amenity", "cafe")],
    "plumbing":     [("craft", "plumber")],
    "hvac":         [("craft", "hvac")],
    "roofing":      [("craft", "roofer")],
    "landscaping":  [("craft", "gardener"), ("shop", "garden_centre")],
    "gym":          [("leisure", "fitness_centre")],
    "fitness":      [("leisure", "fitness_centre")],
    "law":          [("office", "lawyer")],
    "auto":         [("shop", "car_repair"), ("shop", "tyres")],
    "electrician":  [("craft", "electrician")],
    "chiropractor": [("healthcare", "chiropractor"), ("amenity", "chiropractor")],
    "vet":          [("amenity", "veterinary")],
    "real_estate":  [("office", "estate_agent")],
    "pet":          [("shop", "pet")],
}


def _domain_from(url: str) -> str:
    if not url:
        return ""
    d = re.sub(r"^https?://", "", url.strip().lower()).split("/")[0].split("?")[0]
    return d[4:] if d.startswith("www.") else d


def _bbox(city: str):
    """Resolve a city name to (south, west, north, east) via Nominatim."""
    try:
        with httpx.Client(timeout=30, headers={"User-Agent": _UA}) as c:
            r = c.get(_NOMINATIM, params={"q": city, "format": "json", "limit": 1})
        js = r.json()
        if not js:
            return None
        bb = js[0]["boundingbox"]  # [south, north, west, east] (strings)
        return (float(bb[0]), float(bb[2]), float(bb[1]), float(bb[3]))
    except Exception as e:
        print(f"[sourcing] nominatim failed for {city!r}: {e}")
        return None


def _overpass(selectors, bbox, cap: int, require_website: bool = True):
    s, w, n, e = bbox
    web = '["website"]' if require_website else ""
    parts = []
    for k, v in selectors:
        parts.append(f'node["{k}"="{v}"]{web}({s},{w},{n},{e});')
        parts.append(f'way["{k}"="{v}"]{web}({s},{w},{n},{e});')
    query = f"[out:json][timeout:60];(" + "".join(parts) + f");out center tags {cap};"
    with httpx.Client(timeout=90, headers={"User-Agent": _UA}) as c:
        r = c.post(_OVERPASS, data={"data": query})
    return r.json().get("elements", [])


def fetch(limit: int = 500) -> list[dict]:
    """Pull up to `limit` real businesses across configured cities x niches."""
    cities = getattr(config, "SOURCING_CITIES", [])
    niches = getattr(config, "SOURCING_NICHES", [])
    cap = getattr(config, "SOURCING_MAX_PER_QUERY", 60)
    require_website = getattr(config, "SOURCING_REQUIRE_WEBSITE", True)
    out: list[dict] = []
    seen: set = set()

    for city in cities:
        bbox = _bbox(city)
        time.sleep(1.1)  # Nominatim rate limit
        if not bbox:
            continue
        for niche in niches:
            selectors = _NICHE_OSM.get(niche.lower())
            if not selectors:
                continue
            try:
                elements = _overpass(selectors, bbox, cap, require_website)
            except Exception as e:
                print(f"[sourcing] overpass failed {niche}/{city}: {e}")
                time.sleep(1.0)
                continue

            for el in elements:
                tags = el.get("tags", {})
                name = (tags.get("name") or "").strip()
                if not name:
                    continue
                domain = _domain_from(tags.get("website") or tags.get("contact:website") or "")
                email = (tags.get("email") or tags.get("contact:email") or "").strip()
                key = (name.lower(), domain)
                if key in seen:
                    continue
                seen.add(key)
                out.append({
                    "company_name": name,
                    "domain": domain,
                    "category": niche.lower(),
                    "city": city,
                    "contact_email": email,
                    "signals": None,  # force live analysis
                })
                if len(out) >= limit:
                    return out
            time.sleep(0.6)  # be polite to Overpass between queries
    return out


if __name__ == "__main__":
    import json
    got = fetch(limit=15)
    print(f"fetched {len(got)} businesses")
    print(json.dumps(got[:8], indent=2))
