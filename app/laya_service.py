"""Laya decision model, loaded once and shared across requests.

The English checkpoint (~850 MB) is downloaded from Hugging Face on first use and
cached in ~/.cache/huggingface, so the first request is slow and later ones are fast.
"""
import threading

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
