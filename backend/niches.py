"""
Niche intelligence — the core IP of the system.

Each vertical has a knowledge pack: detection signals, the actual software these
companies run, the repetitive workflows that exist, realistic ROI framing, the
objections they'll raise, and a productized offer with pricing. This is what
makes outreach read as *researched* instead of generic — naming "Dentrix recall
lists" or "Bullhorn submittals" signals you actually understand their world.

detect_niche() classifies a lead from company name + job title + description.
"""
import re


NICHE_PACKS = {
    "recruiting": {
        "label": "Recruiting / Staffing",
        "noun": "recruiting teams",
        "match": {
            "title": ["recruiting", "recruiter", "talent", "staffing", "sourcing"],
            "desc": ["candidate", "ats", "bullhorn", "greenhouse", "lever", "submittal",
                     "placement", "interview", "applicant", "job board", "hiring manager"],
            "company": ["staffing", "recruiting", "talent", "search partners", "headhunt"],
        },
        "tools": ["Bullhorn", "Greenhouse", "Lever", "JobDiva", "Crelate"],
        "core_workflows": [
            "scheduling candidate interviews across multiple calendars",
            "chasing candidates who go quiet mid-process",
            "keeping the ATS updated after every stage",
            "sending submittal and status updates to clients",
            "compiling weekly pipeline reports",
        ],
        "pain_narrative": "Recruiters spend roughly 40% of their week on coordination — scheduling, chasing candidates, and ATS hygiene — instead of selling and closing placements. When they're busy, candidates go cold and submittals slow down.",
        "roi_points": [
            {"workflow": "Interview scheduling", "mechanism": "Automated self-scheduling links + calendar sync across candidate, recruiter, and client", "impact": "5–8 hrs/week back per recruiter"},
            {"workflow": "Candidate nurture", "mechanism": "Rule-based follow-up sequences so no candidate goes 48h without contact", "impact": "Fewer cold candidates, faster submittals"},
            {"workflow": "ATS hygiene + reporting", "mechanism": "Auto-logging stage changes and generating pipeline reports", "impact": "3–5 hrs/week, cleaner data"},
        ],
        "objections": {
            "Our ATS already handles this": "Your ATS stores data — it doesn't chase a candidate who's gone quiet or juggle three calendars to book an interview. I automate the work *around* the ATS, and keep it cleaner as a side effect.",
            "We're just going to hire a coordinator": "Makes sense — and automating the scheduling and follow-up first means whoever you hire spends their time on relationships and submittals, not calendar tetris. Most agencies do both.",
            "Recruiting is too relationship-driven to automate": "Completely agree — that's exactly why you want the *repetitive* parts automated. The relationship work stays human; the scheduling and status-chasing don't need to be.",
        },
        "offer": {
            "name": "Recruiting Ops Autopilot",
            "deliverables": ["Automated interview scheduling + calendar sync", "Candidate nurture sequences", "ATS auto-sync + weekly pipeline reports", "Client submittal updates"],
            "setup": 2500, "monthly": 500,
            "pitch": "Take the coordination load off your recruiters so they spend their day placing, not scheduling.",
        },
        "subject_angles": [
            "your {job_title} opening + scheduling load",
            "quick idea for {company}'s recruiters",
            "the scheduling side of recruiting at {company}",
        ],
    },

    "dental_medical": {
        "label": "Dental / Medical",
        "noun": "healthcare practices",
        "match": {
            "title": ["patient", "dental", "medical", "clinical", "front desk", "care coordinator",
                      "scheduling specialist", "authorization", "admissions"],
            "desc": ["patient", "dentrix", "eaglesoft", "opendental", "epic", "kareo", "ehr", "emr",
                     "insurance verification", "recall", "no-show", "practice management", "intake form",
                     "appointment reminder", "therapy", "clinic", "providers", "caregiver"],
            "company": ["dental", "medical", "clinic", "health", "therapy", "wellness center",
                        "pediatric", "orthodont", "behavioral", "care", "vet"],
        },
        "tools": ["Dentrix", "Eaglesoft", "Open Dental", "Epic", "Kareo", "SimplePractice"],
        "core_workflows": [
            "sending appointment reminders and confirmations",
            "working the recall list for patients due for visits",
            "verifying insurance before appointments",
            "rebooking no-shows and cancellations",
            "processing new-patient intake forms",
        ],
        "pain_narrative": "Every no-show is $150–300 of lost chair time, and recall lists go stale the moment the front desk gets busy. Insurance verification and intake eat hours that should go to patients.",
        "roi_points": [
            {"workflow": "No-show reduction", "mechanism": "Multi-touch reminders (text + email) with easy reschedule, plus automatic rebooking of cancellations", "impact": "Cutting no-shows 30% often recovers thousands/month in otherwise-lost appointments"},
            {"workflow": "Recall reactivation", "mechanism": "Automated outreach to patients overdue for cleanings/checkups", "impact": "Fills the schedule from patients you already have"},
            {"workflow": "Insurance + intake", "mechanism": "Digital intake + automated eligibility checks before the visit", "impact": "5–8 hrs/week off the front desk"},
        ],
        "objections": {
            "Our practice software already sends reminders": "Basic reminders, yes — but it won't reactivate a stale recall list, auto-rebook a cancellation, or two-way text a patient who replies. That's where the recovered revenue is.",
            "Our front desk handles this": "They do — until it's busy, and that's exactly when recall and rebooking slip. Automating the repetitive outreach lets them focus on the patients in front of them.",
            "We're a small practice": "Smaller practices feel it most — there's no spare admin to absorb it, so it falls on the people who should be with patients. It scales down well.",
        },
        "offer": {
            "name": "Patient Flow Engine",
            "deliverables": ["Multi-touch appointment reminders + smart rebooking", "Automated recall reactivation", "Digital intake + insurance verification", "Post-visit review requests"],
            "setup": 3000, "monthly": 600,
            "pitch": "Fewer no-shows, a fuller recall schedule, and a front desk that isn't drowning in reminders.",
        },
        "subject_angles": [
            "Question about patient scheduling at {company}",
            "a thought on your {job_title} workload",
            "{company}'s no-show + recall load",
        ],
    },

    "property_management": {
        "label": "Property Management",
        "noun": "property management companies",
        "match": {
            "title": ["property", "leasing", "operations assistant", "operations coordinator",
                      "tenant", "resident"],
            "desc": ["appfolio", "buildium", "yardi", "propertyware", "tenant", "lease", "rent",
                     "maintenance request", "owner report", "units", "showing", "property manage"],
            "company": ["property", "realty", "management", "residential", "apartment", "leasing"],
        },
        "tools": ["AppFolio", "Buildium", "Yardi", "Propertyware"],
        "core_workflows": [
            "coordinating maintenance requests between tenants and vendors",
            "sending rent reminders and chasing late payments",
            "syndicating listings across Zillow, Apartments.com, etc.",
            "generating monthly owner reports",
            "scheduling showings and processing applications",
        ],
        "pain_narrative": "Maintenance coordination is endless back-and-forth, late rent has to be chased every month, and owner reports get built by hand. The admin load scales linearly with units — until something breaks.",
        "roi_points": [
            {"workflow": "Rent + late-payment follow-up", "mechanism": "Automated reminder cadence and late-payment escalation", "impact": "Faster collections, fewer awkward calls"},
            {"workflow": "Maintenance coordination", "mechanism": "Auto-routing requests to vendors with status updates to tenants", "impact": "4–6 hrs/week and happier tenants"},
            {"workflow": "Owner reporting", "mechanism": "Auto-generated monthly owner reports", "impact": "Hours back at month-end"},
        ],
        "objections": {
            "AppFolio already does this": "AppFolio is the system of record — it stores the data but won't proactively chase late rent, coordinate a vendor, or build a polished owner report on its own. I automate the work on top of it.",
            "We just need another assistant": "Often the repetitive 60% — reminders, maintenance routing, reports — can be automated, so the assistant you hire handles the judgment calls instead of the busywork.",
        },
        "offer": {
            "name": "Property Ops Suite",
            "deliverables": ["Automated rent reminders + late-payment follow-up", "Maintenance request routing + tenant updates", "Owner report generation", "Listing syndication"],
            "setup": 2500, "monthly": 500,
            "pitch": "Automate the rent-chasing, maintenance coordination, and owner reporting that scale with every unit you add.",
        },
        "subject_angles": [
            "Question about operations at {company}",
            "your {job_title} opening at {company}",
            "{company}'s maintenance + rent follow-up load",
        ],
    },

    "legal_intake": {
        "label": "Legal / Intake",
        "noun": "intake-driven firms",
        "match": {
            "title": ["legal", "intake", "case", "paralegal", "law"],
            "desc": ["clio", "mycase", "filevine", "litify", "intake", "client", "case management",
                     "consultation", "attorney", "law firm", "retainer", "personal injury"],
            "company": ["law", "legal", "attorney", "injury", "firm llp", "& associates"],
        },
        "tools": ["Clio", "MyCase", "Filevine", "Litify"],
        "core_workflows": [
            "responding to and qualifying inbound leads",
            "scheduling consultations with attorneys",
            "chasing intake paperwork until it's returned",
            "following up with leads who haven't signed",
            "sending case-milestone updates to clients",
        ],
        "pain_narrative": "In intake-driven practices, speed-to-lead wins cases — a lead that waits an hour is often gone. Slow or inconsistent follow-up means signed cases (each worth thousands) walk out the door.",
        "roi_points": [
            {"workflow": "Speed-to-lead", "mechanism": "Instant automated response to every inquiry, day or night, with consultation booking", "impact": "Higher sign rate — even one extra case can be worth thousands"},
            {"workflow": "Intake nurture", "mechanism": "Automated follow-up sequence for leads who haven't signed or returned paperwork", "impact": "Recovers cases that would otherwise go cold"},
            {"workflow": "Paperwork collection", "mechanism": "Automated document requests + reminders", "impact": "Faster file completion, less chasing"},
        ],
        "objections": {
            "We have a paralegal/intake person for this": "And they're great during business hours — but leads come in nights and weekends, and follow-up slips when things are busy. Automating speed-to-lead means you never lose a case to a slow response.",
            "Our cases are too complex to automate": "The casework stays with your team — I only automate the intake funnel: instant response, scheduling, and paperwork follow-up. That's pure conversion, not legal work.",
        },
        "offer": {
            "name": "Intake Conversion System",
            "deliverables": ["Instant lead response + qualification", "Automated consultation scheduling", "Intake nurture sequences", "Document collection + reminders"],
            "setup": 3500, "monthly": 700,
            "pitch": "Respond to every lead in seconds and follow up relentlessly, so you sign the cases you're currently losing to slow follow-up.",
        },
        "subject_angles": [
            "Question about your intake process at {company}",
            "a thought on your {job_title} workload",
            "Speed-to-lead at {company}",
        ],
    },

    "logistics": {
        "label": "Logistics / Freight",
        "noun": "freight and logistics operations",
        "match": {
            "title": ["dispatch", "logistics", "freight", "carrier", "load", "transportation"],
            "desc": ["tms", "carrier", "load", "shipment", "freight", "bol", "pod", "broker",
                     "dispatch", "driver", "warehouse", "delivery"],
            "company": ["logistics", "freight", "transport", "trucking", "3pl", "supply chain"],
        },
        "tools": ["McLeod", "DAT", "Truckstop", "Aljex"],
        "core_workflows": [
            "sending dispatch confirmations to carriers",
            "checking in on shipments and updating customers",
            "chasing missing paperwork (BOLs, PODs)",
            "entering load and carrier details into the TMS",
            "generating daily load board reports",
        ],
        "pain_narrative": "Dispatchers live on the phone doing check-in calls, and missing paperwork delays billing — which delays cash. Status updates to customers are constant and manual.",
        "roi_points": [
            {"workflow": "Carrier check-ins", "mechanism": "Automated check-call requests + status capture via text", "impact": "Frees dispatchers from repetitive calls"},
            {"workflow": "Document collection", "mechanism": "Automated BOL/POD requests + reminders", "impact": "Faster billing, shorter cash cycle"},
            {"workflow": "Customer status updates", "mechanism": "Automated shipment status notifications", "impact": "Fewer 'where's my freight' calls"},
        ],
        "objections": {
            "Our TMS tracks all this": "The TMS records it — it doesn't make the check-call, chase the missing POD, or proactively update the customer. That's the manual work I automate around it.",
            "Freight moves too fast to automate": "That's the case *for* automating — the faster things move, the more a missed check-in or late POD costs you. Automation keeps pace better than a dispatcher juggling 30 loads.",
        },
        "offer": {
            "name": "Dispatch Automation",
            "deliverables": ["Automated carrier check-ins", "BOL/POD collection + reminders", "Customer status notifications", "TMS data entry assist"],
            "setup": 2500, "monthly": 500,
            "pitch": "Automate the check-calls and paperwork chasing so dispatchers move more loads and you bill faster.",
        },
        "subject_angles": [
            "Question about dispatch at {company}",
            "your {job_title} opening at {company}",
            "{company}'s check-call + paperwork load",
        ],
    },

    "home_services": {
        "label": "Home Services",
        "noun": "home-services businesses",
        "match": {
            "title": ["scheduling coordinator", "dispatcher", "service coordinator", "office coordinator",
                      "bdc", "production coordinator"],
            "desc": ["servicetitan", "housecall", "jobber", "technician", "service call", "hvac",
                     "plumbing", "roofing", "landscaping", "pool", "estimate", "field service",
                     "route", "dispatch", "seasonal"],
            "company": ["hvac", "plumbing", "roofing", "landscaping", "pool", "electric", "cleaning",
                        "air", "heating", "pest", "window", "garage"],
        },
        "tools": ["ServiceTitan", "Housecall Pro", "Jobber"],
        "core_workflows": [
            "scheduling and routing service calls",
            "confirming appointments by call and text",
            "following up on outstanding estimates",
            "sending invoices and chasing payments",
            "booking recurring/seasonal maintenance",
        ],
        "pain_narrative": "Unbooked tech hours are lost revenue, estimates go cold without follow-up, and payments have to be chased. Seasonal maintenance rebooking is predictable revenue that slips through the cracks.",
        "roi_points": [
            {"workflow": "Estimate follow-up", "mechanism": "Automated follow-up sequence on every open estimate", "impact": "Recovers jobs that would otherwise go cold — often the fastest ROI"},
            {"workflow": "Scheduling + confirmations", "mechanism": "Automated booking, confirmations, and reschedules to keep techs full", "impact": "Fewer gaps in the schedule"},
            {"workflow": "Maintenance rebooking", "mechanism": "Automated seasonal/recurring service outreach", "impact": "Predictable recurring revenue"},
        ],
        "objections": {
            "ServiceTitan does our scheduling": "It schedules what's booked — it won't chase a cold estimate, recover an unpaid invoice, or rebook last season's maintenance customers. That's the revenue I help recover.",
            "We're booked out already": "Then the win is on the back end — estimate follow-up and maintenance rebooking — so you're not leaving money on the table when things slow down.",
        },
        "offer": {
            "name": "Service Booking Engine",
            "deliverables": ["Automated dispatch confirmations + reminders", "Estimate follow-up sequences", "Invoice + payment follow-up", "Seasonal maintenance rebooking"],
            "setup": 2500, "monthly": 500,
            "pitch": "Keep techs booked, recover cold estimates, and turn seasonal maintenance into predictable revenue.",
        },
        "subject_angles": [
            "Question about scheduling at {company}",
            "a thought on your {job_title} workload",
            "{company}'s estimate follow-up",
        ],
    },

    "professional_services": {
        "label": "Professional Services",
        "noun": "service businesses",
        "match": {
            "title": ["account coordinator", "client service", "project coordinator", "client services",
                      "onboarding", "reporting", "service desk", "client reporting"],
            "desc": ["hubspot", "asana", "quickbooks", "connectwise", "agency", "client", "deliverable",
                     "report", "onboarding", "bookkeeping", "accounting", "msp", "ticket", "engagement"],
            "company": ["agency", "marketing", "consulting", "accounting", "bookkeeping", "advisors",
                        "cpa", "it services", "digital", "studio", "partners"],
        },
        "tools": ["HubSpot", "Asana", "QuickBooks", "ConnectWise", "Monday"],
        "core_workflows": [
            "scheduling client meetings and check-ins",
            "compiling recurring client reports",
            "chasing clients for assets, docs, and approvals",
            "onboarding new clients",
            "keeping the CRM updated after every touch",
        ],
        "pain_narrative": "Recurring reporting and chasing clients for assets eats hours that should be billable. Onboarding is repetitive, and CRM hygiene falls behind whenever the team is busy with delivery.",
        "roi_points": [
            {"workflow": "Recurring reporting", "mechanism": "Auto-compiled reports from your tools on a schedule", "impact": "Reclaims billable hours each week"},
            {"workflow": "Client onboarding", "mechanism": "Automated onboarding sequences + asset collection", "impact": "Faster, smoother starts"},
            {"workflow": "Asset/approval chasing", "mechanism": "Automated reminders until items are received", "impact": "Projects stop stalling on missing inputs"},
        ],
        "objections": {
            "We already use [tool] for this": "Good — I work *with* your stack, automating the manual steps between tools (the reporting, the chasing, the syncing). Usually the software you pay for can do more than it's set up to.",
            "Our work is too custom to automate": "The delivery stays custom — I only automate the repeatable wrapper around it: reporting, onboarding, and follow-up. That's where the billable hours leak.",
        },
        "offer": {
            "name": "Client Ops Automation",
            "deliverables": ["Automated recurring reporting", "Client onboarding sequences", "Asset + approval chasing", "CRM auto-sync"],
            "setup": 2500, "monthly": 500,
            "pitch": "Automate reporting, onboarding, and client chasing so your team spends its hours on billable work.",
        },
        "subject_angles": [
            "Question about your {job_title} role",
            "a thought on client ops at {company}",
            "{company}'s reporting + onboarding load",
        ],
    },

    "fitness_wellness": {
        "label": "Fitness / Wellness",
        "noun": "studios and gyms",
        "match": {
            "title": ["membership", "booking coordinator", "front desk", "studio", "member"],
            "desc": ["mindbody", "mariana", "vagaro", "class", "membership", "studio", "gym",
                     "no-show", "retention", "waitlist", "fitness", "session"],
            "company": ["fitness", "studio", "gym", "yoga", "pilates", "wellness", "spa", "crossfit"],
        },
        "tools": ["Mindbody", "Mariana Tek", "Vagaro"],
        "core_workflows": [
            "managing class bookings and waitlists",
            "sending class reminders and chasing no-shows",
            "reaching out to members whose attendance dropped",
            "following up on failed payments",
            "onboarding new members",
        ],
        "pain_narrative": "Churn is the silent killer — members drift away before anyone notices, retention outreach falls behind, and failed payments go uncollected. No-shows leave classes half-full.",
        "roi_points": [
            {"workflow": "Retention outreach", "mechanism": "Automated detection of dropping attendance + win-back sequences", "impact": "Directly reduces churn — the highest-leverage metric in fitness"},
            {"workflow": "Failed payment recovery", "mechanism": "Automated dunning sequence on failed charges", "impact": "Recovers revenue you've already earned"},
            {"workflow": "No-show recovery", "mechanism": "Reminders + waitlist auto-fill", "impact": "Fuller classes"},
        ],
        "objections": {
            "Mindbody handles our bookings": "Bookings, yes — but it won't notice a member whose attendance is dropping and win them back, or run a smart failed-payment recovery sequence. That's where retention revenue lives.",
            "Our community is what keeps members": "Exactly — automation makes sure no one slips away unnoticed, so your team can focus on the in-person community instead of watching attendance reports.",
        },
        "offer": {
            "name": "Member Retention Engine",
            "deliverables": ["Attendance-drop detection + win-back sequences", "Failed payment recovery", "No-show recovery + waitlist fill", "New member onboarding"],
            "setup": 2000, "monthly": 400,
            "pitch": "Catch churning members before they leave and recover failed payments automatically.",
        },
        "subject_angles": [
            "Question about member retention at {company}",
            "a thought on your {job_title} workload",
            "{company}'s churn + no-show load",
        ],
    },
}

