# Northwind Hackathon: Team Brief

Read this first. It covers the problem, our proposed system, and how we back it with the data.

**Terms:** "contact-centre staff" are the humans who handle complaints. "Agent" means an AI agent only.

---

## 1. The problem in 30 seconds

Northwind (electricity and water, 1.8M accounts) has a complaints crisis:

- 1,599 complaints open. Average resolution time went from 9.1 to 38.2 days.
- 77% breach their SLA (5 / 10 / 20 days for P1 / P2 / P3).
- Regulator score fell from 4.3 to 2.58 out of 5. The target is above 4.0 within 12 months.
- The client asked for an AI system that triages and responds to complaints. We agree, but it must be built the right way (see section 3).

**Our constraints:** we can't reduce demand and we can't add staff. We can change how complaints are sorted and handled.

## 2. The data

| File | What it holds |
|---|---|
| `northwind_complaints.csv` | About 25.4k complaints over 24 months. Category, priority, region, channel, source system, transfers, SLA, days to close, resolution action. |
| `northwind_monthly_kpis.csv` | 24 monthly rows: complaints opened and closed, avg days, first-contact resolution, cost to serve, regulator score. |
| `northwind_meter_reads.csv` | Region by month: estimated-read rate, smart-meter penetration, billing exceptions. |
| `northwind_systems.csv` | The 15 IT systems, their age, integration method and known problems. |
| `northwind_ai_pilot_2025.csv` | Results of the 2025 chatbot pilot (paused). |
| `northwind_unit_costs.csv` | Costs per complaint, transfer, bill correction, penalty and so on. |

**Estimated read:** if Northwind can't get a real meter reading, it bills on an estimate. Estimates are often wrong, and customers dispute the bill. The estimated-read rate is the share of bills that are estimates.

## 3. The three bottlenecks

### Bottleneck 1: Complaints bounce between systems, and each hand-off breaks the case

35% of complaints are transferred between systems. Compared with those not transferred:

| | Not transferred | Transferred |
|---|---|---|
| Days to close | 23.0 | 38.2 |
| SLA breach | 70% | 89% |
| Reopened | 8% | 27% |
| Cost per complaint | 68 | 121 |

- Complaints logged in CaseTrack (SYS-04) are never transferred. Those from SYS-01, 03 and 05 are transferred about 46% of the time.
- The systems file explains it: nightly batch integration, CaseTrack loses history on transfer, and contact-centre staff work across four screens.
- Transfers explain about 18% of all complaint-days. Even untransferred complaints breach 70%, so this is not the whole story.

### Bottleneck 2: Billing and meter errors create most of the complaints

- 63% of complaints are billing or metering, and they make up 68% of the open backlog. They also take longer (31 days against about 25) and breach 81-83% of the time.
- The two old-stack regions (Barrowdale and Dunmoor) have no smart meters. Compared with the other four regions:

| | Barrowdale and Dunmoor | Other four regions |
|---|---|---|
| Estimated reads | 59-64% | 17-26% |
| Billing exceptions per 1,000 accounts | 24-26 | 7-11 |
| Billing/metering share of complaints | 74-76% | 56-57% |

- Region-month correlation between estimated-read rate and billing/metering complaints is 0.66.
- The estimation algorithm has not changed since 2012 and has no feedback from corrected bills.
- 7,874 manual bill corrections in 24 months.
- This is a source of demand, not slow handling: old-stack regions resolve complaints at the same speed as the rest (28.5 against 28.0 days).
- **We can't fix this upstream in 24 hours.** We can handle these cases faster and flag the cause.

### Bottleneck 3: No triage, no fast lane, flat capacity

- Priority makes no difference. Breach rate is 72% for P1, 76% for P2 and 77% for P3. P3 is 70% of volume and 84% of the open backlog.
- 25% of closed complaints (5,865) needed only information or no action, yet they still take 28 days on average and breach 75% of the time.
- Complaints opened are up about 30% (the same in every category, region and channel). Complaints closed are flat at about 1,100 a month. Over 24 months, 25,416 opened and 23,817 closed, a gap of 1,599, exactly the current backlog.
- The backlog is a symptom: backlog is roughly monthly inflow times cycle time. Cutting resolution time shrinks it.

### Why the 2025 chatbot failed

Containment fell from 16% to 10%, escalation rose from 77% to 83%, repeat contact rose from 31% to 45%, and satisfaction fell from 2.6 to 2.04 (cost: 640k a year). It was a customer-facing bot with no access to bills or case history. **Our system is a tool for contact-centre staff, on top of the case data, with a human approving every reply.**

### Why it matters commercially

One quarter of regulator penalty (2.4M) is more than the whole 24-month complaint-handling cost (about 1.7M-2.2M at unit costs). The value is mostly avoiding the penalty.

---

## 4. What our system does

A triage and response tool that sorts every open and new complaint, and gives contact-centre staff a ready-to-approve answer.

