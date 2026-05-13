"""
Shared helpers for the Streamlit frontend pages.
"""

from __future__ import annotations

import os
import textwrap
from typing import Any

import httpx
import streamlit as st


def html(markup: str) -> None:
    """Render dedented HTML — works around Streamlit's markdown treating
    4+-space-indented HTML as a code block."""
    st.markdown(textwrap.dedent(markup).strip(), unsafe_allow_html=True)

BACKEND = os.getenv("BACKEND_URL") or f"http://{os.getenv('BACKEND_HOST', '127.0.0.1')}:{os.getenv('BACKEND_PORT', '8000')}"


def stars(rating: float) -> str:
    full = int(rating)
    half = 1 if rating - full >= 0.3 else 0
    return "★" * full + ("½" if half else "") + "☆" * max(0, 5 - full - half)


def post_json(path: str, body: dict, timeout: float = 60.0) -> tuple[dict[str, Any] | None, str | None]:
    """POST to backend. Returns (data, error). Exactly one is None."""
    try:
        resp = httpx.post(f"{BACKEND}{path}", json=body, timeout=timeout)
    except httpx.ConnectError:
        return None, f"❌ Cannot connect to backend at {BACKEND}. Run: `uvicorn main:app --port 8000`"
    except httpx.TimeoutException:
        return None, f"❌ Timed out calling {path}."
    except Exception as e:
        return None, f"❌ Error calling {path}: {e}"
    if resp.status_code >= 400:
        return None, f"❌ Server error ({resp.status_code}): {resp.text[:300]}"
    try:
        return resp.json(), None
    except ValueError:
        return None, "❌ Server returned a non-JSON response."


def get_json(path: str, timeout: float = 15.0) -> tuple[Any | None, str | None]:
    try:
        resp = httpx.get(f"{BACKEND}{path}", timeout=timeout)
    except httpx.ConnectError:
        return None, f"❌ Cannot connect to backend at {BACKEND}. Run: `uvicorn main:app --port 8000`"
    except Exception as e:
        return None, f"❌ Error calling {path}: {e}"
    if resp.status_code >= 400:
        return None, f"❌ Server error ({resp.status_code}): {resp.text[:300]}"
    try:
        return resp.json(), None
    except ValueError:
        return None, "❌ Server returned a non-JSON response."


def delete(path: str, timeout: float = 15.0) -> tuple[Any | None, str | None]:
    try:
        resp = httpx.delete(f"{BACKEND}{path}", timeout=timeout)
    except Exception as e:
        return None, f"❌ Error: {e}"
    if resp.status_code >= 400:
        return None, f"❌ Server error ({resp.status_code}): {resp.text[:300]}"
    try:
        return resp.json(), None
    except ValueError:
        return None, None
