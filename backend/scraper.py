"""
Job scraper — JSearch RapidAPI (aggregates Indeed, LinkedIn, ZipRecruiter, Glassdoor).
Falls back to empty list if API key not configured.
"""
import httpx
import hashlib
from datetime import datetime, timezone
from typing import Optional
import config
from mock_data import get_mock_jobs


JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"


def _make_job_id(employer: str, title: str, posted: str) -> str:
    raw = f"{employer}::{title}::{posted}"
    return hashlib.md5(raw.encode()).hexdigest()


def _extract_domain(website: Optional[str]) -> str:
    if not website:
        return ""
    website = website.replace("https://", "").replace("http://", "").replace("www.", "")
    return website.split("/")[0].strip()


async def scrape_jobs(queries: list[str], max_per_query: int = 10) -> list[dict]:
    # No API key configured → fall back to realistic seed data so the full
    # pipeline runs end-to-end with zero setup. Real scraping kicks in
    # automatically once RAPIDAPI_KEY is set.
    if not config.RAPIDAPI_KEY:
        print("[scraper] No RAPIDAPI_KEY — using mock seed data")
        return get_mock_jobs(limit=config.MAX_LEADS_PER_RUN)

    results = []
    seen_ids = set()

    async with httpx.AsyncClient(timeout=30) as client:
        for query in queries:
            try:
                resp = await client.get(
                    JSEARCH_URL,
                    headers={
                        "X-RapidAPI-Key": config.RAPIDAPI_KEY,
                        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
                    },
                    params={
                        "query": query,
                        "page": "1",
                        "num_pages": "1",
                        "date_posted": "week",
                        "country": "us",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                for job in (data.get("data") or [])[:max_per_query]:
                    employer = job.get("employer_name", "")
                    title = job.get("job_title", "")
                    posted_ts = job.get("job_posted_at_timestamp", "")

                    job_id = _make_job_id(employer, title, str(posted_ts))
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    posted_at = None
                    if posted_ts:
                        try:
                            posted_at = datetime.fromtimestamp(int(posted_ts), tz=timezone.utc)
                        except Exception:
                            pass

                    results.append({
                        "job_id": job_id,
                        "source": "jsearch",
                        "job_url": job.get("job_apply_link", ""),
                        "company_name": employer,
                        "company_domain": _extract_domain(job.get("employer_website")),
                        "company_linkedin": job.get("employer_linkedin_url", ""),
                        "job_title": title,
                        "job_description": (job.get("job_description") or "")[:4000],
                        "job_location": f"{job.get('job_city', '')} {job.get('job_state', '')}".strip(),
                        "job_posted_at": posted_at,
                    })

            except Exception as e:
                print(f"[scraper] Error on query '{query}': {e}")
                continue

    return results
