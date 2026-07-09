import json
import asyncio
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

import config
from db import init_db, get_db, Lead, PipelineRun
import pipeline as pipeline_module
from quality import check_lead
from settings_store import load_settings, save_settings, apply_signature, build_signature, is_configured

app = FastAPI(title="Opportunity Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL, "http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class LeadUpdate(BaseModel):
    subject_line: Optional[str] = None
    email_body: Optional[str] = None
    email_long: Optional[str] = None
    mini_audit: Optional[str] = None
    follow_up_1: Optional[str] = None
    follow_up_2: Optional[str] = None
    breakup_email: Optional[str] = None
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class ManualLead(BaseModel):
    company_name: str
    company_domain: Optional[str] = None
    job_title: str
    job_description: Optional[str] = None
    job_location: Optional[str] = None
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None


class PipelineStart(BaseModel):
    queries: Optional[list[str]] = None


class BulkAction(BaseModel):
    ids: list[int]


class SenderProfile(BaseModel):
    sender_name: Optional[str] = None
    positioning: Optional[str] = None
    calendar_link: Optional[str] = None
    sender_email: Optional[str] = None


# ─── Utils ────────────────────────────────────────────────────────────────────

def _gmail_compose(to: str, subject: str, body: str) -> str:
    from urllib.parse import quote
    return (
        "https://mail.google.com/mail/?view=cm&fs=1"
        f"&to={quote(to or '')}&su={quote(subject or '')}&body={quote(body or '')}"
    )


def _gmail_url(lead: Lead) -> str:
    return _gmail_compose(lead.contact_email or "", lead.subject_line or "", apply_signature(lead.email_body))


# Follow-up cadence (days to wait at each stage before the next is due)
FOLLOWUP_CADENCE = {0: 3, 1: 4, 2: 7}  # stage -> days since last action
FOLLOWUP_FIELD = {0: "follow_up_1", 1: "follow_up_2", 2: "breakup_email"}
FOLLOWUP_LABEL = {0: "Follow-up 1", 1: "Follow-up 2", 2: "Breakup"}


def _lead_to_dict(lead: Lead) -> dict:
    def safe_json(val, default=None):
        if val is None:
            return default if default is not None else []
        try:
            return json.loads(val)
        except Exception:
            return default if default is not None else []

    return {
        "id": lead.id,
        "source": lead.source,
        "job_id": lead.job_id,
        "job_url": lead.job_url,
        "company_name": lead.company_name,
        "company_domain": lead.company_domain,
        "company_size": lead.company_size,
        "company_industry": lead.company_industry,
        "company_research": safe_json(lead.company_research) if isinstance(lead.company_research, str) and lead.company_research.startswith("{") else lead.company_research,
        "job_title": lead.job_title,
        "job_description": lead.job_description,
        "job_location": lead.job_location,
        "job_posted_at": lead.job_posted_at.isoformat() if lead.job_posted_at else None,
        "automation_score": lead.automation_score,
        "pain_category": lead.pain_category,
        "pain_points": safe_json(lead.pain_points),
        "inferred_workflows": safe_json(lead.inferred_workflows),
        "score_reasoning": lead.score_reasoning,
        "niche": lead.niche,
        "niche_label": lead.niche_label,
        "offer": safe_json(lead.offer, default={}),
        "contact_name": lead.contact_name,
        "contact_title": lead.contact_title,
        "contact_email": lead.contact_email,
        "contact_source": lead.contact_source,
        "contact_verified": lead.contact_verified,
        "verification_score": lead.verification_score,
        "contact_confidence": lead.contact_confidence,
        "sendability": lead.sendability,
        "subject_line": lead.subject_line,
        "email_body": apply_signature(lead.email_body),
        "email_long": apply_signature(lead.email_long),
        "mini_audit": apply_signature(lead.mini_audit),
        "follow_up_1": apply_signature(lead.follow_up_1),
        "follow_up_2": apply_signature(lead.follow_up_2),
        "breakup_email": apply_signature(lead.breakup_email),
        "objection_responses": safe_json(lead.objection_responses, default={}),
        "gmail_compose_url": _gmail_url(lead),
        "quality": check_lead(lead),
        "status": lead.status,
        "sent_at": lead.sent_at.isoformat() if lead.sent_at else None,
        "opened_at": lead.opened_at.isoformat() if lead.opened_at else None,
        "replied_at": lead.replied_at.isoformat() if lead.replied_at else None,
        "meeting_booked_at": lead.meeting_booked_at.isoformat() if lead.meeting_booked_at else None,
        "notes": lead.notes,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
    }


# ─── Stats ────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(Lead).count()
    queued = db.query(Lead).filter(Lead.status == "queued").count()
    approved = db.query(Lead).filter(Lead.status == "approved").count()
    sent = db.query(Lead).filter(Lead.status == "sent").count()
    replied = db.query(Lead).filter(Lead.status == "replied").count()
    meetings = db.query(Lead).filter(Lead.status == "meeting").count()
    rejected = db.query(Lead).filter(Lead.status == "rejected").count()

    # Follow-ups due now
    followups_due = 0
    for l in db.query(Lead).filter(Lead.status == "sent", Lead.followup_stage < 3).all():
        stage = l.followup_stage or 0
        anchor = l.last_action_at or l.sent_at
        if _days_since(anchor) >= FOLLOWUP_CADENCE.get(stage, 7):
            followups_due += 1

    last_run = db.query(PipelineRun).order_by(PipelineRun.id.desc()).first()

    # Niche breakdown (count + avg score per niche)
    from sqlalchemy import func
    niche_rows = (
        db.query(Lead.niche, Lead.niche_label, func.count(Lead.id), func.avg(Lead.automation_score))
        .filter(Lead.niche.isnot(None))
        .group_by(Lead.niche)
        .all()
    )
    niches = sorted(
        [
            {"niche": n, "label": label or n, "count": cnt, "avg_score": round(avg or 0, 1)}
            for n, label, cnt, avg in niche_rows
        ],
        key=lambda x: x["count"], reverse=True,
    )

    return {
        "total_leads": total,
        "queued": queued,
        "approved": approved,
        "sent": sent,
        "replied": replied,
        "meetings": meetings,
        "rejected": rejected,
        "reply_rate": round(replied / sent * 100, 1) if sent > 0 else 0,
        "meeting_rate": round(meetings / replied * 100, 1) if replied > 0 else 0,
        "followups_due": followups_due,
        "sender_configured": is_configured(),
        "niches": niches,
        "last_run": {
            "id": last_run.id,
            "status": last_run.status,
            "scraped": last_run.jobs_scraped,
            "queued": last_run.emails_generated,
            "started_at": last_run.started_at.isoformat() if last_run.started_at else None,
        } if last_run else None,
    }


# ─── Leads ────────────────────────────────────────────────────────────────────

@app.get("/api/leads")
def list_leads(
    status: Optional[str] = None,
    search: Optional[str] = None,
    niche: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    q = db.query(Lead)

    if status:
        statuses = status.split(",")
        q = q.filter(Lead.status.in_(statuses))

    if niche:
        q = q.filter(Lead.niche == niche)

    if search:
        term = f"%{search}%"
        q = q.filter(
            Lead.company_name.ilike(term) | Lead.job_title.ilike(term)
        )

    total = q.count()
    leads = q.order_by(Lead.automation_score.desc(), Lead.created_at.desc()) \
             .offset((page - 1) * limit) \
             .limit(limit) \
             .all()

    return {
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "leads": [_lead_to_dict(l) for l in leads],
    }


@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _lead_to_dict(lead)


@app.patch("/api/leads/{lead_id}")
def update_lead(lead_id: int, body: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(lead, field, value)

    lead.updated_at = datetime.now(timezone.utc)
    db.commit()
    return _lead_to_dict(lead)


@app.post("/api/leads/{lead_id}/approve")
def approve_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.status = "approved"
    lead.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "status": "approved"}


@app.post("/api/leads/{lead_id}/reject")
def reject_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.status = "rejected"
    lead.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "status": "rejected"}


@app.post("/api/leads/{lead_id}/mark-sent")
def mark_sent(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.status = "sent"
    lead.sent_at = datetime.now(timezone.utc)
    lead.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "status": "sent"}


@app.post("/api/leads/{lead_id}/mark-replied")
def mark_replied(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.status = "replied"
    lead.replied_at = datetime.now(timezone.utc)
    lead.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "status": "replied"}


@app.post("/api/leads/{lead_id}/mark-meeting")
def mark_meeting(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.status = "meeting"
    lead.meeting_booked_at = datetime.now(timezone.utc)
    lead.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "status": "meeting"}


@app.post("/api/leads/manual")
def add_manual_lead(body: ManualLead, db: Session = Depends(get_db)):
    import hashlib
    job_id = hashlib.md5(f"manual::{body.company_name}::{body.job_title}".encode()).hexdigest()

    lead = Lead(
        source="manual",
        job_id=job_id,
        company_name=body.company_name,
        company_domain=body.company_domain,
        job_title=body.job_title,
        job_description=body.job_description,
        job_location=body.job_location,
        contact_name=body.contact_name,
        contact_title=body.contact_title,
        contact_email=body.contact_email,
        notes=body.notes,
        status="new",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return _lead_to_dict(lead)


@app.get("/api/leads/{lead_id}/replies")
def lead_reply_playbook(lead_id: int, db: Session = Depends(get_db)):
    from reply_playbooks import build_playbook
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    playbook = build_playbook(lead, lead.niche or "generic")
    # Fill calendar link from sender profile
    settings = load_settings()
    cal = (settings.get("calendar_link") or "").strip()
    cal_display = cal if cal.startswith("http") else (f"https://{cal}" if cal else "[your calendar link]")
    for v in playbook.values():
        v["response"] = apply_signature(v["response"]).replace("{calendar_link}", cal_display)
    return {"lead_id": lead_id, "company": lead.company_name, "niche": lead.niche_label, "playbook": playbook}


class ManualContact(BaseModel):
    contact_name: Optional[str] = ""
    contact_title: Optional[str] = ""
    contact_email: str


@app.post("/api/leads/{lead_id}/set-contact")
async def set_contact(lead_id: int, body: ManualContact, db: Session = Depends(get_db)):
    """Manually attach a contact (e.g. pasted from Apollo's free web app or LinkedIn).
    Runs the same verification + confidence scoring as automated discovery."""
    from enrichment import _verify, _lead_confidence, _sendability
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    verification = await _verify(body.contact_email, "manual")
    confidence = _lead_confidence(body.contact_title or "", 80, verification["score"])
    lead.contact_name = body.contact_name or ""
    lead.contact_title = body.contact_title or ""
    lead.contact_email = body.contact_email
    lead.contact_source = "manual"
    lead.contact_verified = verification["status"]
    lead.verification_score = verification["score"]
    lead.contact_confidence = confidence
    lead.sendability = _sendability(body.contact_email, verification["status"], confidence)
    lead.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "sendability": lead.sendability, "contact_confidence": confidence,
            "contact_verified": lead.contact_verified}


@app.post("/api/leads/{lead_id}/enrich")
async def reenrich_lead(lead_id: int, db: Session = Depends(get_db)):
    from enrichment import enrich
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.company_domain:
        raise HTTPException(status_code=400, detail="No company domain to search")
    profile = {}
    try:
        profile = json.loads(lead.company_research) if lead.company_research else {}
    except Exception:
        pass
    contact = await enrich(
        company_name=lead.company_name,
        domain=lead.company_domain,
        company_size=lead.company_size or "",
        decision_maker_profile=profile.get("decision_maker_profile", "") if isinstance(profile, dict) else "",
    )
    if not contact:
        return {"ok": False, "message": "No contact found"}
    lead.contact_name = contact["contact_name"]
    lead.contact_title = contact["contact_title"]
    lead.contact_email = contact["contact_email"]
    lead.contact_source = contact["contact_source"]
    lead.contact_verified = contact["contact_verified"]
    lead.verification_score = contact["verification_score"]
    lead.contact_confidence = contact["contact_confidence"]
    lead.sendability = contact["sendability"]
    lead.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, **contact}


