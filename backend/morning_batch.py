"""
Morning autopilot — the "fires by itself at 9 AM" batch.

One command builds a fresh batch of website-offer drafts:

    source targets  ->  analyze each site (REAL signals)  ->  score the
    opportunity  ->  write a specific cold email  ->  queue it for review.

It writes straight to the SQLite DB, so the backend does NOT need to be running.
When you open the Opportunity Agent UI, the morning's drafts are already sitting
in the Queue with one-click Gmail send links. Safe by design: it only READS
public websites and generates local drafts — it never sends anything itself.

Run manually:   python morning_batch.py
Scheduled:      run_morning.ps1 (registered via Windows Task Scheduler at 9 AM)
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import config
from db import Lead, PipelineRun, SessionLocal, init_db
from settings_store import apply_signature, load_settings, web_profile
import web_targets
import website_signals
import web_offer
import gmail_drafts
import verify_email
import followups
import owner_name
import screenshots
import vision_audit


def _log(run_log: list[str], msg: str):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    run_log.append(line)
    print(line)


# Higher-ticket / more-urgent niches tend to invest in a site and reply.
_CATEGORY_VALUE = {
    "law": 14, "dental": 13, "medical": 12, "hvac": 12, "plumbing": 12,
    "electrician": 12, "chiropractor": 11, "roofing": 11, "vet": 10,
    "real_estate": 10, "auto": 9, "landscaping": 8, "cleaning": 8,
    "restaurant": 8, "salon": 7, "barber": 7, "gym": 7, "fitness": 7,
    "cafe": 6, "pet": 6, "generic": 5,
}


def _reply_likelihood(signals: dict, email: str, category: str, t: dict | None = None) -> float:
    """Rank how likely this prospect is to reply / be worth sending today.
    Rewards: a reachable email (can become a ready draft), a worse site (more
    need), strong concrete stats to cite, higher-value niche, confirmed-active.

    Research-driven boosts (2026-07-08 canon):
    - "Successful business + neglected site" is the ideal prospect — reviews are
      the free revenue/activity proxy (they've proven customers + reputation care).
    - Ad pixels on the site = already pays for marketing (rank-only; never cited).
    - A phone number keeps no-email leads worth queueing (callable)."""
    t = t or {}
    score = 0.0
    score += 40 if email else 0
    score += signals.get("opportunity_score", 0) * 0.4
    highs = sum(1 for f in signals.get("findings", []) if f.get("sev") == "high")
    score += highs * 6
    score += _CATEGORY_VALUE.get((category or "generic").lower(), 5)
    if signals.get("reachable") or signals.get("social_only"):
        score += 5
    reviews = int(t.get("review_count") or 0)
    rating = float(t.get("rating") or 0)
    if reviews >= 20 and rating >= 4.0:
        score += 12          # thriving business, neglected site — the sweet spot
        if reviews >= 50:
            score += 6
    elif rating >= 4.5:
        score += 6           # fast-mode Maps rarely carries the count; a strong
                             # rating alone still signals a real, liked business
    elif rating == 0 and not t.get("domain"):
        score -= 5           # no site AND no rating: may not be a real buyer yet
    if signals.get("marketing_pixels"):
        score += 8
    if not email and t.get("phone"):
        score += 3
    return round(score, 1)


def run(limit: int | None = None, auto_approve: bool | None = None) -> dict:
    """Generate a fresh batch of website-offer drafts. Returns a summary dict."""
    init_db()
    count = limit or getattr(config, "AUTOPILOT_TARGET_COUNT", 50)
    min_opp = getattr(config, "AUTOPILOT_MIN_OPPORTUNITY", 40)
    if auto_approve is None:
        auto_approve = getattr(config, "AUTOPILOT_AUTO_APPROVE", False)
    landing_status = "approved" if auto_approve else "queued"

    run_log: list[str] = []
    db = SessionLocal()
    run = PipelineRun()
    db.add(run)
    db.commit()
    db.refresh(run)

    queued = skipped_existing = skipped_lowopp = skipped_lang = errors = drafted = 0
    downranked_modern = modern_drafted = vision_used = 0
    try:
        max_analyze = getattr(config, "AUTOPILOT_MAX_ANALYZE", 150)
        targets, source = web_targets.load_targets(limit=max_analyze)
        _log(run_log, f"Loaded {len(targets)} candidates (source: {source})")
        run.jobs_scraped = len(targets)
        db.commit()

        existing_ids = {r[0] for r in db.query(Lead.job_id).all()}

        # Dedup up front — only analyze businesses we haven't processed before.
        todo = []
        for t in targets:
            job_id = web_targets.target_id(t["company_name"], t.get("domain", ""))
            if job_id in existing_ids:
                skipped_existing += 1
            else:
                todo.append((t, job_id))

        # ── Phase 1: analyze candidates CONCURRENTLY, score reply-likelihood ──
        workers = getattr(config, "AUTOPILOT_WORKERS", 12)
        _log(run_log, f"Analyzing {len(todo)} new candidates with {workers} workers...")

        def _analyze_one(pair):
            t, job_id = pair
            try:
                signals = t.get("signals") or website_signals.analyze(
                    t.get("domain", ""), name_hint=t.get("company_name", ""))
                # Trust gap: strong Google reviews + none shown on the site.
                # Runs before the opportunity gate — it's a conversion defect.
                website_signals.apply_trust_gap(
                    signals, t.get("rating"), t.get("review_count"))
                return (t, job_id, signals, None)
            except Exception as e:
                return (t, job_id, None, str(e))

        candidates: list[dict] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for t, job_id, signals, err in pool.map(_analyze_one, todo):
                if err:
                    errors += 1
                    continue
                opportunity = int(signals.get("opportunity_score", 0))
                if opportunity < min_opp:
                    skipped_lowopp += 1
                    continue
                # Site definitively in a language the outreach isn't written in
                # -> an English pitch reads as spam; skip.
                lang = signals.get("language", "en")
                if lang not in getattr(config, "OUTREACH_LANGS", ["en"]):
                    skipped_lang += 1
                    continue
                email = (t.get("contact_email") or "").strip() or signals.get("contact_email", "")
                # Carry the Maps qualification data into the stored signals so the
                # UI/notes can show it ("4.6 stars, 120 reviews, has a phone").
                if t.get("review_count") or t.get("rating") or t.get("phone"):
                    signals["maps"] = {"rating": t.get("rating"),
                                       "review_count": t.get("review_count"),
                                       "phone": t.get("phone", "")}
                candidates.append({
                    "t": t, "signals": signals, "email": email, "job_id": job_id,
                    "opportunity": opportunity,
                    "likelihood": _reply_likelihood(signals, email, t.get("category", "generic"), t),
                })

        # ── Rank most-likely-to-reply first ─────────────────────────────────
        candidates.sort(key=lambda c: c["likelihood"], reverse=True)

        vision_on = bool(getattr(config, "OPENAI_API_KEY", "")) and getattr(config, "VISION_ENABLED", True)
        # When the vision gate is on, screenshot a BIGGER pool than `count`: the
        # gate drops sites that actually look modern (the heuristic scorer
        # over-flags them), so we need extra candidates to refill to `count`
        # genuinely-bad-looking prospects.
        pool_n = min(len(candidates),
                     getattr(config, "VISION_GATE_POOL", 90) if vision_on else count)
        gate_pool = candidates[:pool_n]
        _log(run_log, f"{len(candidates)} good candidates -> "
                      f"{'vision-gating top ' + str(pool_n) if vision_on else 'keeping top ' + str(len(gate_pool))} "
                      f"(target {count} drafts)")

        gmail_on = getattr(config, "GMAIL_ENABLED", True) and gmail_drafts.is_configured()
        _log(run_log, "Gmail drafts: ON (real drafts in your inbox)" if gmail_on
             else "Gmail drafts: off (queueing with one-click compose links)")
        settings = web_profile(load_settings())

        # ── Phase 1.5: screenshot the pool FIRST (feeds the vision gate/opener
        #    and the contact sheet — one capture, several uses) ───────────────
        shots_by_job: dict[str, str] = {}
        contact_sheet = None
        shot_items = []
        if getattr(config, "SCREENSHOTS_ENABLED", True):
            for c in gate_pool:
                host = website_signals.clean_host(c["t"].get("domain", ""))
                url = (f"https://{host}" if host and c["signals"].get("reachable") else "")
                shot_items.append({"job_id": c["job_id"], "company": c["t"]["company_name"],
                                   "url": url, "issues": c["signals"].get("headline_issues", [])})
            try:
                contact_sheet, shot_dir = screenshots.capture(
                    shot_items, max_shots=getattr(config, "VISION_GATE_POOL", 90),
                    log=lambda m: _log(run_log, m))
                if shot_dir:
                    for it in shot_items:
                        mob = (it.get("shots") or {}).get("mobile")
                        if mob:
                            shots_by_job[it["job_id"]] = os.path.join(shot_dir, mob)
            except Exception as e:
                _log(run_log, f"Screenshots failed (non-fatal): {e}")

        # ── Phase 1.6: visual gate = DOWNRANK, not drop ─────────────────────
        # Real eyes on each screenshot BEFORE we pick the daily set. A 'modern'
        # verdict means the heuristic over-flagged a decent site — but Ian would
        # still email them at low priority, so we subtract a big penalty (they
        # sink below every dated site) instead of dropping the lead. 'dated'
        # verdicts hand back the visible flaws to sharpen the opener.
        if vision_on:
            _log(run_log, f"Visual gate: ON ({getattr(config, 'VISION_MODEL', 'gpt-4o-mini')}) "
                          f"— downranks modern-looking sites, sharpens openers on dated ones")
            penalty = getattr(config, "VISION_MODERN_PENALTY", 1000.0)
            for c in gate_pool:
                shot = shots_by_job.get(c["job_id"])
                if not shot:
                    c["visual_verdict"] = "unknown"
                    c["visual_notes"] = []
                    continue
                try:
                    a = vision_audit.assess(shot)
                except Exception:
                    a = {"verdict": "unknown", "problems": []}
                c["visual_verdict"] = a["verdict"]
                c["visual_notes"] = a.get("problems", []) or []
                if a["verdict"] == "modern":
                    c["likelihood"] = round(c["likelihood"] - penalty, 1)
                    downranked_modern += 1
                elif c["visual_notes"]:
                    vision_used += 1
            # Re-rank now that modern sites carry their penalty; dated stay put.
            gate_pool.sort(key=lambda c: c["likelihood"], reverse=True)
            _log(run_log, f"Visual gate: downranked {downranked_modern} modern-looking "
                          f"sites, sharpened {vision_used} openers")

        # ── Phase 2: gate on looks, write copy, create Gmail draft, persist ──
        for c in gate_pool:
            if queued >= count:
                break  # hit the daily target of genuinely-bad-site drafts
            t, signals, email = c["t"], c["signals"], c["email"]
            company = t["company_name"]
            category = t.get("category", "generic")
            city = t.get("city", "")
            # Owner name (selected leads only — 1-2 extra fetches each). A found
            # name turns the opener into "Hi Goli," which measurably lifts
            # replies; abstains rather than guess.
            try:
                contact = owner_name.find(company, t.get("domain", "")) or ""
            except Exception:
                contact = ""
            # Visual gate already ran in Phase 1.6: 'modern' sites were penalised
            # to the bottom of the ranking (drafted only if the pool is short),
            # 'dated' sites handed back visible flaws for the opener. If a modern
            # site DID surface into the daily set, note it so Ian sees why.
            visual_notes = c.get("visual_notes", [])
            if c.get("visual_verdict") == "modern":
                modern_drafted += 1  # pool was short — a downranked site filled a slot
            suite = web_offer.generate_website_suite(
                company_name=company, city=city, category=category,
                contact_name=contact, signals=signals, visual_notes=visual_notes,
            )
            noun = web_offer._ctx(category)[0]
            issues = signals.get("headline_issues", [])
            host = website_signals.clean_host(t.get("domain", ""))

            # Verify before drafting — bounces (not volume) are what get a small
            # Gmail sender flagged. Invalid -> keep the lead, drop the address.
            verification = {"level": "", "ok": False}
            if email:
                verification = verify_email.verify(email)
                if not verification["ok"]:
                    _log(run_log, f"    dropped invalid email for {company}: {email}")
                    email = ""
                    c["email"] = ""

            draft_note = None
            if gmail_on and email:
                draft_id = gmail_drafts.create_draft(
                    to=email, subject=suite["subject_line"],
                    body=apply_signature(suite["email_body"], settings))
                if draft_id:
                    drafted += 1
                    draft_note = f"gmail_draft:{draft_id}"

            lead = Lead(
                source="website_autopilot",
                job_id=c["job_id"],
                job_url=(f"https://{host}" if host else ""),
                company_name=company,
                company_domain=host,
                job_location=city,
                job_title=f"Website — {noun}",
                job_description="Website audit: " + "; ".join(issues) if issues else "Website audit",
                automation_score=c["opportunity"],
                score_breakdown=json.dumps(signals),
                pain_category="website",
                pain_points=json.dumps([f["msg"] for f in signals.get("findings", [])]),
                inferred_workflows=json.dumps(issues),
                score_reasoning="; ".join(issues),
                niche="web_design",
                niche_label="Website",
                offer=json.dumps(suite["offer"]),
                contact_name=contact,
                contact_email=email,
                contact_source=("csv" if t.get("contact_email") else ("website" if email else "")),
                contact_verified=(verification["level"] or "unverified") if email else "",
                verification_score={"valid": 90, "risky": 55}.get(verification["level"], 0),
                contact_confidence=55 if email else 0,
                sendability="review",
                subject_line=suite["subject_line"],
                email_body=suite["email_body"],
                email_long=suite["email_long"],
                mini_audit=suite["mini_audit"],
                follow_up_1=suite["follow_up_1"],
                follow_up_2=suite["follow_up_2"],
                breakup_email=suite["breakup_email"],
                objection_responses=json.dumps(suite["objection_responses"]),
                notes=draft_note,
                status=landing_status,
            )
            db.add(lead)
            db.commit()
            existing_ids.add(c["job_id"])
            queued += 1
            tag = "DRAFTED" if draft_note else "queued"
            _log(run_log, f"  + [{c['likelihood']:.0f}] {company} (opp {c['opportunity']}) {tag} - "
                          f"{issues[0] if issues else 'audited'}")

        # ── Phase 3: follow-up cadence (day +3 / +10) on previously sent leads ──
        try:
            fu = followups.process(db, log=lambda m: _log(run_log, m))
            if "skipped" in fu:
                _log(run_log, f"Follow-ups: skipped ({fu['skipped']})")
            else:
                _log(run_log, f"Follow-ups: {fu['sends_detected']} sends detected, "
                              f"{fu['fu1_drafted']} FU1 + {fu['fu2_drafted']} FU2 drafted "
                              f"({fu['tracked']} leads tracked)")
        except Exception as e:
            _log(run_log, f"Follow-ups failed (non-fatal): {e}")

        # ── Screenshots + vision were done in Phase 1.5; just surface results ──
        if contact_sheet:
            _log(run_log, f"Visual grading sheet ready: {contact_sheet}")
        if vision_on:
            _log(run_log, f"Visual gate: downranked {downranked_modern} modern-looking sites "
                          f"({modern_drafted} still drafted to fill the target), "
                          f"sharpened {vision_used} openers from real screenshots")

        run.leads_scored = len(targets)
        run.leads_passed = len(candidates)
        run.leads_researched = queued
        run.emails_generated = queued
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        run.log = "\n".join(run_log)
        db.commit()

        _log(run_log, f"Done. {queued} leads {landing_status} | {drafted} Gmail drafts | "
                      f"{skipped_existing} already had | {skipped_lowopp} sites fine | "
                      f"{downranked_modern} modern downranked ({modern_drafted} drafted) | "
                      f"{skipped_lang} non-English | {errors} errors")
        return {
            "ok": True, "queued": queued, "drafted": drafted, "status": landing_status,
            "skipped_existing": skipped_existing, "skipped_lowopp": skipped_lowopp,
            "downranked_modern": downranked_modern, "modern_drafted": modern_drafted,
            "skipped_lang": skipped_lang,
            "errors": errors, "source": source, "run_id": run.id,
        }
    except Exception as e:
        run.status = "failed"
        run.error = str(e)
        run.completed_at = datetime.now(timezone.utc)
        run.log = "\n".join(run_log)
        db.commit()
        _log(run_log, f"Batch failed: {e}")
        return {"ok": False, "error": str(e), "queued": queued}
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print(f"Opportunity Agent — morning autopilot  {datetime.now():%Y-%m-%d %H:%M}")
    print("=" * 60)
    summary = run()
    print("-" * 60)
    print(json.dumps(summary, indent=2))
