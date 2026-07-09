"""
Email generation — Claude Sonnet generates the full outreach suite per lead.
Produces: subject line, short email, long email, mini-audit, 2 follow-ups, breakup email.
"""
import json
import anthropic
import config
from email_templates import generate_suite_template
from niches import get_pack

client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY) if config.ANTHROPIC_API_KEY else None

EMAIL_TOOL = {
    "name": "generate_email_suite",
    "description": "Generate a complete personalized outreach email suite",
    "input_schema": {
        "type": "object",
        "properties": {
            "subject_line": {
                "type": "string",
                "description": "Email subject — references the job posting naturally, under 60 chars, no clickbait",
            },
            "email_body": {
                "type": "string",
                "description": "Short initial email — under 150 words. Specific, peer-to-peer tone, one soft CTA. References the specific job posting and 1-2 workflows.",
            },
            "email_long": {
                "type": "string",
                "description": "Longer version (200-250 words) with more workflow detail and context",
            },
            "mini_audit": {
                "type": "string",
                "description": "2-3 paragraph mini-audit. Identifies 3 specific workflow automation opportunities with rough ROI framing. Feels researched and useful, not salesy.",
            },
            "follow_up_1": {
                "type": "string",
                "description": "3-day follow-up — very brief (50-80 words), adds one new insight or angle, low pressure",
            },
            "follow_up_2": {
                "type": "string",
                "description": "7-day follow-up — even shorter (30-50 words), softest possible ask",
            },
            "breakup_email": {
                "type": "string",
                "description": "14-day graceful breakup — 2-3 sentences, closes the loop with a standing offer",
            },
            "objection_responses": {
                "type": "object",
                "description": "Map of 4-6 likely objections (keys) to concise, non-defensive responses (values). Cover: 'we're just going to hire someone', 'no budget', 'we already use [tool]', 'too small', 'send me info'.",
                "additionalProperties": {"type": "string"},
            },
        },
        "required": ["subject_line", "email_body", "mini_audit", "follow_up_1", "follow_up_2", "breakup_email"],
    },
}

SYSTEM_PROMPT = """You write cold outreach that busy small-business owners actually reply to. They get 10 pitches a day and delete anything that smells automated. Your only job is to sound like a sharp human who did 5 minutes of real homework.

HARD RULES (these are what separate a reply from the trash):
- The initial email is SHORT: 60-90 words. Three short paragraphs max. Long = unread.
- Greeting: if you're given a real first name, use "Hi {name},". If NOT, do NOT write "Hi there" — it screams mass-send. Open directly on the observation instead.
- Name only ONE specific tool the company likely uses (e.g. "Bullhorn", "Dentrix"). NEVER write two with a slash ("Bullhorn/Greenhouse") — that reads like an unmerged mail-merge field.
- Make ONE specific, true observation tied to their actual hire and workflows. No generic "I help businesses like yours."
- ONE concrete, honestly-hedged outcome ("usually hands a recruiter back 5-8 hours a week"). Hedge with "usually/typically" — never over-promise.
- CTA must be GIVE-FIRST and low-friction: offer to send a short specific breakdown, not just "book a call". Lower commitment = more replies.
- Sign with "— [Your name]". No fake credentials.

BANNED (instant-delete signals): "Hi there", "I help teams your size", "teams like yours", "game-changing", "revolutionary", "transform", "leverage", "synergy", "cutting-edge", "supercharge", "10x", "unlock", "act now", exclamation marks, any slogan/tagline dropped mid-email, repeating the same phrase twice.

AVOID claiming AI replaces workers. Frame it as taking busywork off the team so people do the judgment work.

MINI-AUDIT: this is the give-first asset, not the email. Write it as if a competent person analyzed their ops — prose + a few bullets, no "Impact:" labels, name the one tool, end with the offer name + price. Specific enough that they think "they actually get what we do."

SUBJECT: looks like a real internal email, lowercase-ish, specific to them. Good: "speed-to-lead at Harborline Legal". Bad: "Automate Your Workflow Today!". Avoid fake "Re:" prefixes.

Reader = a skeptical owner/ops lead at a 10-100 person company. Earn the reply."""


def generate_emails(
    company_name: str,
    contact_name: str,
    contact_title: str,
    job_title: str,
    inferred_workflows: list[str],
    pain_points: list[str],
    company_profile: dict,
    niche_id: str = "generic",
) -> dict:
    workflows_str = "\n".join(f"- {w}" for w in inferred_workflows)
    pain_str = "\n".join(f"- {p}" for p in pain_points)
    hooks_str = "\n".join(f"- {h}" for h in company_profile.get("personalization_hooks", []))

    first_name = contact_name.split()[0] if contact_name else "there"

    pack = get_pack(niche_id)
    tools_str = ", ".join(pack.get("tools", [])) or "their existing tools"
    offer = pack.get("offer", {})

    # No API key → template-based suite (still specific + non-spammy).
    if client is None:
        return generate_suite_template(
            company_name, contact_name, contact_title, job_title,
            inferred_workflows, pain_points, company_profile, niche_id,
        )

    prompt = f"""Generate a personalized outreach suite for this opportunity.

Company: {company_name}
Contact: {contact_name or "the decision maker"} ({contact_title or company_profile.get("decision_maker_profile", "ops lead")})
First name to use: {first_name}

Trigger: They're hiring a "{job_title}"

NICHE: {pack['label']}
Software these companies typically run: {tools_str}
Niche pain narrative: {pack.get('pain_narrative', '')}
Productized offer to steer toward: "{offer.get('name', '')}" ({offer.get('pitch', '')})

Identified workflows to automate:
{workflows_str}

Pain points:
{pain_str}

Personalization hooks from their job post:
{hooks_str}

Company context: {company_profile.get("key_pain_narrative", "")}
Company size: {company_profile.get("company_size_estimate", "small")}

IMPORTANT: Reference the niche's actual software ({tools_str}) where natural — it signals you understand their world. Use the niche pain narrative to make the mini-audit feel researched. Keep the objection_responses tailored to this niche."""

    try:
        response = client.messages.create(
            model=config.SONNET_MODEL,
            max_tokens=2500,
            system=SYSTEM_PROMPT,
            tools=[EMAIL_TOOL],
            tool_choice={"type": "tool", "name": "generate_email_suite"},
            messages=[{"role": "user", "content": prompt}],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "generate_email_suite":
                return block.input

    except Exception as e:
        print(f"[email_gen] Sonnet error for {company_name}, falling back to template: {e}")

    # Any failure → rich template suite (never a dead default)
    return generate_suite_template(
        company_name, contact_name, contact_title, job_title,
        inferred_workflows, pain_points, company_profile, niche_id,
    )
