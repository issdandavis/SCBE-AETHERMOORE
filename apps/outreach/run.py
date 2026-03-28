#!/usr/bin/env python3
"""
Aethermoor Outreach -- Single-command launcher.

Usage:
    python apps/outreach/run.py

Starts the FastAPI server on port 8300 with:
- SQLite database created/migrated
- Routing targets seeded
- Opportunity profiles loaded
- Frontend served at /
"""

import os
import sys
from pathlib import Path

# Ensure the repo root is on sys.path so "apps.outreach.backend" resolves
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "outreach.db"

HOST = os.environ.get("OUTREACH_HOST", "127.0.0.1")
PORT = int(os.environ.get("OUTREACH_PORT", "8300"))


def setup_database():
    """Create tables and seed data."""
    from apps.outreach.backend.models import init_db, get_session, RoutingTarget
    from apps.outreach.backend.services.routing import ROUTING_TARGETS
    from apps.outreach.backend.services.opportunity import seed_opportunity_summary

    print(f"[outreach] Database: {DB_PATH}")

    engine = init_db(str(DB_PATH))
    print("[outreach] Tables created/verified.")

    # Seed routing targets
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()

    existing = session.query(RoutingTarget).count()
    if existing == 0:
        for t in ROUTING_TARGETS:
            rt = RoutingTarget(
                name=t["name"],
                agency=t["agency"],
                contact_info=t.get("contact_info") or "",
                phone=t.get("phone") or "",
                hours=t.get("hours") or "",
                website=t.get("website") or "",
                notes=t.get("notes") or "",
            )
            session.add(rt)
        session.commit()
        print(f"[outreach] Seeded {len(ROUTING_TARGETS)} routing targets.")
    else:
        print(f"[outreach] {existing} routing targets already in DB.")

    # Opportunity profiles are in-memory, just confirm loaded
    print(seed_opportunity_summary())

    session.close()


def main():
    print("=" * 60)
    print("  Aethermoor Outreach")
    print("  Civic workflow engine for Port Angeles, WA")
    print("=" * 60)
    print()

    setup_database()

    print()
    print(f"[outreach] Starting server at http://{HOST}:{PORT}")
    print(f"[outreach] Frontend: http://{HOST}:{PORT}/")
    print(f"[outreach] API docs: http://{HOST}:{PORT}/docs")
    print(f"[outreach] Health:   http://{HOST}:{PORT}/health")
    print()

    import uvicorn
    uvicorn.run(
        "apps.outreach.backend.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
