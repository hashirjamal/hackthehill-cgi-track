# Northwind Challenge Data — Descriptive Summary

Descriptive statistics computed directly from the six CSVs in this folder.
No recommendations or interpretations are included. Derived figures are marked **[derived]** and show the arithmetic used.

---

## 1. Files

| File | Rows | Coverage |
|---|---|---|
| `northwind_complaints.csv` | 25,416 | 2024-10-01 to 2026-09 |
| `northwind_monthly_kpis.csv` | 24 | 2024-10 to 2026-09 |
| `northwind_meter_reads.csv` | 144 | 6 regions × 24 months |
| `northwind_contact_centre_staffing.csv` | 144 | 6 regions × 24 months |
| `northwind_systems.csv` | 15 | Installed 1998–2025 |
| `northwind_ai_pilot_2025.csv` | 9 | 2025-01 to 2025-09 |
| `Additional_CGI_Files/.../northwind_unit_costs.csv` | 10 | Finance cost model FY26 |

---

## 2. Complaints (`northwind_complaints.csv`)

**Status:** Closed 20,041 · Closed – reopened 3,776 · Open 1,599.
(“Closed – reopened” is a status value; the `reopened` flag is reported separately below.)

### By category

| Category | n | Share | SLA breach | Avg days to close | Reopened |
|---|---|---|---|---|---|
| Billing - disputed amount | 8,060 | 31.7% | 81% | 31.0 | 15% |
| Billing - estimated read | 4,833 | 19.0% | 83% | 31.2 | 15% |
| Metering - no read taken | 3,120 | 12.3% | 71% | 24.8 | 15% |
| Supply - interruption | 2,192 | 8.6% | 72% | 24.8 | 15% |
| Service - poor communication | 1,908 | 7.5% | 73% | 25.6 | 15% |
| Service - missed appointment | 1,718 | 6.8% | 71% | 25.5 | 14% |
| Payment - plan or arrears | 1,601 | 6.3% | 72% | 25.8 | 14% |
| Water - pressure or quality | 1,313 | 5.2% | 72% | 26.0 | 16% |
| Other | 671 | 2.6% | 72% | 24.9 | 14% |

Billing + metering categories combined: 16,013 records = 63.0% of volume.

### By priority

| Priority | n | Share | SLA breach | Avg days to close |
|---|---|---|---|---|
| P1 | 1,533 | 6.0% | 72% | 8.5 |
| P2 | 6,017 | 23.7% | 76% | 17.2 |
| P3 | 17,866 | 70.3% | 77% | 33.8 |

### Transferred vs not transferred

| | n | Share | SLA breach | Avg days | Reopened |
|---|---|---|---|---|---|
| Transferred (`transferred_between_systems=1`) | 8,870 | 35% | 89% | 38.2 | 27% |
| Not transferred | 16,546 | 65% | 70% | 23.0 | 8% |

### By source system

| System | n | Share | Transferred | SLA breach | Avg days |
|---|---|---|---|---|---|
| SYS-01 (Aurora Billing) | 6,479 | 25.5% | 47.1% | 79% | 30.2 |
| SYS-05 (CallCentre One) | 6,374 | 25.1% | 45.6% | 78% | 29.9 |
| SYS-03 (Northwind Connect) | 6,282 | 24.7% | 46.4% | 78% | 29.4 |
| SYS-04 (CaseTrack) | 6,281 | 24.7% | 0.0% | 71% | 23.2 |

### By channel

| Channel | n | Share | SLA breach | Avg days |
|---|---|---|---|---|
| Phone | 13,834 | 54.4% | 77% | 28.5 |
| Web form | 4,650 | 18.3% | 78% | 27.9 |
| Email | 2,966 | 11.7% | 76% | 27.8 |
| Social | 1,476 | 5.8% | 77% | 28.0 |
| Post | 1,267 | 5.0% | 75% | 27.0 |
| Regulator referral | 1,223 | 4.8% | 77% | 28.4 |

### By region

| Region | n | SLA breach | Avg days |
|---|---|---|---|
| Dunmoor | 4,320 | 77% | 28.3 |
| Barrowdale | 4,295 | 77% | 28.7 |
| Ashford | 4,269 | 76% | 28.2 |
| Fenwick | 4,234 | 76% | 28.0 |
| Eastmarch | 4,180 | 77% | 28.2 |
| Calderfield | 4,118 | 77% | 27.8 |

