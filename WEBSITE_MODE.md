# Website-Selling Autopilot

A second outreach track bolted onto the Opportunity Agent. The original track
sells **workflow automation** off job-post signals. This one sells **website
rebuilds** off **real website-quality signals**, and fires a fresh batch of
ready-to-review drafts into your Queue **every morning at 9:00 AM by itself**.

Nothing here sends email on its own (by design — see "Not getting banned").
It reads public websites and writes drafts. You glance, approve, and click send.

---

## What runs at 9 AM

`run_morning.ps1` (Windows Task Scheduler task **`OpportunityAgent-MorningOutreach`**)
runs `backend/morning_batch.py`, which:

1. **Sources targets** — **Google Maps via the free gosom scraper**
   (`tools/google_maps_scraper.exe` → `backend/source_maps.py`): every configured
   niche × city, with **rating, review count, and phone** per business. The scrape
   lands in `targets.csv` and auto-refreshes when it's older than
   `SOURCING_REFRESH_DAYS`. Falls back to OpenStreetMap, then the seed set.
   No-website businesses are kept — that's the strongest pitch, and Maps gives
   you their phone number.
2. **Analyzes each site** (`website_signals.py`) for *real, citable* problems:
   no website at all · social-only · no mobile version · "Not Secure" (no HTTPS)
   · slow load · outdated template/builder · stale copyright · **legacy tech
   (jQuery 1.x, Flash, framesets, Bootstrap 2/3)** · missing title/meta. It also
   detects **ad pixels** (Meta/Google/TikTok/Microsoft — a rank-only "already
   pays for marketing" signal, never cited in email) and **scrapes a contact
   email** off the page.
3. **Scores the opportunity** 0–100 (100 = no site; ~30 = a fine modern site).
   Sites that are already good are **skipped** — we don't pester them.
4. **Ranks by reply-likelihood** and keeps only the best N. Big boost for the
   research-proven sweet spot: **20+ reviews at 4.0+ stars AND a neglected site**
   (a thriving business that has already paid for a website once). Ad pixels and
   a reachable email boost too; no-site-no-reviews sinks.
5. **Verifies every email before drafting** (`verify_email.py`: syntax + MX via
   DNS, optional MillionVerifier) — bounces, not volume, are what get a small
   Gmail sender flagged. Invalid addresses are dropped; the lead stays.
6. **Writes a specific cold email** (`web_offer.py`): the real flaw in plain
   text, **no links in email 1** (they hurt deliverability; the mockup/portfolio
   is delivered on reply), under ~100 words, plus the **CAN-SPAM footer** —
   opt-out line + your mailing address from Settings.
7. **Creates a real Gmail draft** in your inbox (if set up — see `GMAIL_SETUP.md`),
   To/subject/body filled, so you just open Gmail and hit **Send**. Also queues it
   in the app either way. The backend does **not** need to be running.
8. **Runs the follow-up cadence** (`followups.py`, day +3 / +10): when a sent
   draft disappears from your Drafts folder it's marked sent, and follow-up
   drafts appear automatically on schedule. Research: follow-ups roughly double
   replies; 3 touches then stop. Mark a lead **replied** in the app to stop its
   sequence.
9. **Screenshots the shortlist** (`screenshots.py`): mobile + desktop shots of
   every selected site → `backend/screenshots/YYYY-MM-DD/contact_sheet.html` —
   the "See" stage as a 5-minute skim instead of 40 tabs.

Ready-to-send drafts land in **Gmail → Drafts**. The app **Queue** also holds
every lead (with a one-click compose link as a fallback) → Review → Send.

Logs: `backend/logs/morning_YYYY-MM-DD.log`.

---

## Point it at real businesses

**It points itself now.** `backend/source_maps.py` scrapes Google Maps (free,
local binary, no key) for every `SOURCING_NICHES` × `SOURCING_CITIES` combo and
writes `targets.csv` with rating/review_count/phone. It re-scrapes automatically
when the file is older than `SOURCING_REFRESH_DAYS` (default 7).

Force a fresh scrape any time:
```
cd backend
python source_maps.py --fresh
```

You can still hand-maintain `targets.csv` — extra columns
(`phone,rating,review_count`) are optional:
   - `domain` blank = the "you have no website" pitch. A real domain gets
     **live-analyzed**. A social URL (facebook.com/…) = the "social-only" pitch.
   - `category`: `barber, salon, dental, medical, restaurant, cafe, plumbing,
     hvac, roofing, landscaping, gym, fitness, law, auto, real_estate, cleaning,
     pet` (anything else = generic).
   - `contact_email` optional — if blank, we try to scrape it from their site.

Run the whole batch now without waiting for 9 AM:
```
cd backend
python morning_batch.py
```

---

## Tuning (all in `backend/.env`)

| Setting | Default | Meaning |
|---|---|---|
| `AUTOPILOT_TARGET_COUNT` | 50 | Best-N drafts kept per morning |
| `AUTOPILOT_MAX_ANALYZE` | 150 | Candidates analyzed before ranking down to the best N |
| `AUTOPILOT_MIN_OPPORTUNITY` | 40 | Only pitch sites scoring ≥ this (skip good sites) |
| `AUTOPILOT_AUTO_APPROVE` | false | **Keep false** until a warmed domain is live (see below) |
| `WEB_SETUP_PRICE` | 1200 | Your build price (shown in the email) |
| `WEB_MONTHLY_PRICE` | 99 | Your monthly hosting/maintenance price |
| `STUDIO_NAME` | Gavika | Studio name cited in the email |
| `PORTFOLIO_URL` | https://gavika.pages.dev | Proof link in every email |
| `OFFER_MEET` | true | Offer a quick Google Meet alongside the free mockup |
| `GMAIL_ENABLED` | true | Create real Gmail drafts (needs `GMAIL_SETUP.md`) |
| `SOURCING_ENABLED` | true | Auto-source businesses from OpenStreetMap when no `targets.csv` |
| `SOURCING_CITIES` | Phoenix/Scottsdale/Mesa AZ | Cities to source (separate with `;`) |
| `SOURCING_NICHES` | barber,salon,dental,… | Niches to source (comma-separated) |
| `SOURCING_REQUIRE_WEBSITE` | false | Keep no-website businesses (strongest pitch; Maps gives their phone) |
| `SOURCING_MAX_PER_QUERY` | 60 | Max results per niche×city query (OSM fallback) |
| `SOURCING_REFRESH_DAYS` | 7 | Re-scrape Google Maps when targets.csv is older than this |
| `SOURCING_DEPTH` | 2 | Maps scroll depth per query (~21 results per scroll) |
| `WEB_TIER2_PRICE` / `WEB_TIER3_PRICE` | 2400 / 4800 | Close-layer price tiers (never in cold email 1) |
| `SCREENSHOTS_ENABLED` / `SCREENSHOTS_MAX` | true / 40 | Mobile+desktop shots + contact sheet for the shortlist |
| `FOLLOWUP_ENABLED` | true | Auto-draft follow-ups for sent-but-unanswered leads |
| `FOLLOWUP_1_DAYS` / `FOLLOWUP_2_DAYS` | 3 / 10 | Follow-up cadence after the send is detected |

**Tune your market:** set `SOURCING_CITIES` and `SOURCING_NICHES` in `.env` to the
metros/niches you want. Each city×niche pool is finite and de-duplicated across
days, so add new cities as one gets exhausted (roughly a week or two of runs).
| `PAGESPEED_API_KEY` | (empty) | Optional — real Google mobile speed score instead of measured load time |

**To get "already in my drafts, just hit send":** do the one-time
[GMAIL_SETUP.md](GMAIL_SETUP.md). Until then it falls back to Queue + one-click
compose links (still one click to send, just from the app instead of Gmail).

Set your name/positioning/calendar in the UI **Settings** page so every draft
signs off correctly (replaces `[Your name]`).

Change the time: re-register the task, or edit it in Task Scheduler
(`OpportunityAgent-MorningOutreach`).

Turn it off:
```powershell
Unregister-ScheduledTask -TaskName "OpportunityAgent-MorningOutreach" -Confirm:$false
```

---

## Not getting banned (read before going full-auto)

Right now this is **draft autopilot**: drafts are built for you, but *you* click
send from your own inbox at human pace. That has **zero ban risk** and gets
replies this week.

**Do NOT flip `AUTOPILOT_AUTO_APPROVE=true` and blast 50/day from your personal
Gmail.** That gets the account flagged and your mail lands in spam (0 replies) —
the exact thing to avoid. To go truly hands-off later, first stand up real
cold-email infrastructure:

1. **Separate lookalike sending domain** (never gavika's main domain — a burn
   must be sacrificial). ~$12/yr + an inbox: Zoho Mail ~$1/mo or Google
   Workspace ~$8/mo. **Start the domain early — the 30–60 day aging clock is
   the real bottleneck to scaling, not tooling.**
2. **SPF + DKIM + DMARC** records so inboxes trust you.
3. **Skip warmup tools/pools entirely** — Google detects and discounts the fake
   engagement (GMass killed theirs under Google threat in 2023; Apollo removed
   theirs in 2024). Warm with REAL ramped sends: ~5/day week 1 → ~25/day by
   week 4–6, never +20% volume in a day.
4. **15–25/day per inbox** (post-2025-crackdown practitioner ceiling), **verify
   emails** (the batch does this automatically now; bounce < 2%), keep a
   **suppression list**, and always include a real physical address + working
   opt-out (CAN-SPAM — the batch bakes both into every draft; set your mailing
   address in Settings, a PO Box works).
5. At-any-volume risk is **complaint RATE on a tiny denominator** — two spam
   flags in a week can spike the percentage. Targeting quality is deliverability.

Until then: draft autopilot + you clicking send is the right, safe setup.

---

## Research canon (2026-07-08) — plan numbers & business legals

Full skeptic-gated report: `ObsidianPKM/research/gavika-web-machine-upgrades-2026-07-08.md`

- **Plan revenue at 1–3% positive reply** (~1–2 real conversations per 100
  sends). 5% total-reply is achievable with sharp targeting; don't budget on it.
- **On a reply**: answer fast (manners, not magic), send the mini-audit + free
  mockup; a 60–90s Loom over their site is a *reply-conversion* tool — never a
  first touch.
- **Close with three tiers** ($1,200 / $2,400 / $4,800 — `WEB_TIER2_PRICE`,
  `WEB_TIER3_PRICE`); most deals should land on the middle. 50% deposit, parent
  co-signs the contract (a minor's signature alone is voidable both ways),
  **Stripe requires a parent/guardian as account OWNER** for under-18.
- **The $99/mo is the floor, not the ceiling** — the researched ladder per
  client: Google Business Profile management (+$150–250/mo), review management
  (+$100–200/mo), later an AI receptionist (+$150–250/mo). Keep SEO promises
  OUT of the care plan (it's the #1 churn trigger).
- **Host client sites on Cloudflare Pages** (free tier explicitly allows
  commercial use, unlimited bandwidth). **Vercel Hobby prohibits commercial
  use** and Netlify's free tier hard-caps and pauses sites — both disqualified.
- **Never cold-SMS** (TCPA: $500–1,500 statutory per text). Google Business
  Profile chat is dead (killed July 2024). Best offline play for the top ~20
  prospects: a short handwritten letter (~$2 each, ANA-benchmarked 2–4%+
  response).
