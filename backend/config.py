import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
# Contact discovery - Apollo primary, Hunter fallback
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")
# Email verification (MillionVerifier / NeverBounce-style). Mandatory before send.
VERIFIER_API_KEY = os.getenv("VERIFIER_API_KEY", "")

MIN_SCORE_THRESHOLD = int(os.getenv("MIN_SCORE_THRESHOLD", "65"))
MAX_LEADS_PER_RUN = int(os.getenv("MAX_LEADS_PER_RUN", "50"))
LEADS_TO_DEEP_PROCESS = int(os.getenv("LEADS_TO_DEEP_PROCESS", "15"))

# ── Website-selling track (morning autopilot) ────────────────────────────────
# Optional: Google PageSpeed Insights key for a real mobile speed score.
PAGESPEED_API_KEY = os.getenv("PAGESPEED_API_KEY", "")
# How many BEST drafts the 9 AM autopilot keeps per run (out of the analyzed pool).
AUTOPILOT_TARGET_COUNT = int(os.getenv("AUTOPILOT_TARGET_COUNT", "40"))
# Only pitch businesses whose site clearly needs it (0-100; higher = worse site).
# Modern/invested sites are capped low by the analyzer, so they fall below this.
AUTOPILOT_MIN_OPPORTUNITY = int(os.getenv("AUTOPILOT_MIN_OPPORTUNITY", "45"))
# Draft-autopilot: leave False so drafts land in Queue for a human glance.
# Set True only once a warmed sending domain is live (full auto-send).
AUTOPILOT_AUTO_APPROVE = os.getenv("AUTOPILOT_AUTO_APPROVE", "false").lower() == "true"
# Website-rebuild offer pricing (edit to your real numbers).
# Three tiers: research says $1,200 is the LOW end of the 2025-26 solo market —
# anchor with tiers in the close/playbook layer (never in cold email 1) and let
# most deals land on the middle. Cold email quotes "from $<setup>".
WEB_SETUP_PRICE = int(os.getenv("WEB_SETUP_PRICE", "1200"))
WEB_TIER2_PRICE = int(os.getenv("WEB_TIER2_PRICE", "2400"))
WEB_TIER3_PRICE = int(os.getenv("WEB_TIER3_PRICE", "4800"))
WEB_MONTHLY_PRICE = int(os.getenv("WEB_MONTHLY_PRICE", "99"))

# Outreach identity + social proof shown in every email.
STUDIO_NAME = os.getenv("STUDIO_NAME", "Gavika")
PORTFOLIO_URL = os.getenv("PORTFOLIO_URL", "https://gavika.pages.dev")
# Offer a quick Google Meet alongside the free-mockup give-first CTA.
OFFER_MEET = os.getenv("OFFER_MEET", "true").lower() == "true"

# Ranking: analyze up to this many candidates, then keep the best AUTOPILOT_TARGET_COUNT.
# Runs unattended at 9 AM, so casting a wide net is fine — the wider the pool, the
# better the top 40. Analysis is parallelized (AUTOPILOT_WORKERS) so 500 is fast.
AUTOPILOT_MAX_ANALYZE = int(os.getenv("AUTOPILOT_MAX_ANALYZE", "500"))
# Concurrent site fetches during analysis (keeps a 500-site run to a few minutes).
AUTOPILOT_WORKERS = int(os.getenv("AUTOPILOT_WORKERS", "12"))

# Gmail drafts — create real drafts in your inbox (sends nothing). Needs OAuth
# (see GMAIL_SETUP.md). Falls back to Queue + one-click compose links if not set up.
GMAIL_ENABLED = os.getenv("GMAIL_ENABLED", "true").lower() == "true"

