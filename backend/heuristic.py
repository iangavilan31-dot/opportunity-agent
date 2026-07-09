"""
Zero-dependency rule-based scoring + workflow extraction.

Used as a fallback when ANTHROPIC_API_KEY is not set, so the pipeline still
ranks opportunities and produces usable workflow lists. When the API key is
present, scorer.py uses Claude Haiku instead for sharper results.
"""
import re
from niches import detect_niche, niche_label

# Title keywords → base points (max ~45)
TITLE_SIGNALS = {
    "scheduling": 30, "scheduler": 30, "dispatch": 28, "dispatcher": 28,
    "coordinator": 26, "coordination": 24, "intake": 28,
    "data entry": 32, "administrative": 22, "admin": 20,
    "front desk": 22, "receptionist": 22, "booking": 26,
    "reservations": 26, "recruiting coordinator": 30, "talent coordinator": 28,
    "patient care": 26, "patient coordinator": 26, "client service": 22,
    "operations assistant": 26, "operations coordinator": 28,
    "office coordinator": 24, "office manager": 20, "executive assistant": 22,
    "processing": 24, "billing": 22, "onboarding": 24, "bdc": 26,
    "service desk": 24, "transaction coordinator": 30, "loan processing": 26,
    "policy administration": 24, "reporting": 22, "membership": 22,
    "admissions": 24, "authorization": 24, "sales support": 22,
    "sales development": 22, "account coordinator": 26,
}

# Description keyword → points (capped per category to avoid runaway)
DESC_SIGNALS = {
    # scheduling / coordination
    "schedule": 6, "scheduling": 6, "reschedul": 5, "appointment": 5,
    "calendar": 5, "confirm": 4, "reminder": 6, "route": 4, "dispatch": 5,
    "coordinate": 5, "coordination": 5,
    # follow-up
    "follow up": 7, "follow-up": 7, "following up": 6, "reach out": 4,
    "chase": 5, "nudge": 4, "no-show": 4, "missed appointment": 4,
    # data / records
    "data entry": 8, "enter": 4, "entering": 4, "update records": 6,
    "update": 3, "records": 3, "crm": 6, "ats": 6, "database": 4,
    "spreadsheet": 6, "transfer data": 7, "reconcile": 5,
    # reporting
    "report": 5, "reports": 5, "reporting": 5, "compile": 5,
    "generate": 3, "weekly report": 6, "monthly report": 6,
    # intake / paperwork / docs
    "intake": 6, "paperwork": 5, "documents": 4, "document": 3,
    "verify": 4, "verification": 4, "process": 3, "processing": 3,
    "onboard": 5, "onboarding": 5, "request list": 5, "checklist": 4,
    # billing
    "invoice": 5, "billing": 4, "payment": 4, "estimates": 3,
    # comms
    "email": 3, "inbound": 3, "confirmation": 4, "status update": 6,
    "recurring": 5, "high volume": 6, "high-volume": 6,
}

CATEGORY_KEYWORDS = {
    "scheduling": ["schedule", "scheduling", "appointment", "calendar", "dispatch", "route", "booking", "reservation"],
    "recruiting": ["candidate", "ats", "interview", "recruit", "talent", "applicant"],
    "crm": ["crm", "salesforce", "hubspot", "pipeline", "record", "database"],
    "intake": ["intake", "new patient", "new client", "application", "onboard", "admission"],
    "reporting": ["report", "compile", "analytics", "dashboard", "summary"],
    "data_entry": ["data entry", "enter", "transfer data", "reconcile", "post charges", "claims"],
    "communication": ["follow up", "follow-up", "reminder", "confirmation", "status update", "outreach"],
    "admin": ["paperwork", "document", "filing", "administrative", "office"],
    "coordination": ["coordinate", "between", "vendor", "logistics", "milestone"],
}

