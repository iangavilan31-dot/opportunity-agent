"""
Scoring engine — uses Claude Haiku for cheap, fast automation opportunity scoring.
~$0.0001/lead. Can batch hundreds in minutes.
"""
import json
import anthropic
import config
from heuristic import score_lead_heuristic
from niches import detect_niche, niche_label

client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY) if config.ANTHROPIC_API_KEY else None

SCORING_TOOL = {
    "name": "score_opportunity",
    "description": "Score a job posting for workflow automation opportunity",
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {
                "type": "integer",
                "description": "0-100 automation opportunity score",
            },
            "pain_category": {
                "type": "string",
                "description": "Primary: scheduling | coordination | crm | reporting | intake | data_entry | communication | admin | recruiting",
            },
            "pain_points": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3-5 specific pain points inferred from job description",
            },
            "inferred_workflows": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-4 concrete automatable workflows extracted from job description",
            },
            "score_reasoning": {
                "type": "string",
                "description": "1-2 sentence explanation of score",
            },
        },
        "required": ["score", "pain_category", "pain_points", "inferred_workflows", "score_reasoning"],
    },
}

SYSTEM_PROMPT = """You are an automation opportunity scorer for a B2B outreach system.

Score job postings for workflow automation potential. Scores reflect how likely the company has repetitive, rule-based workflows that could be automated.

SCORE HIGH (70-100):
- Title: scheduling coordinator, admin assistant, operations coordinator, recruiting coordinator, CRM specialist, intake coordinator, data entry specialist, reporting analyst, follow-up specialist, customer success coordinator
- Description mentions: scheduling, tracking, updating records, generating reports, data entry, spreadsheets, following up, coordinating between teams, manual processes, repetitive tasks

SCORE MEDIUM (40-69):
- Mixed role — some repetitive work alongside judgment-heavy work
- Coordinator role but at larger enterprise (harder to sell)

SCORE LOW (0-39):
- Creative, engineering, or high-judgment roles
- Sales quota roles
- Technical/software roles
- Executive leadership roles

Extract specific workflows FROM THE JOB DESCRIPTION ITSELF — the responsibilities listed ARE the automatable tasks."""


def score_lead(job_title: str, job_description: str, company_name: str) -> dict:
    # No API key → rule-based heuristic so the pipeline still ranks.
    if client is None:
        return score_lead_heuristic(job_title, job_description, company_name)

    prompt = f"""Score this job posting for automation opportunity.

Company: {company_name}
Job Title: {job_title}
Job Description:
{job_description[:3000]}"""

    try:
        response = client.messages.create(
            model=config.HAIKU_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[SCORING_TOOL],
            tool_choice={"type": "tool", "name": "score_opportunity"},
            messages=[{"role": "user", "content": prompt}],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "score_opportunity":
                result = dict(block.input)
                niche = detect_niche(company_name, job_title, job_description)
                result["niche"] = niche
                result["niche_label"] = niche_label(niche)
                return result

    except Exception as e:
        print(f"[scorer] Haiku error for {company_name}, falling back to heuristic: {e}")

    # Any failure → heuristic fallback (never return a dead 0)
    return score_lead_heuristic(job_title, job_description, company_name)
