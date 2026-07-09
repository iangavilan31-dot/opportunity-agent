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

# Free mailbox providers a small local business legitimately uses as its real
# inbox (a dentist on gmail is normal). Address here = trust it.
_FREE_EMAIL_PROVIDERS = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk", "ymail.com",
    "rocketmail.com", "outlook.com", "hotmail.com", "hotmail.co.uk", "live.com",
    "msn.com", "aol.com", "icloud.com", "me.com", "mac.com", "comcast.net",
    "sbcglobal.net", "att.net", "verizon.net", "cox.net", "protonmail.com",
    "proton.me", "gmx.com", "gmx.us", "zoho.com", "ymail.co.uk",
}

# Web developers / agencies / site-builder support domains. An address on one of
# these scraped off a footer is the VENDOR, never the business — sending to it
# bounces or emails a competitor. This list is why terravitasmiles@gmail.com is
# kept but eben@eyebytes.com (a web dev on a law firm's footer) is rejected.
_VENDOR_EMAIL_DOMAINS = (
    "eyebytes.com", "wix.com", "wixpress.com", "squarespace.com", "godaddy.com",
    "secureserver.net", "duda.co", "dudamobile.com", "vendasta.com", "weebly.com",
    "jimdo.com", "yola.com", "site123.com", "webnode.com", "webflow.com",
    "wordpress.com", "hostgator.com", "bluehost.com", "sentry.io", "sentry.wixpress.com",
    "example.com", "domain.com", "yourdomain.com", "email.com", "sentry-next.wixpress.com",
)

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


def registrable_domain(host: str) -> str:
    """The registrable part of a host — the last two labels, lowercased
    (kineticfamchiro.com from www.kineticfamchiro.com). Good enough to compare
    an email's domain against the business's own domain. Not a full public-suffix
    parse; a multi-label ccTLD (foo.co.uk) collapses to co.uk, which only makes
    the own-domain check STRICTER (safe — we abstain rather than mis-send)."""
    h = clean_host(host)
    parts = [p for p in h.split(".") if p]
    return ".".join(parts[-2:]) if len(parts) >= 2 else h


_BIZ_TOKEN_STOP = {"the", "and", "llc", "inc", "pllc", "corp", "co", "company",
                   "clinic", "center", "group", "services", "service", "care",
                   "family", "az", "arizona", "www", "com"}


def _local_matches_business(local: str, host: str, name_hint: str = "") -> bool:
    """Does this email's local-part clearly belong to THIS business? Used to
    trust a free-provider address that was only text-scraped (not in a mailto:).
    terravitasmiles@gmail.com on terravitasmiles.com -> yes; impallari@gmail.com
    (the Lato font author, scraped from a CSS comment) on ironwoodroofing.com ->
    no. Token overlap of >=4 chars between the local part and the site
    root / business name."""
    loc = re.sub(r"[^a-z0-9]", "", local.lower())
    if len(loc) < 3:
        return False
    tokens: set[str] = set()
    root = registrable_domain(host).split(".")[0]
    if root:
        tokens.add(re.sub(r"[^a-z0-9]", "", root.lower()))
    for w in re.split(r"[^a-z0-9]+", (name_hint or "").lower()):
        if len(w) >= 4 and w not in _BIZ_TOKEN_STOP:
            tokens.add(w)
    for tok in tokens:
        if len(tok) >= 4 and (tok in loc or loc in tok):
            return True
    return False


def is_trustworthy_email(email: str, host: str, *, from_mailto: bool = False,
                         name_hint: str = "") -> bool:
    """Can we trust this scraped address to actually reach THIS business?

    True ONLY when the address is:
      • on the business's own domain (registrable domain matches the site), or
      • on a known free mailbox provider (gmail/outlook/...) AND it either came
        from a real `mailto:` link (intentional contact) or its local-part
        clearly matches the business name/site.

    Everything else is rejected: a web developer's address (eben@eyebytes.com —
    the bounce that started this), a builder's support inbox, a third-party
    company domain, or a free-provider address scraped from a font/library
    comment (impallari@gmail.com off a Lato font). A wrong TO address bounces and
    burns the sender's reputation, so the rule is: trust it or drop it, never
    guess. When only a bare string is available (re-auditing a stored address),
    from_mailto defaults False — the stricter path — so a suspect gmail gets
    dropped rather than kept."""
    email = (email or "").strip().strip(".").lower()
    if not email or email.count("@") != 1 or email.endswith(_BAD_EMAIL_SUFFIX):
        return False
    local, _, dom = email.partition("@")
    if not local or "." not in dom or "@2x" in email:
        return False
    if any(dom == v or dom.endswith("." + v) for v in _VENDOR_EMAIL_DOMAINS):
        return False
    reg = registrable_domain(dom)
    site = registrable_domain(host)
    if bool(site) and reg == site:
        return True                      # the business's own domain
    if reg in _FREE_EMAIL_PROVIDERS:
        return from_mailto or _local_matches_business(local, host, name_hint)
    return False