# Phrases that suggest judgment/creative/technical work → dampen score
NEGATIVE_SIGNALS = [
    "software engineer", "developer", "designer", "architect", "creative director",
    "quota", "cold call", "close deals", "strategy", "negotiate contracts",
    "manage a team of", "p&l", "fundraising",
]


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def score_lead_heuristic(job_title: str, job_description: str, company_name: str = "") -> dict:
    title = (job_title or "").lower()
    desc = (job_description or "").lower()

    # Title score
    title_score = 0
    for kw, pts in TITLE_SIGNALS.items():
        if kw in title:
            title_score = max(title_score, pts)
    title_score = _clamp(title_score, 0, 45)

    # Description score (diminishing — count unique hits, weight, cap)
    desc_score = 0
    seen = set()
    for kw, pts in DESC_SIGNALS.items():
        if kw in desc and kw not in seen:
            desc_score += pts
            seen.add(kw)
    desc_score = _clamp(desc_score, 0, 45)

    # Signal/urgency bonus
    signal = 0
    if "high volume" in desc or "high-volume" in desc or "fast-paced" in desc or "fast paced" in desc:
        signal += 5
    if "growing" in desc or "grown" in desc or "scaling" in desc or "outpaced" in desc:
        signal += 5
    if desc.count("follow") >= 2:
        signal += 3
    if "small team" in desc or "small but busy" in desc:
        signal += 2
    signal = _clamp(signal, 0, 10)

    raw = title_score + desc_score + signal

    # Penalties
    for neg in NEGATIVE_SIGNALS:
        if neg in desc or neg in title:
            raw -= 20
            break

    score = _clamp(int(raw), 0, 100)

    # Pain category — pick the category with most keyword hits
    cat_hits = {}
    for cat, kws in CATEGORY_KEYWORDS.items():
        cat_hits[cat] = sum(desc.count(k) for k in kws)
    pain_category = max(cat_hits, key=cat_hits.get) if any(cat_hits.values()) else "admin"

    workflows = extract_workflows(job_description)
    pain_points = derive_pain_points(workflows, pain_category)

    niche = detect_niche(company_name, job_title, job_description)

    reasoning = (
        f"Title signal '{job_title}' + {len(seen)} repetitive-work indicators in the description. "
        f"Primary load looks like {pain_category.replace('_', ' ')}."
    )

    return {
        "score": score,
        "pain_category": pain_category,
        "pain_points": pain_points,
        "inferred_workflows": workflows,
        "score_reasoning": reasoning,
        "niche": niche,
        "niche_label": niche_label(niche),
        "_engine": "heuristic",
    }


# Verbs that begin a repetitive responsibility line
_ACTION_VERBS = [
    "schedule", "scheduling", "send", "sending", "follow up", "following up",
    "enter", "entering", "update", "updating", "generate", "generating",
    "coordinate", "coordinating", "process", "processing", "track", "tracking",
    "confirm", "confirming", "verify", "verifying", "reconcile", "compile",
    "compiling", "book", "booking", "dispatch", "post", "posting", "route",
    "manage", "managing", "handle", "handling", "collect", "collecting",
    "respond", "responding", "reach out", "order", "ordering",
]


def extract_workflows(job_description: str, max_workflows: int = 5) -> list[str]:
    """Pull concrete repetitive workflows from responsibility bullet lines."""
    if not job_description:
        return []

    # Split into candidate lines (bullets, newlines, sentences)
    lines = re.split(r"[\n•\-•]|(?<=[.;])\s+", job_description)
    workflows = []
    for line in lines:
        clean = line.strip().strip("-•* ").strip()
        if len(clean) < 12 or len(clean) > 140:
            continue
        low = clean.lower()
        if any(low.startswith(v) or f" {v} " in f" {low} " for v in _ACTION_VERBS):
            # Normalize to a short phrase
            phrase = clean[0].upper() + clean[1:]
            # Trim trailing clauses for brevity
            phrase = re.split(r"\s+(?:across|throughout|using|via|into our|in our)\s+", phrase)[0]
            phrase = phrase.rstrip(".,;")
            if phrase and phrase not in workflows:
                workflows.append(phrase)
        if len(workflows) >= max_workflows:
            break

    return workflows[:max_workflows]


def derive_pain_points(workflows: list[str], category: str) -> list[str]:
    base = {
        "scheduling": "Manual appointment scheduling and confirmation eats hours daily",
        "recruiting": "Candidate scheduling and ATS updates are time-heavy and error-prone",
        "crm": "Keeping CRM records current after every touch is constant overhead",
        "intake": "New client/patient intake involves repetitive forms and data entry",
        "reporting": "Recurring reports are compiled manually each week/month",
        "data_entry": "High-volume data entry between systems is slow and error-prone",
        "communication": "Follow-up reminders slip through the cracks when the team is busy",
        "admin": "Repetitive admin work is pulling the team away from higher-value tasks",
        "coordination": "Coordinating between multiple parties creates constant back-and-forth",
    }
    points = [base.get(category, base["admin"])]
    if any("follow" in w.lower() for w in workflows):
        points.append("Inconsistent follow-up likely costs leads/revenue")
    if any("report" in w.lower() for w in workflows):
        points.append("Manual reporting is repetitive and automatable")
    if any(("enter" in w.lower() or "update" in w.lower()) for w in workflows):
        points.append("Duplicate data entry across systems")
    return points[:4]
