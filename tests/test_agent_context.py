from datetime import date

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.agents.context import account_history, build_context, case_profile, region_meter_picture
from app.classification.schemas import ComplaintIn


def _db():
    engine = create_engine("sqlite://")
    with Session(engine) as db:
        db.execute(text(
            "CREATE TABLE v_case_profile (category TEXT, region TEXT, source_system TEXT, n INT, "
            "avg_days REAL, info_only_share REAL, transfer_rate REAL, reopen_rate REAL, breach_rate REAL, "
            "top_resolution TEXT)"
        ))
        db.execute(text(
            "CREATE TABLE v_account_history (account_id TEXT, complaint_id TEXT, date_opened TEXT, "
            "category TEXT, status TEXT, resolution_action TEXT, days_to_close INT, is_repeat INT)"
        ))
        db.execute(text(
            "CREATE TABLE v_region_meter_complaints (region TEXT, month TEXT, estimated_read_rate REAL, "
            "smart_meter_penetration REAL, billing_exceptions_per_1000 REAL, billing_metering_share REAL)"
        ))
        yield db


def test_case_profile_returns_none_when_no_matching_history():
    for db in _db():
        assert case_profile(db, "Other", "Ashford", "SYS-01") is None


def test_case_profile_maps_the_matching_row():
    for db in _db():
        db.execute(text(
            "INSERT INTO v_case_profile VALUES ('Billing - estimated read', 'Barrowdale', 'SYS-05', 1281, "
            "31.2, 0.24, 0.33, 0.17, 0.81, 'Bill corrected and re-issued')"
        ))
        profile = case_profile(db, "Billing - estimated read", "Barrowdale", "SYS-05")
        assert profile is not None
        assert (profile.n, profile.avg_days, profile.top_resolution) == (1281, 31.2, "Bill corrected and re-issued")


def test_account_history_returns_empty_list_for_a_new_account():
    for db in _db():
        assert account_history(db, "ACC-999") == []


def test_account_history_orders_most_recent_first_and_respects_limit():
    for db in _db():
        db.execute(text(
            "INSERT INTO v_account_history VALUES ('ACC-1', 'NW-1', '2026-01-01', 'Other', 'Closed', "
            "'Information provided', 5, 0)"
        ))
        db.execute(text(
            "INSERT INTO v_account_history VALUES ('ACC-1', 'NW-2', '2026-06-01', 'Other', 'Closed', "
            "'Information provided', 3, 1)"
        ))
        history = account_history(db, "ACC-1", limit=1)
        assert len(history) == 1
        assert history[0].complaint_id == "NW-2"  # most recent first
        assert history[0].is_repeat is True


def test_region_meter_picture_returns_none_for_an_unseen_region_month():
    for db in _db():
        assert region_meter_picture(db, "Ashford", "2026-09") is None


def test_build_context_degrades_gracefully_with_no_matching_data():
    for db in _db():
        complaint = ComplaintIn(category="Other", region="Ashford", source_system="SYS-01", account_id="ACC-1")
        ctx = build_context(db, complaint, date(2026, 9, 30))
        assert ctx.case_profile is None
        assert ctx.account_history == []
        assert ctx.region_meter_picture is None


def test_build_context_skips_lookups_with_missing_fields():
    for db in _db():
        # No category/region/source_system, no account_id: nothing to look up, no crash.
        complaint = ComplaintIn(text="something", account_id=None)
        ctx = build_context(db, complaint, date(2026, 9, 30))
        assert ctx.case_profile is None
        assert ctx.account_history == []
        assert ctx.region_meter_picture is None
