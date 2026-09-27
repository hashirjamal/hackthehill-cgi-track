"""The Northwind system tools, against fake HTTP responses (httpx.MockTransport) - no servers needed."""
import threading
from datetime import date

import httpx

from app.agents.systems import SYSTEM_TOOLS_BY_DOMAIN, SystemsClient, build_system_tools
from app.agents.tools import build_context_tools_for
from app.models import Complaint

HELIX = "http://localhost:9005"
AURORA = "http://localhost:9001"


def _complaint(**overrides) -> Complaint:
    fields = dict(
        complaint_id="NW-1", account_id="ACC-1", date_opened=date(2026, 9, 1), status="Open", channel="Phone",
        category="Billing - estimated read", priority="P3", region="Barrowdale", source_system="SYS-01",
        transferred_between_systems=False, sla_days=20, sla_breach=False, reopened=False,
    )
    fields.update(overrides)
    return Complaint(**fields)


def _customer(billing="AURORA", connect="nwc_1"):
    return {
        "customerId": "HX-1", "accountRef": "ACC-1",
        "name": {"title": "Ms", "given": "Ada", "family": "Lovelace"},
        "address": {"line1": "1 Mill Lane", "postcode": "BW1 1AA", "region": "Barrowdale"},
        "customerSince": "2010-01-01", "paymentMethod": "Direct Debit",
        "priorityServicesRegister": [{"need": "Young children under 5", "registered": True}],
        "balance": {"arrears": 0.0, "currency": "GBP"}, "paymentArrangement": None, "billingSystem": billing,
        "externalIds": {"auroraAcctNo": "0000000001", "callCentreOneContactId": "C1-1",
                        "caseTrackPartyId": "P1", "connectUserId": connect},
    }


def _aurora_bill(seq, day, read, pence, status="PD"):
    return {"BILL-SEQ": f"{seq:04d}", "BILL-DT": day, "RD-TYP": read, "UNITS": "000400",
            "AMT-DUE-P": f"{pence:+09d}", "PAY-STS": status}


def _client(routes: dict, trace: list) -> SystemsClient:
    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.url.scheme}://{request.url.host}:{request.url.port}{request.url.path}"
        if key not in routes:
            return httpx.Response(404, json={"error": "not found"})
        value = routes[key]
        if isinstance(value, Exception):
            raise value
        return httpx.Response(200, json=value)

    return SystemsClient(trace, httpx.Client(transport=httpx.MockTransport(handler)))


def test_get_bills_goes_to_aurora_for_legacy_regions_and_calls_out_the_pattern():
    trace = []
    bills = [
        _aurora_bill(8, "20260914", "E", 41200, "DS"), _aurora_bill(7, "20260814", "E", 17000),
        _aurora_bill(6, "20260714", "E", 16500), _aurora_bill(5, "20260614", "A", 17500),
        _aurora_bill(4, "20260514", "A", 18000), _aurora_bill(3, "20260414", "A", 17800),
    ]
    client = _client({
        f"{HELIX}/helix/api/v2/customers": _customer(),
        f"{AURORA}/cics/AURB0200": {"AURB0200-RESP": {"RC": "00", "BILLS": bills}},
    }, trace)
    result = build_system_tools(_complaint(), client)["get_bills"].invoke({})

    assert "last 3 bills were all ESTIMATED" in result
    assert "£412.00" in result and "2.3x" in result  # pence converted, jump called out
    assert [t["system"] for t in trace] == ["helix", "aurora"]  # Helix first, for the Aurora account number
    assert trace[1]["summary"] == result and trace[1]["raw"]


def test_get_bills_uses_helix_invoices_for_new_stack_regions():
    trace = []
    invoice = {"issuedOn": "2026-09-14", "readingType": "ACTUAL", "amountDue": {"value": 88.5}, "status": "PAID",
               "consumptionKwh": 300}
    client = _client({
        f"{HELIX}/helix/api/v2/customers": _customer(billing="HELIX"),
        f"{HELIX}/helix/api/v2/customers/HX-1/invoices": {"invoices": [invoice]},
    }, trace)
    result = build_system_tools(_complaint(region="Ashford"), client)["get_bills"].invoke({})
    assert "Helix CIS billing" in result and "£88.50" in result
    assert all(t["system"] == "helix" for t in trace)


def test_a_system_that_is_down_gives_a_plain_sentence_and_is_traced():
    trace = []
    client = _client({f"{HELIX}/helix/api/v2/customers": httpx.ConnectError("refused")}, trace)
    result = build_system_tools(_complaint(), client)["get_customer_record"].invoke({})
    assert result == "Helix CIS did not respond."
    assert trace == [{"system": "helix", "system_name": "Helix CIS", "request": "GET /helix/api/v2/customers?accountRef=ACC-1",
                      "raw": None, "summary": "Helix CIS did not respond."}]


def test_customer_record_includes_vulnerability():
    trace = []
    client = _client({f"{HELIX}/helix/api/v2/customers": _customer()}, trace)
    result = build_system_tools(_complaint(), client)["get_customer_record"].invoke({})
    assert "Ms Ada Lovelace" in result and "Young children under 5" in result


def test_customer_not_registered_on_connect():
    trace = []
    client = _client({f"{HELIX}/helix/api/v2/customers": _customer(connect=None)}, trace)
    result = build_system_tools(_complaint(), client)["get_customer_messages"].invoke({})
    assert result == "The customer is not registered on Northwind Connect."


def test_helix_is_looked_up_once_however_many_tools_run():
    trace = []
    client = _client({
        f"{HELIX}/helix/api/v2/customers": _customer(),
        "http://localhost:9003/v1/contacts/C1-1/interactions": {"data": []},
    }, trace)
    tools = build_system_tools(_complaint(), client)
    tools["get_customer_record"].invoke({})
    tools["get_call_history"].invoke({})
    assert [t["system"] for t in trace] == ["helix", "callcentre"]


def test_each_domain_gets_its_own_short_list_of_systems():
    trace = []
    system_tools = build_system_tools(_complaint(), _client({}, trace))
    lock = threading.Lock()
    for agent_id, expected in SYSTEM_TOOLS_BY_DOMAIN.items():
        names = [t.name for t in build_context_tools_for(agent_id, None, _complaint(), date(2026, 9, 30), lock,
                                                         system_tools=system_tools)]
        assert names[:2] == ["read_case", "get_case_profile"]
        assert set(expected) <= set(names)
        assert "get_account_complaints" not in names  # covered by CaseTrack and CallCentre One
        assert len(names) <= 7
