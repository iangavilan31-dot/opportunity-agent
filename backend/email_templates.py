"""
Template-based email suite generation — used when ANTHROPIC_API_KEY is not set.

Produces specific, non-spammy outreach by slotting the company's actual job
title and extracted workflows into proven cold-email structures. Multiple
variants rotate to avoid sameyness across a batch. When the API key is present,
email_gen.py uses Claude Sonnet for sharper, fully bespoke copy.
"""
import random
import hashlib
from niches import get_pack


def _variant(seed: str, options: list) -> str:
    """Deterministically pick one option from a list based on a stable seed.
    Same company always gets the same variant (consistent across follow-ups),
    but different companies spread across the pool — so a batch isn't identical."""
    if not options:
        return ""
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return options[h % len(options)]


def _article(word: str) -> str:
    return "an" if word and word[0].lower() in "aeiou" else "a"


def _first_name(contact_name: str) -> str:
    if contact_name and contact_name.strip():
        return contact_name.strip().split()[0]
    return "there"


def _workflow_phrase(workflows: list[str]) -> str:
    """Turn extracted workflows into a natural inline phrase."""
    cleaned = []
    for w in workflows[:3]:
        w = w.lower().strip()
        # shorten "schedule phone screens and interviews..." → "scheduling interviews"
        for verb, noun in [
            ("schedul", "scheduling"), ("send", "sending reminders"),
            ("follow", "follow-up"), ("enter", "data entry"),
            ("updat", "CRM updates"), ("generat", "reporting"),
            ("coordinat", "coordination"), ("process", "processing"),
            ("track", "tracking"), ("confirm", "confirmations"),
            ("verif", "verification"), ("book", "booking"),
            ("compil", "report compiling"),
        ]:
            if w.startswith(verb) or verb in w[:14]:
                cleaned.append(noun)
                break
    # dedupe, keep order
    seen, out = set(), []
    for c in cleaned:
        if c not in seen:
            out.append(c); seen.add(c)
    if not out:
        out = ["scheduling", "follow-ups", "data entry"]
    if len(out) == 1:
        return out[0]
    if len(out) == 2:
        return f"{out[0]} and {out[1]}"
    return f"{out[0]}, {out[1]}, and {out[2]}"


def _two_workflows(workflows: list[str]) -> tuple[str, str]:
    phrase = _workflow_phrase(workflows)
    parts = phrase.replace(", and ", ", ").replace(" and ", ", ").split(", ")
    a = parts[0] if parts else "scheduling"
    b = parts[1] if len(parts) > 1 else "follow-ups"
    return a, b


SUBJECT_TEMPLATES = [
    "a thought on your {job_title} workload",
    "your {job_title} opening at {company}",
    "{company} + the {wf_a} load",
    "quick idea for {company}",
    "the {wf_a} side of your {job_title} role",
]


