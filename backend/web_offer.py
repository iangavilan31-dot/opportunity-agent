"""
Website-offer copy engine.

Turns the REAL findings from website_signals.analyze() into a cold-email suite
that pitches a website rebuild. Same hard rules the automation copy learned:
  - no "Hi there" filler; when there's no name, open straight on the observation
  - name ONE specific, verifiable problem (from live analysis), never vague flattery
  - give-first CTA (offer the fix-list / a free mockup), never "book a call"
  - honest and hedged; ~80 words for the initial email
  - a specific, honest subject line (no fake "Re:")

Produces the same dict shape as email_templates.generate_suite_template() so it
drops straight into the existing Lead columns, Queue/Send UI, and analytics.
"""
from __future__ import annotations

import config
from email_templates import _variant, _first_name, _article


# Category -> (singular noun, how their customers find them) for natural copy.
_CATEGORY = {
    "barber":        ("barbershop", "people searching 'barber near me' on their phone"),
    "salon":         ("salon", "people searching for a stylist on their phone"),
    "dental":        ("dental practice", "patients looking for a dentist online"),
    "medical":       ("practice", "patients looking for a provider online"),
    "restaurant":    ("restaurant", "hungry people checking your menu on their phone"),
    "cafe":          ("cafe", "locals checking your hours and menu on their phone"),
    "plumbing":      ("plumbing company", "homeowners with an emergency searching on their phone"),
    "hvac":          ("HVAC company", "homeowners searching when the AC dies"),
    "roofing":       ("roofing company", "homeowners comparing contractors online"),
    "landscaping":   ("landscaping company", "homeowners looking for a crew online"),
    "gym":           ("gym", "people searching for a gym near them"),
    "fitness":       ("studio", "people searching for a class near them"),
    "law":           ("law firm", "people searching for an attorney after hours"),
    "auto":          ("shop", "drivers searching for a nearby shop"),
    "electrician":   ("electrical company", "homeowners searching when something breaks"),
    "chiropractor":  ("chiropractic office", "people searching for a chiropractor nearby"),
    "vet":           ("veterinary clinic", "pet owners searching for a vet nearby"),
    "real_estate":   ("brokerage", "buyers and sellers checking you out online"),
    "cleaning":      ("cleaning company", "people searching for a cleaner online"),
    "pet":           ("business", "pet owners searching nearby"),
    "generic":       ("business", "customers searching for you online"),
}


def _ctx(category: str) -> tuple[str, str]:
    return _CATEGORY.get((category or "generic").lower(), _CATEGORY["generic"])


def offer_pack() -> dict:
    setup = getattr(config, "WEB_SETUP_PRICE", 1200)
    monthly = getattr(config, "WEB_MONTHLY_PRICE", 99)
    return {
        "name": "Website Rebuild",
        "deliverables": [
            "modern, mobile-first redesign",
            "fast, secure (HTTPS) hosting",
            "click-to-call + booking/contact form",
            "Google Business + basic local SEO setup",
        ],
        "setup": setup,
        "monthly": monthly,
        "pitch": "A fast, mobile-first site that turns the people already searching for you into calls and bookings.",
    }


def _issue_clause(signals: dict, company: str, noun: str, how_found: str) -> str:
    """One specific sentence naming the top real problem."""
    codes = {f["code"] for f in signals.get("findings", [])}
    issues = signals.get("headline_issues", [])
    lead_issue = issues[0] if issues else "your site could be working a lot harder"

    if "no_domain" in codes:
        return (f"I went looking for {company}'s website and couldn't find one — "
                f"which means {how_found} are landing on competitors who show up first.")
    if "social_only" in codes:
        return (f"Looks like {company} is running off a social page with no real website — "
                f"so {how_found} have nowhere to book or learn more.")
    if "unreachable" in codes:
        return (f"I tried to pull up your website and it didn't load — "
                f"if that's happening to {how_found} too, it's costing you calls.")
    if "no_mobile" in codes:
        return (f"Your website doesn't have a mobile version — and {how_found} "
                f"are almost all on phones, where it's hard to read and tap.")
    if "not_secure" in codes:
        return (f"Your site shows up as \"Not Secure\" in the address bar, "
                f"which quietly turns away {how_found} before they ever call.")
    if {"slow", "slow_ps"} & codes:
        return (f"Your site is slow to load — {how_found} tend to bounce before it "
                f"even finishes, and Google pushes slow sites down.")
    if "builder" in codes:
        return (f"Your site looks like it's on {signals.get('builder', 'an old builder')}, "
                f"and it's showing its age next to what {how_found} expect now.")
    if "stale" in codes:
        return (f"Small thing that says a lot: your site's copyright still reads "
                f"{signals.get('copyright_year')}, so it reads as abandoned to {how_found}.")
    return f"Quick look at your site turned up something worth fixing — {lead_issue}."


