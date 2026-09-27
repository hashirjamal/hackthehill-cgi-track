# hackthehill-cgi-track

FastAPI + SQLAlchemy backend, connected to Tiger Data (or any Postgres).

## Setup

Requires Python 3.10+ (the code uses `X | None` type hints). On macOS, the system `python3` is often
3.9, which fails to import this code — check with `python3 --version` and use a newer interpreter
(e.g. `python3.12`, via Homebrew: `brew install python@3.12`) if so.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then set DATABASE_URL
```

Tiger Data: create a service, copy the connection details, and build the URL as
`postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require`.

## Run

```bash
uvicorn app.main:app --reload
```

- Docs: http://localhost:8000/docs
- Health check (verifies DB): http://localhost:8000/health

Tables are created on startup from `app/models.py` (no migrations).

## Laya (local decision model)

[Laya](https://huggingface.co/convaiinnovations/laya) classifies text against typed questions
(`choice`, `score`, `noul` = yes/no probability) in one forward pass. It runs locally on CPU.

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu   # CPU-only torch, skip if you have a GPU
pip install laya
```

The first Laya request downloads the English checkpoint (~850 MB) to `~/.cache/huggingface`
and takes about a minute. After that, requests take under a second.

- `GET /laya/test`: runs a canned support-ticket example
- `POST /laya/predict`: your own input:

```bash
curl -X POST localhost:8000/laya/predict -H 'content-type: application/json' -d '{
  "state": "The app crashes when I upload a PDF.",
  "questions": {
    "department": {"type": "choice", "instructions": "Which team?", "criteria": {"billing": "refunds", "technical": "bugs"}},
    "severity":   {"type": "score",  "instructions": "How severe?", "criteria": ["minor", "partly broken", "blocked"]},
    "is_bug":     {"type": "noul",   "instructions": "Is this a software bug?"}
  }
}'
```

## Complaint classification

`POST /complaints/process` classifies complaints with Laya and stores the result in the `classifications` table
(one current row per complaint, older rows kept as history). It then runs the matching domain AI agent - see
"Domain AI agents" below.

Rules and taxonomy: `app/classification/` (`taxonomy.py` groups, routes and Laya questions, `rules.py` priority
and flag rules, `service.py` the pipeline). Thresholds are in `app/config.py` and can be set in `.env`
(`GROUP_CONFIDENCE_THRESHOLD`, `FLAG_THRESHOLD`, `EMERGENCY_THRESHOLD`, `AS_OF_DATE`).

**Laya runs every step on every complaint.** Per the current plan (see `docs/OPTIMIZATION_PLAN.md`), Laya reads the
intake template's answers - filled in by one of the 4 intake teams, whose only job is that template - plus the text
if there is any, and decides the urgency on its own: Northwind's historic priority is not used as the starting
point, because their way of deciding if something was urgent was not that good. Flags then raise the level, never
lower it.

