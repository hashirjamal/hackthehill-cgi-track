"""Generate the simulated data behind the five Northwind system servers.

    python -m northwind_systems.generate

SIMULATED DATA. Northwind's real systems are not available to us, so this builds believable stand-ins
from the challenge's complaint records: every account with an open complaint gets bills, calls,
case notes and web messages that tell the same story across systems. The details (names, amounts,
readings, notes) are invented; the facts they hang on (account, region, complaint dates, category,
channel, transfers, the region's estimated-read rate that month, the bill correction value) come
from the CSVs.

Each system gets its own SQLite file under northwind_systems/data/, and its own customer id, so -
like the real estate - nothing joins up without Helix's cross-references. Deterministic: the same
input always gives the same data.
"""
import csv
import hashlib
import json
import random
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from northwind_systems import templates as T

ROOT = Path(__file__).resolve().parent.parent
DATA_PACK = ROOT / "Northwind_Challenge_Data"
OUT = Path(__file__).resolve().parent / "data"
AS_OF = date(2026, 9, 30)
BILL_MONTHS = 12
LEGACY_REGIONS = {"Barrowdale", "Dunmoor"}  # billed by Aurora (SYS-01); the rest by Helix (SYS-02)
CONNECT_REGISTERED_SHARE = 0.34  # "Only 34% of customers registered" (systems file)
UNIT_RATE = 0.2450  # £ per kWh, illustrative
STANDING_PER_MONTH = 16.10  # £, illustrative


@dataclass
class Complaint:
    complaint_id: str
    account_id: str
    date_opened: date
    date_closed: date | None
    status: str
    channel: str
    category: str
    region: str
    source_system: str
    transferred: bool
    resolution: str
    correction: float | None


def _rng(*parts: str) -> random.Random:
    return random.Random(int(hashlib.sha1("|".join(parts).encode()).hexdigest()[:12], 16))


def _parse_date(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


def load_complaints() -> dict[str, list[Complaint]]:
    """Every complaint on every account that has at least one open complaint, oldest first."""
    rows = list(csv.DictReader(open(DATA_PACK / "northwind_complaints.csv")))
    open_accounts = {r["account_id"] for r in rows if r["status"] == "Open"}
    by_account: dict[str, list[Complaint]] = defaultdict(list)
    for r in rows:
        if r["account_id"] not in open_accounts:
            continue
        by_account[r["account_id"]].append(Complaint(
            complaint_id=r["complaint_id"], account_id=r["account_id"], date_opened=_parse_date(r["date_opened"]),
            date_closed=_parse_date(r["date_closed"]), status=r["status"], channel=r["channel"],
            category=r["category"], region=r["region"], source_system=r["source_system"],
            transferred=r["transferred_between_systems"] == "1", resolution=r["resolution_action"],
            correction=float(r["bill_correction_value"]) if r["bill_correction_value"] else None,
        ))
    for complaints in by_account.values():
        complaints.sort(key=lambda c: c.date_opened)
    return by_account


def load_estimated_read_rates() -> dict[tuple[str, str], float]:
    rows = csv.DictReader(open(DATA_PACK / "northwind_meter_reads.csv"))
    return {(r["region"], r["month"]): float(r["estimated_read_rate"]) for r in rows}


def _months_back(n: int) -> list[date]:
    """Bill dates: the 14th of each of the last n months, oldest first."""
    out, y, m = [], AS_OF.year, AS_OF.month
    for _ in range(n):
        out.append(date(y, m, 14))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))


# --- per-account story ---------------------------------------------------------------------------


