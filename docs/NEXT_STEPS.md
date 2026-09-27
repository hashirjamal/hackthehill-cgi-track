# Next steps: from working pieces to a demo

Status as of 2026-09-27. The code for everything below the "done" line lives in PR #3
(`feat/intake-and-laya-backlog`). Background: [OPTIMIZATION_PLAN.md](OPTIMIZATION_PLAN.md).

**Constraint that shapes all three steps:** no AI runs in someone else's cloud. Laya and the LLM
(Ollama) run on our own machine; no customer data is sent to an AI provider. A cloud-hosted
database (Tiger Data) is allowed, so we keep using it.

**Already done:** dashboard, worklist and case page (UI); New complaint form →
`POST /complaints/intake` → Laya → open case on the worklist; Laya decides category and urgency;
the Get context / Generate draft backend endpoints and their LangChain tools; 86 passing tests.

---

## Step 1 — Fix backlog classification, then re-run the backlog

### Problem
Laya now always decides the group, even when it is unsure. That is right for complaints with
customer text, but the ~1,600 backlog rows from the CSV have **no text**, and on those Laya is
unsure and often wrong. From the first 520 rows of the run:

| CSV category | Where Laya put it | Laya confidence |
|---|---|---|
| Water - pressure or quality | General (should be Field services) | 0.25-0.29 |
| Supply - interruption | mostly General | 0.26 |
| Payment - plan or arrears | General (should be Billing) | 0.28 |
| Service - missed appointment | Customer support (should be Field services) | 0.36 |
| Billing, Metering, Poor communication | correct | 0.56-0.96 |

Result: the water team filters to their section and doesn't see their own cases. The run was
stopped at 520/1,600.

### Fix
In `app/classification/service.py` (`classify_complaint`):

- **Complaint has text** (everything from the intake form): unchanged. Laya's pick always wins;
  unsure → `low_confidence` marker.
- **No text, Laya unsure, record has a category** (the CSV backlog): use the recorded category,
  mapped into our groups (`CATEGORY_TO_GROUP`), with `group.source = "record"`. For text-less
  rows the category is the only description there is, so using it is not trusting their
  labels. It is the only evidence we have.
- **Urgency is Laya's in every case.** Northwind's priority stays ignored.
- Bump `CLASSIFIER_VERSION` to `laya-two-stage-v7`, so the backlog run redoes the 520 rows
  (the old classifications stay as history).

### Tests (tests/test_service.py)
- no text + low confidence + category → group comes from the category, source `record`, and
  stage 2 is skipped, with the category as the subcategory
- text + low confidence → Laya's pick, `low_confidence` true (already covered)
- no text + confident Laya → Laya's pick (already covered)

### Run
```bash
python -m app.classify_backlog --limit 50   # check the distribution first
python -m app.classify_backlog              # the rest (resumable; ~30-60 min, cached)
```
Then check the group-by-category table again: water, supply and missed-appointment rows must
land in Field services, and payment rows in Billing.

### Done when
- Every open complaint has a current `laya-two-stage-v7` classification
- Each team's filter shows its own cases, ranked by urgency, then days overdue
- The urgency spread is not "everything P1"

---

## Step 2 — The two AI buttons on the case page, on a fast local model

### Problem
The backend for **Get context** (`POST /complaints/{id}/context`) and **Generate draft**
(`POST /complaints/{id}/draft`) works, but the case page has no buttons for them. The "Draft
reply and actions" card still says "The AI agents are not connected yet". Also, the configured
model (`gemma4`) isn't installed, and the only installed one (`qwen3:8b`) was too slow to demo.

### 2a. Pick and install the model (do this first, it decides everything else)
Ollama runs on the Mac's M4 GPU. Candidates, all with Ollama tool calling:

| Model | Why try it |
|---|---|
| `gemma4` (small size) | our preference, if its tool calling is reliable |
| `qwen3:4b` with thinking off | fast, strong at tool calling |
| `qwen3:8b` with thinking off | already installed; thinking mode is most of why it was slow |

For each, time **5 real Get context clicks and 5 Generate draft clicks** on different cases.
Pick the fastest one that:
- calls `create_action_brief` / `save_draft_reply` every time (a run that doesn't is recorded
  as failed)
- takes under ~30s per click

Set it in `.env` (`AGENT_MODEL=...`, `AGENT_ENABLED=true`) and raise
`AGENT_TIMEOUT_SECONDS` if needed.

### 2b. Frontend
- `frontend/src/api/reports.ts`: add `useGetContext(id)` and `useGenerateDraft(id)`
  mutations. They POST to the two endpoints with a long timeout (like `useClassify`), show a
  loading toast, and refresh the case query on success.
- `frontend/src/types.ts`: add types for `ContextResponse` (`run_id, status, error,
  action_items[]`) and `DraftOut` (`run_id, status, error, draft_id, body`).
- `frontend/src/pages/CaseDetail.tsx`, the "Draft reply and actions" card:
  - **Get context** and **Generate draft** buttons, each with its own spinner and disabled while
    running.
  - Action items as a ranked list: description, and rationale underneath in grey.
  - The latest draft in a text box staff can edit, with a **Copy** button. Nothing is sent
    from the app; staff send it themselves.
  - A failed run (`status: "failed"`) shows its `error` in plain words, not a blank card.
  - The "not connected yet" empty state is replaced with a short line telling staff to click
    a button.