# ── Free auto-sourcing (no API key, no credit card, $0) ──────────────────────
# Primary: Google Maps via the gosom scraper binary in tools/ (writes
# targets.csv with rating + review_count + phone; refreshed when stale).
# Fallback: OpenStreetMap. Cities are separated by ";".
SOURCING_ENABLED = os.getenv("SOURCING_ENABLED", "true").lower() == "true"
# Re-scrape targets.csv when older than this many days.
SOURCING_REFRESH_DAYS = int(os.getenv("SOURCING_REFRESH_DAYS", "7"))
# Scroll depth per Maps query (~21 results per scroll; 2 ≈ 40+ places/query).
SOURCING_DEPTH = int(os.getenv("SOURCING_DEPTH", "2"))
# Hard cap per city so a hung scrape can never eat the morning run.
SOURCING_CITY_TIMEOUT_S = int(os.getenv("SOURCING_CITY_TIMEOUT_S", "1200"))
# Ian's real backyard (Bergen County, NJ — he's in Englewood Cliffs). Local
# targeting makes every "local" claim in the copy TRUE, enables real Meets /
# in-person, and lets the footer address corroborate the pitch instead of
# contradicting it. (Was Phoenix/Scottsdale/Mesa — build defaults, never his.)
SOURCING_CITIES = [c.strip() for c in os.getenv(
    "SOURCING_CITIES",
    "Englewood, NJ;Fort Lee, NJ;Hackensack, NJ;Teaneck, NJ;Paramus, NJ;"
    "Fair Lawn, NJ;Ridgewood, NJ;Bergenfield, NJ;Cliffside Park, NJ;Tenafly, NJ"
).split(";") if c.strip()]

# ── Local identity (the honesty rule, Ian 2026-07-09) ────────────────────────
# "Local" wording + the footer mailing address appear ONLY when the prospect's
# town is genuinely within driving distance of home base. Never imply localness
# elsewhere: the lie would surface at the exact moment a warm lead replies
# ("you're local? let's meet"). Deliberately a standalone list, NOT derived
# from SOURCING_CITIES, so adding a distant market later can't silently start
# claiming it's local.
STUDIO_HOME_TOWN = os.getenv("STUDIO_HOME_TOWN", "Englewood Cliffs")
LOCAL_TOWNS = {t.strip().casefold() for t in os.getenv(
    "LOCAL_TOWNS",
    "Englewood Cliffs;Englewood;Fort Lee;Hackensack;Teaneck;Paramus;Fair Lawn;"
    "Ridgewood;Bergenfield;Cliffside Park;Tenafly;Leonia;Palisades Park;"
    "Edgewater;Closter;Dumont;New Milford;River Edge;Oradell;Emerson;Westwood;"
    "Cresskill;Demarest;Haworth;Harrington Park;Norwood;Northvale;Alpine;"
    "Bogota;Maywood;Ridgefield;Ridgefield Park;Little Ferry;Fairview;"
    "Hasbrouck Heights;Rochelle Park;Paramus;Glen Rock;Hawthorne"
).split(";") if t.strip()}
# High-ROI, often-neglected industries (trades + storefront services). Deliberately
# NOT restaurants/cafes/real-estate/hotels — those tend to already invest in design.
SOURCING_NICHES = [n.strip() for n in os.getenv(
    "SOURCING_NICHES", "auto,dental,law,chiropractor,plumbing,hvac,roofing,electrician,vet"
).split(",") if n.strip()]
SOURCING_MAX_PER_QUERY = int(os.getenv("SOURCING_MAX_PER_QUERY", "60"))
# Only draft to sites written in these languages — an English pitch to a
# Spanish-only business reads as spam. Detection: <html lang> attr, then a
# stopword sniff; ambiguous defaults to English (skip only when definitive).
OUTREACH_LANGS = [x.strip().lower() for x in
                  os.getenv("OUTREACH_LANGS", "en").split(",") if x.strip()]

# Keep no-website businesses too — "you have no site" is the strongest pitch,
# and Maps sourcing gives us their phone number for manual contact. They rank
# below bad-site-with-reviews leads (which have proven they'll pay for a site).
SOURCING_REQUIRE_WEBSITE = os.getenv("SOURCING_REQUIRE_WEBSITE", "false").lower() == "true"