| Bottleneck | What the system does |
|---|---|
| 1. Transfers | Routes each case to the right team first time, and shows the full history on one screen, so it doesn't bounce. |
| 2. Billing errors | Flags likely estimated-read cases, groups similar cases, and pre-fills the usual fix (bill correction). |
| 3. No triage | Fast lane for information-only cases (about 25%), ranked queue by breach risk, and drafted replies. This frees roughly the capacity that the 30% rise in demand consumed. |

## 5. Input, processing, output

**Input**
- The open backlog (1,599) and new complaints: category, channel, region, priority, source system, account, date opened.
- Context: the region's meter data and the account's earlier complaints.
- History: the 23,817 closed complaints, for learning what usually happens per case type.
- Unit costs, to price options.

Note: the data has no complaint text, only structured fields.

**Processing**
1. Learn the profile of each case type from history.
2. Classify each case: information-only, bill correction, field visit or complex.
3. Add context: link meter data and earlier complaints, and flag likely estimated-read cases.
4. Score breach risk: days open against the SLA, plus the chance of a transfer.
5. Route: fast lane or the right team.
6. Draft the reply for staff to approve.

**Output**
- A ranked worklist for contact-centre staff: next action, draft reply, breach countdown.
- A fast-lane queue for one-click approval.
- A manager view: backlog by type, expected breaches, projected average days.
- A list of root-cause clusters (for example "estimated-read disputes in Dunmoor").

## 6. Tech per step (no model training)

| Step | Tech | How |
|---|---|---|
| 1. Learn from history | SQL on Tiger Data | Load the CSVs and group closed complaints by category, region, channel and source system, for averages and rates. A lookup table, not ML. |
| 2. Classify | Laya (already in the repo) | Turn each case and its profile into one line of text. Laya answers: information only? (yes/no), fix type (choice), urgency (score). We can check it against the `resolvable_by_information_only` flag on closed cases. |
| 3. Add context | SQL join plus a rule | Join to meter data and account history. A billing case in a high-estimate region is flagged "likely estimated read". |
| 4. Breach risk | Plain rules in code | Days open against SLA, plus historical transfer rate for that case type. |
| 5. Route | Rules on Laya's output | Fix type and category map to a queue or team. |
| 6. Draft reply | AI agent (LLM) with MCP access to the DB | The agent reads the case and context and writes the reply. Staff approve. |
| 7. Show results | FastAPI plus a simple web dashboard | Worklist and manager view from SQL totals. |

One agent can run steps 2 to 6 per case. Laya sorts, SQL and rules do the arithmetic, and the agent only writes text.

## 7. Worked example: NW-124233

Opened 2 Sep 2026 by phone. "Billing - disputed amount", Barrowdale, P3 (20-day SLA), logged in CallCentre One (SYS-05). Still open at 28 days.

1. **History:** 1,281 closed Barrowdale billing disputes. 24% information-only, average 31.2 days, 33% transferred (43% when logged in SYS-05), 17% reopened. The most common fix was a bill correction (53%) or a refund (23%).
2. **Classify (Laya):** low chance of information-only (not fast lane), fix type is bill correction, urgency high.
3. **Context:** Barrowdale in Sep 2026 has 62% estimated reads, 0% smart meters and 7,571 billing exceptions, so it is flagged "likely estimated read". The account has no earlier complaints.
4. **Breach risk:** SLA is 20 days and the case is 28 days old, so it is 8 days overdue. Similar cases take 31 days and have a 43% chance of being transferred, so it goes near the top.
5. **Route:** the bill-correction team, working in the billing system that serves Barrowdale (SYS-01), so no transfer.
6. **Draft:** an apology for the delay, an explanation that the bill was probably estimated, and an offer of a corrected bill after a real reading. The suggested action is "bill corrected and re-issued".
7. **Output:** NW-124233 | 8 days overdue | Bill correction | Estimated-read region (62%) | Draft ready.

Fast-lane example: NW-121979, a "poor communication" complaint from Calderfield. 53% of that category is information-only, so it goes to one-click approval.

## 8. Getting to 4.0

The score has tracked resolution time closely. In Jan-Mar 2025 it was 4.08, 4.00 and 3.92 at 19.5, 20.1 and 21.4 days. Today it is 2.58 at 38.2 days. **The target is an average of about 20 days.**

Rough arithmetic (illustrative):
- Without transfer delays, the average complaint takes 23 days today.
- If the fast lane closes the 25% simple cases in a few days, the average falls to roughly 18-20 days.

## 9. Caveats to be honest about

- The score-to-days link is a correlation. Nobody has said how the regulator's score is actually calculated. Frame the promise as "we cut resolution time to about 20 days, the level where the score was 4.0 before".
- Recent resolution times are understated, because the last two months of cases are mostly still open.
- Smart-meter penetration in the other four regions went from 30% to 81%, yet their estimated-read rate stayed flat at about 20%. Smart meters are not an automatic fix, so don't promise that.
- Complaint counts are almost equal across regions even though account bases range from 210k to 412k. This looks like a quirk of the synthetic data.
- The data gives no currency for the unit costs. State your assumption.
- The fix for billing errors (better estimation, smart-meter rollout) is a follow-up recommendation, not part of the build.