def build_account(account_id: str, complaints: list[Complaint], est_rates: dict) -> dict:
    """Everything the five systems hold about one account, generated as one consistent story."""
    rng = _rng(account_id)
    latest = complaints[-1]
    region = latest.region
    first, last = rng.choice(T.FIRST_NAMES), rng.choice(T.LAST_NAMES)
    usual = round(rng.uniform(58, 175), 2)
    focus = next((c for c in reversed(complaints) if c.status == "Open"), latest)
    digits = "".join(ch for ch in account_id if ch.isdigit())

    ids = {
        "helix_id": f"HX-{int(digits):08d}",
        "aurora_acct_no": f"{int(digits) * 7 % 10_000_000_000:010d}" if region in LEGACY_REGIONS else None,
        "crm_contact_id": f"C1-{rng.randint(1_000_000, 9_999_999)}",
        "casetrack_party_id": f"P{rng.randint(100_000, 999_999)}",
        "connect_user_id": None,
    }
    web_channel = any(c.channel == "Web form" for c in complaints)
    if web_channel or rng.random() < CONNECT_REGISTERED_SHARE:
        ids["connect_user_id"] = f"nwc_{hashlib.md5(account_id.encode()).hexdigest()[:10]}"

    psr = rng.sample(T.PSR_NEEDS, 1) if rng.random() < 0.13 else []
    if focus.category == "Payment - plan or arrears" and rng.random() < 0.4:
        psr = ["Young children under 5"]
    if focus.category == "Supply - interruption" and rng.random() < 0.3:
        psr = ["Medical equipment reliant on power"]

    bills = _bills(rng, account_id, region, complaints, focus, usual, est_rates)
    arrears = round(sum(b["amount"] for b in bills if b["status"] == "OVERDUE"), 2)
    payment_plan = None
    if focus.category == "Payment - plan or arrears":
        payment_plan = {
            "status": rng.choice(["PROPOSED", "ACTIVE - NOT APPLIED", "BROKEN"]),
            "agreed_monthly": _affordable(usual),  # what the customer told the call centre they can pay
            "agreed_on": (focus.date_opened + timedelta(days=rng.randint(1, 6))).isoformat(),
        }

    customer = {
        "account_id": account_id, **ids, "title": rng.choice(["Mr", "Mrs", "Ms", "Miss", "Mx", "Dr"]),
        "first_name": first, "last_name": last,
        "address": f"{rng.randint(1, 180)} {rng.choice(T.STREETS)}",
        "postcode": f"{T.POSTCODE_AREAS[region]}{rng.randint(1, 19)} {rng.randint(1, 9)}"
                    f"{rng.choice('ABDEFGHJLNPQRSTUWXYZ')}{rng.choice('ABDEFGHJLNPQRSTUWXYZ')}",
        "region": region, "phone": f"07{rng.randint(100, 999)} {rng.randint(100000, 999999)}",
        "email": f"{first.lower()}.{last.lower()}{rng.randint(1, 99)}@example.com",
        "customer_since": date(rng.randint(2004, 2023), rng.randint(1, 12), rng.randint(1, 28)).isoformat(),
        "payment_method": "Direct Debit" if rng.random() < 0.7 else rng.choice(["Payment card", "Cash / PayPoint"]),
        "psr_needs": psr, "usual_monthly": usual, "arrears": arrears, "payment_plan": payment_plan,
    }
    calls = _calls(rng, complaints, usual, bills)
    cases = _cases(rng, complaints, usual, bills)
    connect = _connect(rng, ids["connect_user_id"], complaints, usual, bills) if ids["connect_user_id"] else None
    return {"customer": customer, "bills": bills, "calls": calls, "cases": cases, "connect": connect}


