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

| Critic | Score |
|---|---|
| A (Awwwards) | 63 |
| B (Product) | 66 |
| C (Info-design) | 68 |
| **Average** | **65.7 — FAIL** |

Converged complaints → fixes shipped (commit c3db26e):
1. **Declined businesses counted but invisible** → dedicated dim Declined cluster in the Field; all 63 real businesses now render; ledger row and label are interactive like every stage.
2. **Cluster labels contradicted the dots during focus** (other centroids project onto the focused cluster) → only the focused label speaks during focus.
3. **Encoding existed only in documentation** → on-screen legend under the ledger: "size = opportunity score · glow = real business · red = only when a business answers."
4. **Legibility floor** → global muted/dim tokens raised (~45% luminance), brighter map strokes, label opacity up.
5. **Queue trust killers** → "Blocked" → calm "Needs contact" when the only blocker is a missing contact; duplicated Website/website chips deduped; draft email's first lines inline; single filled primary "Approve → Gmail"; cards → editorial hairline rows with a left focus rule.
6. **Analytics chart craft** → single-datum charts collapse to stat lines until a comparison exists; projection demoted below real numbers; equal-width ascending bins with "<60 · agg" marked; "42 ld" → "42 leads"; bar column widths capped.
7. **Vocabulary drift** → one canonical stage word everywhere: "Reached."
8. **Atlas** → timeline track notched with every real send (white) / reply (red) event; connection bundle feathered per-business; discovered dots raised above the perception threshold.
Deferred (noted, not shipped): nav consolidation 9→5 (product-structure decision for Ian); auto-framing the map to data extent (rejected — the directive explicitly wants the whole US filling over months).

## Round 3 — 2026-07-09 (commit c3db26e)

| Critic | Score |
|---|---|
| A (Awwwards) | pending |
| B (Product) | pending |
| C (Info-design) | pending |
| **Average** | pending |
