# Demo script (about 6 minutes)

The story: **staff spend their time hunting through Northwind's systems instead of fixing
complaints. We sort every complaint by team and urgency, and one click gathers everything from
every system.**

## Before the demo

```bash
./northwind_systems/run.sh                  # the five simulated Northwind systems (ports 9001-9005)
ollama serve                                # or open the Ollama app; model: gemma4:e4b-it-qat
PRELOAD_LAYA=true uvicorn app.main:app --port 8000
cd frontend && npm run dev                  # http://localhost:5173
```

- The four showcase cases below already have AI results saved, so their pages load instantly.
  If you re-click during the demo, allow ~50 s with AI on, ~1 s with AI off.
- Close heavy apps (the Mac has 16 GB; the AI model uses ~3 GB of it).
- Open five browser tabs in advance: the app, plus the Aurora, Helix, CallCentre One and CaseTrack
  consoles.

## 1. The problem: four screens (1 min)

Open the consoles side by side and look up **David Hill** (case NW-124710, Barrowdale):

| System | Address | Enter |
|---|---|---|
| Aurora Billing (1998 mainframe) | http://localhost:9001 | `0006660675` |
| Helix CIS (customer records) | http://localhost:9005 | `ACC-951525` |
| CallCentre One (calls) | http://localhost:9003 | `C1-6763893` |
| CaseTrack (cases) | http://localhost:9002 | `P892336` |
| Northwind Connect (portal) | http://localhost:9004 | `nwc_00359972e2` |

Say: *"To answer one complaint, an agent does this. Every system has its own ID for the same
customer, its own format - Aurora gives amounts in pence and dates as 20260914 - and nothing
links them. The meter reading this customer sent through the app is sitting in Connect, marked
'not processed', while Aurora keeps estimating his bills."*

## 2. Intake: Laya sorts it (1 min)

**New complaint** page. Account `ACC-951525`, region Barrowdale, received through CallCentre One,
Phone, and type what the customer said, e.g.:

> *I've had three estimated bills in a row and the last one was over £400. I sent you a photo of
> my meter weeks ago. I've rung four times and nobody calls back.*

Click **Log and classify**. Point out: group, urgency, the flags that fired (repeat contact, high
bill), and that it is on the worklist straight away.

Say: *"Laya runs on our own machine. No customer data leaves Northwind."*

## 3. The worklist: each team sees its own queue, urgent first (30 s)

**Worklist** → filter **Domain: Billing**. Point out that the ranking comes from Laya's urgency (P1
only with a stated reason: vulnerable customer, safety risk or emergency), then days overdue.

## 4. The case: one click instead of five systems (2 min)

Open **NW-124710** (or any of the showcase cases). In the **Work this case** card:

- **Action items** - each one names its source: *"Connect: reading received, not processed;
  billing: last 3 bills estimated"*.
- **Systems checked** - expand Aurora: the raw mainframe record on the left, what the AI took from
  it on the right. *"The AI read the pence and the read codes so the agent doesn't have to."*
- **Draft reply** - addresses the customer by name, quotes the real amounts and dates, never asks
  for anything we already hold. Staff edit and send it; nothing is sent automatically.

## 5. "What if we can't use AI?" (1 min)

Flip the switch to **AI off** and click **Get context** again: same systems, same sources, built by
fixed rules in about a second, labelled *"Built by rules - no AI"*.

Say: *"The hard part is joining up Northwind's systems, and that's plain code. The AI is optional
on top."*

If asked whether the AI is worth it, show the measurement (`python -m evals.laya_text_eval --quiet
--fresh`): on complaints neither was tuned on, Laya gets the team right 72% of the time and the
urgency within one level 100% of the time; keyword rules get 39% of teams right.

## Other showcase cases

| Case | Team | What to point at |
|---|---|---|
| NW-123968 (Ben Walker, Fenwick) | Billing / payments | £273 arrears, young children on the Priority Services Register |
| NW-122728 (Chloe Thompson, Calderfield) | Field services | Water quality, pensioner |
| NW-125017 (Liam Wright, Eastmarch) | Customer support | Chasing, pensioner, case history lost on transfer |
| NW-123212 (Zara Taylor, Barrowdale) | Billing / payments | £558.89 arrears, young children, three chase calls, distress about disconnection |

## Honest answers to likely questions

- **Is the data real?** The complaints are the challenge data. The five systems and their records
  are simulated stand-ins, labelled as such, generated to match the challenge data.
- **Where does it run?** Everything including both AI models runs on one machine; in production,
  on Northwind's own servers (see PRODUCTION_ARCHITECTURE.md). The database is Postgres.
- **How accurate is Laya?** See the table above. It is best on billing, payments, metering and
  emergencies; weakest on telling "estimated bill" from "meter not read" (both go to the Metering
  team anyway). The backlog has no customer text, so there Laya mostly reads the category label.
- **What if a system is down?** That system shows "did not respond" in the trace; the rest still
  work. If the AI fails, the no-AI rules run instead.
