# Handoff: project status

For an agent or teammate picking this up cold. Background in [../TEAM_BRIEF.md](../TEAM_BRIEF.md);
how our plan changed in [WHAT_CHANGED.txt](WHAT_CHANGED.txt); what's left in
[NEXT_STEPS.md](NEXT_STEPS.md); the demo in [DEMO_SCRIPT.md](DEMO_SCRIPT.md); the production story
in [PRODUCTION_ARCHITECTURE.md](PRODUCTION_ARCHITECTURE.md). If anything here disagrees with git
history, trust git.

## What the product does (as built, 2026-09-27; the app is called Trev in the UI)

1. **Intake** - staff log a new complaint on the **New complaint** page (`POST /complaints/intake`):
   account, region, intake system, channel, and what the customer said. It is classified straight
   away and saved as an open case. `?mode=rules` uses keyword rules instead of Laya (no AI).
2. **Classification** - Laya (local, CPU) sorts each complaint into our five groups and a
   subcategory, decides urgency, and raises flags. P1 always has a stated reason (emergency,
   vulnerable customer, safety risk). The open backlog was classified once with
   `python -m app.classify_backlog`.
3. **Worklist** - each team filters to its own section and sees its cases ranked: urgency, then days
   overdue.
4. **Work this case** (the case page card) - **Get context** (ranked action items, each citing its source)
   and **Generate draft** (an editable reply; never sent by the app). Both check five simulated
   Northwind systems and show a **Systems checked** trace (raw record vs. what was taken from it).
   An **AI on / AI off** switch: AI on = local LLM (gemma4 via Ollama); AI off = fixed rules and
   templates over the same systems (`app/agents/rules_engine.py`). AI failures fall back to rules.

## Where things live

| Area | Files |
|---|---|
| Classification pipeline | `app/classification/service.py` (steps), `taxonomy.py` (groups, urgency levels, Laya questions - **the wording is tuned; re-run the eval after changing it**), `rules.py` (flags, priority, routing), `keywords.py` (no-AI stand-in with Laya's interface) |
| Laya accuracy test | `evals/laya_text_eval.py` - tuning, holdout and fresh sets of hand-labelled complaints |
| Backlog run | `app/classify_backlog.py` (resumable; skips complaints already on the current classifier version) |
| Intake + case buttons | `app/complaint_routes.py` |
| Agent (AI) | `app/agents/runner.py` (instructions), `config.py` (per-domain system prompts), `tools.py` (our-database tools + the two output tools), `systems.py` (Northwind system lookups, tools, trace) |
| Agent (no AI) | `app/agents/rules_engine.py` |
| Simulated Northwind systems | `northwind_systems/` - `generate.py` (data), one app per system, `run.sh` |
| Frontend | `frontend/src/pages/Intake.tsx`, `CaseDetail.tsx`, `components/AgentPanel.tsx`, `SystemsChecked.tsx` |

## Measured accuracy (evals/laya_text_eval.py)

| Set | Group | Urgency exact | Urgency within one level |
|---|---|---|---|
| Holdout (not tuned on), Laya | 75% | 50% | 100% |
| Fresh (neither tuned on), Laya | 72% | 67% | 100% |
| Fresh, keyword rules (no AI) | 39% | 50% | 89% |

The backlog has no customer text, so there Laya mostly reads the category label; when it is unsure
on a text-less row the recorded category is used (`group_source = 'record'`).

## Gotchas

- **Python 3.12.** The code uses `X | None`; macOS's `python3` is often 3.9. Build `.venv` with
  `python3.12`.
- **gemma4 "thinking" must stay off** (`reasoning=False` in `_build_agent_model`). Left on, it
  writes hundreds of hidden tokens per tool call: ~290 s per click instead of ~20-50 s.
- **16 GB Mac + nearly full disk = swapping.** Laya (~1 GB) and gemma4 (~3 GB) together push memory;
  keep several GB of disk free. `ollama stop gemma4:e4b-it-qat` frees 3 GB when not demoing.
- **Tests never reach the local system servers**: `tests/test_complaint_routes.py::_client()` points
  the system URLs at a closed port.
- `db/migrations/002_agent_tables_complaint_fk.sql` was never run on Tiger. It is no longer needed
  for any current flow (intake creates the complaint row before anything references it).

## Known limits

- The five Northwind systems are simulated (clearly labelled). In production they are replaced by
  an integration gateway; only the URLs in settings change.
- No staff login; no approve/send workflow for drafts (staff copy the text).
- The simulator page has no backend.
- One request thread per button click; fine for a demo, not for many concurrent users (see
  PRODUCTION_ARCHITECTURE.md).

## Testing conventions

- Fake the model, not the database: `FakeLaya` for classification; `ScriptedChatModel` (a
  `FakeMessagesListChatModel` with `bind_tools` as a no-op) for the agent; `httpx.MockTransport`
  for the Northwind systems (`tests/test_agent_systems.py`).
- The dashboard views exist only on Postgres; tests create SQLite tables shaped like the view output.
- Route tests use `TestClient` with `StaticPool` + `check_same_thread=False`.
- Run everything: `./.venv/bin/python -m pytest -q`; frontend: `cd frontend && npx tsc -b --noEmit`.
