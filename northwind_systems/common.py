"""Shared plumbing for the simulated Northwind system servers. Each system still has its own app,
own port, own data file and own API style - this is only the boring part they all need."""
import json
import sqlite3
from pathlib import Path

from fastapi import HTTPException

DATA = Path(__file__).resolve().parent / "data"
SIMULATED = "SIMULATED system for the Hack the Hill demo. Data is generated, not real Northwind data."


def query(system: str, sql: str, *params) -> list[dict]:
    """Rows from a system's own store, with each row's JSON `doc` column decoded."""
    path = DATA / f"{system}.sqlite"
    if not path.exists():
        raise HTTPException(503, f"{system} store not found - run `python -m northwind_systems.generate`")
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        return [json.loads(r["doc"]) for r in conn.execute(sql, params).fetchall()]


def page(title: str, style: str, body: str) -> str:
    """A console page: the system's own look, plus a small lookup script supplied by the system."""
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{style}</style></head><body>{body}</body></html>"""