def _bills(rng, account_id, region, complaints, focus, usual, est_rates) -> list[dict]:
    months = _months_back(BILL_MONTHS)
    reading = rng.randint(8_000, 60_000)
    bills = []
    # Which bills the complaint is about: the one or two issued before it was opened.
    issue_idx = max((i for i, d in enumerate(months) if d <= focus.date_opened), default=len(months) - 1)
    for i, bill_date in enumerate(months):
        seasonal = 1 + 0.28 * (1 if bill_date.month in (11, 12, 1, 2, 3) else -0.4 if bill_date.month in (6, 7, 8) else 0)
        amount = usual * seasonal * rng.uniform(0.9, 1.1)
        est_rate = est_rates.get((region, bill_date.strftime("%Y-%m")), 0.2)
        estimated = rng.random() < est_rate
        status = "PAID"
        cat = focus.category
        if cat == "Billing - estimated read" and issue_idx - 3 < i <= issue_idx:
            estimated = True
            if i == issue_idx:
                amount = usual * rng.uniform(1.8, 2.6)
        elif cat == "Metering - no read taken" and issue_idx - 5 < i <= issue_idx:
            estimated = True
        elif cat == "Billing - disputed amount" and i == issue_idx:
            amount = usual * rng.uniform(1.5, 2.2)
        elif cat == "Payment - plan or arrears" and i > issue_idx - 3:
            status = "OVERDUE"
        if cat in ("Billing - estimated read", "Billing - disputed amount") and i == issue_idx and focus.status == "Open":
            status = "DISPUTED"
        units = max(40, int((amount - STANDING_PER_MONTH) / UNIT_RATE))
        prev = reading
        reading += units
        bills.append({
            "seq": i + 1, "issued": bill_date.isoformat(), "period_from": (bill_date - timedelta(days=30)).isoformat(),
            "period_to": bill_date.isoformat(), "read_type": "ESTIMATED" if estimated else "ACTUAL",
            "previous_reading": prev, "reading": reading, "units_kwh": units, "amount": round(amount, 2),
            "status": status, "tariff": "DOM-STD-E1" if region in LEGACY_REGIONS else "Standard Variable (E)",
        })
    # A closed complaint that ended in a correction shows up as a corrected bill after it.
    for c in complaints:
        if c.correction and c.date_closed and c.date_closed >= date.fromisoformat(bills[0]["issued"]):
            bills.append({
                "seq": len(bills) + 1, "issued": c.date_closed.isoformat(), "period_from": None, "period_to": None,
                "read_type": "CORRECTION", "previous_reading": None, "reading": None, "units_kwh": 0,
                "amount": -round(c.correction, 2), "status": "CREDITED", "tariff": bills[-1]["tariff"],
            })
    bills.sort(key=lambda b: b["issued"])
    for i, b in enumerate(bills, start=1):
        b["seq"] = i
    return bills


def _affordable(usual: float) -> float:
    return float(max(25, round(usual * 0.5)))


def _story_values(rng, complaint: Complaint, usual: float, bills: list[dict]) -> dict:
    disputed = next((b for b in reversed(bills) if b["issued"] <= complaint.date_opened.isoformat() and b["amount"] > 0),
                    bills[-1])
    months_estimated = 0
    for b in reversed([b for b in bills if b["issued"] <= complaint.date_opened.isoformat()]):
        if b["read_type"] != "ESTIMATED":
            break
        months_estimated += 1
    amount = disputed["amount"]
    if complaint.category == "Payment - plan or arrears":
        # Arrears letters and calls quote the total owed, not one bill.
        amount = sum(b["amount"] for b in bills if b["status"] == "OVERDUE") or amount
    return {
        "amount": f"£{amount:.2f}", "usual": f"£{usual:.0f}", "afford": f"£{_affordable(usual):.0f}",
        "months": str(max(months_estimated, 2)),
        "date": (complaint.date_opened - timedelta(days=rng.randint(6, 25))).strftime("%d/%m"),
        "reading": f"{(disputed['reading'] or 0) - rng.randint(300, 900):05d}",
        "days": str(rng.randint(4, 12)),
    }