def generate_website_suite(
    company_name: str,
    city: str,
    category: str,
    contact_name: str,
    signals: dict,
) -> dict:
    fn = _first_name(contact_name)
    noun, how_found = _ctx(category)
    offer = offer_pack()
    issues = signals.get("headline_issues", []) or ["a few things worth fixing"]
    lead_issue = issues[0]
    issue_clause = _issue_clause(signals, company_name, noun, how_found)
    seed = (company_name or "") + (city or "")
    has_name = bool(contact_name and contact_name.strip())
    greeting = f"Hi {fn},\n\n" if has_name else ""

    # Identity + social proof + optional Google Meet offer (config-driven).
    studio = getattr(config, "STUDIO_NAME", "").strip()
    portfolio = getattr(config, "PORTFOLIO_URL", "").strip()
    offer_meet = getattr(config, "OFFER_MEET", False)
    studio_clause = f" (I run {studio}, a small studio)" if studio else ""
    proof = ""
    if portfolio:
        proof = _variant(seed + "proof", [
            f" Here's recent work: {portfolio}.",
            f" You can see my work here: {portfolio}.",
            f" A few of my recent sites: {portfolio}.",
        ])
    meet = " — or a quick 10-min Google Meet if that's easier" if offer_meet else ""

    # ── Subject: specific, honest, no fake Re: ───────────────────────────────
    codes = {f["code"] for f in signals.get("findings", [])}
    if {"no_domain", "social_only", "unreachable"} & codes:
        subject_pool = [
            f"{company_name}'s website",
            f"couldn't find {company_name} online",
            f"quick note for {company_name}",
        ]
    elif "no_mobile" in codes:
        subject_pool = [
            f"{company_name} on mobile",
            f"your site + phones",
            f"quick note on {company_name}'s website",
        ]
    else:
        subject_pool = [
            f"quick note on {company_name}'s website",
            f"noticed something on your site",
            f"{company_name}'s website",
        ]
    subject = _variant(seed + "subj", subject_pool)

    # ── Short initial email (~80-90 words), give-first ───────────────────────
    give = _variant(seed + "give", [
        f"Happy to send a free mockup of your new homepage so you can see it first{meet}. Want me to?",
        f"I can put together a quick homepage mockup for {company_name}, free, so you see it before deciding anything{meet}. Sound good?",
        f"Want me to send over a free mockup of what a new homepage could look like{meet}? No pressure either way.",
    ])
    email_body = f"""{greeting}{issue_clause}

I design fast, mobile-first sites for local {noun}s{f' around {city}' if city else ''}{studio_clause} — the kind that turn a Google search into a phone call.{proof}

{give}

— [Your name]"""

    # ── Long version ─────────────────────────────────────────────────────────
    fix_lines = "\n".join(f"• {i}" for i in issues)
    email_long = f"""{greeting}{issue_clause}

Here's what stood out when I looked:
{fix_lines}

None of it is hard to fix. I design fast, mobile-first sites for local {noun}s — HTTPS, click-to-call, a booking/contact form, and set up so you show up when {how_found}.{proof}

I'd rather show than tell: I can put together a quick mockup of a new homepage for {company_name}, free, and you decide from there{meet}. Want me to send it over?

— [Your name]"""

    # ── Mini-audit (the give-first asset, all real findings) ─────────────────
    audit_lines = [
        f"A quick, honest look at {company_name}'s website — the things I'd fix first:\n"
    ]
    for i, issue in enumerate(issues, 1):
        audit_lines.append(f"{i}. {issue[0].upper()}{issue[1:]}.")
    if signals.get("load_ms") and not signals.get("pagespeed"):
        audit_lines.append(f"\n(For reference, it took about {signals['load_ms']/1000:.1f} seconds to load when I checked.)")
    if signals.get("pagespeed") is not None:
        audit_lines.append(f"\n(Google currently scores its mobile speed {signals['pagespeed']}/100.)")
    audit_lines.append(
        f"\nI'd rebuild it as a fast, mobile-first site — {', '.join(offer['deliverables'])}. "
        f"I do this for local {noun}s for ${offer['setup']:,} to build "
        f"(+ ${offer['monthly']}/mo for hosting, security, and small changes)."
        + (f" Recent work: {portfolio}." if portfolio else "")
        + f" Happy to send a free homepage mockup first so you can see it before deciding{meet}."
    )
    mini_audit = "\n".join(audit_lines)

    # ── Follow-ups ────────────────────────────────────────────────────────────
    follow_up_1 = f"""{greeting}Circling back — figured this might've slipped past.

Short version: {lead_issue}, and it's the kind of thing quietly sending {how_found} to competitors. I already sketched what a new homepage for {company_name} could look like — just say the word and I'll send it over, no charge.

— [Your name]"""

    follow_up_2 = f"""{greeting}Last note from me — if the website isn't a priority right now, totally understand and I'll leave it here.

If it ever is, I make it painless: I do the whole build, you just approve it. My door's open.

— [Your name]"""

    breakup_email = f"""{greeting}Closing the loop on this one — sounds like the timing isn't right, which is completely fair.

If {lead_issue.split(' (')[0]} ever starts costing you real business, reach out anytime. Either way, wishing {company_name} the best.

— [Your name]"""

    # ── Objection responses (website-specific) ───────────────────────────────
    objection_responses = {
        "We already have a website": (
            f"You do — and that's exactly why I reached out. The issue isn't that it "
            f"doesn't exist, it's that {lead_issue}. I'd be rebuilding what you have into "
            f"something that actually converts, not starting from zero."),
        "We're too busy right now": (
            f"Totally get it — that's the point, you shouldn't have to touch it. I do the "
            f"whole build and just send you a link to approve. Takes about an hour of your time, "
            f"start to finish."),
        "We get all our business by word of mouth": (
            f"That's great, and a good site makes word of mouth easier — when someone recommends "
            f"you, the first thing the friend does is look you up. Right now {lead_issue}, so that "
            f"referral can stall right there."),
        "How much does it cost?": (
            f"${offer_pack()['setup']:,} to build it, then ${offer_pack()['monthly']}/mo for hosting, "
            f"security, and small changes so it stays current. I'll send a free homepage mockup first "
            f"so you know exactly what you're getting before you spend anything."),
        "We tried this before and it didn't help": (
            f"Fair — a lot of sites get built and then just sit there. The difference is I build for "
            f"the one job that matters (turning a search into a call) and set up the Google Business "
            f"side so people actually find it. Happy to show you the difference in a quick mockup."),
        "Send me some info": (
            f"On it — I'll put together a short, specific breakdown for {company_name} (what I'd fix and "
            f"a mockup of the new homepage). No deck, no fluff."),
    }

    return {
        "subject_line": subject,
        "email_body": email_body,
        "email_long": email_long,
        "mini_audit": mini_audit,
        "follow_up_1": follow_up_1,
        "follow_up_2": follow_up_2,
        "breakup_email": breakup_email,
        "objection_responses": objection_responses,
        "offer": offer,
        "_engine": "web_template",
        "_niche": "web_design",
    }