# Generic fallback pack
GENERIC_PACK = {
    "label": "General Ops",
    "noun": "small teams",
    "tools": [],
    "core_workflows": [
        "scheduling and confirmations",
        "follow-up reminders",
        "data entry across systems",
        "recurring reporting",
    ],
    "pain_narrative": "Repetitive coordination, follow-up, and data entry are pulling the team away from higher-value work.",
    "roi_points": [
        {"workflow": "Scheduling", "mechanism": "Automated booking + confirmations", "impact": "5–8 hrs/week"},
        {"workflow": "Follow-up", "mechanism": "Rule-based follow-up sequences", "impact": "Nothing slips when busy"},
        {"workflow": "Reporting", "mechanism": "Auto-generated recurring reports", "impact": "2–4 hrs/week"},
    ],
    "objections": {
        "We're just going to hire someone": "Automating the repetitive parts first means whoever you hire spends their time on judgment work, not busywork. Most teams do both.",
        "We don't have budget": "Most of what I set up pays for itself in saved hours within a month or two — it's a shift in where the hours go, not a new cost.",
        "We already use software for this": "I work with your existing tools and automate the manual steps between them — the copy-paste, the reminders, the syncing.",
    },
    "offer": {
        "name": "Ops Automation Starter",
        "deliverables": ["Automated scheduling + confirmations", "Follow-up sequences", "Recurring reporting", "Data sync between tools"],
        "setup": 2000, "monthly": 400,
        "pitch": "Automate the repetitive scheduling, follow-up, and reporting so the team focuses on work that needs a person.",
    },
    "subject_angles": [
        "a thought on your {job_title} workload",
        "your {job_title} opening at {company}",
        "quick idea for {company}",
    ],
}


