"""
offer_router — finding profile → machine → offer module. Research report §13 L3.

One discovery engine, many machines. Each lead gets exactly one `machine`;
the router is the single place that priority lives, so morning_batch and the
HUD never disagree about what a lead is.

Priority (report §13 L2): burning_ads > parked_domain > dead_site (rescue) >
web_design (the original track). LOCAL-above-likelihood law survives INSIDE
each machine bucket (commit a1af4e8) — routing never demotes a local lead
below a non-local one of the same machine.

Machines present today: burning_ads (live), web_design (live). parked/rescue
enter when their feeds (feed_nrd / feed_deadsite) exist — the router already
knows their slot in the order so nothing reshuffles later.
"""
from __future__ import annotations

import json

# machine name -> (priority rank, offer module name)
MACHINES = {
    "burning_ads": (0, "cro_offer"),
    "parked_domain": (1, "parked_offer"),      # feed_nrd pending (E4)
    "dead_site": (2, "rescue_offer"),          # feed_deadsite pending
    "web_design": (3, "web_offer"),
}

PSI_SLOW = 40  # report §13: burning_ads = ad_active AND psi_mobile < 40


def route(lead) -> str:
    """Which machine owns this lead, from its detection columns. Pure."""
    sb = {}
    try:
        sb = json.loads(lead.score_breakdown or "{}")
    except Exception:
        pass

    ad_active = getattr(lead, "ad_active", None)
    psi = getattr(lead, "psi_mobile", None)
    if ad_active == 1 and psi is not None and psi < PSI_SLOW:
        return "burning_ads"
    # Slow-but-not-advertising and advertising-but-fast both stay web_design:
    # the CRO pitch's proof ("your ad money leaks here") requires BOTH halves.
    findings = {f.get("code") for f in sb.get("findings", [])}
    if "parked_domain" in findings:
        return "parked_domain"
    if "dead_site" in findings:
        return "dead_site"
    return "web_design"


def machine_priority(machine: str) -> int:
    return MACHINES.get(machine, (99, ""))[0]


def offer_module(machine: str) -> str:
    return MACHINES.get(machine, (99, "web_offer"))[1]


def sort_key(lead, is_local: bool, likelihood: float):
    """The batch ranking key: machine first, then the LOCAL law, then score."""
    return (machine_priority(getattr(lead, "machine", None) or route(lead)),
            0 if is_local else 1,
            -likelihood)


def reroute_all(db, log=print) -> dict:
    """Recompute machine for every lead from current detection columns."""
    from db import Lead
    counts: dict[str, int] = {}
    for lead in db.query(Lead).filter(Lead.source == "website_autopilot").all():
        m = route(lead)
        if lead.machine != m:
            lead.machine = m
        counts[m] = counts.get(m, 0) + 1
    db.commit()
    log(f"routing: {counts}")
    return counts