@app.delete("/api/leads/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead)
    db.commit()
    return {"ok": True}


# ─── Pipeline ─────────────────────────────────────────────────────────────────

@app.post("/api/pipeline/run")
async def start_pipeline(body: PipelineStart, background_tasks: BackgroundTasks):
    status = pipeline_module.get_run_status()
    if status["status"] == "running":
        return {"error": "Pipeline already running"}

    background_tasks.add_task(pipeline_module.run_pipeline, body.queries)
    return {"ok": True, "message": "Pipeline started"}


@app.get("/api/pipeline/status")
def pipeline_status():
    return pipeline_module.get_run_status()


class MorningRun(BaseModel):
    limit: Optional[int] = None
    auto_approve: Optional[bool] = None


@app.post("/api/pipeline/morning")
def start_morning_batch(body: MorningRun, background_tasks: BackgroundTasks):
    """Website-selling autopilot: build a fresh batch of website-offer drafts.
    This is what the 9 AM scheduled task runs (there, straight via morning_batch.py)."""
    import morning_batch
    background_tasks.add_task(morning_batch.run, body.limit, body.auto_approve)
    return {"ok": True, "message": "Morning batch started"}


@app.get("/api/settings")
def get_settings():
    s = load_settings()
    return {**s, "configured": is_configured(), "signature_preview": build_signature(s)}


@app.put("/api/settings")
def update_settings(body: SenderProfile):
    saved = save_settings(body.model_dump(exclude_none=True))
    return {**saved, "configured": is_configured(), "signature_preview": build_signature(saved)}


@app.get("/api/pipeline/history")
def pipeline_history(db: Session = Depends(get_db)):
    runs = db.query(PipelineRun).order_by(PipelineRun.id.desc()).limit(20).all()
    return [
        {
            "id": r.id,
            "status": r.status,
            "scraped": r.jobs_scraped,
            "scored": r.leads_scored,
            "passed": r.leads_passed,
            "researched": r.leads_researched,
            "emailed": r.emails_generated,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "error": r.error,
        }
        for r in runs
    ]


# ─── Bulk actions ─────────────────────────────────────────────────────────────

@app.post("/api/leads/bulk-approve")
def bulk_approve(body: BulkAction, db: Session = Depends(get_db)):
    n = (
        db.query(Lead)
        .filter(Lead.id.in_(body.ids))
        .update({Lead.status: "approved", Lead.updated_at: datetime.now(timezone.utc)},
                synchronize_session=False)
    )
    db.commit()
    return {"ok": True, "approved": n}


@app.post("/api/leads/bulk-reject")
def bulk_reject(body: BulkAction, db: Session = Depends(get_db)):
    n = (
        db.query(Lead)
        .filter(Lead.id.in_(body.ids))
        .update({Lead.status: "rejected", Lead.updated_at: datetime.now(timezone.utc)},
                synchronize_session=False)
    )
    db.commit()
    return {"ok": True, "rejected": n}


# ─── Drafts / send flow ─────────────────────────────────────────────────────

@app.get("/api/drafts")
def get_drafts(status: str = "approved", db: Session = Depends(get_db)):
    """Approved leads ready to send, with one-click Gmail compose URLs."""
    statuses = status.split(",")
    leads = (
        db.query(Lead)
        .filter(Lead.status.in_(statuses))
        .order_by(Lead.automation_score.desc())
        .all()
    )
    return [
        {
            "id": l.id,
            "company_name": l.company_name,
            "contact_name": l.contact_name,
            "contact_email": l.contact_email,
            "subject_line": l.subject_line,
            "email_body": apply_signature(l.email_body),
            "automation_score": l.automation_score,
            "status": l.status,
            "gmail_compose_url": _gmail_url(l),
            "has_email": bool(l.contact_email),
        }
        for l in leads
    ]


def _build_eml(lead: Lead) -> str:
    to = lead.contact_email or "recipient@example.com"
    subject = lead.subject_line or ""
    body = apply_signature(lead.email_body)
    return (
        f"To: {to}\r\n"
        f"Subject: {subject}\r\n"
        f"X-Unsent: 1\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"{body}\r\n"
    )


@app.get("/api/leads/{lead_id}/eml")
def download_eml(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    eml = _build_eml(lead)
    safe = "".join(c for c in (lead.company_name or "draft") if c.isalnum() or c in " -_")[:40]
    return Response(
        content=eml,
        media_type="message/rfc822",
        headers={"Content-Disposition": f'attachment; filename="{safe}.eml"'},
    )


# ─── Follow-up sequencing ───────────────────────────────────────────────────

def _days_since(dt) -> float:
    if not dt:
        return 999.0
    now = datetime.now(timezone.utc)
    # SQLite returns naive datetimes; treat as UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds() / 86400.0


@app.get("/api/followups")
def get_followups(db: Session = Depends(get_db)):
    """Sent leads that haven't replied, bucketed into due-now and upcoming."""
    leads = (
        db.query(Lead)
        .filter(Lead.status == "sent", Lead.followup_stage < 3)
        .order_by(Lead.sent_at.asc())
        .all()
    )

    due, upcoming = [], []
    for l in leads:
        stage = l.followup_stage or 0
        wait = FOLLOWUP_CADENCE.get(stage, 7)
        anchor = l.last_action_at or l.sent_at
        days = _days_since(anchor)
        field = FOLLOWUP_FIELD[stage]
        body = apply_signature(getattr(l, field) or "")
        orig = l.subject_line or ""
        subject = orig if orig.lower().startswith("re:") else f"Re: {orig}"
        item = {
            "id": l.id,
            "company_name": l.company_name,
            "contact_name": l.contact_name,
            "contact_email": l.contact_email,
            "niche_label": l.niche_label,
            "stage": stage,
            "stage_label": FOLLOWUP_LABEL[stage],
            "days_waiting": round(days, 1),
            "days_until_due": max(0, round(wait - days, 1)),
            "subject_line": subject,
            "body": body,
            "gmail_compose_url": _gmail_compose(l.contact_email or "", subject, body),
            "has_email": bool(l.contact_email),
        }
        (due if days >= wait else upcoming).append(item)

    upcoming.sort(key=lambda x: x["days_until_due"])
    return {"due": due, "upcoming": upcoming, "due_count": len(due)}


@app.post("/api/leads/{lead_id}/advance-followup")
def advance_followup(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.followup_stage = (lead.followup_stage or 0) + 1
    lead.last_action_at = datetime.now(timezone.utc)
    lead.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "followup_stage": lead.followup_stage}


# ─── Analytics ───────────────────────────────────────────────────────────────

# Realistic close probability by current stage (cold outreach → automation consulting)
STAGE_CLOSE_PROB = {
    "queued": 0.02, "approved": 0.03, "email_generated": 0.02,
    "scored": 0.01, "researched": 0.01,
    "sent": 0.05, "replied": 0.25, "meeting": 0.45, "closed": 1.0,
}


@app.get("/api/analytics")
def analytics(db: Session = Depends(get_db)):
    leads = db.query(Lead).all()

    # Cumulative funnel — since status is terminal, downstream stages roll up.
    cnt = {s: 0 for s in ["queued", "approved", "sent", "replied", "meeting", "closed"]}
    for l in leads:
        if l.status in cnt:
            cnt[l.status] += 1
    funnel = {
        "queued": cnt["queued"],
        "approved": cnt["approved"] + cnt["sent"] + cnt["replied"] + cnt["meeting"] + cnt["closed"],
        "sent": cnt["sent"] + cnt["replied"] + cnt["meeting"] + cnt["closed"],
        "replied": cnt["replied"] + cnt["meeting"] + cnt["closed"],
        "meeting": cnt["meeting"] + cnt["closed"],
    }

    # Pipeline value
    def acv(l) -> float:
        try:
            offer = json.loads(l.offer) if l.offer else {}
        except Exception:
            offer = {}
        setup = offer.get("setup", 0) or 0
        monthly = offer.get("monthly", 0) or 0
        return setup + monthly * 12  # first-year value

    active = [l for l in leads if l.status not in ("rejected",)]
    total_potential = sum(acv(l) for l in active)
    weighted = sum(acv(l) * STAGE_CLOSE_PROB.get(l.status, 0.01) for l in active)

    # Value by stage
    value_by_stage = {}
    for l in active:
        value_by_stage.setdefault(l.status, {"count": 0, "potential": 0.0})
        value_by_stage[l.status]["count"] += 1
        value_by_stage[l.status]["potential"] += acv(l)

    # By niche
    from collections import defaultdict
    niche_agg = defaultdict(lambda: {"count": 0, "score_sum": 0, "ever_sent": 0, "replied": 0, "potential": 0.0, "label": ""})
    for l in leads:
        if not l.niche:
            continue
        n = niche_agg[l.niche]
        n["label"] = l.niche_label or l.niche
        n["count"] += 1
        n["score_sum"] += l.automation_score or 0
        n["potential"] += acv(l)
        # Everyone who was ever emailed (status is terminal, so include downstream states)
        if l.status in ("sent", "replied", "meeting", "closed"):
            n["ever_sent"] += 1
        if l.status in ("replied", "meeting", "closed"):
            n["replied"] += 1
    by_niche = sorted([
        {
            "niche": k, "label": v["label"], "count": v["count"],
            "avg_score": round(v["score_sum"] / v["count"], 1) if v["count"] else 0,
            "potential": round(v["potential"]),
            "reply_rate": round(v["replied"] / v["ever_sent"] * 100, 1) if v["ever_sent"] else None,
        }
        for k, v in niche_agg.items()
    ], key=lambda x: x["potential"], reverse=True)

    # Score bands
    bands = [("90-100", 90, 100), ("80-89", 80, 89), ("70-79", 70, 79), ("65-69", 65, 69), ("<65", 0, 64)]
    score_bands = []
    for label, lo, hi in bands:
        band_leads = [l for l in leads if lo <= (l.automation_score or 0) <= hi]
        score_bands.append({"band": label, "count": len(band_leads)})

    # Sends over last 14 days
    from datetime import date
    today = datetime.now(timezone.utc).date()
    sends_by_day = {}
    for l in leads:
        if l.sent_at:
            d = (l.sent_at.date() if hasattr(l.sent_at, "date") else None)
            if d and (today - d).days <= 13:
                sends_by_day[d.isoformat()] = sends_by_day.get(d.isoformat(), 0) + 1

    return {
        "funnel": funnel,
        "pipeline": {
            "total_potential": round(total_potential),
            "weighted": round(weighted),
            "by_stage": {k: {"count": v["count"], "potential": round(v["potential"])} for k, v in value_by_stage.items()},
        },
        "by_niche": by_niche,
        "score_bands": score_bands,
        "sends_by_day": sends_by_day,
    }
