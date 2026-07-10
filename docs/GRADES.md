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
| A (Awwwards) | 63 |
| B (Product) | 71 |
| C (Info-design) | 71 |
| **Average** | **68.3 — FAIL** (trend 63.7 → 65.7 → 68.3) |

Converged complaints → fixes shipped (commit af853f2):
1. **Labels still detached from their dot populations** (perspective puts world-centroid projections away from where the cluster appears) → labels now bind to the visible center of mass (mean of each stage's projected nodes) every frame.
2. **Shot 02 wasn't even focused** — the ledger row's hover-focus was instantly overridden by the canvas picker underneath → ledger swallows mousemove; focus now holds.
3. **Hover card leaked the raw enum** ("rejected" lowercase) → renders "Declined", matching every surface.
4. **$100k projection at typographic parity with truth** → "Earned $0" is now the first and loudest money; projection demoted to a caption line under the funnel.
5. **Two competing filled primaries + un-gated Gmail action on contact-less leads** → one filled primary; "Approve → Gmail" visually gates with an explanatory tooltip when no contact email exists.
6. **"23 discovered" vs ~2 perceptible dots on the Atlas** → discovered/declined dots raised above the perception threshold; map strokes brightened; replay keeps the known network as faint ghost structure (the past is never a blank screen).
7. **Zeros rendered as pills** (a mark with width lies) → zero stages are hairlines. **Legend** reworded to state provenance as provenance ("every glow is one real business") and node size range widened so size=score is readable. **Failed pipeline runs** get alarm red (operational harm is not gagged by the activity-red law).
Deferred for Ian: nav consolidation 9→5; Overview/Analytics share modules by design for now.

## Round 4 — 2026-07-09 (commit af853f2) — FINAL THIS SESSION

| Critic | Score |
|---|---|
| A (Awwwards) | 71 |
| B (Product) | 78 |
| C (Info-design) | 79 |
| **Average** | **76.0 — FAIL vs the 85 gate** (trend 63.7 → 65.7 → 68.3 → 76.0) |

**Honest verdict: NOT at the bar yet. Do not call this shipped.** The identity and honesty laws are praised by all three critics as "genuinely ownable" / "Stripe-grade data discipline" / "a dashboard with an actual soul" — the remaining gap is execution polish, concentrated in known places.

Fixed after round-4 screenshots (already committed, will show next round):
- Hover card enum leak: "sent" → "Reached" (all three critics caught it) + card surface brightened.
- Replay ghost dropped to unmistakably-ghost intensity (0.12).
- Send page now gates "Open in Gmail" when no contact email (same law as Queue).
- CAN-SPAM missing-mailing-address now raises an operational alarm banner on Send (B5 — and it is Ian's real open action).
- One more global contrast step for tertiary text.

## NEXT-SESSION QUEUE (path to ≥85, ranked by critic convergence)
1. **Port the Field's language INTO Queue/Analytics** (A's #1 all four rounds): unit-chart funnel built from the same light-dots (C5's idea — extends the covenant), poster-numeral page headers, ghost chart scaffolding for empty space so sparse pages still compose.
2. **Stage encoding beyond position** on the Field: brightness tier / halo weight per stage so cluster membership is readable at rest; collision avoidance between stacked labels; disclose position encoding in the legend.
3. **Follow-ups scanning structure** (B4): group by due date, collapse repeated chips, demote "Mark replied" to row-hover.
4. **Nav consolidation 9→5** (B, twice) — Ian's product-structure call.
5. **Atlas**: label the 19 single-city dots on hover-zoom or micro-labels (C misread real businesses as decorative); on-canvas "ghost = known network" tag during replay.
6. Overview/Analytics differentiation (B5): one canonical health page or clearly distinct jobs.
