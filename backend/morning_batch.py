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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import config
from db import Lead, PipelineRun, SessionLocal, init_db
from settings_store import apply_signature, load_settings
import web_targets
import website_signals
import web_offer
import gmail_drafts


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


def _reply_likelihood(signals: dict, email: str, category: str) -> float:
    """Rank how likely this prospect is to reply / be worth sending today.
    Rewards: a reachable email (can become a ready draft), a worse site (more
    need), strong concrete stats to cite, higher-value niche, confirmed-active."""
    score = 0.0
    score += 40 if email else 0
    score += signals.get("opportunity_score", 0) * 0.4
    highs = sum(1 for f in signals.get("findings", []) if f.get("sev") == "high")
    score += highs * 6
    score += _CATEGORY_VALUE.get((category or "generic").lower(), 5)
    if signals.get("reachable") or signals.get("social_only"):
        score += 5
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

    queued = skipped_existing = skipped_lowopp = errors = drafted = 0
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
                signals = t.get("signals") or website_signals.analyze(t.get("domain", ""))
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
                email = (t.get("contact_email") or "").strip() or signals.get("contact_email", "")
                candidates.append({
                    "t": t, "signals": signals, "email": email, "job_id": job_id,
                    "opportunity": opportunity,
                    "likelihood": _reply_likelihood(signals, email, t.get("category", "generic")),
                })

        # ── Rank: keep the best `count`, most-likely-to-reply first ──────────
        candidates.sort(key=lambda c: c["likelihood"], reverse=True)
        selected = candidates[:count]
        _log(run_log, f"{len(candidates)} good candidates -> keeping top {len(selected)} by reply-likelihood")

        gmail_on = getattr(config, "GMAIL_ENABLED", True) and gmail_drafts.is_configured()
        _log(run_log, "Gmail drafts: ON (real drafts in your inbox)" if gmail_on
             else "Gmail drafts: off (queueing with one-click compose links)")
        settings = load_settings()

        # ── Phase 2: write copy, create Gmail draft, persist ─────────────────
        for c in selected:
            t, signals, email = c["t"], c["signals"], c["email"]
            company = t["company_name"]
            category = t.get("category", "generic")
            city = t.get("city", "")
            suite = web_offer.generate_website_suite(
                company_name=company, city=city, category=category,
                contact_name="", signals=signals,
            )
            noun = web_offer._ctx(category)[0]
            issues = signals.get("headline_issues", [])
            host = website_signals.clean_host(t.get("domain", ""))

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
                contact_email=email,
                contact_source=("csv" if t.get("contact_email") else ("website" if email else "")),
                contact_verified="unverified" if email else "",
                verification_score=0,
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

        run.leads_scored = len(targets)
        run.leads_passed = len(candidates)
        run.leads_researched = queued
        run.emails_generated = queued
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        run.log = "\n".join(run_log)
        db.commit()

        _log(run_log, f"Done. {queued} leads {landing_status} | {drafted} Gmail drafts | "
                      f"{skipped_existing} already had | {skipped_lowopp} sites fine | {errors} errors")
        return {
            "ok": True, "queued": queued, "drafted": drafted, "status": landing_status,
            "skipped_existing": skipped_existing, "skipped_lowopp": skipped_lowopp,
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
