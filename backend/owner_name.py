"""
Owner/contact name discovery — free, precision-first.

A personalized greeting measurably lifts replies, but a WRONG name is worse
than none ("Hi Sarah" to Bob is fatal). So this only returns a name when it is
anchored to hard evidence, and abstains on ambiguity:

  1. The Google Maps title itself — local health practices very often embed the
     owner: "Terravita Smiles - Goli Asadi, DDS".
  2. The business's homepage / about page — but ONLY credential- or
     role-anchored patterns (Dr. X · X, DDS · "owner: X" · "founded by X").
     No generic name-guessing.

Multiple distinct doctors found (group practice) -> abstain. Never invent.
"""
from __future__ import annotations

import re

import httpx

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_CREDS = r"(?:D\.?D\.?S|D\.?M\.?D|D\.?C|D\.?V\.?M|D\.?P\.?M|O\.?D|M\.?D|N\.?D|L\.?Ac|Esq)\.?"
_NAME = r"([A-Z][a-zA-Z'\-]{1,15})\s+(?:[A-Z]\.?\s+)?([A-Z][a-zA-Z'\-]{1,18})"

# Words that regex can mistake for first names on business pages.
_NOT_NAMES = {
    "family", "dental", "smile", "smiles", "care", "meet", "our", "the", "new",
    "contact", "about", "team", "welcome", "quality", "premier", "valley",
    "first", "gentle", "modern", "advanced", "affordable", "emergency", "top",
    "north", "south", "east", "west", "old", "town", "auto", "repair", "law",
    "animal", "pet", "desert", "sun", "state", "call", "visit", "your",
}

_PATTERNS = [
    # "Dr. Jane Doe" (the workhorse for dental/chiro/vet/medical)
    re.compile(rf"\bDr\.?\s+{_NAME}"),
    # "Jane Doe, DDS"
    re.compile(rf"\b{_NAME},?\s+{_CREDS}(?![a-zA-Z])"),
    # "owner: Jane Doe" / "founded by Jane Doe" / "owned and operated by Jane Doe"
    re.compile(rf"(?:[Oo]wner|[Ff]ounder|[Ff]ounded by|[Oo]wned and operated by)"
               rf"[:,]?\s+(?:Dr\.?\s+)?{_NAME}"),
]


def _valid(first: str, last: str) -> bool:
    return (first.lower() not in _NOT_NAMES and last.lower() not in _NOT_NAMES
            and first.isalpha())


def _extract(text: str) -> str | None:
    """Return 'First Last' when the page names exactly ONE anchored person."""
    found: list[tuple[str, str]] = []
    for pat in _PATTERNS:
        for m in pat.finditer(text):
            first, last = m.group(1), m.group(2)
            if _valid(first, last) and (first, last) not in found:
                found.append((first, last))
    uniq_firsts = {f for f, _ in found}
    if len(found) == 1 or len(uniq_firsts) == 1:
        f, l = found[0]
        return f"{f} {l}"
    return None  # zero or several people — abstain


def from_maps_title(title: str) -> str | None:
    """'Terravita Smiles - Goli Asadi, DDS' -> 'Goli Asadi'."""
    for sep in (" - ", " — ", " – ", " | ", ": "):
        if sep in (title or ""):
            tail = title.split(sep, 1)[1].strip()
            m = re.match(rf"^(?:Dr\.?\s+)?{_NAME},?\s*(?:{_CREDS})?\s*$", tail)
            if m and _valid(m.group(1), m.group(2)):
                return f"{m.group(1)} {m.group(2)}"
    m = re.search(rf"\bDr\.?\s+{_NAME}", title or "")
    if m and _valid(m.group(1), m.group(2)):
        return f"{m.group(1)} {m.group(2)}"
    return None


def _get(url: str) -> str:
    try:
        with httpx.Client(follow_redirects=True, timeout=10,
                          headers={"User-Agent": _UA}) as c:
            r = c.get(url)
        if r.status_code < 400:
            # Strip tags so patterns match visible text across markup breaks.
            return re.sub(r"<[^>]+>", " ", r.text[:400_000])
    except Exception:
        pass
    return ""


_ABOUT_PATHS = ("/about", "/about-us", "/our-team", "/team", "/meet-the-doctor",
                "/meet-dr", "/our-doctor", "/staff")


def find(company_name: str, domain: str) -> str | None:
    """Best-effort owner name. Maps title first (free), then homepage,
    then one about-ish page. Returns 'First Last' or None (abstain)."""
    name = from_maps_title(company_name or "")
    if name:
        return name
    host = (domain or "").strip()
    if not host or "." not in host:
        return None
    if not host.startswith("http"):
        host = f"https://{host}"
    home = _get(host)
    if home:
        name = _extract(home)
        if name:
            return name
        low = home.lower()
        for path in _ABOUT_PATHS:
            if path.strip("/") in low:   # only follow links the site actually has
                page = _get(host.rstrip("/") + path)
                if page:
                    name = _extract(page)
                    if name:
                        return name
                break                     # one extra fetch max
    return None
