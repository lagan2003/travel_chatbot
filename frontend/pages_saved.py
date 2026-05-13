"""
Saved Trips — list / open / delete.
"""

from __future__ import annotations

import streamlit as st

from frontend.common import get_json, delete, html


def render() -> None:
    st.markdown("""
    <div class="hero-wrap">
        <div class="hero-icon">💼</div>
        <div class="hero-title">Your Saved Trips</div>
        <div class="hero-sub">Plans you've saved — open any to view the full itinerary.</div>
    </div>
    """, unsafe_allow_html=True)

    trips, err = get_json("/trips", timeout=10.0)
    if err:
        st.error(err)
        return

    if not trips:
        st.info("No saved trips yet. Plan one in the Itinerary Planner and click Save.")
        return

    open_id = st.session_state.get("saved_open_id")

    if open_id:
        _render_one(open_id)
        if st.button("← Back to list", key="saved_back"):
            st.session_state.saved_open_id = None
            st.rerun()
        return

    for t in trips:
        title = t.get("title") or t.get("route") or t.get("id", "")[:8]
        cost = t.get("total_cost") or t.get("payload", {}).get("total_cost") or 0
        route = t.get("route") or f'{t.get("source", "?")} → {t.get("destination", "?")}'
        saved_at = t.get("saved_at", "")
        tid = t.get("id")

        with st.container(border=True):
            col_info, col_price = st.columns([4, 1])
            with col_info:
                st.markdown(f"### {title}")
                st.caption(f"{route}  •  saved {saved_at}")
            with col_price:
                st.markdown(f"### :green[${float(cost or 0):.0f}]")

            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("📂 Open", key=f"saved_open_{tid}", use_container_width=True):
                    st.session_state.saved_open_id = tid
                    st.rerun()
            with c2:
                if st.button("🗑️ Delete", key=f"saved_del_{tid}", use_container_width=True):
                    _, derr = delete(f"/trips/{tid}")
                    if derr:
                        st.error(derr)
                    else:
                        st.success("Deleted.")
                        st.rerun()


def _render_one(trip_id: str) -> None:
    trip, err = get_json(f"/trips/{trip_id}")
    if err:
        st.error(err)
        return

    title = trip.get("title") or trip_id[:8]
    st.markdown(f"## {title}")
    st.caption(f"Saved at: {trip.get('saved_at', '—')}")

    cost = trip.get("total_cost") or 0
    route = trip.get("route") or f"{trip.get('source', '?')} → {trip.get('destination', '?')}"
    chips = '<div class="cost-strip">'
    chips += f'<div class="cost-chip"><div class="val">{route}</div><div class="lbl">Route</div></div>'
    chips += f'<div class="cost-chip"><div class="val">${float(cost or 0):.0f}</div><div class="lbl">Estimated</div></div>'
    chips += '</div>'
    st.markdown(chips, unsafe_allow_html=True)

    md = trip.get("markdown") or ""
    if md:
        st.markdown(md)
    else:
        st.info("This trip has no rendered itinerary text saved.")