### By resolution action (closed records)

| Resolution action | n | Share | Avg days | SLA breach |
|---|---|---|---|---|
| Bill corrected and re-issued | 6,089 | 24.0% | 30.7 | 80% |
| Information provided only | 4,783 | 18.8% | 27.5 | 74% |
| Meter visit required | 4,055 | 16.0% | 27.7 | 75% |
| Field repair required | 2,074 | 8.2% | 25.3 | 71% |
| Refund or credit applied | 1,785 | 7.0% | 31.0 | 79% |
| *(no action — status Open)* | 1,599 | 6.3% | — | 98% |
| Payment plan amended | 1,122 | 4.4% | 25.4 | 70% |
| Appointment rebooked by agent | 1,087 | 4.3% | 25.3 | 70% |
| No action - explained to customer | 1,082 | 4.3% | 30.6 | 80% |
| Apology and manual process fix | 976 | 3.8% | 25.4 | 71% |
| Compensation payment issued | 764 | 3.0% | 25.2 | 70% |

**Information-only subset:** `resolvable_by_information_only=1` on 5,865 closed records (23.1% of all records); avg 28.0 days, 75% breach.

**Bill correction values:** 7,874 records with a value; total £1,345,190; average £171.

**Volume by half-year of `date_opened`:** 2024-H2 2,693 · 2025-H1 5,746 · 2025-H2 6,517 · 2026-H1 6,753 · 2026-H2 (3 months) 3,707.

---

## 3. Monthly KPIs (`northwind_monthly_kpis.csv`)

| Month | Opened | Closed | Avg days to close | FCR | Inbound calls | Cost/account | Regulator score /5 |
|---|---|---|---|---|---|---|---|
| 2024-10 | 912 | 476 | 9.1 | 0.620 | 42,571 | 18.73 | 4.30 |
| 2024-11 | 830 | 760 | 16.5 | 0.611 | 43,098 | 17.71 | 4.22 |
| 2024-12 | 951 | 873 | 18.4 | 0.602 | 41,856 | 18.88 | 4.15 |
| 2025-01 | 985 | 927 | 19.5 | 0.593 | 42,840 | 18.91 | 4.08 |
| 2025-02 | 851 | 840 | 20.1 | 0.584 | 41,820 | 19.92 | 4.00 |
| 2025-03 | 901 | 901 | 21.4 | 0.575 | 42,227 | 19.72 | 3.92 |
| 2025-04 | 1,023 | 952 | 22.0 | 0.566 | 44,644 | 18.79 | 3.85 |
| 2025-05 | 1,004 | 942 | 23.2 | 0.557 | 43,396 | 20.00 | 3.77 |
| 2025-06 | 982 | 965 | 23.1 | 0.548 | 45,387 | 20.81 | 3.70 |
| 2025-07 | 1,222 | 1,062 | 24.9 | 0.539 | 50,662 | 19.50 | 3.62 |
| 2025-08 | 1,026 | 1,089 | 26.6 | 0.530 | 47,010 | 19.57 | 3.55 |
| 2025-09 | 1,020 | 1,000 | 28.6 | 0.521 | 47,136 | 20.49 | 3.47 |
| 2025-10 | 1,189 | 1,029 | 27.6 | 0.512 | 49,033 | 20.52 | 3.40 |
| 2025-11 | 940 | 1,067 | 29.8 | 0.503 | 48,295 | 21.71 | 3.32 |
| 2025-12 | 1,120 | 1,019 | 29.6 | 0.494 | 48,825 | 20.67 | 3.25 |
| 2026-01 | 1,177 | 1,025 | 31.0 | 0.485 | 50,977 | 21.44 | 3.17 |
| 2026-02 | 1,002 | 1,000 | 33.6 | 0.476 | 48,137 | 21.18 | 3.10 |
| 2026-03 | 1,171 | 1,117 | 32.8 | 0.467 | 51,169 | 22.52 | 3.02 |
| 2026-04 | 1,190 | 1,109 | 33.3 | 0.458 | 50,476 | 22.89 | 2.95 |
| 2026-05 | 1,049 | 1,146 | 34.6 | 0.449 | 52,245 | 21.54 | 2.88 |
| 2026-06 | 1,164 | 1,063 | 35.9 | 0.440 | 53,421 | 22.40 | 2.80 |
| 2026-07 | 1,271 | 1,163 | 35.7 | 0.431 | 53,113 | 22.99 | 2.72 |
| 2026-08 | 1,185 | 1,130 | 37.4 | 0.422 | 55,014 | 22.90 | 2.65 |
| 2026-09 | 1,251 | 1,162 | 38.2 | 0.413 | 57,060 | 23.92 | 2.58 |