# Punchy 2-3 word workflow labels for inline use in email copy (the full
# core_workflows are too long to chain two together cleanly), plus one concrete,
# honestly-hedged outcome sentence per niche. Merged into the packs at load.
_SHORT_WF = {
    "recruiting": ["interview scheduling", "candidate follow-up", "ATS updates"],
    "dental_medical": ["appointment reminders", "recall outreach", "no-show rebooking"],
    "property_management": ["rent follow-up", "maintenance coordination", "owner reports"],
    "legal_intake": ["lead response", "consult scheduling", "intake paperwork"],
    "logistics": ["carrier check-ins", "paperwork chasing", "status updates"],
    "home_services": ["estimate follow-up", "appointment scheduling", "payment follow-up"],
    "professional_services": ["client reporting", "onboarding", "chasing approvals"],
    "fitness_wellness": ["retention outreach", "no-show recovery", "payment recovery"],
}
_OUTCOME = {
    "recruiting": "Automating the scheduling and follow-up usually hands each recruiter back 5–8 hours a week to actually place people.",
    "dental_medical": "Automated reminders and recall outreach typically cut no-shows by around a third and keep the schedule full from patients you already have.",
    "property_management": "Automating the rent and maintenance chasing usually frees up most of a part-time admin role.",
    "legal_intake": "Responding to every lead in seconds — even after hours — is often the difference between signing a case and losing it to a faster firm.",
    "logistics": "Automating the check-calls and POD collection frees up your dispatchers and gets invoices out faster.",
    "home_services": "Automated estimate follow-up alone usually recovers jobs that would've gone cold — typically the fastest payback.",
    "professional_services": "Automating the reporting and client chasing usually hands the team back several billable hours a week.",
    "fitness_wellness": "Automated win-back and failed-payment recovery usually pays for itself in retained members within a month or two.",
}
for _nid, _pack in NICHE_PACKS.items():
    _pack["short_workflows"] = _SHORT_WF.get(_nid, ["scheduling", "follow-ups", "reporting"])
    _pack["outcome"] = _OUTCOME.get(_nid, "Automating those pieces usually hands the team back 8–15 hours a week.")
    _pack["primary_tool"] = _pack["tools"][0] if _pack.get("tools") else None

GENERIC_PACK["short_workflows"] = ["scheduling", "follow-ups", "reporting"]
GENERIC_PACK["outcome"] = "Automating those pieces usually hands the team back 8–15 hours a week."
GENERIC_PACK["primary_tool"] = None


def detect_niche(company_name: str, job_title: str, job_description: str) -> str:
    """Return the best-matching niche id, or 'generic'."""
    name = (company_name or "").lower()
    title = (job_title or "").lower()
    desc = (job_description or "").lower()

    scores = {}
    for niche_id, pack in NICHE_PACKS.items():
        m = pack["match"]
        s = 0
        # Title hits weigh most, then company, then description
        for kw in m.get("title", []):
            if kw in title:
                s += 5
        for kw in m.get("company", []):
            if kw in name:
                s += 4
        for kw in m.get("desc", []):
            if kw in desc:
                s += 1
        scores[niche_id] = s

    best = max(scores, key=scores.get) if scores else None
    # Require a minimum confidence; otherwise generic
    if best and scores[best] >= 4:
        return best
    return "generic"


def get_pack(niche_id: str) -> dict:
    return NICHE_PACKS.get(niche_id, GENERIC_PACK)


def niche_label(niche_id: str) -> str:
    return get_pack(niche_id)["label"]
