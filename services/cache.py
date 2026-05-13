"""
Lightweight in-process TTL cache + retry decorator shared by API services.
Zero external deps beyond stdlib + tenacity.
"""

from __future__ import annotations

import os
import asyncio
import functools
import hashlib
import json
import logging
import time
from typing import Any, Callable, Tuple

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

logger = logging.getLogger(__name__)


_DEFAULT_TTL = int(os.getenv("CACHE_TTL_SECONDS", "900"))

# (key) -> (expires_at, value)
_STORE: dict[str, Tuple[float, Any]] = {}


def _make_key(prefix: str, *args, **kwargs) -> str:
    payload = json.dumps({"a": args, "k": kwargs}, sort_keys=True, default=str)
    return f"{prefix}:{hashlib.md5(payload.encode()).hexdigest()}"


def cache_get(key: str) -> Any | None:
    entry = _STORE.get(key)
    if not entry:
        return None
    expires_at, value = entry
    if expires_at < time.time():
        _STORE.pop(key, None)
        return None
    return value


def cache_set(key: str, value: Any, ttl: int = _DEFAULT_TTL) -> None:
    _STORE[key] = (time.time() + ttl, value)


def cache_clear(prefix: str | None = None) -> int:
    """Drop entries (all, or matching a prefix). Returns count removed."""
    if prefix is None:
        n = len(_STORE)
        _STORE.clear()
        return n
    to_drop = [k for k in _STORE if k.startswith(f"{prefix}:")]
    for k in to_drop:
        _STORE.pop(k, None)
    return len(to_drop)


def cache_stats() -> dict:
    now = time.time()
    live = sum(1 for exp, _ in _STORE.values() if exp >= now)
    return {"total_entries": len(_STORE), "live_entries": live}


def cached(prefix: str, ttl: int = _DEFAULT_TTL):
    """Decorator that caches async function results in-process by args."""
    def deco(fn: Callable):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            key = _make_key(prefix, *args, **kwargs)
            hit = cache_get(key)
            if hit is not None:
                logger.debug(f"cache hit: {key}")
                return hit
            result = await fn(*args, **kwargs)
            cache_set(key, result, ttl)
            return result
        return wrapper
    return deco


# ─── retry decorator for external HTTP calls ───

http_retry = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type((
        httpx.TimeoutException,
        httpx.NetworkError,
        httpx.RemoteProtocolError,
    )),
)
