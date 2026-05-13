"""
Streamlit Frontend — AI Travel Planner.

Multi-page app with sidebar navigation:
  1. Chat
  2. Itinerary Planner
  3. Flight Recommendation
  4. Hotel Recommendation
  5. Saved Trips
  6. API Status
"""

from __future__ import annotations

import os
import sys

import streamlit as st

# Make the project root importable so `frontend.*` modules resolve.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontend.styles import CSS  # noqa: E402
from frontend import (  # noqa: E402
    pages_planner,
    pages_flight_nlp,
    pages_hotel_nlp,
    pages_saved,
    pages_status,
    pages_chat,
)
from frontend.common import BACKEND, get_json  # noqa: E402


st.set_page_config(page_title="AI Travel Planner", page_icon="✈️", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)


PAGES = {
    "💬 Chat": pages_chat.render,
    "🌍 Itinerary Planner": pages_planner.render,
    "✈️ Flight Recommendation": pages_flight_nlp.render,
    "🏨 Hotel Recommendation": pages_hotel_nlp.render,
    "💼 Saved Trips": pages_saved.render,
    "📡 API Status": pages_status.render,
}


def _backend_status_pill() -> str:
    data, err = get_json("/health", timeout=3.0)
    if err or not data:
        return '<span style="color:#EF4444">● Backend offline</span>'
    return '<span style="color:var(--accent)">● Backend online</span>'


def main() -> None:
    with st.sidebar:
        st.markdown(
            '<div style="font-size:24px;font-weight:800;background:linear-gradient(135deg,#6C63FF,#00D4AA);'
            '-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:6px">'
            '✈️ TravelGenie</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div style="color:var(--text-secondary);font-size:13px;margin-bottom:18px">'
                    'Agentic AI Travel Assistant</div>', unsafe_allow_html=True)

        default_idx = 1  # land on Itinerary Planner by default
        choice = st.radio(
            "Navigate",
            list(PAGES.keys()),
            index=default_idx,
            label_visibility="collapsed",
            key="nav_radio",
        )

        st.markdown("---")
        st.markdown(f'<div style="font-size:12px">{_backend_status_pill()}</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:11px;color:var(--text-dim)">{BACKEND}</div>',
                    unsafe_allow_html=True)

        with st.expander("ℹ️ About"):
            st.write(
                "Multi-agent travel planner powered by LangGraph + Groq. "
                "Backend: FastAPI, Frontend: Streamlit."
            )
            st.write(
                "**Agents:** Intent → (Flight ∥ Hotel ∥ Weather) → Budget → "
                "Itinerary → Recommendation → Validation → Formatter."
            )

    try:
        PAGES[choice]()
    except Exception as e:  # final safety net so a page crash doesn't blank the app
        st.error(f"Page crashed: {e}")
        st.exception(e)


if __name__ == "__main__":
    main()
else:
    main()