# ── Visual UI audit (GPT-4o-mini reads the screenshot -> real UI problems) ───
# The sharpest reply-rate lever: turns "you're on Wix" into "your phone number
# is below three scrolls". ~$0.0004/site on gpt-4o-mini (cents/day for the
# shortlist). Skips cleanly with no key. Get a key at platform.openai.com.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
VISION_ENABLED = os.getenv("VISION_ENABLED", "true").lower() == "true"
VISION_MODEL = os.getenv("VISION_MODEL", "gpt-4o-mini")
# The gate DOWNRANKS sites that look modern (it no longer drops them — Ian would
# still email a decent-looking business, just at low priority), so screenshot+judge
# a bigger pool than the daily draft target to fill the top with genuinely-bad
# prospects first and let modern ones sink below.
VISION_GATE_POOL = int(os.getenv("VISION_GATE_POOL", "90"))
# Reply-likelihood penalty applied to a 'modern' visual verdict. Large by default
# so every modern-looking site ranks below every dated one — they get drafted only
# when there aren't enough genuinely-dated prospects to hit the daily target.
VISION_MODERN_PENALTY = float(os.getenv("VISION_MODERN_PENALTY", "1000"))

# ── Autonomous sending (OFF by default — read auto_send.py before enabling) ──
# The deliverability law stands: NEVER point this at the main personal Gmail.
# It exists for a sacrificial alt or a warmed Workspace inbox, selected via the
# GMAIL_TOKEN_PATH / GMAIL_READ_TOKEN_PATH / DB_PATH profile env vars.
SEND_MODE = os.getenv("SEND_MODE", "off")                    # off | dry | live
SEND_DAILY_CAP = int(os.getenv("SEND_DAILY_CAP", "25"))
SEND_GAP_MIN = float(os.getenv("SEND_GAP_MIN", "3"))         # minutes between sends
SEND_GAP_MAX = float(os.getenv("SEND_GAP_MAX", "9"))
SEND_WINDOW = os.getenv("SEND_WINDOW", "9-17")               # local send hours
# false = only leads Ian APPROVED in the Queue UI may auto-send (his quality
# gate survives, minus the clicking). true = queued leads may send too.
SEND_INCLUDE_QUEUED = os.getenv("SEND_INCLUDE_QUEUED", "false").lower() == "true"

# ── Screenshot pipeline (visual grading) ─────────────────────────────────────
# After ranking, capture mobile+desktop screenshots of the selected leads into
# backend/screenshots/YYYY-MM-DD/ plus a contact-sheet HTML for a 5-minute skim.
SCREENSHOTS_ENABLED = os.getenv("SCREENSHOTS_ENABLED", "true").lower() == "true"
SCREENSHOTS_MAX = int(os.getenv("SCREENSHOTS_MAX", "40"))

# ── Follow-up cadence (day 0 / +3 / +10) ─────────────────────────────────────
# Research: follow-ups roughly double replies; 3 touches then stop. The batch
# drafts follow-ups only for leads whose previous email was actually sent
# (Gmail draft disappeared) and that haven't been marked replied in the app.
FOLLOWUP_ENABLED = os.getenv("FOLLOWUP_ENABLED", "true").lower() == "true"
FOLLOWUP_1_DAYS = int(os.getenv("FOLLOWUP_1_DAYS", "3"))
FOLLOWUP_2_DAYS = int(os.getenv("FOLLOWUP_2_DAYS", "10"))

DB_PATH = os.getenv("DB_PATH", "opportunity_agent.db")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5120")

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"

JOB_QUERIES = [
    "scheduling coordinator",
    "administrative coordinator",
    "operations assistant",
    "recruiting coordinator",
    "customer success coordinator",
    "CRM specialist",
    "intake coordinator",
    "data entry specialist",
    "office manager",
    "executive assistant",
    "operations coordinator",
    "reporting analyst",
]