# Generic role inboxes: read by whoever staffs the front desk, pounded by spam,
# quick to hit report-spam, and the reader usually can't hire us anyway. A
# person-named inbox (betsy@, goli@, shane.mccall@) is read by a human with a
# name — dramatically better reply odds. So person-looking locals now outrank
# role accounts (2026-07-09, from send-screenshot review: almost every TO was
# info@/office@/support@).
_ROLE_LOCALS = set(_ROLE_PREFERENCE) | {
    "support", "service", "sales", "welcome", "intake", "admin", "billing",
    "team", "mail", "email", "help", "hi", "appointments", "appointment",
    "reception", "enquiries", "inquiries", "inquiry", "bookings", "booking",
    "schedule", "scheduling", "hr", "jobs", "careers", "marketing", "accounts",
    "accounting", "customerservice", "customercare", "frontoffice",
}
# Never pick these even as a last resort — nobody reads them.
_NEVER_LOCALS = {"noreply", "no-reply", "donotreply", "do-not-reply",
                 "webmaster", "postmaster", "abuse", "privacy", "unsubscribe",
                 "mailer-daemon", "newsletter"}


def _looks_personal(local: str) -> bool:
    """Does this local part read like a person (goli, betsy, shane.mccall,
    drkent) rather than a desk (info, office2, frontdesk)? Letters only once
    separators are stripped, sane length, and not a known role word."""
    if local in _ROLE_LOCALS or local in _NEVER_LOCALS:
        return False
    core = re.sub(r"[._\-]", "", local)
    return core.isalpha() and 2 <= len(core) <= 24


def _pick_email(mailtos: list[str], texts: list[str], host: str,
                name_hint: str = "") -> str:
    """Choose the best TRUSTWORTHY contact email, or '' if none can be trusted to
    reach this business (abstain over guess — see is_trustworthy_email).

    `mailtos` = addresses from `mailto:` links (intentional contact points);
    `texts`   = addresses regex-scraped from page text (riskier — may be a font
    author, a testimonial, an example). mailto sources are trusted first."""
    site = registrable_domain(host)
    trusted: list[str] = []
    seen: set[str] = set()
    for src, is_mailto in ((mailtos, True), (texts, False)):
        for c in (src or []):
            c = (c or "").strip().strip(".").lower()
            if not c or c in seen or c.split("@")[0] in _NEVER_LOCALS:
                continue
            seen.add(c)
            if is_trustworthy_email(c, host, from_mailto=is_mailto, name_hint=name_hint):
                trusted.append(c)
    if not trusted:
        return ""
    own = [e for e in trusted if registrable_domain(e.split("@")[-1]) == site]
    # 1) a PERSON on the business's own domain — the decision-maker's inbox
    for e in own:
        if _looks_personal(e.split("@")[0]):
            return e
    # 2) a role account on the business's OWN domain (owner@, info@, ...)
    for pref in _ROLE_PREFERENCE:
        for e in own:
            if e.split("@")[0] == pref:
                return e
    # 3) any other address on the business's own domain
    if own:
        return own[0]
    # 4) otherwise a trusted address (mailto ones are already ordered first),
    #    person-looking first for the same reason as (1)
    for e in trusted:
        if _looks_personal(e.split("@")[0]):
            return e
    for pref in _ROLE_PREFERENCE:
        for e in trusted:
            if e.split("@")[0] == pref:
                return e
    return trusted[0]


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


def _tls_handshake_ok(host: str) -> bool | None:
    """Does the host speak TLS on 443? Raw handshake — far more reliable than a
    full page GET (no redirects, no WAF, no body). True = yes; False =
    DEFINITIVELY not (refused / not TLS); None = unknown (timeouts etc.).
    The 'Not Secure' email claim requires a hard False — flaky fetches lied
    to us twice on 2026-07-08/09."""
    import socket
    import ssl
    for _ in range(2):
        try:
            ctx = ssl._create_unverified_context()
            with socket.create_connection((host, 443), timeout=6) as sock:
                with ctx.wrap_socket(sock, server_hostname=host):
                    return True
        except ConnectionRefusedError:
            return False          # nothing listens on 443
        except ssl.SSLError:
            return False          # something listens, but it isn't TLS
        except Exception:
            continue              # timeout / reset / no route — try once more
    return None


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


_LANG_ATTR = re.compile(r"<html[^>]*\slang=[\"']?([a-zA-Z]{2})")
_LANG_HINTS = {
    "es": (" servicios ", " nosotros ", " contáctenos", " cont&aacute;ctenos",
           " nuestro ", " nuestra ", " años ", " empresa ", " llámenos", " hoy mismo "),
    "en": (" services ", " contact us", " about us", " our team", " we offer ",
           " call us", " get a quote", " schedule "),
}


