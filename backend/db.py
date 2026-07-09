from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
import config

engine = create_engine(
    f"sqlite:///{config.DB_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)

    # Source
    source = Column(String, default="jsearch")
    job_id = Column(String, unique=True, index=True)
    job_url = Column(String)

    # Company
    company_name = Column(String, index=True)
    company_domain = Column(String)
    company_size = Column(String)
    company_industry = Column(String)
    company_linkedin = Column(String)
    company_research = Column(Text)  # JSON

    # Job
    job_title = Column(String)
    job_description = Column(Text)
    job_location = Column(String)
    job_posted_at = Column(DateTime)

    # Scoring
    automation_score = Column(Integer, default=0)
    score_breakdown = Column(Text)   # JSON
    pain_category = Column(String)
    pain_points = Column(Text)       # JSON list
    inferred_workflows = Column(Text)  # JSON list
    score_reasoning = Column(Text)

    # Niche specialization
    niche = Column(String, index=True)        # niche id
    niche_label = Column(String)              # human label
    offer = Column(Text)                       # JSON productized offer

    # Contact
    contact_name = Column(String)
    contact_title = Column(String)
    contact_email = Column(String)
    contact_linkedin = Column(String)
    contact_source = Column(String)
    contact_verified = Column(String)       # valid | risky | unknown | unverified | invalid
    verification_score = Column(Integer, default=0)
    contact_confidence = Column(Integer, default=0)  # 0-100 lead confidence
    sendability = Column(String)            # ready | review | risky | blocked

    # Outreach
    subject_line = Column(Text)
    email_body = Column(Text)
    email_long = Column(Text)
    mini_audit = Column(Text)
    follow_up_1 = Column(Text)
    follow_up_2 = Column(Text)
    breakup_email = Column(Text)
    objection_responses = Column(Text)  # JSON {objection: response}

    # Status: new → scored → researched → email_generated → queued → approved → sent → replied → meeting → rejected
    status = Column(String, default="new", index=True)

    # Tracking
    sent_at = Column(DateTime)
    opened_at = Column(DateTime)
    replied_at = Column(DateTime)
    meeting_booked_at = Column(DateTime)
    closed_at = Column(DateTime)

    # Follow-up sequencing: 0=none sent, 1=FU1 sent, 2=FU2 sent, 3=breakup sent
    followup_stage = Column(Integer, default=0)
    last_action_at = Column(DateTime)

    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime)

    jobs_scraped = Column(Integer, default=0)
    leads_scored = Column(Integer, default=0)
    leads_passed = Column(Integer, default=0)
    leads_researched = Column(Integer, default=0)
    emails_generated = Column(Integer, default=0)

    status = Column(String, default="running")  # running, completed, failed
    error = Column(Text)
    log = Column(Text)


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
