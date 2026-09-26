"""Laya decision model, loaded once and shared across requests.

The English checkpoint (~850 MB) is downloaded from Hugging Face on first use and
cached in ~/.cache/huggingface, so the first request is slow and later ones are fast.
"""
import json
import threading
from typing import Any

from laya import Router

_router: Router | None = None
_lock = threading.Lock()


def get_router() -> Router:
    global _router
    with _lock:
        if _router is None:
            # max_loaded=1 keeps RAM down; multilingual/typed-decisions load on demand.
            _router = Router(device="cpu", max_loaded=1)
            _router.preload(["english"])
        return _router


def warm_up() -> None:
    """Load the checkpoint and run one dummy question, so the first real request is not slower."""
    get_router().predict("warm up", {"q": {"type": "noul", "instructions": "Is this a test?"}})


class CachedLaya:
    """Remembers Laya's answers. Complaints with the same fields render to the same state, so they share answers."""

    def __init__(self, max_size: int = 50_000):
        self._cache: dict[tuple[str, str], dict] = {}
        self._max_size = max_size

    def predict(self, state: str, questions: dict[str, dict[str, Any]]) -> dict:
        key = (state, json.dumps(questions, sort_keys=True))
        if key not in self._cache:
            if len(self._cache) >= self._max_size:
                self._cache.clear()
            self._cache[key] = get_router().predict(state, questions)
        return self._cache[key]


_cached = CachedLaya()


def get_laya() -> CachedLaya:
    return _cached
