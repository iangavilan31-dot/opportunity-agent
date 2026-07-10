# SESSION START — Web Machine (opportunity-agent)

_The stable entry point. Read this first after /clear._

## What this is
The Gavika web machine: finds real local businesses with weak websites, drafts personalized cold email, Ian reviews + sends ~10/day from the UI, replies tracked via Gmail. Backend FastAPI **:8010**, frontend React/Vite **:5120** (strictPort — if the port is busy the app is already running; reuse it).

## Current state (2026-07-09, Fable 5 session)
- **Complete frontend redesign shipped: "WEB MACHINE"** — monochrome + reserved-red identity per Ian's master design directive (BRIEF.md at repo root is the goal-locked brief).
  - `/` **The Field** — WebGL living sculpture, one glowing node per REAL lead (source=website_autopilot only), funnel-spiral clusters, two-pass bloom, hover a node → business card, ledger right, monumental real-milestone readout. Engine: `frontend/src/field/engine.ts`.
  - `/atlas` **Growth Atlas** — custom canvas US map (us-atlas TopoJSON + d3 albersUsa), real leads at real cities (gazetteer `frontend/src/lib/geo.ts`), permanent HQ→business connections on send, red ripples on reply, **drag timeline replay** of the real event history. Engine: `frontend/src/atlas/engine.ts`.
  - Rail shell (`components/Sidebar.tsx`), old Dashboard → `/overview`, all workflow pages rethemed.
- QA: `frontend/scripts/shoot.mjs` — VISIBLE Playwright, real clicks, screenshots → `docs/shots/`, fps + console sweep. 166fps, zero console errors.
- Blind critic grades: `docs/GRADES.md` (gate ≥85 avg).

## Laws (do not break)
- **Real data only.** Filter `source === 'website_autopilot'` in every visualization. Never render projected money as money — estimates must say "estimate". Red is reserved for real business activity (reply/meeting/won).
- DB timestamps are **UTC without offset** — parse via `ts()` in `frontend/src/lib/leads.ts`, never `new Date(raw)`.
- WebGL QA needs a **visible** browser (hidden tabs freeze rAF). Never `dispatchEvent`.
- Never `loseContext()` in engine cleanup (StrictMode remounts the same canvas → white screen).
- Emails cite only verifiable claims; never send to untrusted addresses; gmail_*token.json stay gitignored.
- Bare `git` in PowerShell is broken — use `"C:\Program Files\Git\cmd\git.exe"` or the Bash tool.

## Run
- Backend: `python -m uvicorn app:app --port 8010` from `backend/` (often already running).
- Frontend: `npm run dev` in `frontend/` → http://localhost:5120
- QA shoot: `node scripts/shoot.mjs` in `frontend/` (needs both servers).

## Open threads
- Growth execution (research/web-machine-growth-strategy-2026-07-09.md): parent-on-Stripe, CAN-SPAM mailing address in Settings, follow-up cadence, warmed domain.
- First reply/meeting/won will light the red language end-to-end (built, awaiting real events).
- Old hud at :8010/hud still exists (backend/hud.html) — superseded by `/` Field but untouched.
