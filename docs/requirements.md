# Requirements: Complaint Triage and Response System

**Terms:** "contact-centre staff" are the humans who handle complaints. "Agent" always means an AI agent.
Background and evidence are in [../TEAM_BRIEF.md](../TEAM_BRIEF.md). The database design is in [db-schema.md](db-schema.md).

---

## 1. Goal

Make contact-centre staff faster and more accurate at clearing complaints, and prove with a simulator that this brings the average resolution time back to about 20 days, the level where the regulator score was 4.0.

**Constraints**
- No extra staff, and demand cannot be reduced.
- 24-hour build, no model training.
- A human approves every customer reply. The AI agents draft, staff decide.

## 2. Users

| User | Needs |
|---|---|
| Contact-centre staff | A ranked list of what to do next, with a draft reply and clear action items per case. |
| Team lead / manager | Visibility of the backlog, its causes and its trend, and evidence that the system works. |
| Judges (demo) | The what-if simulator with the arithmetic and assumptions visible. |

## 3. System flow

```
Complaint arrives
      │
      ▼
[A] Classification: Laya + custom rules → stored classes
      │
      ▼
[B] Domain AI agent (one per class) → draft reply + action items
      │
      ▼
[C] Staff workspace: review, edit, approve, act
      
In parallel:
[D] SQL dashboards: backlog, root causes, case and account context
[E] Simulator: what-if evidence for the score
[F] Staff chat assistant (last priority)
```

## 4. Functional requirements

Priority: **P0** = must have for the demo, **P1** = should have, **P2** = only if time allows.

### A. Classification (P0)

Runs on every open complaint (the 1,599 backlog) and on each new one.

| ID | Requirement |
|---|---|
| A1 | Classify each complaint with **Laya** and custom rules. Store the result in the DB (never recompute on screen). |
| A2 | Classes to store: **domain** (which AI agent handles it), **fix type** (information only, bill correction, field visit, payment plan, appointment, complex), **information-only probability**, **urgency**, **likely estimated read**, **breach risk**, **fast-lane eligible**. |
| A3 | Custom rules cover the deterministic parts: breach risk (days open against `sla_days`), estimated-read flag (billing or metering case in a region with a high estimated-read rate), and routing to the right team. |
| A4 | Keep the rules that fired and Laya's raw output next to each classification, so any decision can be explained. |
| A5 | A complaint can be reclassified. Keep history and mark one classification as current. |

