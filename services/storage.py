"""
JSON-file-backed store for saved trips. Single-process, simple, no DB.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_STORE_PATH = os.getenv("TRIPS_STORE_PATH", "./saved_trips.json")
_LOCK = threading.Lock()


def _read_all() -> list[dict[str, Any]]:
    if not os.path.exists(_STORE_PATH):
        return []
    try:
        with open(_STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not read trips store ({e!r}). Starting empty.")
        return []


def _write_all(rows: list[dict[str, Any]]) -> None:
    with open(_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, default=str)


def save_trip(trip: dict[str, Any]) -> str:
    """Persist a trip and return its id."""
    with _LOCK:
        rows = _read_all()
        trip_id = trip.get("id") or str(uuid.uuid4())
        record = {
            "id": trip_id,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            **{k: v for k, v in trip.items() if k != "id"},
        }
        # replace if exists else append
        for i, r in enumerate(rows):
            if r.get("id") == trip_id:
                rows[i] = record
                break
        else:
            rows.append(record)
        _write_all(rows)
        return trip_id


def list_trips() -> list[dict[str, Any]]:
    return sorted(_read_all(), key=lambda r: r.get("saved_at", ""), reverse=True)


def get_trip(trip_id: str) -> dict[str, Any] | None:
    for r in _read_all():
        if r.get("id") == trip_id:
            return r
    return None


def delete_trip(trip_id: str) -> bool:
    with _LOCK:
        rows = _read_all()
        new_rows = [r for r in rows if r.get("id") != trip_id]
        if len(new_rows) == len(rows):
            return False
        _write_all(new_rows)
        return True
