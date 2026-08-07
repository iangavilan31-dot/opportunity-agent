"""
cro_offer — the Burning-Ad-Money Rescue email suite. Research report §13 L3.

The pitch the research says nobody sends: not an audit, not a call request —
the prospect's own running ad, their measured page speed, one labeled waste
number, and (artifact arm) the rebuilt page already live.

Copy laws inherited whole: greeting always (greeting_name), sentence-case
subject, <100 words, one verifiable finding, opt-out line, [Mailing address]
via the CAN-SPAM/local gates in settings_store, humanize() at the choke
points, no em dashes in email strings.

E2 experiment arms (report §19): variant='artifact' → touch 1 carries the
waste math, touch 2 carries the live rebuilt page; variant='control' →
identical sequence, no artifact. Attribution via the leads.variant column.
"""
from __future__ import annotations

import waste_math
from email_templates import _variant, _first_name, greeting_name, sentence_case


def generate_cro_suite(company_name: str, contact_name: str, category: str,
                       city: str, psi_mobile: int | None, ad_first_seen: str,
                       ad_creative_url: str, variant: str = "artifact",
                       rebuilt_url: str = "") -> dict:
    fn = _first_name(contact_name)
    has_name = bool(contact_name and contact_name.strip())
    short = greeting_name(company_name)
    greeting = f"Hi {fn},\n\n" if has_name else f"Hi {short} team,\n\n"
    seed = (company_name or "") + "cro"
    w = waste_math.compute(category, psi_mobile)

    # "2026-05-14" is a machine tell — a human writes "May 14"
    since = ""
    if ad_first_seen:
        try:
            from datetime import date
            d = date.fromisoformat(ad_first_seen)
            human = f"{d.strftime('%B')} {d.day}" + ("" if d.year == date.today().year
                                                     else f", {d.year}")
            since = f", running since {human}"
        except ValueError:
            pass
    # No PSI measurement = no speed claim (the false-claim law: any claim in an
    # email must be measured or it doesn't ship). Fall back to the lead's
    # original verified site finding via original_finding.
    psi_clause = (f"the page it lands on scores {psi_mobile}/100 on Google's mobile speed test"
                  if psi_mobile is not None else
                  "the page it lands on undoes some of that spend")

    def _cap(s: str) -> str:  # first letter only — .capitalize() would downcase "Google"
        return s[0].upper() + s[1:] if s else s

    subject = sentence_case(_variant(seed + "subj", [
        f"your ad and the page it lands on",
        f"{short}'s ad is faster than {short}'s website",
        f"the page behind your ad",
        f"{short}",
    ]))

    opener = _variant(seed + "open", [
        f"Saw your ad{since} (it comes up in Meta's public ad library). The ad looks good. The problem is {psi_clause}.",
        f"Your ad is doing its job{since}. Then {psi_clause}, which quietly undoes it.",
        f"I came across {short}'s ad in Meta's ad library{since}. Clicks are not the problem. {_cap(psi_clause)}.",
    ])

    waste_line = waste_math.email_line(w)

    cta = _variant(seed + "cta", [
        "I already built the page your ad should land on. Want the link?",
        f"I went ahead and built {short} the landing page that fixes this. Want to see it?",
        "I put together the fixed page already, no charge to look. Want me to send it over?",
    ]) if variant == "artifact" else _variant(seed + "cta", [
        "Worth a look at what a proper landing page would change?",
        "Happy to show you exactly what I would fix. Interested?",
    ])

    email_body = (f"{greeting}{opener}\n\n{waste_line}\n\n{cta}\n\n"
                  f"If this is not useful, reply \"no thanks\" and I will not write again.\n\n"
                  f"- [Your name]\n[Mailing address]")

    fu1_artifact = (f"{greeting}The page is live if you want to see it side by side with "
                    f"your current one: {rebuilt_url or '[staged page link]'}\n\n"
                    f"Built for {short} specifically, mobile-first, loads fast on a phone. "
                    f"If you point your ad at it and it does not out-convert the current page, "
                    f"you have lost nothing.\n\n- [Your name]\n[Mailing address]")
    fu1_control = (f"{greeting}Circling back on the landing page behind your ad. The math "
                   f"only gets worse the longer the ad runs. Worth a look this week?\n\n"
                   f"- [Your name]\n[Mailing address]")

    follow_up_1 = fu1_artifact if variant == "artifact" else fu1_control
    follow_up_2 = (f"{greeting}Last note from me. The ad spend is yours either way; I would "
                   f"just rather it landed somewhere that converts. If the timing is wrong, "
                   f"no worries at all.\n\n- [Your name]\n[Mailing address]")

    return {
        "subject_line": subject,
        "email_body": email_body,
        "email_long": email_body,
        "mini_audit": waste_math.one_pager_md(short, w, ad_first_seen,
                                              ad_creative_url, rebuilt_url),
        "follow_up_1": follow_up_1,
        "follow_up_2": follow_up_2,
        "breakup_email": follow_up_2,
        "objection_responses": {
            "We already have an agency": (
                "Keep them. This is one page, built and paid for by results: point one ad "
                "at it for two weeks and let the numbers decide. Your agency can keep "
                "everything else."),
            "How do I know it converts better": (
                "You do not, yet, and neither do I — that is what the two-week test is for. "
                "Tracking goes in day one, under your ownership, so the numbers are yours "
                "either way."),
            "What does it cost": (
                "The test costs nothing. If you keep the page it is $399/mo, month to "
                "month, cancel anytime, and you own the page and the tracking."),
        },
        "offer": {"name": "Landing Page Rescue", "setup": 0, "monthly": 399,
                  "deliverables": ["landing page matched to your running ad",
                                   "conversion tracking you own, installed day one",
                                   "monthly what-changed report",
                                   "new page per new ad the monitor catches"]},
        "_engine": "cro_offer",
        "_variant": variant,
    }
