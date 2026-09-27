# Handoff: project status and what's next

For an agent or teammate picking this up cold. Background and evidence are in
[../TEAM_BRIEF.md](../TEAM_BRIEF.md); full requirements in [requirements.md](requirements.md);
DB design in [db-schema.md](db-schema.md). This file is the "where are we right now" layer on
top of those — it will go stale as work continues, so prefer git history over this file for
anything that sounds outdated.

## Current state (as of this writing)

Everything below is merged into local `main`, **not yet pushed to `origin/main`**. Two lines of
work landed here: a teammate's frontend + dashboard API (`frontend/`, `app/reports/`), and the
domain-agent chat described in this file.

- Classification (`app/classification/`, requirements section A) — Laya-based, fully built and tested, unchanged by any of this.
- Dashboards (section D) — mostly built: `app/reports/` serves worklist, backlog flow/breakdown, root-cause, cases, case detail, account history, case profiles, classification summary and agent-results, and `frontend/` (React + Vite) has pages for all of them.
- Simulator (section E) — a **preview/placeholder page only** (`frontend/src/pages/Simulator.tsx`); no backend behind it yet.
- Staff workspace (section C) — partially covered by the dashboard pages (worklist, case detail) plus the new chat below; there's still no staff login/auth (see the placeholder staff below), and no approve/edit/send flow for a saved draft.
- Domain AI agent (section B) — **rebuilt from scratch this session**, see below. The chat is the main thing to know about if you're picking this up.

## Environment gotcha

The codebase uses `X | None` type syntax (Python 3.10+). The macOS system `python3` is often
3.9, which fails to import this code. Use `python3.12` (`brew install python@3.12` if needed)
when creating `.venv`. See the README's Setup section.

## Domain AI agent: on-demand staff chat, not a pipeline

**This replaced an earlier design** (an automatic per-complaint pipeline that ran on every
complaint inside `POST /complaints/process`, producing a draft + action items via a single
structured-output LLM call). That design is gone — deleted, not deprecated. If you find a
reference to `app/agents/backends.py`, `service.py`, `context.py`, `prompt.py`,
`OllamaBackend`, `TemplateBackend`, `run_domain_agent`, or `AgentBackendError` anywhere
(old docs, an old branch, your own memory of an earlier version of this file), it's stale.

**How it actually works now:** nothing about the agent runs automatically. Classification still
runs on every complaint. The agent only runs when a staff member opens one specific complaint on
the dashboard and sends it a message — `POST /complaints/{complaint_id}/chat`. It:

