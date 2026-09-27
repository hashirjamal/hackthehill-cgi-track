"""Agent tools that reach into Northwind's systems: Helix CIS, Aurora Billing, CaseTrack,
CallCentre One and Northwind Connect.

Each system has its own API style and its own customer id. Helix (the system of record) holds the
cross-references, so every tool starts from the customer's Helix record. That lookup, and the
choice of billing system (Aurora for Barrowdale and Dunmoor, Helix for the other regions), happen
here in code: the model only ever asks "get the bills", never "which system, which id".

Every call is recorded in `trace` - which system, what was asked, the raw response and the short
summary the model was given - so staff can see where each fact came from. A system that is down or
has no record gives the model a plain sentence instead of an error, and the run carries on.
"""
import json
import threading
from typing import Any

import httpx
from langchain.tools import tool

from app.config import settings
from app.models import Complaint

SYSTEM_NAMES = {
    "helix": "Helix CIS", "aurora": "Aurora Billing", "casetrack": "CaseTrack",
    "callcentre": "CallCentre One", "connect": "Northwind Connect",
}
_RAW_LIMIT = 6000  # characters of raw response kept in the trace, per call


class SystemsClient:
    """Plain HTTP to each system, with every call written to the trace."""

    def __init__(self, trace: list[dict], http: httpx.Client | None = None):
        self.trace = trace
        self.http = http or httpx.Client(timeout=settings.systems_timeout_seconds)
        self.urls = {
            "helix": settings.helix_url, "aurora": settings.aurora_url, "casetrack": settings.casetrack_url,
            "callcentre": settings.callcentre_url, "connect": settings.connect_url,
        }

    def get(self, system: str, path: str, params: dict | None = None) -> tuple[Any | None, str | None]:
        """(json, None) on success, (None, reason) when the system is down or has no record."""
        request = path + ("?" + "&".join(f"{k}={v}" for k, v in params.items()) if params else "")
        try:
            response = self.http.get(self.urls[system] + path, params=params)
        except httpx.HTTPError:
            return None, f"{SYSTEM_NAMES[system]} did not respond."
        if response.status_code == 404:
            return None, f"{SYSTEM_NAMES[system]} has no record for this customer."
        if response.status_code >= 400:
            return None, f"{SYSTEM_NAMES[system]} returned an error ({response.status_code})."
        body = response.json()
        self._record(system, request, body)
        return body, None

    def _record(self, system: str, request: str, raw: Any) -> None:
        text = json.dumps(raw, indent=1)
        self.trace.append({
            "system": system, "system_name": SYSTEM_NAMES[system], "request": f"GET {request}",
            "raw": text if len(text) <= _RAW_LIMIT else text[:_RAW_LIMIT] + "\n...",
            "summary": None,  # filled in by the tool, once it has summarised the response
        })

    def summarise(self, system: str, summary: str) -> str:
        """Attach the summary the model was given to that system's most recent call."""
        for entry in reversed(self.trace):
            if entry["system"] == system:
                entry["summary"] = summary
                break
        return summary

    def note_failure(self, system: str, request: str, reason: str) -> str:
        self.trace.append({"system": system, "system_name": SYSTEM_NAMES[system], "request": f"GET {request}",
                           "raw": None, "summary": reason})
        return reason


def _money(value: float) -> str:
    return f"£{value:,.2f}"


def _aurora_bill(b: dict) -> dict:
    """Translate one Aurora bill (pence, YYYYMMDD, single-letter codes) into plain terms."""
    read = {"A": "ACTUAL", "E": "ESTIMATED", "C": "CORRECTION"}[b["RD-TYP"]]
    status = {"PD": "PAID", "OS": "OVERDUE", "DS": "DISPUTED", "CR": "CREDITED"}[b["PAY-STS"]]
    d = b["BILL-DT"]
    return {"issued": f"{d[:4]}-{d[4:6]}-{d[6:]}", "read_type": read, "amount": int(b["AMT-DUE-P"]) / 100,
            "status": status, "kwh": int(b["UNITS"])}


def _helix_bill(b: dict) -> dict:
    return {"issued": b["issuedOn"], "read_type": b["readingType"], "amount": b["amountDue"]["value"],
            "status": b["status"], "kwh": b["consumptionKwh"]}


