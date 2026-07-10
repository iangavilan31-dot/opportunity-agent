# WEB MACHINE — Blind Critic Grades

Gate: **3 blind adversarial critics, average ≥ 85/100. No ship under the gate.**
Critics see only screenshots + product facts; they never know who built it.
Personas: A = Awwwards juror/art director · B = principal product designer (Linear/Stripe bar) · C = information-design + brand skeptic (Tufte bar).

## Round 1 — 2026-07-09 (commit ae26fc2)

| Critic | Score |
|---|---|
| A (Awwwards) | 62 |
| B (Product) | 68 |
| C (Info-design) | 61 |
| **Average** | **63.7 — FAIL** |

Converged complaints → fixes shipped (commit 6c585e6):
1. **Red-law violations in the product's own chrome** (Blocked badges, zero-state funnel bars, "0% rep", reject/delete hovers) → all non-activity red purged; red now appears nowhere until a business actually replies/meets/wins.
2. **Numbers contradicted each other across views** (Field said 8 queued/63 discovered — Analytics said 23/91 via mock-polluted server stats; "148% conv" innumeracy) → every surface (Field, Atlas, sidebar badges, Queue, Overview, Analytics) now computes from ONE canonical dataset: real `website_autopilot` leads from `/api/leads`. Invented conversion percentages deleted. Unequal histogram bins → equal-width.
3. **Ambient dust contradicted "every point is one real company"** → dust deleted entirely; atmosphere now comes from a bloom pass that only halos real businesses.
4. **Sub-legibility** (hover card near-invisible, dots below perception threshold, dim functional text) → luminance floor on every real business, brighter early-stage color, card rebuilt on solid surface with labeled STAGE/SCORE fields (kills the "SENT 71" ambiguity), ledger/timestamps raised to readable tiers.
5. **Workflow pages read as a different, generic product** → one letterspaced-caps header system everywhere, labeled icon rail, sentence-length "tags" recomposed as quiet observation lines, monochrome score chips (confidence = brightness).

## Round 2 — 2026-07-09 (commit 6c585e6)

_Fresh blind critics, same personas, updated screenshots._

| Critic | Score |
|---|---|
| A (Awwwards) | pending |
| B (Product) | pending |
| C (Info-design) | pending |
| **Average** | pending |