1. Loads the complaint and its current classification (to know which domain/team owns it).
2. Builds a small set of tools scoped to that one complaint (closures over `db` + the complaint,
   so the model never has to pass ids as tool arguments — a small local model can't get an id wrong
   if it's never given one to pass).
3. Runs a [LangChain](https://python.langchain.com) `create_agent` tool-calling loop against a
   local [Ollama](https://ollama.com) model (`ChatOllama`).
4. Logs every message, both directions, to `chat_sessions`/`chat_messages` (audit trail; a new
   session is created per visit — reopening the same complaint later does **not** resume the old
   conversation, by design).

**The agent never takes any real action.** It only looks things up to help staff decide what to
do. The one tool with a side effect, `save_draft_reply`, writes a `DraftResponse` row (status
`draft`) — it doesn't send anything, and the model is instructed to only call it when staff
explicitly ask for a draft.

| File | Job |
|---|---|
| `app/agents/config.py` | **Edit this for real prompt wording.** `AGENT_CONFIGS` has one entry per domain with a working-but-generic system prompt, unchanged in shape from before. |
| `app/agents/tools.py` | `TOOL_BUILDERS` maps `agent_id -> factory(db, complaint, as_of) -> [tools]`. Every domain shares four tools (`build_shared_tools`): `get_account_complaints`, `get_case_profile`, `get_region_meter_picture` (all read-only, zero-argument, scoped to the current complaint), and `save_draft_reply(body)` — none of the three read tools reference anything domain-specific, so there was no reason to duplicate them per domain. `general` additionally gets `search_knowledge_base(question)`, a small static FAQ (the team's own knowledge-base examples), since that's the one genuinely domain-specific real data source available right now. |
| `app/agents/chat.py` | `run_chat_turn(model, cfg, tools, history, message)` — one turn: builds messages, runs `create_agent`, extracts the final reply and whether `save_draft_reply` was called. |
| `app/agents/schemas.py` | `ChatRequest`/`ChatResponse`/`ChatTurnIn` — the endpoint's request/response shape. |
| `app/complaint_routes.py` | `POST /complaints/{complaint_id}/chat` — the actual wiring: 404 if the complaint doesn't exist, resolves the domain, creates the `ChatSession`, calls the model (or the N6 fallback message if `AGENT_ENABLED=false`), logs both messages. |

### Config (`app/config.py`, all overridable via `.env`)

- `AGENT_ENABLED` (default `true`) — `false` skips the LLM call entirely; the chat endpoint
  returns a fixed "AI assistance is turned off" message instead (requirement N6).
- `AGENT_MODEL` (default `gemma4`) — **gemma3 has no tool-calling support in Ollama at all**
  (confirmed: no gemma3 tag, size, or variant supports it). gemma4 does, natively, ~86%
  tool-calling accuracy per Google. `ollama pull gemma4` (or whatever size fits) before relying on this for real.
- `OLLAMA_HOST` (default `http://localhost:11434`), `AGENT_TIMEOUT_SECONDS` (default `30.0`, per call).

### Placeholder staff, since there's no auth yet

`chat_sessions.staff_id` is a required foreign key to `staff`, and nothing in this project logs
anyone in. `ChatRequest.staff_id` defaults to `1`, and `db/schema.sql` now seeds exactly one
placeholder row (`'Demo Staff'`) so that id resolves to something on a fresh database. **This seed
row is not yet on the live Tiger Data service** — see below.

### A side effect worth knowing about: `v_agent_results` / the "AI agent results" dashboard page now shows zero activity

The old pipeline wrote to `agent_runs`; the new chat never does (nothing in this design needs an
`agent_runs` row — there's no "run" concept for an interactive chat the way there was for a
one-shot batch draft). `db/views.sql`'s `v_agent_results` view, and whatever frontend page reads
it (`useAgentResults` in `frontend/src/api/reports.ts`), will show 0 classified/fast-lane/drafts
for every agent from now on — not broken, just structurally unable to reflect chat activity as
currently written. If that dashboard matters for the demo, it needs a different query (probably
against `chat_sessions`/`draft_responses` directly) — not attempted here.

### Known, deliberately-deferred issues (real, not urgent)

- No concurrency: a batch scenario doesn't apply the same way to a one-complaint-at-a-time chat,
  but multiple staff chatting about *different* complaints at once will each block their own
  request thread for up to `AGENT_TIMEOUT_SECONDS` if Ollama is slow. Fine for a demo, not for real concurrent load.
- `get_account_complaints` doesn't paginate (hardcoded `LIMIT 20`) — fine for the data size here.
- Reprocessing/reclassifying a complaint and chatting about it again doesn't retire anything from
  an earlier chat session (each chat is independent by design, so this isn't really a bug the way
  it would have been in the old pipeline — just worth knowing chats don't merge or supersede each other).

### One thing NOT yet done — needs a human's go-ahead

`db/migrations/002_agent_tables_complaint_fk.sql` (from the earlier pipeline design, still valid -
it fixes a real `db/schema.sql` bug unrelated to the chat rewrite) is written but **has not been
run** against the live Tiger Data service (`hackthehill`, service id `rhw3xtuwno`, DEV
environment). Same for the new `staff` seed row above — neither has been applied to Tiger Data.
Both are safe, additive, low-risk changes, but they touch a shared service other teammates may be
pointed at, so they weren't applied without asking first.

## What's still genuinely unbuilt

- **Simulator backend** (section E) — the frontend page is a labeled preview; the what-if
  calculator (transfer reduction / fast-lane share → projected days, cost, regulator score) has no
  API behind it. Per requirements.md this and the worklist are what were meant to carry the demo.
- **Staff auth** — no login, no real staff identity; everything defaults to the one placeholder row.
- **Approve/edit/send flow for a saved draft** — `DraftResponse` rows get created (`status='draft'`)
  but nothing in the frontend or backend yet lets staff mark one approved/edited/sent.
- Domain-specific tools beyond the shared four — there's no real per-domain backing data yet
  (no per-account bill/appointment/outage tables), so metering/field_services/customer_support
  don't have anything beyond the shared set. If a real domain-specific data source shows up later,
  add its tool the same way `search_knowledge_base` was added to `general`.
- Staff chat assistant beyond one complaint (requirements section F: "what happened on this
  account before?" as a general, not-complaint-scoped question) — out of scope of what's here.

## Testing conventions established so far (follow these, don't reinvent)

- Fake the model, not the DB: `FakeLaya` (`tests/test_service.py`) for classification;
  `ScriptedChatModel` (a `FakeMessagesListChatModel` subclass with `bind_tools` made a no-op —
  see `tests/test_agent_chat.py` or `tests/test_complaint_routes.py`) for the chat agent. Plain
  dependency-injected stand-ins, no mocking library.
- The dashboard SQL views (`db/views.sql`) only exist on Postgres. Tests that need one create a
  plain SQLite table shaped like the view's output columns (see `tests/test_agent_tools.py`'s
  `_db()` fixture) — the queries in `app/agents/tools.py` only need the column names to match,
  since they're straight `SELECT ... WHERE ...`, no Postgres-only SQL.
- Route-level tests use FastAPI's `TestClient` with `StaticPool` + `check_same_thread=False`
  (plain SQLite in-memory otherwise gives each thread its own empty DB, since FastAPI runs sync
  routes in a worker thread) — see `tests/test_complaint_routes.py::_client()`.
- Run the full suite with `./.venv/bin/python -m pytest -q`.