def _detect_language(low: str) -> str:
    """Best-effort page language ('en', 'es', ...). Defaults to 'en' when
    ambiguous — we only want to SKIP a lead when the site is definitively in a
    language the outreach isn't written in, never on a hunch."""
    m = _LANG_ATTR.search(low)
    if m:
        return m.group(1).lower()
    scores = {lang: sum(low.count(h) for h in hints)
              for lang, hints in _LANG_HINTS.items()}
    best = max(scores, key=scores.get)
    if best != "en" and scores[best] >= 3 and scores[best] > scores.get("en", 0) * 2:
        return best
    return "en"


def apply_trust_gap(signals: dict, rating, review_count) -> None:
    """Inject the trust-gap finding when Google Maps data proves it: a business
    with strong reviews whose site shows none of them. The single most
    'this person actually looked' line we can write, and fully verifiable —
    review numbers come from Maps, the absence comes from the page source."""
    try:
        rating = float(rating or 0)
        review_count = int(float(review_count or 0))
    except (TypeError, ValueError):
        return
    if not signals.get("reachable") or signals.get("social_only"):
        return
    if signals.get("reviews_onsite") or "reviews_onsite" not in signals:
        return
    if any(f.get("code") == "trust_gap" for f in signals.get("findings", [])):
        return
    # Fast-mode Maps data reliably has the RATING but usually not the count —
    # never state a number we don't have. Both message forms are verifiable.
    if review_count >= 20 and rating >= 4.0:
        msg = (f"has {review_count} Google reviews at {rating:.1f} stars, "
               f"but the site doesn't show a single one")
    elif rating >= 4.5:
        msg = (f"shows a {rating:.1f}-star rating on Google, "
               f"but the site doesn't show any of your reviews")
    else:
        return
    signals["findings"].insert(0, {"sev": "high", "code": "trust_gap", "msg": msg})
    signals["headline_issues"] = [msg] + list(signals.get("headline_issues", []))[:2]
    signals["opportunity_score"] = min(100, int(signals.get("opportunity_score", 0)) + 10)


def analyze(domain: str, name_hint: str = "") -> dict:
    """
    Analyze a business's web presence. Always returns a result dict; never raises.

    opportunity_score (0-100) is how much this business NEEDS a new site:
    100 = no site at all, ~30 = clean modern site (skip -- don't pitch them).

    name_hint (the business name) helps the email picker trust a free-provider
    address whose local-part matches the business but not the domain
    (mesachiropracticpllc@gmail.com on mesaazchiropractic.com).
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
    https_confirmed_off = False
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
                # The site is reachable over plain http. Before the "Not
                # Secure" claim is allowed, 443 must DEFINITIVELY refuse TLS —
                # a raw handshake separates "their config" from "our network".
                tls = _tls_handshake_ok(host)
                if tls:
                    https_ok = True          # they serve TLS; our fetch was flaky
                else:
                    https_ok = False
                    https_confirmed_off = (tls is False)
            else:
                # Totally unreachable.
                res["findings"].append({"sev": "high", "code": "unreachable",
                                        "msg": "website didn't load (may be down or gone)"})
                res["headline_issues"] = ["your website didn't load when I checked"]
                res["opportunity_score"] = 88
                return res
    else:
        https_ok = str(resp.url).startswith("https://")
        # https reached the server but the site redirected to plain http —
        # a deliberate config, users really do see "Not Secure". Claim is fair.
        https_confirmed_off = not https_ok

    res["reachable"] = True
    res["https_ok"] = https_ok
    res["load_ms"] = round(load_ms)
    html = (resp.text or "")[:600_000]
    low = html.lower()
    res["language"] = _detect_language(low)

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
    # Claim allowed ONLY when 443 definitively refused TLS. Unknown = silence.
    if not https_ok and https_confirmed_off:
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

    # ── Reviews visible on the site? (for the trust-gap check) ──────────────
    res["reviews_onsite"] = bool(re.search(
        r"testimonial|aggregaterating|ratingvalue|google reviews|customer reviews|"
        r"our (?:customers|clients|patients) say|review-?widget|trustindex|birdeye|"
        r"podium\.(?:com|io)|elfsight|reviewsonmywebsite|five[- ]star|5[- ]star", low))

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
    # mailto: links are intentional contact points (trust free-provider ones);
    # regex-scraped text addresses are riskier (a font author / library email in
    # a CSS comment, a testimonial) and a free-provider one must match the biz.
    mailtos = re.findall(r"mailto:([^\"'?>\s]+)", html, re.IGNORECASE)
    res["contact_email"] = _pick_email(list(mailtos), _EMAIL_RE.findall(html),
                                       host, name_hint=name_hint)

    # Top issues, worst-first, for the email copy.
    order = {"high": 0, "med": 1, "low": 2}
    ranked = sorted(res["findings"], key=lambda f: order.get(f["sev"], 3))
    res["headline_issues"] = [f["msg"] for f in ranked[:3]]
    return res