**Input to Laya:** one short text built from the structured fields (category, channel, priority, region, source system, days open, region's estimated-read rate, historic profile). The dataset has no complaint text.

### B. Domain AI agents (P0)

One agent per domain. They share the same code and differ only in configuration (instructions, historic patterns, reply templates).

| Domain agent | Complaint categories |
|---|---|
| Billing | Billing - disputed amount, Payment - plan or arrears |
| Metering | Billing - estimated read, Metering - no read taken |
| Supply and water | Supply - interruption, Water - pressure or quality |
| Service | Service - poor communication, Service - missed appointment |
| General | Other (also the fallback) |

| ID | Requirement |
|---|---|
| B1 | Each agent gets the case, the account's history, the region's meter data and the **historic pattern** for that case type (average days, usual resolution, transfer and reopen rates). Patterns come from SQL summaries put into the agent's context, or from the agent querying the DB through MCP. |
| B2 | Each agent produces a **draft reply** where a reply applies (not every case needs one). |
| B3 | Each agent produces **action items** for staff (for example: correct the bill, book a meter read, escalate to field team), each with a short reason and a suggested order. |
| B4 | Every run is logged (which agent, input context, result, errors) for auditing. |
| B5 | If an agent fails, the case stays in the queue with its classification and no draft. Nothing blocks. |

### C. Staff workspace (P0)

| ID | Requirement |
|---|---|
| C1 | **Ranked worklist:** open cases ordered by breach risk, with days overdue, domain, likely cause and next action. |
| C2 | **Case view:** the complaint, the account's earlier complaints, the region's meter picture, the classification, the draft reply and the action items on one screen. |
| C3 | Staff can approve, edit or reject a draft. The decision, the final text and who made it are saved. |
| C4 | Staff can mark action items as in progress, done or dismissed. |
| C5 | **Fast-lane queue (P1):** cases the system rates as likely information-only, for quick review. A wrong guess sends the case back to the normal queue. It is never auto-closed. |

### D. Dashboards (SQL) (P0 / P1)

Built on SQL views in the DB. All views can filter by region, category, priority and month.

| ID | View | Purpose | Priority |
|---|---|---|---|
| D1 | **Backlog and flow** | Opened against closed per month, backlog by age, priority and domain, breach status. | P0 |
| D2 | **Root-cause map** | Estimated-read rate against billing and metering complaints by region and month (joins the complaints and meter files), plus clusters such as "estimated-read disputes in Dunmoor". | P0 |
| D3 | **Case context** | Everything known about one complaint (see C2). | P0 |
| D4 | **Account history** | All complaints for an account, with categories, outcomes and repeats. | P1 |
| D5 | **Classification and agent results** | How many cases per class, fast-lane volume, drafts approved, edited or rejected. | P1 |

**Not building:** a transfer-impact screen and a pilot post-mortem screen. Those findings stay as background in the pitch only.

### E. Simulator (P0)

Purpose: give evidence that the system brings the score back to about 4.0.

| ID | Requirement |
|---|---|
| E1 | Sliders for the levers we control: **transfer reduction** (share of hand-offs removed by correct routing), **fast-lane share** (share of cases closed through the fast lane), **fast-lane close time** in days. |
| E2 | Baseline comes from the data: recent average days, breach rate, transfer rate, monthly inflow. |
| E3 | Outputs: projected **average days to close**, **SLA breach rate**, **backlog** (inflow × cycle time), **cost change** (from the unit costs) and **penalty avoided** (quarters out of breach × the quarterly penalty). |
| E4 | Outputs a projected **regulator score** using the historic relationship between average days and score in the KPI file. It must be labelled as an estimate from a correlation. |
| E5 | Scenarios can be saved (name, settings, results) so the demo can show base, conservative and target cases. |
| E6 | Assumptions are visible on screen. The fast-lane setting defaults to a conservative value, because information-only cases are only weakly predictable from the available fields (category is the only useful one). |

Model in one line: average days = share transferred × transferred days + share not transferred × untransferred days, with the fast-lane share moved to its close time. The transferred and untransferred baselines are 38.2 and 23.0 days.

#### Cost view in the simulator

Shows what it costs to handle the same complaints **without** our system and **with** it, and what hiring would cost instead.

| ID | Requirement |
|---|---|
| E7 | **Without the system:** yearly handling cost of the last 12 months of complaints, priced from the unit costs (non-transferred 68, transferred 121). Also shows the equivalent number of full-time staff (handling cost ÷ 46,000). |
| E8 | **Hiring alternative:** extra staff needed to stop the backlog growing and bring it down to the level that gives the target resolution time. Priced at 46,000 a year plus 11,500 recruiting and onboarding per hire (year one). |
| E9 | **With the system:** handling cost after the slider settings. Shows the saving by source, the staff-equivalent capacity freed (saving ÷ 46,000), and the net effect after the system's running cost. |
| E10 | **Penalty is shown separately:** quarters out of breach × 2.4M per quarter. It is a scenario input, never added into the handling savings. |
| E11 | Shows the **break-even running cost**: the most the system can cost per year before the handling saving is used up. Default running cost is the 2025 pilot's 640,000 a year, as a conservative stand-in, and can be edited. |
| E12 | All unit costs come from the `unit_costs` table (including the hiring cost), never hard-coded. |

Formulas (N = complaints opened in the last 12 months, t = share transferred):
- Baseline handling cost = N × (t × 121 + (1 − t) × 68).
- Transfer saving = N × (t − t after reduction) × (121 − 68).
- Fast-lane saving = correct cases × (average cost − 7.4) − wrongly flagged cases × 7.4. Correct = N × fast-lane share × precision. A fast-lane review is priced at the cost of one handled call (7.4), which is an assumption.
- Hiring needed = (monthly opened − monthly closed + (backlog − target backlog) ÷ 12) ÷ complaints per staff member per month. Target backlog = monthly inflow × target days ÷ 30.

**Reference run on the current data** (illustrative, conservative defaults: transfers cut 40%, fast lane flags 10% of cases with 54% precision):

| | Value |
|---|---|
| Complaints per year (last 12 months) | 13,709, 35% transferred |
| Baseline handling cost | about 1.19M a year (about 26 staff-equivalents) |
| Transfer saving | about 102k a year |
| Fast-lane saving (net of wrong flags) | about 54k a year |
| **Total handling saving** | **about 156k a year, about 3.4 staff-equivalents** |
| Hiring alternative | about 3 extra staff, about 165k in year one |
| Penalty avoided | 2.4M per quarter out of breach |

**What this means for the pitch:** on handling cost alone, our system is worth about as much as hiring three people. It does not pay back a 640k-a-year running cost on its own. The strong case is penalty avoidance (one quarter is worth 3.75 years of a 640k system) and the speed gain. The cost view has to show this honestly.

#### How the system reduces cost

| Lever | Effect | Claimed? |
|---|---|---|
| Fewer transfers (routing, one case view) | Saves 53 per avoided transfer, plus fewer reopens | Yes |
| Fast lane for information-only cases | A quick review instead of a full case | Yes, conservatively (weak prediction) |
| Ranked queue | No direct cost saving, but shorter waits and fewer breaches | Through the penalty input |
| Avoiding hires | Capacity freed, priced at the hiring cost | Yes, as staff-equivalents |
| Reopen reduction | 13.5% of cases reopen today. If a reopen costs one more standard handling (68), it adds to the saving | Optional switch, off by default (assumption) |
| Bill corrections (34 each), field visits (92), compensation (40) | These come from upstream errors. We cannot reduce them | No |

### F. Staff chat assistant (P2, last priority)

| ID | Requirement |
|---|---|
| F1 | A chat panel for contact-centre staff to ask about a case or account ("what happened on this account before?"), answered from the DB. |
| F2 | Not customer-facing. The 2025 customer chatbot failed, so we do not repeat it. |

## 5. Data requirements

- Load all six CSVs into the DB, keeping every column, with relationships (see [db-schema.md](db-schema.md)).
- New tables hold classifications, agent runs, draft replies, action items and simulator scenarios.
- Known data limits to design around:
  - No complaint text, only structured fields.
  - `sla_breach` is set on 1,568 of 1,599 open cases, which cannot be right for recent ones. Recompute breach status live from days open and `sla_days`.
  - 284 accounts appear in more than one region, so the region belongs to the complaint, not the account.
  - The data runs to 30 Sep 2026. Live calculations must use a configurable "as of" date, not today's date.
  - No currency is stated for the unit costs.
  - The staff count is not in the data. Staff-equivalents are derived from the handling cost, which assumes the unit costs are mostly staff time.
  - The second data pack (Additional CGI Files) adds one unit cost: recruiting and onboarding, 11,500 per hire. Its KPI file also differs from the first for Mar to Sep 2026 (September average days is 43.8, not 38.2). Confirm which KPI file is authoritative. The simulator reads its baseline from the DB.

## 6. Non-functional requirements

| ID | Requirement |
|---|---|
| N1 | **Human in the loop:** no reply is sent or case closed without staff approval. |
| N2 | **Explainable:** every classification shows why (rules fired, Laya output). |
| N3 | **Auditable:** agent runs, drafts and staff decisions are stored with time and user. |
| N4 | **Fast enough:** dashboards load in seconds. Classification is done ahead of time, not on screen load. |
| N5 | **Runs on Tiger Data (Postgres)** with the existing FastAPI app. |
| N6 | **Confidentiality fallback:** if LLMs are not allowed, replace agent drafts with templates filled from case data. Classification, worklist, dashboards and simulator stay unchanged. |

## 7. Build order

1. Load the CSVs and build the schema, plus the SQL views (D1, D2, worklist).
2. Classification (A): Laya plus rules, store results.
3. Staff workspace (C1, C2) and the simulator (E). These carry the demo.
4. Domain AI agents (B): drafts and action items, then approval flow (C3, C4).
5. Remaining dashboards (D4, D5), the fast-lane queue (C5).
6. Staff chat assistant (F), only if time is left.

## 8. Open questions

- Is the chat assistant for contact-centre staff only? (assumed yes)
- Are LLMs allowed, and is a local model like Laya acceptable? (fallback is N6)
- Should "Billing - estimated read" belong to the Metering agent, as above, or to the Billing agent?
- What currency should the value case use?
