# WEB MACHINE — COMPLETE REDESIGN BRIEF
_Compiled 2026-07-09 via /brief. Goal-locked by Ian ("Yes — locked, go"), then upgraded to FULLY AUTONOMOUS ("no questions, finish, spawn judges, send it to me")._

## GOAL
Opening Web Machine feels like **watching your company grow** — the :5120 frontend becomes one instantly-recognizable identity where a living Business Field (home) and a separate Growth Atlas (US expansion + timeline replay) show agency health, momentum, and the next action at a glance, carried by the existing Revenue Universe particle engine.

## NON-GOALS
- NOT a dashboard/CRM reskin — no card grids, no admin-template feel, no HubSpot/Salesforce shape.
- NOT backend/pipeline changes — frontend redesign + one additive read-only endpoint only. Real data only; **never render projected money as money**.
- NOT "AI" aesthetics — never visualize AI; no cyberpunk, no neon-cyan holo, banned list enforced.
- NOT two visual languages — Field and Atlas are two experiences, ONE identity.

## DONE-BAR
Runs on the real DB (63 website_autopilot leads) at 60fps; engine architecture (single draw call, instanced attributes, LOD) comfortably scales to 100k nodes; real-click QA via a **visible** Playwright browser; **3 blind adversarial critics average ≥85/100** recorded in `docs/GRADES.md`. No ship under the gate.

**If any instruction below conflicts with the GOAL, the GOAL wins. Re-read the GOAL before every major decision.**

`/goal` condition: "Web Machine :5120 redesigned as Field + Atlas on real data, visible-Playwright QA'd, 3 blind critics avg ≥85 in docs/GRADES.md, committed."

---

## Identity for THIS project (Ian's directive overrides the house default palette)
- **Mostly monochrome**: deep black `#060607–#0a0a0b`, soft charcoal surfaces, white typography `#f5f5f6`, muted gray `#8b8b93`.
- **Red is reserved ONLY for meaningful business activity** (reply, meeting, won, live pulse). Never fill large areas with red. No beige, no excessive gradients, no thin decorative dividers.
- Still BANNED (house law, rejected 3×): neon-cyan holo HUD, scanlines, mono microtype, cursive gold slop, generic AI-template feel.
- **Typography IS the design**: enormous tabular numbers, tiny letterspaced uppercase labels, large whitespace, no decorative fonts.
- Motion: expensive — everything eases and glides, tiny inertia, no bounce/overshoot. Calm. 60fps.

## Ian's taste
Visual-first: spectacle and animation carry meaning; minimal on-screen text (title + one short tag). If a designer wouldn't stop scrolling to inspect it, iterate.

## Autonomy contract
Work continuously; if blocked, scaffold/mock/QA/polish and continue. Decide everything; zero questions mid-run. Ian is off-keyboard.

## Self-QA law
- Real clicks only, never `dispatchEvent` (masked an invisible-overlay bug once).
- WebGL/canvas: capture with a **visible** Playwright window (hidden preview tab freezes rAF). Vertical monitor DISPLAY2 at `--window-position=-1080,-578`.
- Screenshot every view, actually look, fix, re-shoot. Judges see evidence, not claims.

## Session durability
Maintain `SESSION_START.md` at repo root; commit at every working state (`"C:\Program Files\Git\cmd\git.exe"` or Bash tool — bare `git` in PowerShell is broken); update PROJECTS.md + vault + memory at milestones.

---

# BUILD SPEC

## Data truths (verified 2026-07-09)
- Backend FastAPI :8010 (RUNNING — reuse, never restart); frontend Vite+React+Tailwind :5120 (strictPort).
- 63 REAL leads = `source='website_autopilot'` (40 mock leads exist — ALWAYS filter them out).
- Real statuses today: 8 queued · 34 sent · 21 rejected · 0 replied/meeting/won. Earned = $0. Show that honestly.
- No lat/lng in DB; `job_location` is a real "City, ST" for all leads — 22 distinct real cities (Phoenix 18, Scottsdale 15, Mesa 11 + 19 single-lead cities nationwide). Atlas uses an embedded gazetteer of THESE cities (city-precision, deterministic per-lead jitter — honest).
- HQ: Englewood Cliffs, NJ (40.8859, −73.9532).
- Event timestamps are real: created_at (discovery), sent_at, replied_at, meeting_booked_at. History currently spans 2026-07-08 → 09; replay must adapt to any span.
- `/api/hud` already returns honest funnel counts; `/api/stats`, `/api/leads`, `/api/analytics` exist.

## 1. The Business Field (home, `/`)
The homepage is a living sculpture, not analytics. Port the `backend/hud.html` WebGL engine (raw WebGL, gl.POINTS, additive blend, easing camera, funnel-spiral centroids, hover-focus, cluster labels, monumental readout, ledger) into React (`src/field/`):
- One bright core node per REAL lead. Node size = automation_score; opacity = quality/sendability; drift = alive; pulse = activity in last 24h (last_action_at); permanent glow = won.
- Color: cool desaturated white for early stages → bright white at sent → **red family strictly for replied/meeting/won**. Replace all gold.
- Ambient dust density scales only with real counts (existing law in hud.html — keep it).
- Monumental readout = furthest REAL milestone (earned $ > meetings > replies > reached > drafts ready). Red treatment only when the milestone is real activity (reply or beyond).
- Progressive disclosure: minimal at a distance; hover a cluster → focus + counts; click locks.
- Keep Gmail sync button + live chip + 20s polling.

## 2. The Growth Atlas (`/atlas`)
Custom visualization, NOT a maps product. Canvas 2D on near-black:
- US silhouette + state borders as thin quiet strokes (us-atlas TopoJSON + d3-geo albersUsa, bundled — no runtime fetches).
- Every real business at its real city; HQ anchor in NJ. Outreach = a thin line that **grows from HQ to the business and permanently remains**. Replies ripple. Meetings raise prominence. Won = permanent landmark + strengthened connection.
- Timeline replay: drag to scrub the real event history; play button; the network re-grows. Editorial date + counts readout while scrubbing.
- New endpoint `GET /api/atlas` (read-only, additive): real leads with city coords + timestamps + status. No money fields.

## 3. Shell + workflow surfaces
- Thin icon rail (like hud.html's) + `WEB MACHINE` wordmark; routes: `/` Field, `/atlas` Atlas, `/overview` (old Dashboard), Queue/Send/Followups/Outreach/Analytics/Pipeline/Settings unchanged in function.
- Retheme all pages via tokens: kill indigo/cyan/green-yellow noise → monochrome + reserved red; editorial hierarchy (big numbers, tiny labels). Progressive density, no popups, no spinners on poll refreshes.

## 4. Performance
Single draw call for the Field; attribute buffers rebuilt only on data change; DPR capped at 2; rAF paused when tab hidden; Atlas redraws only on interaction/animation frames with dirty-checking. Comfortable at 100k instanced points.

## 5. The loops (before calling anything done)
Component/motion/typography loops: compare against Apple/Linear/Arc restraint; remove what communicates nothing; if it feels cheap, redo it. Then the judge loop: 3 blind critics, ≥85 avg, docs/GRADES.md, iterate.