### Done when
- On a Billing case, Get context shows 2-5 sensible action items in under ~30s
- Generate draft shows an editable reply that can be copied
- With `AGENT_ENABLED=false`, both buttons show a clear "AI assistance is off" message and
  the rest of the page still works

---

## Step 3 — Mock Northwind systems, tools that call them, and a "Systems checked" trace

### Why
Today's tools read real but thin data: the case itself, the account's past complaints,
similar-case averages, and regional meter statistics. The agent can say *"Barrowdale has 62%
estimated reads"* but not *"this customer's last three bills were estimates and they've called
twice"*. That per-account detail is the demo. It lives in Northwind's separate systems, which we
don't have, so we build believable stand-ins.

### 3a. The mock systems: separate servers, separate data, separate styles
One folder, `northwind_systems/`, with one small FastAPI app per system. Each app runs as its
own server on its own port, with its own data file, and **each looks like its own vendor and
era**. The inconsistency is deliberate: it is the "staff juggle four screens" problem the agent
solves.

| System | Port | Holds | Response style |
|---|---|---|---|
| Aurora Billing (SYS-01) | 9001 | bills, read type per bill, tariff, balance, arrears, payment plan. **Barrowdale and Dunmoor accounts only** | legacy mainframe: upper-case field codes, amounts in pence, dates `20260914`, read codes `E`/`A`/`C` |
| Helix CIS (SYS-02) | 9005 | account summary and billing for the other four regions | clean vendor JSON |
| CaseTrack (SYS-04) | 9002 | case record, status history, staff case notes, transfers | enterprise JSON; notes by different staff; history missing after transfers |
| CallCentre One (SYS-05) | 9003 | calls: date, length, agent, wrap-up code, agent notes | shorthand notes, e.g. "cust adv bill est x3, wants actual rd, v unhappy, cb req" |
| Northwind Connect (SYS-03) | 9004 | customer web messages, submitted meter reads, portal logins | modern JSON; customers' own words, typos included |

> **Open decision:** Helix is a fifth system. Without it, billing complaints in Ashford,
> Eastmarch, Calderfield and Fenwick have no bill data, because Aurora only serves Barrowdale and
> Dunmoor. Recommended: include it.

**Data generation:** `northwind_systems/generate.py`, templates only (no LLM), deterministic
(seeded), so reruns give the same data.
- Built from the real CSVs: same accounts, regions, complaint dates and categories.
- Matches the real numbers: old-stack regions have ~62% estimated bills; bill corrections
  average ~£171.
- **Consistent across systems for the same account.** Example: a £412 estimated bill in Aurora,
  three calls about it in CallCentre One, a web message with a meter photo in Connect, and a
  CaseTrack case with a transfer note. The story joining up is what makes the agent's output
  convincing.
- Labelled as simulated in each system's API description and in the README.

Each system also gets a small **web console** in its own era's style (Aurora as a green-on-black
terminal; CaseTrack as a dated enterprise page), so the demo can open all of them side by side:
*"this is what a Northwind agent juggles today"*.

### 3b. Tools that call the systems (app/agents/)
- `app/agents/systems_client.py`: one small HTTP client per system. Base URLs come from
  settings (`AURORA_URL`, ...), with short timeouts. A system that is down returns *"CaseTrack
  did not respond"* to the model instead of crashing the run.
- New zero-argument tools, scoped to the complaint's account like the existing ones:
  - `get_billing`: **our code** picks Aurora for Barrowdale/Dunmoor and Helix for the other
    regions. The model never chooses a system.
  - `get_case_notes`: CaseTrack
  - `get_call_history`: CallCentre One
  - `get_customer_messages`: Connect
- Each tool returns a short, readable summary (it converts pence and odd dates), not the raw
  record. The raw response is kept for the trace.
- **Keep the tool list short per domain** (4-6 tools). Small local models get worse as the
  list grows. Billing: billing + calls + messages + account complaints. Field services: case
  notes + calls + regional meter picture. And so on.

### 3c. "Systems checked" trace
- Every tool call records `{system, what was asked, raw response, summary}` in the run's
  existing `agent_runs.context` JSON column. No schema change needed.
- `/context` and `/draft` return the trace, and the case report returns it for the latest run.
- On the case page, a **Systems checked** list under the action items: one row per system
  consulted, each expandable to show the messy raw data next to what the agent made of it.
  Each action item names its source, e.g. *"Aurora: last 3 bills estimated (E), £412 vs usual
  ~£180"*.

### Running it
A script (or Docker Compose) starts the five system servers next to the backend and Ollama.
All of it is local; only the database is on Tiger.

### Done when
- Each system answers on its own port and has its own console page
- On a Barrowdale billing case, Get context produces action items that cite Aurora and
  CallCentre One data for that specific account
- The trace shows which systems were called, with raw and summarised data
- Stopping one system server gives a clear "did not respond" in the trace, not a failed run

---

## Order and dependencies
1. **Step 1** first: without it, the team filters show the wrong cases.
2. **Step 2a** (model choice) before 2b, and before 3b's tool design: tool count and wording
   depend on how well the chosen model handles tools.
3. **Step 3** last. It builds on step 2's buttons. The data generator (3a) can start in
   parallel with step 2.
