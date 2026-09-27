# Handoff: project status and what's next

For an agent or teammate picking this up cold. Background and evidence are in
[../TEAM_BRIEF.md](../TEAM_BRIEF.md); full requirements in [requirements.md](requirements.md);
DB design in [db-schema.md](db-schema.md). This file is the "where are we right now" layer on
top of those — it will go stale as work continues, so prefer git history over this file for
anything that sounds outdated.

## Current state (as of this writing)

Everything below is merged into local `main`, **not yet pushed to `origin/main`**. Two lines of
work landed here: a teammate's frontend + dashboard API (`frontend/`, `app/reports/`), and the
domain-agent buttons described in this file.

- Classification (`app/classification/`, requirements section A) — Laya-based, fully built and tested, unchanged by any of this.
- Dashboards (section D) — mostly built: `app/reports/` serves worklist, backlog flow/breakdown, root-cause, cases, case detail, account history, case profiles, classification summary and agent-results, and `frontend/` (React + Vite) has pages for all of them.
- Simulator (section E) — a **preview/placeholder page only** (`frontend/src/pages/Simulator.tsx`); no backend behind it yet.
- Staff workspace (section C) — partially covered by the dashboard pages (worklist, case detail) plus the "Get context"/"Generate draft" buttons below; there's still no staff login/auth, and no approve/edit/send flow for a saved draft.
- Domain AI agent (section B) — **rebuilt twice this session**, see below. Read that section fully before touching `app/agents/` - it's the part most likely to have changed since you last looked.

## Environment gotcha

The codebase uses `X | None` type syntax (Python 3.10+). The macOS system `python3` is often
3.9, which fails to import this code. Use `python3.12` (`brew install python@3.12` if needed)
when creating `.venv`. See the README's Setup section.

## Domain AI agent: two one-shot buttons, no chatbot

**This has been rebuilt twice this session.** First from an automatic per-complaint pipeline to a
free-form staff chat, then from that chat to what's here now: two single-purpose buttons on a
case, no message box, no conversation. If you find a reference to `app/agents/backends.py`,
`service.py`, `context.py`, `prompt.py`, `chat.py`, `OllamaBackend`, `TemplateBackend`,
`run_domain_agent`, `run_chat_turn`, `ChatRequest`/`ChatSession`-for-this-feature, or a `/chat`
endpoint anywhere (old docs, your own memory of an earlier version of this file), it's stale.
**The current design's own git history is the accurate record — read that over any prose,
including this file, if something looks inconsistent.**

