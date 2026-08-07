"""
Dead-man alarm — the machine died of silence once (26 dark days, July '26:
tokens expired + PC asleep + nobody watching). This is the layer that makes
that impossible to repeat. Design law (research report §13): every layer runs
unattended AND fails loudly.

Runs daily via Task Scheduler (OpportunityAgent-HealthCheck, 9:45 AM — after
the 9:00 batch). Checks, tiered:

  CRITICAL (any one fires the alarm):
    - Gmail compose/read tokens refresh cleanly
    - a pipeline run happened in the last 26 hours and didn't fail
    - Gmail Drafts has machine drafts when the queue has emailable leads
  WARN (logged, shown in the summary, no popup):
    - no sends detected yesterday (Ian may just be away)
    - bounce-blocked rate over 2% of ever-emailed

Loud = three channels at once: backend/HEALTH_ALERT.txt (HUD/humans),
a Windows popup via msg.exe, and logs/health_YYYY-MM-DD.log. Silence is
only ever allowed to mean healthy.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(_HERE)
sys.path.insert(0, _HERE)

DB = os.path.join(_HERE, "opportunity_agent.db")
ALERT_FILE = os.path.join(_HERE, "HEALTH_ALERT.txt")
LOG_DIR = os.path.join(_HERE, "logs")


def _log(lines: list[str]) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    with open(os.path.join(LOG_DIR, f"health_{stamp}.log"), "a", encoding="utf-8") as f:
        f.write(f"=== {datetime.now():%Y-%m-%d %H:%M:%S} ===\n")
        f.write("\n".join(lines) + "\n")


def _popup(text: str) -> None:
    try:
        subprocess.run(["msg", os.environ.get("USERNAME", "*"), "/TIME:0", text],
                       timeout=10, capture_output=True)
    except Exception:
        pass  # popup is best-effort; the alert file is the durable channel


def _check_tokens() -> list[str]:
    problems = []
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        import gmail_drafts
        import gmail_read
        for name, path, scopes in (
                ("compose", gmail_drafts.TOKEN_PATH, gmail_drafts.SCOPES),
                ("read", gmail_read.READ_TOKEN_PATH, gmail_read.READ_SCOPES)):
            if not os.path.exists(path):
                problems.append(f"CRITICAL: {name} token file missing ({path})")
                continue
            try:
                creds = Credentials.from_authorized_user_file(path, scopes)
                if not creds.valid:
                    creds.refresh(Request())
            except Exception as e:
                problems.append(f"CRITICAL: {name} token dead ({e}) — run: python gmail_{'drafts' if name == 'compose' else 'read'}.py")
    except Exception as e:
        problems.append(f"CRITICAL: token check itself failed ({e})")
    return problems


def main() -> int:
    critical: list[str] = []
    warns: list[str] = []
    info: list[str] = []

    critical += _check_tokens()

    db = sqlite3.connect(DB)
    # pipeline ran recently and didn't fail
    row = db.execute("SELECT started_at, status, error FROM pipeline_runs "
                     "ORDER BY started_at DESC LIMIT 1").fetchone()
    if not row:
        critical.append("CRITICAL: no pipeline runs recorded at all")
    else:
        started, status, error = row
        # started_at is UTC-naive (DB law) — compare in UTC
        age = datetime.utcnow() - datetime.fromisoformat(started)
        if age > timedelta(hours=26):
            critical.append(f"CRITICAL: last pipeline run is {age.days}d {age.seconds // 3600}h old "
                            f"(task not firing / PC asleep through it)")
        if status == "failed":
            critical.append(f"CRITICAL: last pipeline run FAILED: {str(error)[:120]}")
        info.append(f"last run: {started[:16]} ({status})")

    emailable_queued = db.execute(
        "SELECT COUNT(*) FROM leads WHERE status IN ('queued','approved') "
        "AND contact_email IS NOT NULL AND contact_email != '' "
        "AND (sendability IS NULL OR sendability != 'blocked')").fetchone()[0]
    info.append(f"emailable queued: {emailable_queued}")

    sent_yesterday = db.execute(
        "SELECT COUNT(*) FROM leads WHERE sent_at >= datetime('now','-1 day')").fetchone()[0]
    if sent_yesterday == 0:
        warns.append("WARN: no sends detected in the last 24h")

    ever_emailed = db.execute(
        "SELECT COUNT(*) FROM leads WHERE sent_at IS NOT NULL").fetchone()[0]
    bounced = db.execute(
        "SELECT COUNT(*) FROM leads WHERE sendability='blocked' AND sent_at IS NOT NULL").fetchone()[0]
    if ever_emailed and bounced / ever_emailed > 0.02:
        warns.append(f"WARN: bounce-blocked rate {bounced}/{ever_emailed} "
                     f"({100 * bounced / ever_emailed:.1f}%) exceeds 2%")
    db.close()

    # drafts-vs-queue check needs the compose token; skip cleanly if it's down
    # (the token CRITICAL already fired in that case).
    if not any("token" in c for c in critical):
        try:
            import gmail_drafts
            metas = gmail_drafts.list_drafts_meta()
            if metas is not None:
                db = sqlite3.connect(DB)
                lead_emails = {r[0].strip().lower() for r in db.execute(
                    "SELECT contact_email FROM leads WHERE contact_email IS NOT NULL "
                    "AND contact_email != ''")}
                db.close()
                lead_drafts = sum(1 for m in metas if m["to"] in lead_emails)
                info.append(f"machine drafts in Gmail: {lead_drafts}")
                if lead_drafts == 0 and emailable_queued > 0:
                    critical.append(
                        f"CRITICAL: 0 machine drafts in Gmail while {emailable_queued} "
                        f"emailable leads sit queued (draft creation silently dead?)")
        except Exception as e:
            warns.append(f"WARN: drafts check failed ({e})")

    lines = critical + warns + info
    _log(lines)

    if critical:
        body = "OPPORTUNITY AGENT HEALTH ALARM\n" + "\n".join(critical + warns) + \
               f"\n(checked {datetime.now():%Y-%m-%d %H:%M})\n"
        with open(ALERT_FILE, "w", encoding="utf-8") as f:
            f.write(body)
        _popup("Web Machine ALARM: " + " | ".join(c.replace("CRITICAL: ", "")
                                                  for c in critical)[:200])
        print(body)
        return 1

    # healthy: clear any stale alarm so the file's presence stays meaningful
    if os.path.exists(ALERT_FILE):
        os.remove(ALERT_FILE)
    print("healthy | " + " | ".join(warns + info))
    return 0


if __name__ == "__main__":
    sys.exit(main())
