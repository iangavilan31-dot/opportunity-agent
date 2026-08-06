# BRIEF — SITE GIFT TRACK (locked 2026-08-06, ~1:40 AM)

> Third outreach track for the Web Machine. If any instruction below conflicts
> with the GOAL, the GOAL wins. Re-read the GOAL before every major decision.

## GOAL
A business with no real website gets an email that says "I already built
yours" with a live link — a real, deployed one-page site with their name,
trade, and their real Google reviews on it — generated and sent
automatically, zero clicks from Ian.

**Link mode (Ian's locked call): the FIRST email carries the live link.**
Maximum wow over deliverability caution; accepted trade.

## NON-GOALS
- Not mockup screenshots or attachments — a real deployed URL or nothing.
- Not invented content: no fabricated testimonials, services, hours, or
  addresses. If real review text is unavailable, show the real rating +
  review count only. (Real-data law extends to prospect sites.)
- Not a new project — lives in `business\opportunity-agent` beside the
  automation and website-rebuild tracks.
- Not auto-send from Ian's main personal Gmail — standing law. Live sending
  waits for a sacrificial alt / warmed identity via the profile env vars.

## DONE-BAR
1. 5+ real Bergen no-real-website businesses get real generated sites at
   live Vercel URLs.
2. 3 blind critics grade the site template ≥85/100 (docs/GRADES_SITES.md).
3. auto_send completes an end-to-end **dry** run on gift leads.
4. Ian eyeballs one full cycle before SEND_MODE=live is ever set.

## House rules that bind this build
- These sites belong to the PROSPECT's trade, not to Gavika's identity —
  category-appropriate professional design (trades bold, medical airy, law
  serif-traditional, salon stylish). The banned-slop list still applies:
  no neon cyan holo, no scanlines, no cursive gold, no generic AI-template feel.
- Deterministic variety: palette/typography variant keyed by company hash so
  a batch never looks like one template stamped 5 times.
- Every email obeys the existing copy laws: greeting (greeting_name),
  humanize() scrub, sentence-case subject, <100 words, opt-out line,
  [Mailing address] placeholder, LOCAL-first ranking law.
- Only verifiable claims. The email may say "your reviews are on it" only
  when the site actually renders review data.

## Architecture (build spec)
1. **`backend/reviews_source.py`** — `get_reviews(lead)` returns
   `{rating, count, quotes:[{text, author, stars}]}`. Providers: SerpAPI
   (SERPAPI_KEY) for real quotes; fallback = rating/count from targets.csv
   (Maps scrape). Never fabricates; quotes=[] is a valid, honest result.
2. **`backend/sitegen.py`** — `generate_site(lead, reviews) -> slug` writes
   `backend/generated_sites/<slug>/index.html`. Single file, inline CSS,
   mobile-first, `tel:` CTA (phone from Maps), rating hero, reviews section
   (quotes if real, else rating badge + "read our N Google reviews" link),
   category service names (generic to the trade, nothing invented), footer
   "Free website concept built for {company} by Gavika · reply to the email
   to claim it". Design families keyed by category.
3. **`backend/site_deploy.py`** — deploys `generated_sites/` to Vercel
   project `gavika-sites` (CLI is logged in as iangavilan31-dot);
   `deploy() -> base_url`; per-lead URL `<base>/<slug>/`. Loud failure =
   leads stay undrafted (no link, no email — never email a dead link).
4. **`web_offer.py`** — `generate_gift_suite(lead, url, reviews)`: subject
   pool citing the real thing ("built {company} a website", "your reviews
   are on it"), body = I built it, it's live here, yours free if you want
   it, reply no thanks to opt out. FU1 (+3d): one real site feature added;
   FU2 (+10d): closing, link once more.
5. **`morning_batch.py`** — new phase after ranking, gated by
   `GIFT_ENABLED` / `GIFT_DAILY_MAX` (default 5): eligible = no_domain or
   social_only finding + trustworthy contact_email + not contacted; local
   tier first. generate → deploy → verify URL 200 → draft gift email →
   status approved + `gift_site:<slug>` note marker.
6. **`auto_send.py`** — untouched gates; gift leads flow through as
   approved. SEND_MODE stays off/dry until Ian's eyeball + alt account.

## Known blockers (Ian's side)
- Gmail tokens dead since ~7/15 (invalid_grant) — `python gmail_drafts.py`
  + `python gmail_read.py` re-auth before any drafting works. Root fix:
  publish GCP app "booksy-bot" Testing → Production (7-day expiry ends).
- postal_address still unset (CAN-SPAM line auto-drops until filled).
- Live auto-send needs the alt sending account decision.

## Autonomy contract
Work continuously; if blocked (dead tokens, deploy hiccup) build + verify
everything up to that wall, leave the wall loudly documented. Self-QA:
open every generated site in a visible browser and LOOK at it; blind
critics before declaring done. Commit at every working state. Update
SESSION_START.md + memory at milestones.
