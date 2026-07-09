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

1. **Sources targets** — `targets.csv` if present; else **auto-sources real local
   businesses from OpenStreetMap** (free, no key/card) by your configured niches +
   cities; else a built-in seed set. By default it only pulls businesses that have
   a website (so the analyzer can audit it and scrape an email).
2. **Analyzes each site** (`website_signals.py`) for *real, citable* problems:
   no website at all · social-only · no mobile version · "Not Secure" (no HTTPS)
   · slow load · outdated template/builder · stale copyright · missing title/meta.
   It also **scrapes a contact email** off the page.
3. **Scores the opportunity** 0–100 (100 = no site; ~30 = a fine modern site).
   Sites that are already good are **skipped** — we don't pester them.
4. **Ranks by reply-likelihood** and keeps only the **best 50**: has a reachable
   email (so it can become a ready draft), worse site = more need, strong concrete
   stat to cite, higher-value niche, confirmed-active.
5. **Writes a specific cold email** (`web_offer.py`) that names the real problem,
   cites **Gavika** as proof (`PORTFOLIO_URL`), and gives first — a free homepage
   mockup **or a quick Google Meet**.
6. **Creates a real Gmail draft** in your inbox (if set up — see `GMAIL_SETUP.md`),
   To/subject/body filled, so you just open Gmail and hit **Send**. Also queues it
   in the app either way. The backend does **not** need to be running.

Ready-to-send drafts land in **Gmail → Drafts**. The app **Queue** also holds
every lead (with a one-click compose link as a fallback) → Review → Send.

Logs: `backend/logs/morning_YYYY-MM-DD.log`.

---

## Point it at real businesses

The seed set is just so it runs today. For real prospects:

1. Copy `targets.example.csv` → `targets.csv` (in the project root).
2. Fill it in. Columns: `company_name,domain,category,city,contact_email`
   - `domain` blank = the "you have no website" pitch. A real domain gets
     **live-analyzed**. A social URL (facebook.com/…) = the "social-only" pitch.
   - `category`: `barber, salon, dental, medical, restaurant, cafe, plumbing,
     hvac, roofing, landscaping, gym, fitness, law, auto, real_estate, cleaning,
     pet` (anything else = generic).
   - `contact_email` optional — if blank, we try to scrape it from their site.
3. Where to get the list: Google Maps search ("barbers in <city>"), then export
   name/site, or a scraper. Aim for businesses with weak/no sites — that's the pitch.

Run it now without waiting for 9 AM:
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
| `PORTFOLIO_URL` | https://gavika.vercel.app | Proof link in every email |
| `OFFER_MEET` | true | Offer a quick Google Meet alongside the free mockup |
| `GMAIL_ENABLED` | true | Create real Gmail drafts (needs `GMAIL_SETUP.md`) |
| `SOURCING_ENABLED` | true | Auto-source businesses from OpenStreetMap when no `targets.csv` |
| `SOURCING_CITIES` | Phoenix/Scottsdale/Mesa AZ | Cities to source (separate with `;`) |
| `SOURCING_NICHES` | barber,salon,dental,… | Niches to source (comma-separated) |
| `SOURCING_REQUIRE_WEBSITE` | true | Only pull businesses that have a site (needed to scrape an email) |
| `SOURCING_MAX_PER_QUERY` | 60 | Max results per niche×city query |

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

1. **Separate sending domain** (never your main one). ~$10.
2. **SPF + DKIM + DMARC** records so inboxes trust you.
3. **Warm it up 3–4 weeks** — ramp from a few/day to 30–40/day. Skipping this is
   the #1 mistake.
4. **~30–40/day per inbox** (so 50/day wants 2 inboxes), **verify emails**
   (bounce < 2%), keep a **suppression list**, and always include a real physical
   address + working unsubscribe (CAN-SPAM). Compliance = deliverability here.
5. A tool like Instantly/Smartlead (~$37–97/mo) handles warmup + rotation +
   sending; then wire it up and flip auto-approve.

Until then: draft autopilot + you clicking send is the right, safe setup.
```
