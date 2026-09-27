# Handoff: project status and what's next

For an agent or teammate picking this up cold. Background and evidence are in
[../TEAM_BRIEF.md](../TEAM_BRIEF.md); full requirements in [requirements.md](requirements.md);
DB design in [db-schema.md](db-schema.md). This file is the "where are we right now" layer on
top of those — it will go stale as work continues, so prefer git history/PRs over this file
for anything that sounds outdated.

## Current state (as of this writing)

- **Branch:** `worktree-domain-agent-scaffold`, PR open at
  https://github.com/hashirjamal/hackthehill-cgi-track/pull/2, **not merged**.
- **`main`** has: the DB schema (`db/schema.sql`, `db/views.sql`), the CSV seed loader, and the
  classification layer (`app/classification/`, section A of requirements.md) — Laya-based,
  fully built and tested.
- **This PR adds:** the domain AI agent scaffold (section B) — see "What's built" below.
- **Not started at all:** staff workspace (C), dashboard API/UI (D), simulator (E), chat
  assistant (F). See "What's not built" below.

## Environment gotcha

The codebase uses `X | None` type syntax (Python 3.10+). The macOS system `python3` is often
3.9, which fails to import this code. Use `python3.12` (`brew install python@3.12` if needed)
when creating `.venv`. See the README's Setup section.

## What's built: domain AI agent scaffold (`app/agents/`)

After a complaint is classified (existing code, untouched), a domain agent runs and produces
a draft reply (where one applies) + ranked action items, persisted and logged.

| File | Job |
|---|---|
| `app/agents/schemas.py` | Pydantic models: `AgentDraftOutput` (what an agent produces), `AgentContext` (what it's given) |
| `app/agents/context.py` | Queries `v_case_profile`, `v_account_history`, `v_region_meter_complaints` (the dashboard SQL views) and builds an `AgentContext` |
| `app/agents/config.py` | **The file to edit for real prompt wording.** `AGENT_CONFIGS` has one entry per domain (billing/metering/field_services/customer_support/general) with working-but-generic default instructions, built from `app/classification/taxonomy.py`'s own group descriptions. Nothing else in the scaffold needs to change to specialize the agents — just replace the `instructions` strings here (or restructure `AgentConfig` if the team wants more than a single instructions string per domain, e.g. reply templates). |
| `app/agents/prompt.py` | Pure function rendering a complaint + its context into the text handed to the backend |
| `app/agents/backends.py` | Two interchangeable backends: `OllamaBackend` (a local LLM via [Ollama](https://ollama.com), single call with JSON-schema-constrained structured output — no multi-turn tool-calling, since the model isn't finalized) and `TemplateBackend` (deterministic, no LLM — requirement N6's confidentiality fallback, and what the whole test suite runs against) |
| `app/agents/service.py` | `run_domain_agent(...)` orchestrates one run: builds context, calls the backend, persists `AgentRun`/`DraftResponse`/`ActionItem`. Guarantees a backend failure never raises (requirement B5) |

Wired into `POST /complaints/process` (`app/complaint_routes.py`), right after classification,
inside a DB savepoint per complaint (so one complaint's agent-step failure — LLM or otherwise —
never costs the whole batch's classifications).

### Config (`app/config.py`, all overridable via `.env`)

- `AGENT_ENABLED` (default `true`) — `false` forces `TemplateBackend` everywhere (N6 fallback).
- `AGENT_MODEL` (default `gemma3`) — **placeholder**, unconfirmed. Whoever runs this for real
  needs `ollama pull <model>` first and should update this to match.
- `OLLAMA_HOST` (default `http://localhost:11434`).
- `AGENT_TIMEOUT_SECONDS` (default `30.0`) — per Ollama call; a batch of N complaints against a
  slow model can still take up to N × this, since calls are sequential (no concurrency built yet).

### Known, deliberately-deferred issues (real, not urgent — no code triggers them yet)

- Reclassifying a complaint (already supported by the classification layer, A9) doesn't retire
  the previous run's open action items or pending draft — they pile up. Will bite once a
  reclassification flow actually exists.
- `v_account_history` includes the complaint currently being processed when it's a reprocessed
  backlog case (not excluded from "earlier complaints" in the prompt).

### One thing NOT yet done — needs a human's go-ahead

`db/migrations/002_agent_tables_complaint_fk.sql` is in this PR but **has not been run** against
the live Tiger Data service (`hackthehill`, service id `rhw3xtuwno`, DEV environment). It drops a
foreign key on `agent_runs`/`draft_responses`/`action_items.complaint_id` that otherwise breaks
agent-processing of any genuinely new complaint (not yet in the `complaints` table) with a 500
that loses the whole batch's classifications — this predates the PR (it's a `db/schema.sql` bug)
but the PR's code is the first thing to actually trigger it. **Run this migration before relying
on the agent step for anything beyond the pre-loaded backlog.**

## What's not built (all P0 per requirements.md except F)

- **C. Staff workspace** — no API or UI for the ranked worklist (`v_worklist` view exists),
  case view, or approving/editing/rejecting a draft. Drafts currently just sit in `draft_responses`
  with nothing surfacing them.
- **D. Dashboards** — the SQL views exist (`db/views.sql`) but nothing serves them over an API
  or renders them.
- **E. Simulator** — the what-if calculator (transfer reduction / fast-lane share → projected
  resolution time, cost, regulator score) isn't started. Per requirements.md this and the staff
  workspace are what carry the actual demo.
- **F. Staff chat assistant** (P2, lowest priority) — not started.

## Testing conventions established so far (follow these, don't reinvent)

- Fake the model/client, not the DB, for classification and agent tests: see `FakeLaya` in
  `tests/test_service.py` and `FakeOllamaClient` in `tests/test_agent_backends.py` — plain
  dependency-injected stand-ins, no mocking library.
- The dashboard SQL views (`db/views.sql`) only exist on Postgres. Tests that need one create a
  plain SQLite table shaped like the view's output columns (see `tests/test_agent_context.py`'s
  `_db()` fixture) — the queries in `app/agents/context.py` only need the column names to match,
  since they're straight `SELECT ... WHERE ...`, no Postgres-only SQL.
- Route-level tests use FastAPI's `TestClient` with `StaticPool` + `check_same_thread=False`
  (plain SQLite in-memory otherwise gives each thread its own empty DB, since FastAPI runs sync
  routes in a worker thread) — see `tests/test_complaint_routes.py::_client()`.
- Run the full suite with `./.venv/bin/python -m pytest -q` (75 tests as of this PR).