24-month totals: opened 25,416; closed 23,817; difference 1,599 (**[derived]**, equals the count of `status=Open` records in the complaints file).

---

## 4. Meter reads (`northwind_meter_reads.csv`)

**Snapshot, 2026-09:**

| Region | Accounts | Estimated-read rate | Smart penetration | Billing exceptions /1,000 accounts | Systems serving region |
|---|---|---|---|---|---|
| Ashford | 412,000 | 0.250 | 0.806 | 10.3 | SYS-02 / SYS-07 |
| Barrowdale | 298,000 | 0.620 | 0.000 | 25.4 | SYS-01 / SYS-06 |
| Calderfield | 355,000 | 0.214 | 0.806 | 8.8 | SYS-02 / SYS-07 |
| Dunmoor | 221,000 | 0.615 | 0.000 | 25.2 | SYS-01 / SYS-06 |
| Eastmarch | 304,000 | 0.180 | 0.806 | 7.4 | SYS-02 / SYS-07 |
| Fenwick | 210,000 | 0.262 | 0.806 | 10.7 | SYS-02 / SYS-07 |

**Billing exceptions per month, first (2024-10) → last (2026-09):** Ashford 3,563 → 4,224 · Barrowdale 7,911 → 7,571 · Calderfield 2,600 → 3,121 · Dunmoor 5,052 → 5,576 · Eastmarch 2,609 → 2,243 · Fenwick 2,194 → 2,252.

Across the 24 months, smart-meter penetration rises ~2.2 percentage points/month in the four SYS-07 regions (0.30 → 0.806) and stays 0.000 in Barrowdale and Dunmoor for the full period.

---

## 5. Contact centre staffing (`northwind_contact_centre_staffing.csv`)

- Total agent FTE: 380 (2024-10) → 333 (2026-09).
- Calderfield: 73 FTE (2024-10) → 63 (2026-02) → 37 (2026-03 onward), with 32 open vacancies and 12-month attrition 0.40–0.46 from 2026-03; row note: “Recruitment freeze; vacancies unfilled”, preceded by “Attrition rising; two team leads resigned” (2026-01).
- Fenwick has the highest complaints-opened-per-agent throughout (2.1 → 4.0 range, peaking 5.1 in 2026-07); Ashford the lowest (1.7–2.8).

---

## 6. AI pilot 2025 (`northwind_ai_pilot_2025.csv`)

| Month | Sessions | Fully contained | Escalated to agent | Abandoned | Repeat contact ≤7d | CSAT /5 | Complaint raised after session |
|---|---|---|---|---|---|---|---|
| 2025-01 | 14,775 | 0.160 | 0.770 | 0.070 | 0.310 | 2.60 | 0.110 |
| 2025-02 | 13,685 | 0.153 | 0.777 | 0.070 | 0.327 | 2.53 | 0.114 |
| 2025-03 | 15,773 | 0.146 | 0.784 | 0.070 | 0.344 | 2.46 | 0.118 |
| 2025-04 | 18,069 | 0.139 | 0.791 | 0.070 | 0.361 | 2.39 | 0.122 |
| 2025-05 | 18,791 | 0.132 | 0.798 | 0.070 | 0.378 | 2.32 | 0.126 |
| 2025-06 | 18,766 | 0.125 | 0.805 | 0.070 | 0.395 | 2.25 | 0.130 |
| 2025-07 | 20,133 | 0.118 | 0.812 | 0.070 | 0.412 | 2.18 | 0.134 |
| 2025-08 | 19,890 | 0.111 | 0.819 | 0.070 | 0.429 | 2.11 | 0.138 |
| 2025-09 | 20,780 | 0.104 | 0.826 | 0.070 | 0.446 | 2.04 | 0.142 |

Total sessions: 160,662. Run cost per `northwind_unit_costs.csv` / `northwind_systems.csv` (SYS-15): £640,000 per year. Status per systems file: paused after nine months.

---

## 7. Systems (`northwind_systems.csv`)

