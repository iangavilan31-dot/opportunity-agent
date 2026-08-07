# BRIEF — BURNING-AD-MONEY RESCUE (locked 2026-08-07, noon)

> The research report IS the spec: `ObsidianPKM/research/smb-opportunity-engine-2026-08-06.md`
> §13 (architecture), §18 (underwriting), §19 (experiments E0–E6), §20 (roadmap).
> If anything below conflicts with the report, the report wins. If any instruction
> conflicts with the GOAL, the GOAL wins.

## GOAL
Detect local businesses actively running Meta/Google ads onto weak pages,
pre-build the landing page their ad should hit plus a waste-arithmetic proof
pack, and sell it at $299–499/mo — the experiment sequence E0→E6 decides
scale-or-pivot on data, not vibes.

## NON-GOALS
- Not an agency, not audits-and-calls — finished artifacts and a number.
- Not a rewrite: layers reuse the existing scanner/DB/copy/deploy machinery.
- No fabricated claims: waste math labeled as estimates (FTC hygiene), PSI and
  ad-activity only ever from real lookups. All existing copy laws bind.
- No auto-send from the main Gmail (standing law). Scale track waits for
  warmed secondary domains.
- Site-gift motion is NOT dead — it becomes E5 (mail/walk-in to the 141
  no-email Bergen leads). Gift tasks are absorbed, not deleted.

## DONE-BAR (this build phase = E0 complete + E1 running + E2 buildables staged)
1. E0: healthcheck.py dead-man alarm armed as a daily scheduled task; owed
   FU1 drafts created for every eligible sent lead; cadence provably alive.
2. E1: feed_psi.py + feed_adlib.py runnable over the 1,500-lead DB; PSI pass
   actually run; ad-library pass run to the extent keys/scrape allow, with
   coverage honestly reported (E1 verdict: ≥40 in-county qualified or go
   multi-metro).
3. offer_router.py skeleton + DB columns (machine, variant, ad_active,
   psi_mobile) migrated with backup.
4. cro_offer.py + waste_math.py drafted (E2 buildables; sends wait on warmup).
5. AZ tail suppressed per §20-7d.

## IAN'S SIDE (blocking items, in priority order)
1. GCP app Testing → Production (or tokens die again in 7 days).
2. Postal address in Settings (CAN-SPAM footer currently auto-drops).
3. Purchases when ready: MillionVerifier top-up (~$89); 2 secondary domains +
   3 Workspace inboxes (warmup clock gates E2 by ~5 weeks); optional
   ScrapeCreators/SerpAPI key for robust ad-library coverage.
4. Cloudflare account auth for Pages staging move (report §12.11 ToS finding);
   Vercel remains interim until then.

## Autonomy contract
As before: continuous work, loud failures, commit at working states, honest
verdicts. Every new layer must run unattended AND fail loudly — the machine
died of silence once; healthcheck exists so it can't twice.
