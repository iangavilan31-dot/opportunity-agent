"""
Reply-handling playbooks — what to say when they actually reply.

Most outreach systems stop at "sent". Replies are where deals are won or lost,
and the same situations recur: skeptical, price, timing, trust, "we have
software", "send info", ghosting. These are niche-aware, give-first, and built
for an operator with NO testimonials yet — so trust comes from specificity and
de-risking (small pilots, judge-the-work-first), never fake social proof.
"""
from niches import get_pack


def build_playbook(lead, niche_id: str = "generic") -> dict:
    pack = get_pack(niche_id)
    fn = (lead.contact_name or "").split()[0] if lead.contact_name else "there"
    company = lead.company_name or "your team"
    tool = pack.get("primary_tool")
    noun = pack.get("noun", "teams like yours")
    sw_a = pack.get("short_workflows", ["the scheduling"])[0]
    outcome = pack.get("outcome", "")
    offer = pack.get("offer", {})
    offer_name = offer.get("name", "the automation setup")
    setup = offer.get("setup", 0)
    monthly = offer.get("monthly", 0)
    pilot_price = max(500, round(setup * 0.4 / 100) * 100)  # smaller first step

    return {
        "interested": {
            "label": "Positive / curious",
            "when": "“Sounds interesting”, “tell me more”, “how does it work?”",
            "response": (
                f"Hi {fn} — glad it landed. Quickest way to make it concrete: I'll send the breakdown I put together for {company} "
                f"(the exact {sw_a} workflow I'd automate first, and the time it frees up). If it makes sense after you read it, "
                f"we grab 15 minutes; if not, no harm done. Want me to send it over?"
            ),
        },
        "book_meeting": {
            "label": "Wants to talk",
            "when": "“Let's set up a call”, “when are you free?”",
            "response": (
                f"Perfect, {fn}. Here's my calendar — grab whatever works: {{calendar_link}}\n\n"
                f"I'll keep it to 15 minutes: I'll walk through the {sw_a} workflow specifically for {company}, "
                f"what it'd take to set up, and you can decide from there. Anything you want me to dig into beforehand?"
            ),
        },
        "skeptical": {
            "label": "Skeptical / how does it actually work",
            "when": "“How does this actually work?”, “sounds too good”",
            "response": (
                f"Fair question, {fn} — here's the unglamorous version. I map your current {sw_a} steps, then wire up automation that "
                f"handles the rule-based parts (the reminders, the chasing, the data entry) and only pings a human for the exceptions. "
                f"It runs alongside {tool or 'your current tools'}, not instead of it. {outcome} "
                f"If it helps, I'll set up one workflow first so you can see it working before committing to the rest."
            ),
        },
        "price": {
            "label": "Price objection",
            "when": "“How much?”, “that's expensive”, “what's the cost?”",
            "response": (
                f"Straight answer: the full setup runs ${setup:,} to build + ${monthly}/mo to run. But you don't have to start there — "
                f"I'd rather prove it. We can start with just the {sw_a} workflow for around ${pilot_price:,}, and if the time savings are real "
                f"(they usually are), we expand. The whole point is it pays for itself in saved hours, not adds to the pile."
            ),
        },
        "timing": {
            "label": "Bad timing",
            "when": "“Not right now”, “circle back next quarter”",
            "response": (
                f"Totally understand, {fn} — timing's everything. Two options: I can send the {company} breakdown now so it's ready when you are "
                f"(no commitment), and I'll check back in a few weeks. Or if there's a specific trigger — new hire starts, busy season hits — "
                f"just say the word and I'll pick it back up then. Which is easier?"
            ),
        },
        "trust": {
            "label": "Trust / “never heard of you”",
            "when": "“Do you have references?”, “who have you worked with?”",
            "response": (
                f"Honest answer, {fn}: I'm early — I'd rather earn it than name-drop. So here's how I de-risk it for you: "
                f"I'll do the first {sw_a} workflow on a small paid pilot (${pilot_price:,}), and if it doesn't save the hours I claim, "
                f"you don't continue and I refund it. You judge the actual work, not a testimonial. Hard to lose on that setup — fair?"
            ),
        },
        "have_software": {
            "label": "Already have software",
            "when": f"“We already use {tool or 'a tool'} for this”",
            "response": (
                f"That's exactly the setup I work best with — I'm not replacing {tool or 'your software'}. It stores the data; it doesn't "
                f"chase the follow-ups, re-key between systems, or notice when something slips. I automate those manual steps *around* it. "
                f"Most teams are using maybe 40% of what they're paying for — I close the gap. Worth seeing where it'd plug in?"
            ),
        },
        "not_interested": {
            "label": "Not interested",
            "when": "“Not for us”, “we're good”",
            "response": (
                f"No problem at all, {fn} — appreciate you saying so rather than leaving me hanging. I'll get out of your inbox. "
                f"If the {sw_a} load ever becomes a headache down the line, you know where to find me. Best of luck with the hire."
            ),
        },
        "send_info": {
            "label": "Send me info",
            "when": "“Send me some info”, “email me details”",
            "response": (
                f"On its way, {fn}. Rather than a generic deck, I'm sending the breakdown specific to {company} — the actual {sw_a} workflow "
                f"I'd automate, how it runs with {tool or 'your stack'}, and the rough hours saved. Two-minute read. If anything resonates, "
                f"just reply and we'll take it from there."
            ),
        },
        "ghost_nudge": {
            "label": "Went quiet (nudge)",
            "when": "Replied once, then went dark",
            "response": (
                f"Hey {fn} — no pressure at all, just didn't want this to slip through. Still happy to send the {company} breakdown "
                f"whenever you've got two minutes. And if now's not the time, totally fine — just let me know and I'll leave it."
            ),
        },
    }
