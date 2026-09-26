# hackthehill-cgi-track

FastAPI + SQLAlchemy backend, connected to Tiger Data (or any Postgres).

## Setup

```bash
python3 -m venv .venv
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