| ID | Name | Purpose | Year | Integration | Annual run cost | Note (abridged) |
|---|---|---|---|---|---|---|
| SYS-01 | Aurora Billing | Billing and invoicing | 1998 | Nightly batch | £4,100,000 | COBOL/DB2 mainframe; serves Barrowdale and Dunmoor only; two remaining developers understand the rating engine |
| SYS-02 | Helix CIS | Customer information system | 2004 | Nightly batch | £3,250,000 | System of record; vendor support ends in 18 months |
| SYS-03 | Northwind Connect | Web/app self-service | 2019 | REST API | £1,450,000 | 34% of customers registered; cannot display a bill breakdown |
| SYS-04 | CaseTrack | Complaint and case management | 2011 | Nightly batch | £980,000 | Cases transferred in from other channels lose their history |
| SYS-05 | CallCentre One | Telephony and CRM | 2015 | REST API | £2,200,000 | Agents run four systems side by side per call |
| SYS-06 | MeterHub | Meter read collection/validation | 2009 | Nightly batch | £1,700,000 | Estimation algorithm unchanged since 2012; no feedback loop from corrected bills |
| SYS-07 | SmartRead Gateway | Smart meter data ingestion | 2021 | Streaming | £2,600,000 | Live in Ashford, Eastmarch, Calderfield, Fenwick; Barrowdale/Dunmoor rollout deferred twice on cost |
| SYS-08 | FieldForce | Field scheduling/dispatch | 2013 | REST API | £1,350,000 | No link to CaseTrack; engineers arrive without complaint history |
| SYS-09 | GridWatch | Outage/asset monitoring | 2016 | Message queue | £3,800,000 | Outage data not used to suppress related billing chasers |
| SYS-10 | AquaTrack | Water network/leakage | 2007 | Manual export | £890,000 | Acquired 2007; never integrated |
| SYS-11 | Ledger Core | General ledger | 2012 | Batch interface | £5,400,000 | ECC end-of-support programme underway |
| SYS-12 | PeopleBase | HR/workforce | 2017 | REST API | £1,100,000 | Out of scope |
| SYS-13 | RegReport | Regulatory reporting | 2010 | Manual export | £240,000 | Quarterly submission assembled by hand over nine working days |
| SYS-14 | DocVault | Document/correspondence archive | 2005 | Manual export | £760,000 | Retrieval takes 2–4 minutes per document during a call |
| SYS-15 | AskNorthwind (pilot) | AI virtual assistant | 2025 | REST API | £640,000 | Nine-month pilot, paused; results in pilot file |

---

## 8. Unit costs (`northwind_unit_costs.csv`)

| Item | Unit cost | Unit | Source note |
|---|---|---|---|
| Inbound call handled by agent | £7.40 | per call | Finance cost model FY26 |
| Complaint handled end to end (average) | £68.00 | per complaint | Finance cost model FY26, fully loaded |
| Complaint handled end to end (transferred) | £121.00 | per complaint | Finance cost model FY26 |
| Manual bill correction and re-issue | £34.00 | per correction | Finance cost model FY26 |
| Field meter visit | £92.00 | per visit | Operations, FY26 actuals |
| Smart meter installation | £148.00 | per meter | SYS-07 rollout actuals, Ashford |
| Contact centre agent, fully loaded | £46,000 | per FTE per year | HR, FY26 |
| AskNorthwind assistant pilot | £640,000 | per year | SYS-15 vendor contract, 2025 |
| Regulator penalty, enhanced monitoring | £2,400,000 | per quarter in breach | Regulatory Affairs estimate |
| Compensation, missed appointment or outage | £40.00 | per case | Regulated standard |

---

## 9. Derived arithmetic **[derived]**

- Complaint handling cost at unit rates, 24 months: 25,416 × £68 = £1,728,288; transfer premium: 8,870 × (£121 − £68) = £470,110; combined £2,198,398.
- One quarter of regulator penalty exposure (£2,400,000) exceeds the above combined figure.
- 7,874 manual corrections × £34 = £267,716 in correction handling cost (excludes the £1,345,190 disputed bill value in section 2).

---

### Method notes

- Breach % = share of records with `sla_breach=1`. Averages of `days_to_close` are over records where the field is non-empty (i.e. closed records).
- Percentages are rounded to one decimal place or the nearest whole percent as shown.
- All figures computed with a standard-library Python script over the CSVs; no external data used.
