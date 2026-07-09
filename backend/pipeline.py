"""
Pipeline orchestrator — runs the full discovery → score → research → email pipeline.
Designed to run async in the background so the UI stays responsive.
"""
import json
import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from db import Lead, PipelineRun, SessionLocal
from scraper import scrape_jobs
from scorer import score_lead
from researcher import research_company
from email_gen import generate_emails
from enrichment import enrich
from niches import get_pack
import config

# Single-process state (this is a single-user tool)
_current_run: dict = {
    "status": "idle",
    "run_id": None,
    "log": [],
    "progress": {},
}


def get_run_status() -> dict:
    return _current_run.copy()


def _log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    _current_run["log"].append(entry)
    print(entry)


async def run_pipeline(queries: list[str] | None = None):
    global _current_run

    if _current_run["status"] == "running":
        return {"error": "Pipeline already running"}

    _current_run = {
        "status": "running",
        "run_id": None,
        "log": [],
        "progress": {
            "scraped": 0,
            "scored": 0,
            "passed": 0,
            "researched": 0,
            "emailed": 0,
        },
    }

    db = SessionLocal()
    run = PipelineRun()
    db.add(run)
    db.commit()
    db.refresh(run)
    _current_run["run_id"] = run.id

    try:
        # Step 1: Scrape
        _log("Starting job discovery...")
        active_queries = queries or config.JOB_QUERIES
        jobs = await scrape_jobs(active_queries, max_per_query=8)
        _log(f"Scraped {len(jobs)} raw job postings")
        _current_run["progress"]["scraped"] = len(jobs)
        run.jobs_scraped = len(jobs)
        db.commit()

        if not jobs:
            _log("No jobs found. Check RAPIDAPI_KEY or try manual entry.")
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            run.log = "\n".join(_current_run["log"])
            db.commit()
            _current_run["status"] = "idle"
            return

        # Deduplicate against existing leads
        existing_ids = {r[0] for r in db.query(Lead.job_id).all()}
        new_jobs = [j for j in jobs if j["job_id"] not in existing_ids]
        _log(f"{len(new_jobs)} new (filtered {len(jobs) - len(new_jobs)} duplicates)")

        capped = new_jobs[: config.MAX_LEADS_PER_RUN]

        # Step 2: Score all leads
        _log(f"Scoring {len(capped)} leads...")
        scored_leads = []
        for job in capped:
            result = score_lead(job["job_title"], job["job_description"], job["company_name"])
            niche_id = result.get("niche", "generic")
            lead = Lead(
                **{k: v for k, v in job.items()},
                automation_score=result["score"],
                score_breakdown=json.dumps(result),
                pain_category=result.get("pain_category", ""),
                pain_points=json.dumps(result.get("pain_points", [])),
                inferred_workflows=json.dumps(result.get("inferred_workflows", [])),
                score_reasoning=result.get("score_reasoning", ""),
                niche=niche_id,
                niche_label=result.get("niche_label", ""),
                offer=json.dumps(get_pack(niche_id).get("offer", {})),
                status="scored",
            )
            db.add(lead)
            scored_leads.append((lead, result))

        db.commit()
        _current_run["progress"]["scored"] = len(scored_leads)
        run.leads_scored = len(scored_leads)
        db.commit()

        # Step 3: Filter by threshold
        passing = [
            (lead, result)
            for lead, result in scored_leads
            if lead.automation_score >= config.MIN_SCORE_THRESHOLD
        ]
        _log(f"{len(passing)} leads passed threshold (>= {config.MIN_SCORE_THRESHOLD})")
        _current_run["progress"]["passed"] = len(passing)
        run.leads_passed = len(passing)
        db.commit()

        # Step 4: Deep process top leads
        to_process = passing[: config.LEADS_TO_DEEP_PROCESS]
        _log(f"Deep processing top {len(to_process)} leads...")

        for i, (lead, score_result) in enumerate(to_process):
            _log(f"  [{i+1}/{len(to_process)}] {lead.company_name} — score {lead.automation_score}")

            pain_points = json.loads(lead.pain_points or "[]")
            inferred_workflows = json.loads(lead.inferred_workflows or "[]")

            # Research
            profile = research_company(
                company_name=lead.company_name,
                company_domain=lead.company_domain or "",
                job_title=lead.job_title,
                job_description=lead.job_description or "",
                pain_points=pain_points,
                inferred_workflows=inferred_workflows,
            )
            lead.company_research = json.dumps(profile)
            lead.company_size = profile.get("company_size_estimate", "")
            lead.status = "researched"
            db.commit()
            _current_run["progress"]["researched"] = i + 1
            run.leads_researched = i + 1
            db.commit()

            # Discover + verify decision-maker contact (Apollo→Hunter→simulate→verify)
            if lead.company_domain:
                contact = await enrich(
                    company_name=lead.company_name,
                    domain=lead.company_domain,
                    company_size=lead.company_size or "",
                    decision_maker_profile=profile.get("decision_maker_profile", ""),
                )
                if contact:
                    lead.contact_name = contact["contact_name"]
                    lead.contact_title = contact["contact_title"]
                    lead.contact_email = contact["contact_email"]
                    lead.contact_source = contact["contact_source"]
                    lead.contact_verified = contact["contact_verified"]
                    lead.verification_score = contact["verification_score"]
                    lead.contact_confidence = contact["contact_confidence"]
                    lead.sendability = contact["sendability"]
                    db.commit()

            # Generate emails (niche-aware)
            emails = generate_emails(
                company_name=lead.company_name,
                contact_name=lead.contact_name or "",
                contact_title=lead.contact_title or "",
                job_title=lead.job_title,
                inferred_workflows=inferred_workflows,
                pain_points=pain_points,
                company_profile=profile,
                niche_id=lead.niche or "generic",
            )
            lead.subject_line = emails.get("subject_line", "")
            lead.email_body = emails.get("email_body", "")
            lead.email_long = emails.get("email_long", "")
            lead.mini_audit = emails.get("mini_audit", "")
            lead.follow_up_1 = emails.get("follow_up_1", "")
            lead.follow_up_2 = emails.get("follow_up_2", "")
            lead.breakup_email = emails.get("breakup_email", "")
            lead.objection_responses = json.dumps(emails.get("objection_responses", {}))
            lead.status = "queued"
            db.commit()

            _current_run["progress"]["emailed"] = i + 1
            run.emails_generated = i + 1
            db.commit()

            # Small pause to avoid hammering the API
            await asyncio.sleep(0.5)

        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        run.log = "\n".join(_current_run["log"])
        db.commit()

        total_queued = _current_run["progress"]["emailed"]
        _log(f"Pipeline complete. {total_queued} leads queued for review.")

    except Exception as e:
        _log(f"Pipeline failed: {e}")
        run.status = "failed"
        run.error = str(e)
        run.completed_at = datetime.now(timezone.utc)
        run.log = "\n".join(_current_run["log"])
        db.commit()

    finally:
        _current_run["status"] = "idle"
        db.close()