**How it actually works:** nothing about the agent runs automatically. Classification still runs
on every complaint. Staff filter the dashboard to their team (e.g. Billing), see complaints
ranked by urgency (Laya's classification), click into a specific one, and then click one of two
buttons on that case's view:

- **"Get context"** → `POST /complaints/{complaint_id}/context` — runs the agent's read-only
  tools and asks it to record **action items only**. Returns the list it created.
- **"Generate draft"** → `POST /complaints/{complaint_id}/draft` — runs the same read-only tools,
  then asks it to save **one drafted reply only**. Staff copy/edit/approve/send it themselves;
  nothing is sent automatically.

Each button binds a different single output tool (`create_action_brief` vs. `save_draft_reply`) -
**this is enforced structurally, not just by prompt wording**: the model literally cannot produce
the other kind of output, because the other tool was never given to it. Both endpoints log an
`agent_runs` row (status, error, `finished_at`) for every call, success or failure - this is the
first code to actually use that table since it was added (an earlier design's `agent_runs` FK bug
was fixed back when it still mattered; unaffected by any of this).

| File | Job |
|---|---|
| `app/agents/config.py` | **Edit this for real prompt wording.** `AGENT_CONFIGS` has one entry per domain with a working-but-generic system prompt. |
| `app/agents/tools.py` | `build_context_tools(db, complaint, as_of)` — the four shared read-only tools: `read_case` (the complaint's own category/channel/priority/region/source system/status/days-open — added because the agent otherwise has *no way* to know what case it's even looking at), `get_account_complaints`, `get_case_profile`, `get_region_meter_picture`. `build_context_tools_for(agent_id, ...)` adds `search_knowledge_base` for `general` only. `build_action_item_tool(db, complaint, run_id)` and `build_draft_tool(db, complaint, run_id)` are the two single-purpose output tools, each built fresh per call and bound to that call's `AgentRun.run_id`. |
| `app/agents/runner.py` | `run_agent_once(model, cfg, tools, instruction)` — one fixed-instruction invocation via `create_agent`; nothing is returned, the tool's own DB write is the output. Raises `AgentBackendError` (defined here) on any model/tool-loop failure - the only exception the route code catches. |
| `app/agents/schemas.py` | `ContextResponse`/`DraftOut`/`ActionItemOut` — the two endpoints' response shapes. |
| `app/complaint_routes.py` | `POST /complaints/{complaint_id}/context` and `.../draft` — 404 if the complaint doesn't exist, resolves the domain (falls back to `general` if unclassified), creates the `AgentRun`, builds that call's tools, runs it, reads back what got written, commits. |

### Config (`app/config.py`, all overridable via `.env`)

- `AGENT_ENABLED` (default `true`) — `false` skips the LLM call entirely; both endpoints record a
  failed `AgentRun` (`error` explains why) and return one instead of calling anything (requirement N6).
- `AGENT_MODEL` (default `gemma4`) — **gemma3 has no tool-calling support in Ollama at all**
  (confirmed: no gemma3 tag, size, or variant supports it). gemma4 does, natively, ~86%
  tool-calling accuracy per Google. `ollama pull gemma4` (or whatever size fits) before relying on this for real.
- `OLLAMA_HOST` (default `http://localhost:11434`), `AGENT_TIMEOUT_SECONDS` (default `30.0`, per call).

### `chat_sessions`/`chat_messages` and the placeholder `staff` row are unused by this feature

Both tables exist in the schema for a *different*, still-unbuilt feature (requirements section F,
a general not-complaint-scoped staff chat assistant, P2/lowest priority) - they're not used by
`/context` or `/draft` at all, since there's no conversation and no staff identity needed to click
a button. The placeholder `staff` seed row (`db/schema.sql`) is still there and still harmless,
just not required for this feature specifically.

### Known, deliberately-deferred issues (real, not urgent)

- No concurrency: each button call blocks its own request thread for up to
  `AGENT_TIMEOUT_SECONDS` if Ollama is slow. Fine for a demo, not for real concurrent load.
- `get_account_complaints` doesn't paginate (hardcoded `LIMIT 20`) — fine for the data size here.
- Clicking "Get context" again on the same case adds *more* action items rather than superseding
  the earlier ones (no "dismiss the old batch" step) — same idea for "Generate draft" and old drafts.

### One thing NOT yet done — needs a human's go-ahead

`db/migrations/002_agent_tables_complaint_fk.sql` (fixes a real, pre-existing `db/schema.sql` bug:
`agent_runs`/`draft_responses`/`action_items.complaint_id` had a FK that broke processing any
complaint not already in the `complaints` table) is written but **has not been run** against the
live Tiger Data service (`hackthehill`, service id `rhw3xtuwno`, DEV environment). Safe and
additive, but it touches a shared service other teammates may be pointed at, so it wasn't applied
without asking first.

## What's still genuinely unbuilt

- **Simulator backend** (section E) — the frontend page is a labeled preview; the what-if
  calculator (transfer reduction / fast-lane share → projected days, cost, regulator score) has no
  API behind it. Per requirements.md this and the worklist are what were meant to carry the demo.
- **Staff auth** — no login, no real staff identity anywhere yet.
- **Approve/edit/send flow for a saved draft** — `DraftResponse` rows get created (`status='draft'`)
  but nothing in the frontend or backend yet lets staff mark one approved/edited/sent.
- Domain-specific tools beyond the shared four — there's no real per-domain backing data yet
  (no per-account bill/appointment/outage tables), so metering/field_services/customer_support
  don't have anything beyond the shared set. If a real domain-specific data source shows up later,
  add its tool the same way `search_knowledge_base` was added to `general`.
- The "clicking again piles up" issue above, and the general (not-complaint-scoped) staff chat
  assistant from requirements section F — both out of scope of what's here.

## Testing conventions established so far (follow these, don't reinvent)

- Fake the model, not the DB: `FakeLaya` (`tests/test_service.py`) for classification;
  `ScriptedChatModel` (a `FakeMessagesListChatModel` subclass with `bind_tools` made a no-op —
  see `tests/test_agent_runner.py` or `tests/test_complaint_routes.py`) for the agent's model.
  Plain dependency-injected stand-ins, no mocking library.
- The dashboard SQL views (`db/views.sql`) only exist on Postgres. Tests that need one create a
  plain SQLite table shaped like the view's output columns (see `tests/test_agent_tools.py`'s
  `_db()` fixture) — the queries in `app/agents/tools.py` only need the column names to match,
  since they're straight `SELECT ... WHERE ...`, no Postgres-only SQL.
- Route-level tests use FastAPI's `TestClient` with `StaticPool` + `check_same_thread=False`
  (plain SQLite in-memory otherwise gives each thread its own empty DB, since FastAPI runs sync
  routes in a worker thread) — see `tests/test_complaint_routes.py::_client()`.
- Run the full suite with `./.venv/bin/python -m pytest -q`.
