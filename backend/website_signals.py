"""
Website signal analysis — the "smart stats" engine for the website-selling track.

Given a business domain, this fetches the live site and extracts REAL, citable
problems that a cold email can name specifically:

    - no website at all (or social-only)   -> the strongest pitch
    - no mobile version (missing viewport)  -> most customers are on phones
    - "Not Secure" (no HTTPS)               -> spooks customers, hurts Google rank
    - slow load                              -> measured round-trip time
    - outdated template / stale copyright    -> looks abandoned
    - missing <title> / meta description     -> invisible to search

It also scrapes a contact email off the page so drafts come out ready-to-send.

Everything here works with ZERO API keys. If PAGESPEED_API_KEY is set, we also
pull Google's real mobile Performance score; otherwise we fall back to the
measured load time. One bad site never crashes a batch -- every path is guarded.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone

import httpx

import config

CURRENT_YEAR = datetime.now(timezone.utc).year

_SOCIAL_HOSTS = ("facebook.com", "instagram.com", "linkedin.com", "yelp.com",
                 "twitter.com", "x.com", "tiktok.com", "google.com", "wa.me")

# Builders: (signatures, points, strong_outdated?). Only Google Sites is damning
# on its own — every other builder can host a perfectly nice modern site, so it
# just adds points and must be corroborated by a real problem (no mobile / no
# HTTPS / stale / slow) or the modernity gate skips it. A pretty Weebly/Wix site
# should NOT be pitched, and this reflects that.
_BUILDERS = {
    "Google Sites":      (["sites.google.com", "gstatic.com/sites", "google.com/sites"], 95, True),
    "Weebly":            (["weebly.com", "weeblycloud", "editmysite.com"], 38, False),
    "GoDaddy's builder": (["img1.wsimg.com", "godaddy.com/websites", "websitebuilder.godaddy"], 38, False),
    "Jimdo":             (["jimdo.com", "jimdofree", "jimdosite"], 38, False),
    "Yola":              (["yola.com", "yolasite"], 38, False),
    "Webnode":           (["webnode.com", "webnode.page"], 35, False),
    "Site123":           (["site123.me", "site123.com"], 35, False),
    "Wix":               (["wixstatic.com", "_wixcssimports", "parastorage.com", "wix.com"], 30, False),
    "Squarespace":       (["static1.squarespace", "squarespace.com", "sqs-"], 16, False),
    "WordPress":         (["wp-content", "wp-includes"], 14, False),
}
# Modern stacks = the business INVESTED. Presence (without strong-outdated signals)
# means "skip them" — they don't need us.
_MODERN_FRAMEWORKS = {
    "Next.js":   ["__next_data__", "/_next/static", "/_next/"],
    "React":     ["data-reactroot", "react-dom", "__reactcontainer"],
    "Webflow":   ["data-wf-page", "data-wf-site", "website-files.com"],
    "Framer":    ["data-framer", "framerusercontent.com", "__framer"],
    "Gatsby":    ["___gatsby", "/page-data/"],
    "Nuxt/Vue":  ["__nuxt", "data-v-app"],
    "Shopify":   ["cdn.shopify.com", "shopify.theme"],
}

_ROLE_PREFERENCE = ["owner", "info", "contact", "hello", "office", "frontdesk",
                    "appointments", "booking", "reception", "admin", "team", "sales"]

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_BAD_EMAIL_SUFFIX = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js")

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def clean_host(domain: str) -> str:
    d = (domain or "").strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = d.split("/")[0].split("?")[0]
    if d.startswith("www."):
        d = d[4:]
    return d


def is_social(domain: str) -> bool:
    host = clean_host(domain)
    return any(host == s or host.endswith("." + s) for s in _SOCIAL_HOSTS)


def _pick_email(candidates: list[str], host: str) -> str:
    """Choose the best contact email scraped from a page."""
    seen: list[str] = []
    for c in candidates:
        c = c.strip().strip(".").lower()
        if not c or c.endswith(_BAD_EMAIL_SUFFIX):
            continue
        if any(x in c for x in ("example.com", "sentry.", "@2x", "wixpress.com", "godaddy.com")):
            continue
        if c not in seen:
            seen.append(c)
    if not seen:
        return ""
    root = host.split(".")[-2] if host.count(".") >= 1 else host
    # 1) role account on the business's own domain
    for pref in _ROLE_PREFERENCE:
        for e in seen:
            local, _, dom = e.partition("@")
            if local == pref and root and root in dom:
                return e
    # 2) any address on the business's own domain
    for e in seen:
        if root and root in e.split("@")[-1]:
            return e
    # 3) any role account
    for pref in _ROLE_PREFERENCE:
        for e in seen:
            if e.startswith(pref + "@"):
                return e
    return seen[0]


def _fetch(url: str, timeout: float = 12.0, verify: bool = True) -> tuple[httpx.Response | None, float, str]:
    """GET a URL. Returns (response|None, elapsed_ms, error)."""
    start = time.perf_counter()
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout,
                          headers={"User-Agent": _UA}, verify=verify) as client:
            resp = client.get(url)
        return resp, (time.perf_counter() - start) * 1000.0, ""
    except httpx.ConnectError as e:
        return None, (time.perf_counter() - start) * 1000.0, f"connect: {e}"
    except (httpx.TimeoutException,):
        return None, timeout * 1000.0, "timeout"
    except Exception as e:  # SSL errors, protocol errors, etc.
        return None, (time.perf_counter() - start) * 1000.0, f"{type(e).__name__}: {e}"


def _pagespeed_score(url: str) -> int | None:
    """Google PageSpeed Insights mobile Performance score (0-100). Optional."""
    key = getattr(config, "PAGESPEED_API_KEY", "")
    if not key:
        return None
    try:
        api = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        with httpx.Client(timeout=45.0) as client:
            r = client.get(api, params={"url": url, "strategy": "mobile",
                                        "category": "performance", "key": key})
        data = r.json()
        score = data["lighthouseResult"]["categories"]["performance"]["score"]
        return round(score * 100)
    except Exception:
        return None


def _empty_result(domain: str) -> dict:
    return {
        "domain": clean_host(domain),
        "reachable": False,
        "social_only": False,
        "https_ok": False,
        "mobile_friendly": None,
        "load_ms": None,
        "pagespeed": None,
        "title_ok": None,
        "meta_desc_ok": None,
        "builder": None,
        "framework": None,
        "modern_hits": 0,
        "marketing_pixels": [],
        "copyright_year": None,
        "contact_email": "",
        "findings": [],
        "headline_issues": [],
        "opportunity_score": 0,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "engine": "live",
    }


def analyze(domain: str) -> dict:
    """
    Analyze a business's web presence. Always returns a result dict; never raises.

    opportunity_score (0-100) is how much this business NEEDS a new site:
    100 = no site at all, ~30 = clean modern site (skip -- don't pitch them).
    """
    res = _empty_result(domain)
    host = res["domain"]

    if not host or "." not in host:
        res["findings"].append({"sev": "high", "code": "no_domain",
                                "msg": "no website on file"})
        res["headline_issues"] = ["you don't seem to have a website yet"]
        res["opportunity_score"] = 95
        return res

    if is_social(domain):
        res["social_only"] = True
        res["findings"].append({"sev": "high", "code": "social_only",
                                "msg": "only a social-media page, no real website"})
        res["headline_issues"] = ["you're running on a social page with no real website"]
        res["opportunity_score"] = 90
        res["contact_email"] = ""
        return res

    # Try HTTPS first, then plain HTTP. The "Not Secure" claim goes into a real
    # email, so it must be DETERMINISTIC — a transient timeout once produced a
    # false "Not Secure" line about a perfectly fine site (2026-07-08). Hence:
    # retry https once, and before ever claiming no-HTTPS, confirm the server
    # truly doesn't speak TLS (verify=False probe separates cert quirks — which
    # browsers often tolerate via AIA chain fetching — from actual no-HTTPS).
    cert_note = ""
    resp, load_ms, err = _fetch(f"https://{host}")
    if resp is None:
        resp, load_ms, err = _fetch(f"https://{host}")  # retry: transients lie
    https_ok = resp is not None and resp.status_code < 500
    if not https_ok:
        resp_nv, load_nv, _err_nv = _fetch(f"https://{host}", verify=False)
        if resp_nv is not None and resp_nv.status_code < 500:
            # HTTPS is served; only Python's cert validation failed. Chrome
            # likely shows this site as secure — never claim "Not Secure".
            resp, load_ms = resp_nv, load_nv
            https_ok = True
            cert_note = err
        else:
            resp2, load_ms2, err2 = _fetch(f"http://{host}")
            if resp2 is not None and resp2.status_code < 500:
                resp, load_ms, err = resp2, load_ms2, err2
                https_ok = False  # confirmed: reachable, but NOT over https
            else:
                # Totally unreachable.
                res["findings"].append({"sev": "high", "code": "unreachable",
                                        "msg": "website didn't load (may be down or gone)"})
                res["headline_issues"] = ["your website didn't load when I checked"]
                res["opportunity_score"] = 88
                return res
    else:
        https_ok = str(resp.url).startswith("https://")

    res["reachable"] = True
    res["https_ok"] = https_ok
    res["load_ms"] = round(load_ms)
    html = (resp.text or "")[:600_000]
    low = html.lower()

    def add(sev, code, msg):
        res["findings"].append({"sev": sev, "code": code, "msg": msg})

    score = 0
    strong_outdated = False  # a hard signal the site is genuinely old/neglected

    # ── Builder detection ────────────────────────────────────────────────────
    builder = None
    for label, (sigs, pts, strong) in _BUILDERS.items():
        if any(s in low for s in sigs):
            builder = label
            score += pts
            if strong:
                strong_outdated = True
                add("high", "builder", f"built on {label}")
            else:
                add("low", "builder", f"built on {label}")
            if label == "WordPress" and ("themes/twenty" in low or "themes/astra" in low):
                score += 25
                strong_outdated = True
                add("med", "old_theme", "running an old WordPress theme")
            break
    res["builder"] = builder

    # ── Modern framework? (business invested — a reason to EXCLUDE) ──────────
    framework = None
    for label, sigs in _MODERN_FRAMEWORKS.items():
        if any(s in low for s in sigs):
            framework = label
            break
    res["framework"] = framework

    # ── Ad pixels = "already pays for marketing" (RANK-ONLY signal) ──────────
    # A business running paid ads onto a weak site is the ideal rebuild prospect.
    # Used only to prioritize — never claimed in an email (pixels persist years
    # after spend stops, and GA alone is free analytics, not spend).
    pixels = []
    if "connect.facebook.net" in low or "fbq(" in low:
        pixels.append("Meta pixel")
    if "googleadservices.com" in low or re.search(r"gtag\(['\"]config['\"],\s*['\"]aw-", low):
        pixels.append("Google Ads tag")
    if "analytics.tiktok.com" in low:
        pixels.append("TikTok pixel")
    if "bat.bing.com" in low:
        pixels.append("Microsoft Ads tag")
    res["marketing_pixels"] = pixels

    # ── Legacy tech fingerprints (citable, hard "outdated" evidence) ─────────
    if re.search(r"jquery[/-]1\.\d|jquery(?:\.min)?\.js\?ver=1\.", low):
        score += 15
        strong_outdated = True
        add("med", "old_jquery", "runs a ~2013-era JavaScript library (jQuery 1.x)")
    if ".swf" in low:
        score += 30
        strong_outdated = True
        add("high", "flash", "still embeds Flash, which browsers dropped in 2020")
    if "<frameset" in low:
        score += 30
        strong_outdated = True
        add("high", "frameset", "built with HTML framesets (a 1990s technique)")
    if "<marquee" in low:
        score += 15
        strong_outdated = True
        add("med", "marquee", "uses scrolling marquee text (a 1990s effect)")
    if re.search(r"bootstrap[/-]3\.\d|bootstrap[/-]2\.\d", low):
        score += 10
        add("med", "old_bootstrap", "styled with a 2013-era CSS framework (Bootstrap 2/3)")

    # ── HTTPS / "Not Secure" ────────────────────────────────────────────────
    if not https_ok:
        score += 30
        strong_outdated = True
        add("high", "not_secure", "shows 'Not Secure' in the browser (no HTTPS)")
    elif cert_note:
        # True but browser-invisible in most cases — low sev, never a headline.
        add("low", "cert", "its TLS certificate didn't validate cleanly when I checked")

    # ── Mobile viewport ─────────────────────────────────────────────────────
    has_viewport = 'name="viewport"' in low or "name='viewport'" in low
    res["mobile_friendly"] = has_viewport
    if not has_viewport:
        score += 30
        strong_outdated = True
        add("high", "no_mobile", "no mobile version (missing responsive viewport)")

    # ── Stale copyright year (relative to now) ──────────────────────────────
    years = [int(y) for y in re.findall(r"(?:©|&copy;|copyright)[^0-9]{0,14}(20\d{2})", low)]
    if years:
        newest = max(years)
        res["copyright_year"] = newest
        age = CURRENT_YEAR - newest
        if age >= 6:
            score += 20; strong_outdated = True
        elif age == 5:
            score += 15; strong_outdated = True
        elif age == 4:
            score += 10
        elif age == 3:
            score += 5
        if age >= 4:
            add("med", "stale", f"copyright still says {newest}")

    # ── Abandonment signals ─────────────────────────────────────────────────
    if "under construction" in low:
        score += 40; strong_outdated = True
        add("high", "construction", "still shows 'under construction'")
    if "lorem ipsum" in low:
        score += 25; strong_outdated = True
        add("med", "lorem", "has placeholder 'lorem ipsum' text")
    has_favicon = ('rel="icon"' in low or "rel='icon'" in low
                   or 'rel="shortcut icon"' in low or "shortcut icon" in low)
    if not has_favicon:
        score += 8
        add("low", "no_favicon", "no favicon (tab icon)")
    if https_ok and re.search(r'(?:src|href)=["\']http://', low):
        score += 15
        add("med", "mixed", "loads insecure content on a secure page")

    # ── Real speed (Google PageSpeed only — raw fetch time is too noisy) ─────
    ps = _pagespeed_score(f"https://{host}" if https_ok else f"http://{host}")
    res["pagespeed"] = ps
    if ps is not None:
        if ps < 40:
            score += 20; strong_outdated = True
            add("high", "slow_ps", f"Google rates its mobile speed {ps}/100")
        elif ps < 50:
            score += 15
            add("med", "slow_ps", f"mobile speed score is only {ps}/100")

    # ── Call-to-action present? (phone link / booking) ──────────────────────
    has_cta = ("tel:" in low or "book now" in low or "book online" in low
               or "schedule" in low or "request a quote" in low or "get a quote" in low
               or "appointment" in low or "contact us" in low)
    if not has_cta:
        score += 15
        add("med", "no_cta", "no clear call-to-action (call / book)")

    # ── Title / meta (LOW weight — JS sites inject these; not a real problem) ─
    m_title = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    res["title_ok"] = bool(m_title and m_title.group(1).strip())
    if not res["title_ok"]:
        score += 4
    res["meta_desc_ok"] = bool(re.search(r'<meta[^>]+name=["\']description["\']', html, re.IGNORECASE))
    if not res["meta_desc_ok"]:
        score += 3

    # ── MODERNITY EXCLUSION — the "eliminate good businesses" gate ───────────
    has_og = 'property="og:' in low or "property='og:" in low
    has_ldjson = "application/ld+json" in low
    has_fonts = ("fonts.googleapis.com" in low or "@font-face" in low or "use.typekit" in low
                 or "fonts.gstatic" in low)
    has_srcset = "srcset=" in low
    modern_hits = sum([has_viewport, has_og, has_ldjson, has_fonts, has_favicon,
                       has_srcset, https_ok, framework is not None])
    res["modern_hits"] = modern_hits

    # A detected modern framework, absent hard-outdated signals, = invested → skip.
    if framework and not strong_outdated:
        score = min(score, 15)
    # Looks broadly modern and nothing screams "old" → skip.
    elif modern_hits >= 4 and not strong_outdated:
        score = min(score, 20)

    res["opportunity_score"] = min(100, score)

    # ── Scrape a contact email ──────────────────────────────────────────────
    mailtos = re.findall(r"mailto:([^\"'?>\s]+)", html, re.IGNORECASE)
    res["contact_email"] = _pick_email(list(mailtos) + _EMAIL_RE.findall(html), host)

    # Top issues, worst-first, for the email copy.
    order = {"high": 0, "med": 1, "low": 2}
    ranked = sorted(res["findings"], key=lambda f: order.get(f["sev"], 3))
    res["headline_issues"] = [f["msg"] for f in ranked[:3]]
    return res
