from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.classification.service import CLASSIFIER_VERSION
from app.classify_backlog import classify_backlog
from app.db import Base
from app.models import Classification, Complaint
from tests.test_complaint_routes import FakeLaya

AS_OF = date(2026, 9, 30)


def _complaint(complaint_id: str, status: str = "Open") -> Complaint:
    return Complaint(
        complaint_id=complaint_id, account_id="ACC-1", date_opened=date(2026, 9, 1), status=status,
        channel="Phone", category="Billing - disputed amount", priority="P3", region="Ashford",
        source_system="SYS-01", transferred_between_systems=False, sla_days=20, sla_breach=False, reopened=False,
    )


def _db() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_classifies_every_open_complaint_and_skips_closed_ones():
    db = _db()
    db.add_all([_complaint("NW-1"), _complaint("NW-2"), _complaint("NW-3", status="Closed")])
    db.commit()

    assert classify_backlog(db, FakeLaya(), AS_OF, log=lambda _: None) == 2
    current = db.query(Classification).filter_by(is_current=True).all()
    assert {c.complaint_id for c in current} == {"NW-1", "NW-2"}
    assert all(c.base_priority_source == "laya" for c in current)  # urgency is Laya's, not Northwind's P3


def test_rerunning_skips_complaints_already_on_the_current_classifier():
    db = _db()
    db.add_all([_complaint("NW-1"), _complaint("NW-2")])
    db.commit()
    classify_backlog(db, FakeLaya(), AS_OF, limit=1, log=lambda _: None)

    assert classify_backlog(db, FakeLaya(), AS_OF, log=lambda _: None) == 1  # only NW-2 was left
    assert classify_backlog(db, FakeLaya(), AS_OF, log=lambda _: None) == 0


def test_an_older_classification_is_replaced_and_intake_text_is_kept():
    db = _db()
    db.add(_complaint("NW-1"))
    db.add(Classification(
        complaint_id="NW-1", classifier_version="laya-two-stage-v4", is_current=True, as_of_date=AS_OF,
        input={"text": "They cut my gas off."}, emergency=False, priority="P3", base_priority="P3",
        base_priority_source="data", routed_team="Billing team", lane="standard", flags=[], laya_output={},
    ))
    db.commit()

    assert classify_backlog(db, FakeLaya(), AS_OF, log=lambda _: None) == 1
    current = db.query(Classification).filter_by(complaint_id="NW-1", is_current=True).one()
    assert current.classifier_version == CLASSIFIER_VERSION
    assert current.input["text"] == "They cut my gas off."
    assert db.query(Classification).filter_by(complaint_id="NW-1").count() == 2  # the old one is kept as history
