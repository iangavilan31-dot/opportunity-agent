"""
waste_math — the number that opens the conversation. Research report §13 L4.

Renders the waste arithmetic for a burning_ads lead: their verified CPC band
(LocaliQ 2025, 3,211-campaign dataset), their real PSI mobile score, and a
conservative estimate of what a slow page costs per 100 paid clicks.

FTC hygiene (report §18 named risk): every projected number is labeled an
estimate; the only unlabeled facts are the ones we measured (their ad is
running; their PSI score) or cite (the CPC benchmark). We never claim to know
their actual spend or click volume — the math is expressed per-100-clicks so
it stays honest at any budget.
"""
from __future__ import annotations

# Category CPC anchors — LocaliQ 2025 home-services benchmarks + report §7
# table [VERIFIED]. Only categories with a verified anchor get a $ line;
# everything else falls back to the qualitative version.
CPC = {
    "plumbing": 10.49, "plumber": 10.49,
    "electrician": 12.18, "electric": 12.18,
    "hvac": 9.30,
    "landscaping": 8.76, "landscaper": 8.76,
    "painting": 13.74, "painter": 13.74,
    "auto": 3.90, "auto repair": 3.90,
}
# roofing ($228) and cleaning ($47) are verified as cost-per-LEAD, not CPC
CPL = {"roofing": 228, "cleaning": 47}
SOURCE = "LocaliQ 2025 search-ads benchmarks (3,211 home-services campaigns)"

# Conservative slow-page loss band for PSI<40 mobile pages. ESTIMATE, always
# labeled — the defensible framing is "a meaningful share bounce before the
# page renders", quantified as a 20-35% band, never a point claim.
LOSS_LOW, LOSS_HIGH = 0.20, 0.35


def compute(category: str, psi_mobile: int | None) -> dict:
    cat = (category or "").strip().lower()
    cpc = CPC.get(cat)
    cpl = CPL.get(cat)
    out = {"category": cat, "psi": psi_mobile, "cpc": cpc, "cpl": cpl,
           "source": SOURCE, "loss_low": LOSS_LOW, "loss_high": LOSS_HIGH}
    if cpc:
        per100 = cpc * 100
        out["per100_spend"] = per100
        out["est_lost_low"] = per100 * LOSS_LOW
        out["est_lost_high"] = per100 * LOSS_HIGH
    return out


def email_line(w: dict) -> str:
    """The one waste sentence that goes in the cold email. Short, labeled."""
    psi = w.get("psi")
    if w.get("cpc"):
        return (f"At the going ~${w['cpc']:.2f}/click for your trade, every 100 ad clicks "
                f"is about ${w['per100_spend']:,.0f}, and a page that slow typically loses "
                f"an estimated ${w['est_lost_low']:,.0f}-{w['est_lost_high']:,.0f} of it "
                f"before anyone sees your name.")
    if w.get("cpl"):
        return (f"Leads in your trade run about ${w['cpl']}/lead at benchmark, and a page "
                f"this slow gives a real share of them back to whoever loads faster (estimate).")
    return ("A meaningful share of mobile visitors give up on a page this slow before "
            "it finishes loading, and every one of them was a paid click (estimate).")


def one_pager_md(company: str, w: dict, ad_first_seen: str = "",
                 ad_url: str = "", rebuilt_url: str = "") -> str:
    """The proof one-pager (markdown; staged as HTML alongside the rebuilt
    page once Cloudflare staging is live)."""
    psi = w.get("psi")
    lines = [f"# Where {company}'s ad money leaks", ""]
    if ad_first_seen:
        lines.append(f"**Your ad has been running since {ad_first_seen}** "
                     f"(Meta Ad Library, public record{': ' + ad_url if ad_url else ''}).")
    else:
        lines.append(f"**Your ads are running right now** (Meta Ad Library, public record).")
    if psi is not None:
        lines.append(f"**The page they land on scores {psi}/100 on Google's mobile "
                     f"speed test** (PageSpeed Insights, measured, not estimated).")
    lines.append("")
    lines.append(email_line(w))
    lines.append("")
    lines.append(f"_Benchmark source: {w['source']}. Loss figures are estimates — "
                 f"your own numbers replace them the day tracking goes in._")
    if rebuilt_url:
        lines.append("")
        lines.append(f"**The page your ad should be landing on is already built: {rebuilt_url}**")
    return "\n".join(lines)
