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
(one current row per complaint, older rows kept as history). Today it runs the classification layer only; the
domain AI agents will be called from the same endpoint later.

Rules and taxonomy: `app/classification/` (`taxonomy.py` groups, routes and Laya questions, `rules.py` priority
and flag rules, `service.py` the pipeline). Thresholds are in `app/config.py` and can be set in `.env`
(`GROUP_CONFIDENCE_THRESHOLD`, `FLAG_THRESHOLD`, `EMERGENCY_THRESHOLD`, `AS_OF_DATE`).

**Laya runs every step on every complaint**, even when the data already has a category or priority. New complaints
have no text, so Laya reads a description of the record (category, channel, priority, region, source system,
whether it was transferred), plus the text if there is any. The category in the data is not used to skip a step. It is
compared with Laya's answer afterwards (`group_matches_data`, `subcategory_matches_data`). The one exception is
priority: Northwind's priority (or the level that goes with its `sla_days`) is the starting point, and Laya's urgency
score is used only when the complaint has neither. Flags then raise it, never lower it.

If Laya's top group probability is under `GROUP_CONFIDENCE_THRESHOLD` (0.6), the group and category already in the
data are used instead, and stage 2 is skipped. Only a complaint with no data category goes to the review queue.

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
