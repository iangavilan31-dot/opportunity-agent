"""
Company researcher — uses Claude Sonnet to build a company profile from available signals.
Input: job description (rich signal) + company name + domain.
No external search needed for MVP — the job post itself is the research.
"""
import json
import anthropic
import config
from email_templates import build_profile_heuristic

client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY) if config.ANTHROPIC_API_KEY else None

RESEARCH_TOOL = {
    "name": "build_company_profile",
    "description": "Build a company intelligence profile from job posting signals",
    "input_schema": {
        "type": "object",
        "properties": {
            "company_description": {
                "type": "string",
                "description": "What this company likely does (2-3 sentences inferred from context)",
            },
            "company_size_estimate": {
                "type": "string",
                "description": "Estimated size: micro (1-10), small (10-50), mid (50-200), large (200+)",
            },
            "operational_maturity": {
                "type": "string",
                "description": "startup | early | scaling | mature",
            },
            "automation_readiness": {
                "type": "string",
                "description": "low | medium | high — how receptive they likely are",
            },
            "decision_maker_profile": {
                "type": "string",
                "description": "Who to reach: founder, CEO, COO, ops director, etc.",
            },
            "key_pain_narrative": {
                "type": "string",
                "description": "2-3 sentence story of their operational pain based on what they're hiring for",
            },
            "personalization_hooks": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-3 specific details from the job post to reference in outreach",
            },
            "urgency_signals": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Signals suggesting they're in pain NOW (e.g., 'hiring fast', multiple similar roles)",
            },
        },
        "required": [
            "company_description",
            "company_size_estimate",
            "key_pain_narrative",
            "personalization_hooks",
            "decision_maker_profile",
        ],
    },
}

SYSTEM_PROMPT = """You are a business intelligence analyst for an automation consulting firm.

Given a job posting, build an intelligence profile for outreach personalization.

The job description is your PRIMARY source — it explicitly lists the workflows that exist and are currently manual.
Read between the lines: what responsibilities suggest the company is overwhelmed? What signals suggest this is a first hire for this function?

Be specific and grounded. Do not invent information not supported by the posting."""


def research_company(
    company_name: str,
    company_domain: str,
    job_title: str,
    job_description: str,
    pain_points: list[str],
    inferred_workflows: list[str],
) -> dict:
    # No API key → heuristic profile from the job posting signals.
    if client is None:
        return build_profile_heuristic(
            company_name, company_domain, job_title,
            job_description, pain_points, inferred_workflows,
        )

    prompt = f"""Build an intelligence profile for outreach personalization.

Company: {company_name}
Domain: {company_domain or "unknown"}
Job Title: {job_title}
Automation signals already identified:
- Pain points: {', '.join(pain_points)}
- Workflows: {', '.join(inferred_workflows)}

Full Job Description:
{job_description[:3500]}"""

    try:
        response = client.messages.create(
            model=config.SONNET_MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=[RESEARCH_TOOL],
            tool_choice={"type": "tool", "name": "build_company_profile"},
            messages=[{"role": "user", "content": prompt}],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "build_company_profile":
                return block.input

    except Exception as e:
        print(f"[researcher] Error for {company_name}: {e}")

    return {
        "company_description": f"Company hiring a {job_title}",
        "company_size_estimate": "unknown",
        "key_pain_narrative": f"Hiring a {job_title} suggests growing coordination overhead.",
        "personalization_hooks": [f"Hiring a {job_title}"],
        "decision_maker_profile": "founder or ops lead",
    }
