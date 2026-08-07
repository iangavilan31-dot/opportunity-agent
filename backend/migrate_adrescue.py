"""
One-shot migration for the Ad-Rescue machine (research report §13 L5).
Adds the detection/attribution columns; safe to re-run (checks existing).
Backs up the DB first.
"""
import os
import sqlite3
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(_HERE, "opportunity_agent.db")

COLUMNS = [
    ("machine", "TEXT"),          # which machine owns this lead (web_design/burning_ads/parked/rescue)
    ("variant", "TEXT"),          # outbound copy/experiment arm (E2/E3 attribution)
    ("ad_active", "INTEGER"),     # 1=ads found in Meta/Google libraries, 0=checked & none, NULL=unchecked
    ("ad_first_seen", "TEXT"),    # earliest running-ad start date found
    ("ad_creative_url", "TEXT"),  # a live ad-library permalink (proof-pack input)
    ("psi_mobile", "INTEGER"),    # PageSpeed mobile performance score 0-100
    ("psi_checked_at", "TEXT"),
]


def main():
    stamp = datetime.now().strftime("%Y-%m-%d")
    backup = os.path.join(_HERE, f"opportunity_agent.backup-{stamp}-adrescue.db")
    src = sqlite3.connect(DB)
    if not os.path.exists(backup):
        dst = sqlite3.connect(backup)
        src.backup(dst)
        dst.close()
        print(f"backup: {os.path.basename(backup)}")

    existing = {r[1] for r in src.execute("PRAGMA table_info(leads)")}
    for name, typ in COLUMNS:
        if name not in existing:
            src.execute(f"ALTER TABLE leads ADD COLUMN {name} {typ}")
            print(f"added leads.{name} {typ}")
    # existing website-track leads belong to the web_design machine
    n = src.execute("UPDATE leads SET machine='web_design' "
                    "WHERE machine IS NULL AND source='website_autopilot'").rowcount
    print(f"backfilled machine=web_design on {n} leads")
    src.commit()
    src.close()
    print("migration complete")


if __name__ == "__main__":
    main()
