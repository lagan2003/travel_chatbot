"""
Flight Recommendation Assistant — accepts free-form NL queries.
"""

from __future__ import annotations

import streamlit as st

from frontend.common import post_json, html


EXAMPLES = [
    "Find cheapest flights from Delhi to Dubai next weekend",
    "Suggest business class flights from New York to London",
    "Morning flights from Mumbai to Bangalore under $100",
    "Non-stop flights from San Francisco to Tokyo in October",
]


def render() -> None:
    st.markdown("""
    <div class="hero-wrap">
        <div class="hero-icon">✈️</div>
        <div class="hero-title">Flight Recommendation Assistant</div>
        <div class="hero-sub">Just describe what you're looking for — we'll handle the rest.</div>
    </div>
    """, unsafe_allow_html=True)

    if "flight_nlp_query" not in st.session_state:
        st.session_state.flight_nlp_query = ""
    if "flight_nlp_result" not in st.session_state:
        st.session_state.flight_nlp_result = None

    st.markdown('<div class="section-hdr"><span class="icon">⚡</span> Try an Example</div>',
                unsafe_allow_html=True)
    cols = st.columns(2)
    for i, ex in enumerate(EXAMPLES):
        with cols[i % 2]:
            st.markdown('<div class="starter-btn">', unsafe_allow_html=True)
            if st.button(f"💡  {ex}", key=f"fnlp_ex_{i}", use_container_width=True):
                st.session_state.flight_nlp_query = ex
                _do_search(ex)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    q = st.text_area(
        "Describe the flights you want",
        value=st.session_state.flight_nlp_query,
        height=80,
        key="flight_nlp_query_input",
        placeholder="e.g. cheap morning flights from Mumbai to Goa next Friday under $120",
    )

    if st.button("🔎 Search Flights", use_container_width=True, key="flight_nlp_search_btn"):
        if not q.strip():
            st.warning("Please describe what you're looking for.")
        else:
            st.session_state.flight_nlp_query = q
            _do_search(q)

    if st.session_state.flight_nlp_result:
        _render_results(st.session_state.flight_nlp_result)


def _do_search(query: str) -> None:
    with st.spinner("🤖 Extracting intent and searching flights…"):
        data, err = post_json("/flights/search", {"query": query}, timeout=60.0)
    if err:
        st.error(err)
        return
    st.session_state.flight_nlp_result = data
    st.rerun()


def _render_results(data: dict) -> None:
    ex = data.get("extracted", {})
    flights = data.get("flights", [])
    expl = data.get("explanation", "")

    st.markdown('<div class="section-hdr"><span class="icon">🧠</span> What I Understood</div>',
                unsafe_allow_html=True)
    chips = '<div class="cost-strip">'
    chips += f'<div class="cost-chip"><div class="val">{ex.get("source") or "—"}</div><div class="lbl">From</div></div>'
    chips += f'<div class="cost-chip"><div class="val">{ex.get("destination") or "—"}</div><div class="lbl">To</div></div>'
    chips += f'<div class="cost-chip"><div class="val">{ex.get("departure_date") or "—"}</div><div class="lbl">Date</div></div>'
    chips += f'<div class="cost-chip"><div class="val">{(ex.get("cabin_class") or "economy").title()}</div><div class="lbl">Class</div></div>'
    if ex.get("max_price"):
        chips += f'<div class="cost-chip"><div class="val">${ex["max_price"]:.0f}</div><div class="lbl">Max Price</div></div>'
    if ex.get("time_of_day"):
        chips += f'<div class="cost-chip"><div class="val">{ex["time_of_day"].title()}</div><div class="lbl">Time of Day</div></div>'
    if ex.get("non_stop"):
        chips += '<div class="cost-chip"><div class="val">Yes</div><div class="lbl">Non-stop</div></div>'
    chips += '</div>'
    st.markdown(chips, unsafe_allow_html=True)

    st.info(expl)

    st.markdown('<div class="section-hdr"><span class="icon">🎯</span> Results</div>', unsafe_allow_html=True)
    if not flights:
        st.warning("No flights matched your filters.")
        return

    for i, f in enumerate(flights):
        dep = f["departure_time"].split("T")[1][:5] if "T" in f["departure_time"] else f["departure_time"]
        arr = f["arrival_time"].split("T")[1][:5] if "T" in f["arrival_time"] else f["arrival_time"]
        stops_lbl = "Non-stop" if f.get("stops", 0) == 0 else f"{f['stops']} stop(s)"
        dur_lbl = ""
        if f.get("duration_minutes"):
            h, m = divmod(int(f["duration_minutes"]), 60)
            dur_lbl = f" • {h}h {m}m"
        badge = "  🏆 **RECOMMENDED**" if f.get("recommended") else ""
        url = f.get("booking_url") or "#"

        with st.container(border=True):
            col_info, col_price = st.columns([4, 1])
            with col_info:
                st.markdown(f"### {f['airline']} _({f['cabin_class'].title()})_{badge}")
                st.caption(f"{f['flight_number']}  •  {dep} → {arr}{dur_lbl}  •  {stops_lbl}")
                st.markdown(f"[Book ↗]({url})")
            with col_price:
                st.markdown(f"### :green[${f['price']:.0f}]")
