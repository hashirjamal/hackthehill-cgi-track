"""Classify the open backlog with Laya, once, so every open complaint has our group and urgency.

    python -m app.classify_backlog            # every open complaint not yet on the current classifier
    python -m app.classify_backlog --limit 20 # try a few first

New complaints are classified as they arrive (POST /complaints/intake); this is only for the
complaints that were already open. It is safe to stop and re-run: complaints whose current
classification is already from this classifier version are skipped. The backlog rows come from the
CSV and have no text, so Laya reads their fields; a complaint logged through intake keeps its text.
"""
import argparse
import time
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.classification.schemas import ComplaintIn
from app.classification.service import CLASSIFIER_VERSION, classify_complaint, db_as_of_date, save_classification
from app.config import settings
from app.models import Classification, Complaint

COMMIT_EVERY = 50


def _pending(db: Session, limit: int | None) -> list[tuple[Complaint, Classification | None]]:
    rows = db.execute(
        select(Complaint, Classification)
        .outerjoin(
            Classification,
            (Classification.complaint_id == Complaint.complaint_id) & Classification.is_current.is_(True),
        )
        .where(Complaint.status == "Open")
        .order_by(Complaint.date_opened, Complaint.complaint_id)
    ).all()
    pending = [(c, cl) for c, cl in rows if cl is None or cl.classifier_version != CLASSIFIER_VERSION]
    return pending[:limit] if limit else pending


def classify_backlog(db: Session, laya: Any, as_of: date, limit: int | None = None, log=print) -> int:
    """Classify every open complaint that is not on the current classifier yet. Returns how many."""
    pending = _pending(db, limit)
    log(f"{len(pending)} open complaints to classify (as of {as_of})")
    started = time.monotonic()
    for i, (c, current) in enumerate(pending, start=1):
        complaint = ComplaintIn(
            complaint_id=c.complaint_id,
            # Only complaints logged through intake have text; it is kept in their classification input.
            text=(current.input or {}).get("text") if current else None,
            category=c.category,
            channel=c.channel,
            region=c.region,
            source_system=c.source_system,
            transferred_between_systems=c.transferred_between_systems,
            date_opened=c.date_opened,
            account_id=c.account_id,
        )
        result, raw = classify_complaint(complaint, c.complaint_id, as_of, laya)
        save_classification(db, complaint, result, raw, as_of)
        if i % COMMIT_EVERY == 0 or i == len(pending):
            db.commit()
            log(f"  {i}/{len(pending)} done ({time.monotonic() - started:.0f}s)")
    return len(pending)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=None, help="only classify this many (for a trial run)")
    args = parser.parse_args()

    from app.db import SessionLocal
    from app.laya_service import get_laya

    with SessionLocal() as db:
        as_of = settings.as_of_date or db_as_of_date(db) or date.today()
        classify_backlog(db, get_laya(), as_of, args.limit)


if __name__ == "__main__":
    main()
