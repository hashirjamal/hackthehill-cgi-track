"""Turn the Northwind CSVs into INSERT files under db/seed/ (stdlib only).

    python3 db/build_seed.py

Run the files in name order after db/schema.sql. Every INSERT uses ON CONFLICT DO NOTHING,
so re-running is safe. The main data pack is used, except unit_costs, which comes from the
second pack because it adds the recruiting-and-onboarding row.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "Northwind_Challenge_Data"
EXTRA = DATA / "Additional_CGI_Files" / "Additional CGI Files"
OUT = Path(__file__).resolve().parent / "seed"
CHUNK = 5000

COST_KEYS = {
    "Inbound call handled by agent": "call",
    "Complaint handled end to end (average)": "complaint_standard",
    "Complaint handled end to end (transferred between systems)": "complaint_transferred",
    "Manual bill correction and re-issue": "bill_correction",
    "Field meter visit": "field_visit",
    "Smart meter installation": "smart_meter_install",
    "Contact centre agent, fully loaded": "staff_annual",
    "Recruiting and onboarding a contact centre agent": "staff_hire",
    "AskNorthwind assistant pilot": "ai_pilot_annual",
    "Regulator penalty, enhanced monitoring": "penalty_quarter",
    "Compensation payment, missed appointment or outage": "compensation",
}


def read(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{k: v.strip() for k, v in row.items()} for row in csv.DictReader(f)]


def lit(value, kind="text"):
    if value == "":
        return "NULL"
    if kind == "bool":
        return {"1": "TRUE", "0": "FALSE"}[value]
    if kind == "num":
        float(value)  # fail loudly on bad numbers
        return value
    return "'" + value.replace("'", "''") + "'"


def inserts(table, columns, rows, kinds, conflict="DO NOTHING"):
    """Yield multi-row INSERT statements of at most CHUNK rows."""
    for i in range(0, len(rows), CHUNK):
        values = ",\n".join(
            "(" + ", ".join(lit(r[c], kinds.get(c, "text")) for c in columns) + ")"
            for r in rows[i:i + CHUNK]
        )
        yield f"INSERT INTO {table} ({', '.join(columns)}) VALUES\n{values}\nON CONFLICT {conflict};\n"


def table(name, path, kinds):
    rows = read(path)
    columns = list(rows[0].keys())
    return list(inserts(name, columns, rows, kinds))


def main():
    OUT.mkdir(exist_ok=True)
    files = {}

    num = "num"
    systems = table("systems", DATA / "northwind_systems.csv",
                    {"year_installed": num, "records_held": num, "annual_run_cost": num})

    meter = read(DATA / "northwind_meter_reads.csv")
    pairs = sorted({(r["region"], s) for r in meter for s in r["systems_serving_region"].split("/")})
    region_systems = [
        "INSERT INTO region_systems (region, system_id) VALUES\n"
        + ",\n".join(f"({lit(r)}, {lit(s)})" for r, s in pairs)
        + "\nON CONFLICT DO NOTHING;\n"
    ]
    meter_sql = list(inserts("meter_reads", list(meter[0].keys()), meter, {
        "accounts": num, "estimated_read_rate": num, "smart_meter_penetration": num,
        "billing_exceptions_raised": num}))

    staffing = table("contact_centre_staffing", DATA / "northwind_contact_centre_staffing.csv", {
        "agent_fte": num, "open_vacancies": num, "attrition_rate_12m": num,
        "complaints_opened_per_agent": num})
    kpis = table("monthly_kpis", DATA / "northwind_monthly_kpis.csv", {
        c: num for c in ["complaints_opened", "complaints_closed", "avg_days_to_close",
                         "first_contact_resolution_rate", "inbound_calls",
                         "cost_to_serve_per_account", "regulator_satisfaction_score_of_5"]})
    pilot = table("ai_pilot_2025", DATA / "northwind_ai_pilot_2025.csv", {
        c: num for c in ["assistant_sessions", "fully_contained_rate", "escalated_to_agent_rate",
                         "abandoned_rate", "repeat_contact_within_7_days_rate",
                         "assistant_csat_of_5", "complaint_raised_after_session_rate"]})

    costs = read(EXTRA / "northwind_unit_costs.csv")
    for r in costs:
        r["cost_key"] = COST_KEYS[r["item"]]  # KeyError means a new cost row needs a key
    cost_sql = list(inserts("unit_costs", ["cost_key", "item", "unit_cost", "unit", "source_note"],
                            costs, {"unit_cost": num}))

    files["01_reference.sql"] = systems + region_systems + meter_sql + staffing + kpis + pilot + cost_sql

    complaints = read(DATA / "northwind_complaints.csv")
    accounts = [{"account_id": a} for a in sorted({r["account_id"] for r in complaints})]
    files["02_accounts.sql"] = list(inserts("accounts", ["account_id"], accounts, {}))

    kinds = {"transferred_between_systems": "bool", "sla_breach": "bool", "reopened": "bool",
             "resolvable_by_information_only": "bool", "sla_days": num, "days_to_close": num,
             "bill_correction_value": num}
    for n, stmt in enumerate(inserts("complaints", list(complaints[0].keys()), complaints, kinds), 1):
        files[f"03_complaints_{n}.sql"] = [stmt]

    for name, stmts in files.items():
        (OUT / name).write_text("".join(stmts), encoding="utf-8")
        print(f"{name}: {sum(s.count(chr(10)) for s in stmts)} lines")


if __name__ == "__main__":
    main()