def _describe_bills(bills: list[dict], source: str) -> str:
    """Newest first. Calls out the pattern staff care about: estimates in a row and a jump in amount."""
    if not bills:
        return f"{source}: no bills on record."
    lines = [f"- {b['issued']}: {_money(b['amount'])}, {b['read_type'].lower()} read, {b['status'].lower()}" for b in bills]
    regular = [b for b in bills if b["read_type"] != "CORRECTION"]
    streak = 0
    for b in regular:
        if b["read_type"] != "ESTIMATED":
            break
        streak += 1
    older = [b["amount"] for b in regular[3:]]
    typical = sorted(older)[len(older) // 2] if older else None
    facts = []
    if streak >= 2:
        facts.append(f"the last {streak} bills were all ESTIMATED")
    if typical and regular and regular[0]["amount"] > 1.4 * typical:
        facts.append(f"the latest bill ({_money(regular[0]['amount'])}) is {regular[0]['amount'] / typical:.1f}x "
                     f"the usual ~{_money(typical)}")
    overdue = sum(b["amount"] for b in bills if b["status"] == "OVERDUE")
    if overdue:
        facts.append(f"{_money(overdue)} is overdue")
    head = f"{source} (last {len(bills)} bills). " + ("Key points: " + "; ".join(facts) + "." if facts else "")
    return head + "\n" + "\n".join(lines)


def build_system_tools(complaint: Complaint, client: SystemsClient) -> dict[str, Any]:
    """All the system tools for one complaint, by name. Callers pick the ones a domain needs."""
    cache: dict[str, Any] = {}
    lookup_lock = threading.Lock()  # tools can run in parallel; look the customer up once

    def customer() -> tuple[dict | None, str | None]:
        with lookup_lock:
            return _customer()

    def _customer() -> tuple[dict | None, str | None]:
        if "customer" not in cache:
            cache["customer"] = client.get("helix", "/helix/api/v2/customers", {"accountRef": complaint.account_id})
            if cache["customer"][0]:
                client.summarise("helix", "Found the customer, and their ids in the other systems.")
        return cache["customer"]

    @tool
    def get_customer_record() -> str:
        """Look up the customer's record in Helix CIS (the system of record): name, how long they
        have been a customer, payment method, arrears, any payment arrangement, and Priority
        Services Register needs (vulnerability, e.g. medical equipment or young children)."""
        c, err = customer()
        if err:
            return client.note_failure("helix", f"/helix/api/v2/customers?accountRef={complaint.account_id}", err)
        name = f"{c['name']['title']} {c['name']['given']} {c['name']['family']}"
        psr = ", ".join(p["need"] for p in c["priorityServicesRegister"]) or "none"
        arrangement = c["paymentArrangement"]
        plan = (f"{arrangement['status']} at {_money(arrangement['agreed_monthly'])}/month (agreed {arrangement['agreed_on']})"
                if arrangement else "none")
        return client.summarise(
            "helix", f"Helix CIS: {name}, {c['address']['region']}, customer since {c['customerSince']}, pays by "
            f"{c['paymentMethod']}. Arrears: {_money(c['balance']['arrears'])}. Payment arrangement: {plan}. "
            f"Priority Services Register: {psr}."
        )

    @tool
    def get_bills() -> str:
        """Get the customer's recent bills from the billing system: dates, amounts, whether each
        was based on an ACTUAL or ESTIMATED meter reading, and whether it is paid, overdue or
        disputed. Use this for any billing, payment or meter-reading question."""
        c, err = customer()
        if err:
            return client.note_failure("helix", f"/helix/api/v2/customers?accountRef={complaint.account_id}", err)
        if c["billingSystem"] == "AURORA":
            acct = c["externalIds"]["auroraAcctNo"]
            body, err = client.get("aurora", "/cics/AURB0200", {"ACCTNO": acct, "CNT": 8})
            if err:
                return client.note_failure("aurora", f"/cics/AURB0200?ACCTNO={acct}", err)
            bills = [_aurora_bill(b) for b in body["AURB0200-RESP"]["BILLS"]]
            return client.summarise("aurora", _describe_bills(bills, "Aurora Billing"))
        body, err = client.get("helix", f"/helix/api/v2/customers/{c['customerId']}/invoices", {"limit": 8})
        if err:
            return client.note_failure("helix", f"/helix/api/v2/customers/{c['customerId']}/invoices", err)
        return client.summarise("helix", _describe_bills([_helix_bill(b) for b in body["invoices"]], "Helix CIS billing"))

    @tool
    def get_call_history(keyword: str = "") -> str:
        """Get the customer's phone calls from CallCentre One, newest first, with the agent's notes.
        Optionally pass a keyword (e.g. "estimate", "disconnect", "engineer") to only see calls
        whose notes mention it. Shows how often they have called and what they were told."""
        c, err = customer()
        if err:
            return client.note_failure("helix", f"/helix/api/v2/customers?accountRef={complaint.account_id}", err)
        contact = c["externalIds"]["callCentreOneContactId"]
        params = {"q": keyword} if keyword.strip() else None
        body, err = client.get("callcentre", f"/v1/contacts/{contact}/interactions", params)
        if err:
            return client.note_failure("callcentre", f"/v1/contacts/{contact}/interactions", err)
        calls = body["data"]
        if not calls:
            return client.summarise("callcentre", f"CallCentre One: no calls{' mentioning ' + repr(keyword) if keyword else ''}.")
        chases = sum(1 for i in calls if i["wrapUpCode"].endswith("-CHS"))
        lines = [f"- {i['startedAt'][:10]} ({round(i['durationSec'] / 60)} min, {i['wrapUpCode']}): {i['notes']}" for i in calls]
        return client.summarise("callcentre", f"CallCentre One: {len(calls)} calls, {chases} of them chasing an earlier contact.\n"
                                + "\n".join(lines))

    @tool
    def get_case_history() -> str:
        """Get this complaint's case in CaseTrack: who handled it, every note in order, and whether
        its history was lost when it was transferred in from another system."""
        c, err = customer()
        if err:
            return client.note_failure("helix", f"/helix/api/v2/customers?accountRef={complaint.account_id}", err)
        body, err = client.get("casetrack", "/casetrack/rest/v1/cases", {"externalRef": complaint.complaint_id})
        if err or not body["cases"]:
            return client.note_failure("casetrack", f"/casetrack/rest/v1/cases?externalRef={complaint.complaint_id}",
                                       err or "CaseTrack has no case for this complaint.")
        case = body["cases"][0]
        lines = [f"- {a['timestamp'][:10]} {a['activityType']} ({a['user']}): {a['text']}" for a in case["activity"]]
        lost = " Its history before the transfer was NOT migrated." if case["importedViaBatch"] else ""
        return client.summarise("casetrack", f"CaseTrack {case['caseRef']}: {case['caseStatus']}, queue {case['ownerQueue']}.{lost}\n"
                                + "\n".join(lines))

    @tool
    def get_customer_messages() -> str:
        """Get what the customer wrote to us through Northwind Connect (the web and app portal), in
        their own words, and any meter readings they submitted there themselves."""
        c, err = customer()
        if err:
            return client.note_failure("helix", f"/helix/api/v2/customers?accountRef={complaint.account_id}", err)
        user = c["externalIds"]["connectUserId"]
        if not user:
            return client.note_failure("connect", "/api/v1/users/-", "The customer is not registered on Northwind Connect.")
        msgs, err = client.get("connect", f"/api/v1/users/{user}/messages")
        if err:
            return client.note_failure("connect", f"/api/v1/users/{user}/messages", err)
        parts = [f"- {m['sentAt'][:10]} \"{m['body']}\"" for m in msgs["messages"]] or ["- no messages"]
        summary = "Northwind Connect messages:\n" + "\n".join(parts)
        client.summarise("connect", summary)
        readings, err = client.get("connect", f"/api/v1/users/{user}/meter-readings")
        if not err and readings["readings"]:
            r_lines = [f"- {r['submittedAt'][:10]}: {r['value']} (photo: {'yes' if r['photo'] else 'no'}), status "
                       f"{r['processingStatus']}" for r in readings["readings"]]
            reading_summary = "Meter readings the customer submitted:\n" + "\n".join(r_lines)
            client.summarise("connect", reading_summary)
            summary += "\n" + reading_summary
        return summary

    return {t.name: t for t in (get_customer_record, get_bills, get_call_history, get_case_history, get_customer_messages)}


# Which systems each domain's agent consults. Short lists on purpose: small local models choose
# worse as the list grows.
SYSTEM_TOOLS_BY_DOMAIN: dict[str | None, list[str]] = {
    "billing": ["get_customer_record", "get_bills", "get_call_history", "get_customer_messages"],
    "metering": ["get_bills", "get_call_history", "get_customer_messages"],
    "field_services": ["get_customer_record", "get_case_history", "get_call_history"],
    "customer_support": ["get_case_history", "get_call_history", "get_customer_messages"],
    "general": ["get_customer_record", "get_call_history"],
    None: ["get_customer_record", "get_call_history"],
}