def generate_suite_template(
    company_name: str,
    contact_name: str,
    contact_title: str,
    job_title: str,
    inferred_workflows: list[str],
    pain_points: list[str],
    company_profile: dict,
    niche_id: str = "generic",
) -> dict:
    fn = _first_name(contact_name)
    pack = get_pack(niche_id)

    # Prefer the niche's known workflows (they reference real tasks/tools);
    # fall back to extracted workflows.
    niche_workflows = pack.get("core_workflows", [])
    wf_a = niche_workflows[0] if niche_workflows else _two_workflows(inferred_workflows)[0]
    wf_b = niche_workflows[1] if len(niche_workflows) > 1 else _two_workflows(inferred_workflows)[1]
    wf_phrase = _workflow_phrase(inferred_workflows)

    tools = pack.get("tools", [])
    tool_ref = pack.get("primary_tool") or (tools[0] if tools else None)
    noun = pack.get("noun", "small teams")
    pain_narrative = pack.get("pain_narrative", "")
    offer = pack.get("offer", {})
    value_prop = offer.get("pitch", "")
    short_wf = pack.get("short_workflows", ["scheduling", "follow-ups", "reporting"])
    sw_a, sw_b = short_wf[0], (short_wf[1] if len(short_wf) > 1 else "follow-ups")
    outcome = pack.get("outcome", "")

    # ── Subject (stable per company, varied across the batch) ────────────
    subject_angles = pack.get("subject_angles") or [a for a in SUBJECT_TEMPLATES]
    subject = _variant(company_name + "subj", subject_angles).format(
        job_title=job_title, company=company_name, wf_a=wf_a,
        article=_article(job_title),
    )

    # ── Short initial email — human cadence, no "Hi there", one tool, give-first ──
    seed = company_name or job_title
    # Greeting: real name → "Hi {name},". No name → greet the business by name
    # (Ian, 2026-07-10: every email greets; "Hi there" stays banned as a
    # mass-send tell, so the company-team greeting is the fallback).
    has_name = bool(contact_name and contact_name.strip())
    greeting = f"Hi {fn},\n\n" if has_name else f"Hi {company_name} team,\n\n"
    tool_tail = _variant(seed + "tool", [
        f", and {tool_ref} never quite stays current",
        f" — and keeping {tool_ref} updated falls to the bottom of the list",
        f", with {tool_ref} always a step behind",
        f" (and {tool_ref} only as current as someone has time to make it)",
    ]) if tool_ref else ""

    opener = _variant(seed + "open", [
        f"Saw {company_name} is hiring {_article(job_title)} {job_title} — usually a sign {sw_a} and {sw_b} are starting to eat the week{tool_tail}.",
        f"Noticed the {job_title} opening at {company_name}. In my experience a role like that means {sw_a} and {sw_b} have outgrown what the team can keep up with{tool_tail}.",
        f"Came across your {job_title} role at {company_name} — usually that points to {sw_a} and {sw_b} quietly taking over the day{tool_tail}.",
    ])

    middle = _variant(seed + "mid", [
        f"Most of that's rule-based and repeatable. {outcome}",
        f"The repetitive part of that follows clear rules, so it's a good fit for automation. {outcome}",
        f"A lot of that runs on predictable patterns. {outcome}",
    ])

    cta = _variant(seed + "cta", [
        f"I roughed out what that'd look like for {company_name} specifically — want me to send it over? No call needed unless it's useful.",
        f"Happy to map out exactly what I'd automate for {company_name} and send it across — worth a look?",
        f"I can put together a short, specific breakdown for {company_name} — want to see it before we even talk?",
    ])

    email_body = f"""{greeting}{opener}

{middle}

{cta}

— [Your name]"""

    # ── Long version ─────────────────────────────────────────────────────
    tool_line = f" {tool_ref} usually holds the data, but the manual steps around it — the chasing, the re-keying — are the real time sink." if tool_ref else ""
    email_long = f"""{greeting}{opener}

{pain_narrative}{tool_line}

Most of that follows predictable rules, so it can be handed off to automation cleanly. {outcome} A new hire still spends their first weeks on the repetitive parts; automating those first means the person you bring on focuses on judgment and relationships from day one.

I've roughed out what I'd automate for {company_name} specifically. Happy to send it over — no charge, no pitch — and you can decide if a call's even worth it.

— [Your name]"""

    # ── Mini-audit — reads like a person wrote it, names one tool ─────────
    roi = pack.get("roi_points", [])
    audit_lines = [f"A quick breakdown for {company_name} — the three workflows I'd automate first, based on your {job_title} posting:\n"]
    for point in roi:
        audit_lines.append(f"• {point['workflow']} — {point['mechanism'].lower()}. {point['impact']}")
    if tool_ref:
        audit_lines.append(
            f"\nAll of this runs alongside {tool_ref} rather than replacing it — I'm automating the manual steps around your existing setup, not asking you to switch tools."
        )
    audit_lines.append(
        f"\nRolled up, that's most of {_article(job_title)} {job_title}'s workload handled automatically — the new hire (or your existing team) spends their time on the judgment calls instead. I'd package this as the \"{offer.get('name', 'automation setup')}\" (${offer.get('setup', 0):,} to build + ${offer.get('monthly', 0)}/mo to run). Happy to walk through it whenever's useful."
    )
    mini_audit = "\n".join(audit_lines)

    # ── Follow-ups ───────────────────────────────────────────────────────
    fu_anchor = short_wf[0]
    follow_up_1 = f"""{greeting}Circling back on this — figured it might've gotten buried.

Short version: automating {sw_a} is usually the fastest win for {noun}, and it's normally where the time (and money) is leaking. I already put the breakdown together for {company_name}; just say the word and I'll send it over.

— [Your name]"""

    follow_up_2 = f"""{greeting}Last one from me — if taking the {fu_anchor} load off your team isn't a priority right now, no worries at all. I'll leave it here.

— [Your name]"""

    breakup_email = f"""{greeting}Closing the loop on this one. Sounds like the timing isn't right, which is completely fair.

If {sw_a} ever turns into a real headache down the road, my door's open. Either way, good luck filling the {job_title} role.

— [Your name]"""

    # ── Objection responses (niche-specific) ─────────────────────────────
    objection_responses = dict(pack.get("objections", {}))
    # Always include the universal "send me info" handler
    objection_responses.setdefault(
        "Send me some info",
        f"Already on it — I put together a short breakdown specific to {company_name} (the actual workflows I'd automate and the rough time saved). Sending it your way now; no deck, no fluff.",
    )

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
        "_engine": "template",
        "_niche": niche_id,
    }


def build_profile_heuristic(
    company_name: str, company_domain: str, job_title: str,
    job_description: str, pain_points: list[str], inferred_workflows: list[str],
) -> dict:
    """Lightweight company profile when no API key is available."""
    desc = (job_description or "").lower()
    size = "small (10-50)"
    for hint, label in [
        ("1,200", "mid (50-200)"), ("800", "small (10-50)"),
        ("boutique", "micro (1-10)"), ("small team", "micro (1-10)"),
        ("small but busy", "micro (1-10)"),
    ]:
        if hint in desc:
            size = label
            break

    dm = "founder or owner"
    if "metro" in desc or "locations" in desc or "1,200" in desc:
        dm = "operations director or office manager"

    wf_phrase = _workflow_phrase(inferred_workflows)
    return {
        "company_description": f"{company_name} appears to be a {size.split(' ')[0]} operation hiring a {job_title} to handle growing operational load.",
        "company_size_estimate": size,
        "operational_maturity": "scaling",
        "automation_readiness": "medium",
        "decision_maker_profile": dm,
        "key_pain_narrative": f"Hiring a {job_title} signals that {wf_phrase} have outgrown the current team's capacity — classic automation territory.",
        "personalization_hooks": [f"Hiring a {job_title}"] + inferred_workflows[:2],
        "urgency_signals": (["growing fast"] if ("grow" in desc or "fast" in desc) else []),
        "_engine": "heuristic",
    }
