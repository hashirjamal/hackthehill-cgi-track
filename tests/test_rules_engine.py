"""The no-AI rules: action items and draft reply from facts, no model and no servers."""
from datetime import date

from app.agents.rules_engine import Facts, action_items, draft_reply
from app.models import Complaint


def _complaint(category="Billing - estimated read") -> Complaint:
    return Complaint(
        complaint_id="NW-1", account_id="ACC-1", date_opened=date(2026, 9, 1), status="Open", channel="Phone",
        category=category, priority="P3", region="Barrowdale", source_system="SYS-01",
        transferred_between_systems=True, sla_days=20, sla_breach=False, reopened=False,
    )


def _customer(psr=(), arrears=0.0, plan=None, method="Direct Debit"):
    return {"name": {"title": "Ms", "given": "Ada", "family": "Lovelace"}, "paymentMethod": method,
            "priorityServicesRegister": [{"need": n} for n in psr], "balance": {"arrears": arrears},
            "paymentArrangement": plan}


def _bills(*spec):
    """(read_type, amount, status), newest first."""
    return [{"issued": f"2026-{9 - i:02d}-14", "read_type": r, "amount": a, "status": s} for i, (r, a, s) in enumerate(spec)]


def _types(facts):
    return [t for t, _, _ in action_items(facts)]


ESTIMATED_SPIKE = _bills(("ESTIMATED", 412.0, "DISPUTED"), ("ESTIMATED", 170.0, "PAID"), ("ESTIMATED", 165.0, "PAID"),
                         ("ACTUAL", 175.0, "PAID"), ("ACTUAL", 180.0, "PAID"), ("ACTUAL", 178.0, "PAID"))
READING = {"readings": [{"value": 40123, "submittedAt": "2026-08-20T19:02:00", "processingStatus": "RECEIVED - NOT PROCESSED"}],
           "messages": []}


def test_estimated_bills_with_a_submitted_reading_rebill_from_it_and_cite_both_systems():
    f = Facts(complaint=_complaint(), customer=_customer(), bills=ESTIMATED_SPIKE, calls=[], connect=READING)
    items = action_items(f)
    rebill = next(i for i in items if i[0] == "rebill_from_reading")
    assert "40123" in rebill[1] and "Connect:" in rebill[2] and "last 3 bills estimated" in rebill[2]
    assert "review_bill" in _types(f) and "pause_direct_debit" in _types(f)
    assert "book_meter_read" not in _types(f)  # a reading already exists


def test_vulnerability_and_distress_come_first():
    calls = [{"notes": "cust in tears, worried re cutoff", "wrapUpCode": "PAY-ARR-CHS", "startedAt": "2026-09-20T10:00:00"},
             {"notes": "chasing PP", "wrapUpCode": "PAY-ARR-CHS", "startedAt": "2026-09-10T10:00:00"}]
    f = Facts(complaint=_complaint("Payment - plan or arrears"),
              customer=_customer(psr=["Young children under 5"], arrears=558.89,
                                 plan={"status": "PROPOSED", "agreed_monthly": 60.0, "agreed_on": "2026-08-10"}),
              bills=[], calls=calls)
    assert _types(f)[:3] == ["vulnerability", "hold_recovery", "call_back"]
    assert "approve_payment_plan" in _types(f)


def test_at_most_five_items_each_with_a_source():
    f = Facts(complaint=_complaint(), customer=_customer(psr=["Pensionable age"], arrears=90.0), bills=ESTIMATED_SPIKE,
              calls=[], connect=READING, case={"importedViaBatch": True, "caseRef": "CT-1"},
              profile={"n": 40, "avg_days": 21.4, "top_resolution": "Bill corrected and re-issued"})
    items = action_items(f)
    assert len(items) == 5
    assert all(rationale for _, _, rationale in items)


def test_without_the_systems_the_rules_still_work_from_our_database():
    f = Facts(complaint=_complaint("Service - missed appointment"),
              profile={"n": 12, "avg_days": 9.0, "top_resolution": "Appointment rebooked by agent"},
              history=[{"date_opened": date(2026, 3, 2), "category": "Other", "status": "Closed"}])
    assert _types(f) == ["rebook_and_compensate", "likely_resolution", "review_history"]


def test_draft_uses_the_facts_and_promises_nothing_unconfirmed():
    f = Facts(complaint=_complaint(), customer=_customer(psr=["Hearing impaired"]), bills=ESTIMATED_SPIKE,
              calls=[], connect=READING)
    body = draft_reply(f)
    assert body.startswith("Dear Ms Lovelace,")
    assert "last 3 bills were based on estimated readings" in body and "£412.00" in body and "40123" in body
    assert "using the reading you sent us" in body and "Priority Services Register" in body
    assert "refund" not in body.lower() and "account number" not in body.lower()
    assert body.endswith("[Your name], Northwind Energy & Water")


def test_draft_without_customer_details_is_still_polite_and_generic():
    body = draft_reply(Facts(complaint=_complaint("Other")))
    assert body.startswith("Dear Customer,") and "passed your case to the right team" in body