If Laya's top group probability is under `GROUP_CONFIDENCE_THRESHOLD` (0.6), Laya's top pick is still used (we
classify into our own categories, never Northwind's) and the case is marked `low_confidence` for staff to check.
Northwind's priority is not shown to Laya at all. Deadline risk (open over 75% of our target) is a marker only: most
of the backlog is past target, so letting it raise urgency would make everything P1.

**New complaints:** `POST /complaints/intake` (the "New complaint" page) takes the intake template - account, region,
intake system, channel and what the customer said - runs Laya, and saves the complaint as an open case, so it is on
the worklist immediately. **The existing open backlog** is classified once with `python -m app.classify_backlog`
(safe to stop and re-run; complaints already on the current classifier version are skipped).

**The model loads once when the server starts** (plus one warm-up call), so no request pays for it. Set
`PRELOAD_LAYA=false` to skip that in development. Answers are cached by state, so complaints that describe the same
way share them. On CPU, Laya costs about 0.5 s per question, or about 5 s per complaint, so classify a large backlog
as a background job.

```bash
curl -X POST localhost:8000/complaints/process -H 'content-type: application/json' -d '{
  "as_of_date": "2026-09-30",
  "complaints": [
    {"complaint_id": "NW-124233", "category": "Billing - disputed amount", "priority": "P3", "sla_days": 20,
     "channel": "Phone", "region": "Barrowdale", "source_system": "SYS-05",
     "transferred_between_systems": false, "date_opened": "2026-09-02"}
  ]}'
```

Tests (no model download needed): `pip install pytest && python -m pytest`.

## Domain AI agents (two buttons on a case, no chatbot)

The domain agent never runs on its own, and there's no chat/message box - just two one-shot
actions on a specific complaint's case view. Classification (above) happens for every complaint;
the agent only runs when staff click one of these:

```bash
# "Get context" - runs the agent's read-only tools, returns action items, drafts nothing.
curl -X POST localhost:8000/complaints/NW-124233/context

# "Generate draft" - runs the same read-only tools, then drafts one reply for staff to review.
curl -X POST localhost:8000/complaints/NW-124233/draft
```

It never acts on a real account - it only looks things up (via [LangChain](https://python.langchain.com)
tools bound to that one complaint, `app/agents/tools.py`) to help staff decide what to do. Each
button binds a different single output tool, so the model can't produce the wrong kind of output
regardless of what it decides to do: `/context` gives it `create_action_brief` (writes to
`action_items`) and nothing else can write; `/draft` gives it `save_draft_reply` (writes to
`draft_responses`, never sent automatically) and nothing else can write. Both log an `agent_runs`
row (status, error, timestamps) for audit, whether the run succeeds or fails.

Every domain shares four context tools: reading the complaint's own details, pulling the
account's other complaints, the historic pattern for this category/region/system, and the
region's meter picture. None of them reference anything domain-specific - they just look up
whatever complaint is open - so there was no reason to build them five times. General
additionally gets `search_knowledge_base`, a small static FAQ lookup for general information
questions ("how do I pay my bill?" and similar).

By default it calls a local [Ollama](https://ollama.com) model (`OLLAMA_HOST`, default
`http://localhost:11434`; `AGENT_MODEL`, default `gemma4` - **gemma3 has no tool-calling support in
Ollama at all**, gemma4 does; pull whatever you actually run with `ollama pull <model>` and set
`AGENT_MODEL` to match; `AGENT_TIMEOUT_SECONDS`, default `30.0`, per call). Set `AGENT_ENABLED=false`
to turn the agent off entirely (requirement N6's confidentiality fallback) - both endpoints record
a failed run and return one instead of calling an LLM, which is also what the test suite uses so
it never needs a running Ollama server.

`app/agents/config.py`'s `AGENT_CONFIGS` holds each domain's instructions - a real but generic
default today. That's the file to edit together to write the actual system-prompt wording; a new
domain-specific tool is a new entry in `app/agents/tools.py`'s `build_context_tools_for`.

## Database setup (Tiger Data or any Postgres)

`DATABASE_URL` needs the password in it (Tiger Data's connection string leaves it out). `postgres://` and
`postgresql://` URLs are accepted and rewritten for SQLAlchemy.

```bash
URL='postgres://tsdbadmin:PASSWORD@HOST:PORT/tsdb?sslmode=require'
psql "$URL" -f db/schema.sql
psql "$URL" -f db/views.sql
python3 db/build_seed.py && for f in db/seed/*.sql; do psql "$URL" -f "$f"; done
```

A database built from the first version of `db/schema.sql` (old `classifications` table, old agent ids) needs
`db/migrations/001_classification_layer.sql`, then `db/views.sql` again. The migration refuses to run if the old table
has rows.

`days open` is measured to the first of: the request's `as_of_date`, `AS_OF_DATE` in `.env`, `app_settings.as_of_date`
in the database, today.

## Reporting APIs

`GET /reports/...` feeds the dashboards. They read the SQL views in `db/views.sql`, so they need the Postgres
database (not the local SQLite one). Interactive docs: `/docs`.

| Endpoint | Returns |
|---|---|
| `/reports/worklist` | Open complaints ranked by priority and days overdue, with their classification |
| `/reports/backlog-flow` | Opened, closed and running backlog per month |
| `/reports/backlog-breakdown` | The open backlog grouped by any of region, category, domain, priority, age band, channel, source system |
| `/reports/root-cause` | Estimated-read rate against billing and metering complaints, by region and month |
| `/reports/root-cause/clusters` | Open complaints by region and category next to the region's meter data |
| `/reports/cases` | Search every complaint, open or closed |
| `/reports/cases/{complaint_id}` | One complaint with its classification, meter data, history profile, account history, drafts and actions (a single record, so no pagination of its own; `history_limit` caps the account history) |
| `/reports/account-history` | Complaints per account with repeat information |
| `/reports/agent-results` | Classified cases, runs and drafts per AI agent |
| `/reports/classifications/summary` | Classification results grouped by group, lane, team, priority and so on |
| `/reports/case-profiles` | Historic outcomes per category, region and source system |

Every list endpoint takes the same query parameters:

- **Pagination:** `page` (from 1) and `page_size` (default 25, at most 200). The response has `items`, `page`,
  `page_size`, `total` (rows matching the filters), `total_pages` and `sort`. A page past the end returns no items.
- **Sorting:** `sort=name:desc,name2` (direction defaults to `asc`, nulls last). Only the names listed in each
  endpoint's docs are accepted, anything else is a 422. A tie-breaker keeps pages stable.
- **Filtering:** repeat a parameter for several values (`region=Ashford&region=Fenwick`), `*_min` and `*_max` for
  ranges, `*_from` and `*_to` for dates, `true` or `false` for flags, and `q` for an id prefix search. A filter that
  matches nothing returns an empty page. Flags that can be unknown (for example `low_confidence` on an unclassified
  case) match only known values.
- **Grouping** (`backlog-breakdown`, `classifications/summary`): repeat `group_by`; each row has those columns plus the metrics.

Tests: `tests/test_reports_query.py` covers the shared helper without a database.
