# Asset-Led Outreach — the "listing video" playbook, adapted

**Source:** "Claude Code + Airbnb = $13,000/Month" — Oliver Rasmussen,
youtube.com/watch?v=N1rACQTJepA (watched + extracted 2026-07-10).
His market is real-estate agents and the asset is an AI cinematic listing
video; ours is local businesses and the asset is the free homepage concept.
The mechanics transfer almost 1:1, and most of them were already built here.

## The system he teaches

1. **Scrape leads where the pain is visible.** Zillow/realtor.com listings
   that have sat unsold; grab the exact address + agent contact
   (Instant Data Scraper Chrome extension).
2. **Subject line = ONLY the exact address.** No pitch words. It reads like
   a client or colleague emailing about that specific property, so it gets
   opened.
3. **Body formula:** "I was going to call you, but I decided to send you an
   email first. I noticed this listing has been up for a while, so I made a
   cinematic video that would make more people show up to a house viewing.
   Would you mind taking a look at the video I made for {address}?"
4. **Produce the asset only on reply** (he *claims* it exists in email 1 —
   we don't do that part, see honesty note), then meeting → pitch.
5. **Sell a monthly done-for-you content retainer**, not a one-off:
   Starter $500 / Growth $1,250 / Full $2,500 per month (top tier includes
   running their social with the assets).
6. **Unit economics he shows:** 10 retained clients ≈ 102 deliverables/mo ≈
   35 hrs/mo ≈ $11,660/mo at ~97% margin. "You don't need 100 clients,
   you need 10 good ones."

## Mapping to this machine

| Video system | Here | Status |
|---|---|---|
| Scrape stale Zillow listings | Google-Maps sourcing, weak-site vision gate, lead score | already built (gosom swap is the planned upgrade) |
| Address-only subject | bare `{company_name}` subject variant (~20% of a batch) | **added 2026-07-10**, `web_offer.py` subject pools |
| "I was going to call you" opener | `call_lead` variant (~24% of a batch) | **added 2026-07-10**, `web_offer.py` |
| "Look at the video I made for {address}" | free homepage-concept offer; `?b=` particle link already spells their name on the portfolio | already built (stronger + honest) |
| Asset produced on reply | mockup-on-reply flow | already built |
| Day-based follow-ups | day 0 / +3 / +10 drafts, reply-detection drop-out | already built (`followups.py`) |
| Monthly retainer tiers | see ladder below | pricing exists in research canon; not yet a one-pager |

## Honesty note (law, do not relax)

The video says the asset exists before it does. Our emails cite only
verifiable claims, so the assertive line is capped at "I already started
sketching…" until the pipeline actually pre-generates the concept.
**Upgrade that unlocks the full formula:** pre-generate the homepage concept
for the top ~5 scored leads each morning (batch Playwright screenshot →
concept render), store it, and only then let copy say "I put together a
homepage concept for {name} — want me to send it over?" Still no link in
email 1; the asset is teased, delivered on reply.

## The retainer ladder (his $500/$1,250/$2,500, our numbers)

Build prices stay as researched (2026-07-08 canon): $1,200 / $2,400 / $4,800.
The video's real lesson is the **monthly done-for-you framing** on top:

- **Care — $99/mo** (exists): hosting, security, small changes.
- **Care+ — $250/mo** (canon upsell): + monthly content/photo refresh,
  Google Business posts, review-collection nudges.
- **Growth — $450/mo** (canon upsell): + they send phone photos, we return
  enhanced/branded assets and post them (the direct port of his top tier —
  owner takes iPhone pictures, we make them look professional and keep the
  socials alive). SEO stays OUT per canon.

## The honest 10-client math (vs his $11,660 slide)

10 retained clients at a $250–450/mo blend ≈ **$2,500–4,500/mo recurring**
before any new builds; ~2 builds/mo at $1,200–2,400 layers **$2,400–4,800**
on top → **~$5–9k/mo** at maybe 30–40 focused hrs. Same shape as his slide,
without pretending one-off build revenue is recurring. The target that
matters is his closing line: not 100 clients — **10 good ones on retainers**.

## REALITY CHECK (deep research, same day — read before acting on the video's framing)

The 5-researcher + skeptic run (`ObsidianPKM/research/ai-service-retainer-niches-2026-07-10.md`)
killed the video's core premises: listing media is a per-listing $200-600
purchase (retainers exist only as $3-10k/mo brand content for $2M+ teams),
AI photo enrichment market-clears at $0.53-2.67/photo not $30-100, and the
creator's Skool community grosses ~5x the income his video dangles. The
parts of this playbook that survive: the copy formula (shipped), the honest
retainer ladder below, asset-first pre-generation, and "10 good clients."
The RE-agent angle survives only as per-listing editorial reels ($150-300,
top-producer teams only, no AI-fabricated imagery). Honest funnel number:
~0.2-0.25 clients/mo per 800 personalized sends — first client ~4 months on
cold alone; referrals after client 3 are the only fast path.

## Next actions (in order)

1. First replies prove the funnel (34 sent, 0 replies — cadence + volume
   before new machinery).
2. Asset-first pre-generation for top-5 daily leads (unlocks the full
   "concept already made" formula honestly).
3. Care+/Growth one-pager for the on-reply materials + gavika pricing
   section, so the retainer ladder is pitchable at the first meeting.