def _calls(rng, complaints: list[Complaint], usual: float, bills: list[dict]) -> list[dict]:
    calls = []
    for c in complaints:
        notes = T.CALL_NOTES.get(c.category, T.CALL_NOTES["Other"])
        values = _story_values(rng, c, usual, bills)
        n_first = 1 if c.channel == "Phone" else (1 if rng.random() < 0.35 else 0)
        end = c.date_closed or AS_OF
        span = max(1, (end - c.date_opened).days)
        n_chase = min(3, span // 12 + (1 if rng.random() < 0.4 else 0)) if c.status == "Open" or span > 15 else 0
        moments = [("first", c.date_opened)] * n_first + [
            ("chase", c.date_opened + timedelta(days=rng.randint(max(2, span // 4), max(3, span - 1))))
            for _ in range(n_chase)
        ]
        # Chase notes are drawn without repeats, so three chase calls never read identically.
        chase_notes = rng.sample(notes["chase"], len(notes["chase"]))
        for kind, day in sorted(moments, key=lambda m: m[1]):
            agent_id, agent = rng.choice(T.AGENTS)
            note = rng.choice(notes["first"]) if kind == "first" else chase_notes.pop() if chase_notes else None
            if note is None:
                continue
            at = datetime(day.year, day.month, day.day, rng.randint(8, 18), rng.randint(0, 59), rng.randint(0, 59))
            calls.append({
                "started_at": at.isoformat(), "duration_s": rng.randint(180, 1500) if kind == "first" else rng.randint(120, 900),
                "agent_id": agent_id, "agent": agent, "queue": "Billing" if "Bill" in c.category or "Pay" in c.category else "General",
                "wrap_code": T.WRAP_CODES.get(c.category, "GEN-ENQ") + ("-CHS" if kind == "chase" else ""),
                "notes": note.format(**values), "related_ref": c.complaint_id if rng.random() < 0.5 else None,
            })
    return calls


def _cases(rng, complaints: list[Complaint], usual: float, bills: list[dict]) -> list[dict]:
    cases = []
    for n, c in enumerate(complaints):
        values = _story_values(rng, c, usual, bills)
        team = T.OWNER_TEAMS.get(c.category, "Customer Care")
        opened = datetime(c.date_opened.year, c.date_opened.month, c.date_opened.day, rng.randint(8, 17), rng.randint(0, 59))
        events = []
        if c.transferred:
            # History lost in the transfer: CaseTrack only knows what happened after the batch import.
            imported = opened + timedelta(days=rng.randint(1, 4), hours=2)
            events.append({"at": imported.isoformat(), "type": "IMPORTED", "by": "BATCH",
                           "note": T.TRANSFER_NOTE.format(system=c.source_system)})
            cursor = imported
        else:
            events.append({"at": opened.isoformat(), "type": "OPENED", "by": rng.choice(T.CASE_HANDLERS),
                           "note": f"Case opened from {c.channel.lower()} contact."})
            cursor = opened
        for note in T.CASE_NOTES.get(c.category, T.CASE_NOTES["Other"]):
            cursor += timedelta(days=rng.randint(1, 6), hours=rng.randint(1, 7))
            if cursor.date() > (c.date_closed or AS_OF):
                break
            events.append({"at": cursor.isoformat(), "type": "NOTE", "by": rng.choice(T.CASE_HANDLERS),
                           "note": note.format(**values)})
        if c.status == "Open":
            while cursor.date() < AS_OF - timedelta(days=10):
                cursor += timedelta(days=rng.randint(7, 16))
                if cursor.date() > AS_OF:
                    break
                events.append({"at": cursor.isoformat(), "type": "NOTE", "by": rng.choice(T.CASE_HANDLERS),
                               "note": rng.choice(T.STILL_OPEN_NOTES).format(team=team)})
        else:
            closed = c.date_closed or AS_OF
            events.append({"at": datetime(closed.year, closed.month, closed.day, 16, 30).isoformat(), "type": "CLOSED",
                           "by": rng.choice(T.CASE_HANDLERS), "note": f"Resolved: {c.resolution or 'no action recorded'}."})
            if c.status == "Closed - reopened":
                events.append({"at": (datetime(closed.year, closed.month, closed.day, 10) + timedelta(days=rng.randint(3, 20))).isoformat(),
                               "type": "REOPENED", "by": "SYSTEM", "note": "Customer contacted again on the same issue."})
        cases.append({
            "case_ref": f"CT-{c.date_opened.year}-{int(c.complaint_id.split('-')[1]) - 100000:06d}",
            "external_ref": c.complaint_id, "opened": opened.isoformat(), "category": c.category, "status": c.status,
            "owner_team": team, "origin_system": c.source_system, "transferred": c.transferred, "events": events,
        })
    return cases


def _connect(rng, user_id: str, complaints: list[Complaint], usual: float, bills: list[dict]) -> dict:
    messages, readings = [], []
    for c in complaints:
        values = _story_values(rng, c, usual, bills)
        if c.channel == "Web form" or rng.random() < 0.25:
            body = rng.choice(T.CUSTOMER_MESSAGES.get(c.category, T.CUSTOMER_MESSAGES["Other"])).format(**values)
            if rng.random() < 0.3:
                body = body.replace(". ", ".. ", 1).replace("I am", "Im", 1)
            at = datetime(c.date_opened.year, c.date_opened.month, c.date_opened.day, rng.randint(6, 23), rng.randint(0, 59))
            messages.append({"sent_at": at.isoformat(), "subject": c.category.split(" - ")[-1].capitalize(),
                             "body": body, "has_attachment": "photo" in body.lower()})
        if c.category in ("Billing - estimated read", "Metering - no read taken"):
            # The customer did submit a reading - and the next bill was still estimated. Nothing flows back.
            day = c.date_opened - timedelta(days=rng.randint(6, 25))
            readings.append({"submitted_at": datetime(day.year, day.month, day.day, rng.randint(7, 22), rng.randint(0, 59)).isoformat(),
                             "reading": int(values["reading"]), "photo": True, "status": "RECEIVED - NOT PROCESSED"})
    first_login = min(c.date_opened for c in complaints) - timedelta(days=rng.randint(30, 400))
    return {"user_id": user_id, "registered_on": first_login.isoformat(), "last_login": (AS_OF - timedelta(days=rng.randint(0, 20))).isoformat(),
            "messages": messages, "meter_readings": readings}


# --- writing the per-system stores ---------------------------------------------------------------


def _db(name: str) -> sqlite3.Connection:
    path = OUT / f"{name}.sqlite"
    path.unlink(missing_ok=True)
    return sqlite3.connect(path)


def write(accounts: dict[str, dict]) -> None:
    OUT.mkdir(exist_ok=True)

    helix = _db("helix")
    helix.execute("CREATE TABLE customers (helix_id TEXT PRIMARY KEY, account_ref TEXT UNIQUE, doc TEXT)")
    helix.execute("CREATE TABLE invoices (helix_id TEXT, doc TEXT)")
    aurora = _db("aurora")
    aurora.execute("CREATE TABLE accounts (acct_no TEXT PRIMARY KEY, doc TEXT)")
    aurora.execute("CREATE TABLE bills (acct_no TEXT, doc TEXT)")
    casetrack = _db("casetrack")
    casetrack.execute("CREATE TABLE cases (case_ref TEXT PRIMARY KEY, party_id TEXT, external_ref TEXT, doc TEXT)")
    callcentre = _db("callcentre")
    callcentre.execute("CREATE TABLE interactions (contact_id TEXT, started_at TEXT, doc TEXT)")
    connect = _db("connect")
    connect.execute("CREATE TABLE users (user_id TEXT PRIMARY KEY, doc TEXT)")

    for account_id, a in accounts.items():
        cust = a["customer"]
        helix_doc = {k: cust[k] for k in cust if k not in ("usual_monthly",)}
        helix.execute("INSERT INTO customers VALUES (?, ?, ?)", (cust["helix_id"], account_id, json.dumps(helix_doc)))
        if cust["aurora_acct_no"]:
            aurora.execute("INSERT INTO accounts VALUES (?, ?)", (cust["aurora_acct_no"], json.dumps(cust)))
            for b in a["bills"]:
                aurora.execute("INSERT INTO bills VALUES (?, ?)", (cust["aurora_acct_no"], json.dumps(b)))
        else:
            for b in a["bills"]:
                helix.execute("INSERT INTO invoices VALUES (?, ?)", (cust["helix_id"], json.dumps(b)))
        for c in a["cases"]:
            casetrack.execute("INSERT INTO cases VALUES (?, ?, ?, ?)",
                              (c["case_ref"], cust["casetrack_party_id"], c["external_ref"], json.dumps(c)))
        for call in a["calls"]:
            callcentre.execute("INSERT INTO interactions VALUES (?, ?, ?)",
                               (cust["crm_contact_id"], call["started_at"], json.dumps(call)))
        if a["connect"]:
            connect.execute("INSERT INTO users VALUES (?, ?)", (a["connect"]["user_id"], json.dumps(a["connect"])))

    for conn in (helix, aurora, casetrack, callcentre, connect):
        conn.commit()
        conn.close()


def main() -> None:
    complaints = load_complaints()
    rates = load_estimated_read_rates()
    accounts = {acc: build_account(acc, cs, rates) for acc, cs in complaints.items()}
    write(accounts)
    print(f"Simulated {len(accounts)} accounts across 5 systems -> {OUT}")


if __name__ == "__main__":
    main()
