"""
Itinerary Planner page — the multi-step trip planning workflow that was the
original Streamlit app. Search → Pick Flight → Pick Hotel → Itinerary.
"""

from __future__ import annotations

import os
import tempfile

import httpx
import streamlit as st

from frontend.common import BACKEND, stars, post_json, html

STARTER_PROMPTS = [
    ("Mumbai", "Goa", "Weekend getaway, budget 25000 INR, prefer beaches"),
    ("New York", "Paris", "5-day luxury trip with a budget of $5000"),
    ("London", "Tokyo", "7-day family vacation, $8000 budget, kid-friendly"),
    ("Delhi", "Manali", "3-day solo backpacking, budget 15000 INR"),
    ("Singapore", "Bali", "5-day honeymoon, $4000 budget, romantic"),
    ("Dubai", "Istanbul", "4-day cultural exploration, $3000 budget"),
]


def _init_state() -> None:
    defaults = {
        "planner_result": None,
        "planner_last_destination": None,
        "planner_source_input": "", "planner_dest_input": "", "planner_query_input": "",
        "planner_run_query": False,
        "planner_selected_flight": 0, "planner_selected_hotel": 0,
        "planner_step": "search",  # search | select_flight | select_hotel | itinerary
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _set_starter(src: str, dest: str, desc: str) -> None:
    st.session_state.planner_source_input = src
    st.session_state.planner_dest_input = dest
    st.session_state.planner_query_input = desc
    st.session_state.planner_run_query = True
    st.session_state.planner_result = None
    st.session_state.planner_step = "search"


def _clear_all() -> None:
    keys = [k for k in st.session_state if k.startswith("planner_")]
    for k in keys:
        del st.session_state[k]
    _init_state()


def render() -> None:
    _init_state()

    st.markdown("""
    <div class="hero-wrap">
        <div class="hero-icon">🌍</div>
        <div class="hero-title">Agentic AI Travel Planner</div>
        <div class="hero-sub">
            AI agents search flights, hotels, check weather, optimize your budget,
            and build a day-by-day itinerary — all in seconds.
        </div>
    </div>
    """, unsafe_allow_html=True)

    steps = {"search": "① Search", "select_flight": "② Pick Flight",
             "select_hotel": "③ Pick Hotel", "itinerary": "④ Itinerary"}
    order = list(steps.keys())
    cur_idx = order.index(st.session_state.planner_step)

    pills = []
    for i, (key, label) in enumerate(steps.items()):
        cls = "step-done" if i < cur_idx else ("step-active" if i == cur_idx else "")
        pills.append(f'<span class="step-pill {cls}">{label}</span>')
    st.markdown(f'<div class="step-bar">{"".join(pills)}</div>', unsafe_allow_html=True)

    step = st.session_state.planner_step

    if step == "search":
        _render_search()
    elif step == "select_flight" and st.session_state.planner_result:
        _render_select_flight()
    elif step == "select_hotel" and st.session_state.planner_result:
        _render_select_hotel()
    elif step == "itinerary" and st.session_state.planner_result:
        _render_itinerary()


def _render_search() -> None:
    if st.session_state.planner_result is None:
        st.markdown('<div class="section-hdr"><span class="icon">⚡</span> Quick Start</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Click any trip below to auto-fill, or enter your own details.</div>',
                    unsafe_allow_html=True)
        cols = st.columns(2)
        for i, (src, dest, desc) in enumerate(STARTER_PROMPTS):
            with cols[i % 2]:
                st.markdown('<div class="starter-btn">', unsafe_allow_html=True)
                st.button(
                    f"✈️  {src} → {dest}  •  {desc[:48]}…",
                    key=f"planner_s_{i}",
                    use_container_width=True,
                    on_click=_set_starter,
                    args=(src, dest, desc),
                )
                st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        st.text_input("🛫 From (origin)", key="planner_source_input", placeholder="e.g. Mumbai, New York")
    with c2:
        st.text_input("🛬 To (destination)", key="planner_dest_input", placeholder="e.g. Goa, Paris, Tokyo")
    st.text_input("📝 Trip details", key="planner_query_input",
                  placeholder="e.g. 5-day luxury trip, budget $5000, prefer beaches")

    plan_clicked = st.button("🚀 Plan My Trip", use_container_width=True, key="planner_plan_btn")
    should_run = plan_clicked or st.session_state.planner_run_query

    if not should_run:
        return

    st.session_state.planner_run_query = False
    src = st.session_state.planner_source_input.strip()
    dest = st.session_state.planner_dest_input.strip()
    desc = st.session_state.planner_query_input.strip()

    if not src or not dest:
        st.warning("Please enter both origin and destination cities.")
        return
    if not desc:
        st.warning("Please describe your trip details.")
        return

    full_query = f"{desc} from {src} to {dest}"
    with st.spinner("🔍 Agents collaborating — searching flights, hotels, weather…"):
        data, err = post_json("/plan", {"query": full_query, "source": src, "destination": dest}, timeout=180.0)

    if err:
        st.error(err)
        return

    st.session_state.planner_result = data
    st.session_state.planner_last_destination = data.get("destination", dest)
    st.session_state.planner_selected_flight = 0
    st.session_state.planner_selected_hotel = 0
    st.session_state.planner_step = "select_flight" if data.get("all_flights") else "itinerary"
    st.rerun()


def _render_select_flight() -> None:
    data = st.session_state.planner_result
    flights = data.get("all_flights", [])
    route = f"{data.get('source', '?')} → {data.get('destination', '?')}"

    st.markdown(f'<div class="section-hdr"><span class="icon">✈️</span> Select Your Flight — {route}</div>',
                unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-sub">Choose from {len(flights)} available flights. '
        f'The recommended option is pre-selected.</div>',
        unsafe_allow_html=True,
    )

    if flights:
        min_price = min(f["price"] for f in flights)
        for i, f in enumerate(flights):
            is_selected = i == st.session_state.planner_selected_flight
            badge = ""
            if f.get("recommended"):
                badge = "  🏆 **RECOMMENDED**"
            elif f["price"] == min_price:
                badge = "  💰 **CHEAPEST**"

            dep = f["departure_time"].split("T")[1][:5] if "T" in f["departure_time"] else f["departure_time"]
            arr = f["arrival_time"].split("T")[1][:5] if "T" in f["arrival_time"] else f["arrival_time"]
            stops_lbl = "Non-stop" if f.get("stops", 0) == 0 else f"{f['stops']} stop(s)"
            dur_lbl = ""
            if f.get("duration_minutes"):
                h, m = divmod(int(f["duration_minutes"]), 60)
                dur_lbl = f" • {h}h {m}m"

            with st.container(border=True):
                col_info, col_price = st.columns([4, 1])
                with col_info:
                    sel_marker = "✅ " if is_selected else ""
                    st.markdown(f"### {sel_marker}{f['airline']}{badge}")
                    st.caption(f"{f['flight_number']}  •  {dep} → {arr}{dur_lbl}  •  {stops_lbl}")
                with col_price:
                    st.markdown(f"### :green[${f['price']:.0f}]")

                if st.button(
                    "Selected ✓" if is_selected else f"Select {f['airline']}",
                    key=f"planner_sf_{i}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state.planner_selected_flight = i
                    st.rerun()

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back", use_container_width=True, key="planner_back_to_search"):
            st.session_state.planner_step = "search"
            st.rerun()
    with c2:
        st.markdown('<div class="confirm-btn">', unsafe_allow_html=True)
        if st.button("Confirm Flight →", use_container_width=True, key="planner_confirm_flight"):
            st.session_state.planner_step = "select_hotel" if data.get("all_hotels") else "itinerary"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def _render_select_hotel() -> None:
    data = st.session_state.planner_result
    hotels = data.get("all_hotels", [])
    dest = data.get("destination", "?")

    st.markdown(f'<div class="section-hdr"><span class="icon">🏨</span> Select Your Hotel in {dest}</div>',
                unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-sub">Choose from {len(hotels)} hotels. Recommended option is pre-selected.</div>',
        unsafe_allow_html=True,
    )

    if hotels:
        max_rating = max(h["rating"] for h in hotels)
        for i, h in enumerate(hotels):
            is_selected = i == st.session_state.planner_selected_hotel
            badge = ""
            if h.get("recommended"):
                badge = "  🏆 **RECOMMENDED**"
            elif h["rating"] == max_rating:
                badge = "  ⭐ **TOP RATED**"

            star_str = stars(h["rating"])
            amen_lbl = ""
            if h.get("amenities"):
                amen_lbl = " • " + ", ".join(h["amenities"][:3])
            dist_lbl = ""
            if h.get("distance_from_center_km") is not None:
                dist_lbl = f" • {h['distance_from_center_km']:.1f} km from center"

            with st.container(border=True):
                col_info, col_price = st.columns([4, 1])
                with col_info:
                    sel_marker = "✅ " if is_selected else ""
                    st.markdown(f"### {sel_marker}{h['name']}{badge}")
                    st.caption(f"{star_str} ({h['rating']})  •  {h['address']}{dist_lbl}{amen_lbl}")
                with col_price:
                    st.markdown(f"### :green[${h['price_per_night']:.0f}]")
                    st.caption("per night")

                if st.button(
                    "Selected ✓" if is_selected else f"Select {h['name']}",
                    key=f"planner_sh_{i}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state.planner_selected_hotel = i
                    st.rerun()

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back to Flights", use_container_width=True, key="planner_back_to_flights"):
            st.session_state.planner_step = "select_flight"
            st.rerun()
    with c2:
        st.markdown('<div class="confirm-btn">', unsafe_allow_html=True)
        if st.button("Confirm Hotel & Generate Itinerary →",
                     use_container_width=True, key="planner_confirm_hotel"):
            st.session_state.planner_step = "itinerary"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def _render_itinerary() -> None:
    data = st.session_state.planner_result
    flights = data.get("all_flights", [])
    hotels = data.get("all_hotels", [])
    fi = st.session_state.planner_selected_flight
    hi = st.session_state.planner_selected_hotel

    errors = data.get("validation_errors", [])
    if errors:
        with st.expander("⚠️ Validation Notes", expanded=False):
            for err in errors:
                st.write(f"• {err}")

    st.success("✅ Your travel plan is ready!")

    route = f"{data.get('source', '?')} → {data.get('destination', '?')}"
    cost = data.get("total_cost", 0)
    sel_flight = flights[fi] if fi < len(flights) else None
    sel_hotel = hotels[hi] if hi < len(hotels) else None

    chips = '<div class="cost-strip">'
    chips += f'<div class="cost-chip"><div class="val">{route}</div><div class="lbl">Route</div></div>'
    chips += f'<div class="cost-chip"><div class="val">${cost:,.0f}</div><div class="lbl">Total Estimated</div></div>'
    if sel_flight:
        chips += f'<div class="cost-chip"><div class="val">{sel_flight["airline"]}</div><div class="lbl">Flight — ${sel_flight["price"]:.0f}</div></div>'
    if sel_hotel:
        chips += f'<div class="cost-chip"><div class="val">{sel_hotel["name"][:20]}</div><div class="lbl">Hotel — ${sel_hotel["price_per_night"]:.0f}/night</div></div>'
    chips += '</div>'
    st.markdown(chips, unsafe_allow_html=True)

    st.markdown('<div class="section-hdr"><span class="icon">📋</span> Full Itinerary</div>', unsafe_allow_html=True)
    md_out = data.get("markdown_output", "")
    if md_out:
        st.markdown(md_out)
    else:
        st.info("No itinerary content was generated.")

    recs = data.get("recommendations", [])
    if recs:
        st.markdown('<div class="section-hdr"><span class="icon">💎</span> Hidden Gems & Recommendations</div>',
                    unsafe_allow_html=True)
        rc = st.columns(min(len(recs), 3))
        for i, r in enumerate(recs):
            with rc[i % 3]:
                st.markdown(f'<div class="glass-card" style="min-height:70px">{r}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-hdr"><span class="icon">📥</span> Export</div>', unsafe_allow_html=True)
    ec1, ec2, ec3 = st.columns(3)
    with ec1:
        if md_out:
            st.download_button("⬇ Download Markdown", md_out, "travel_itinerary.md",
                               "text/markdown", use_container_width=True)
    with ec2:
        try:
            from services.pdf_export import export_itinerary_to_html
            td = tempfile.mkdtemp()
            hp = os.path.join(td, "itinerary.html")
            if md_out and export_itinerary_to_html(md_out, hp):
                with open(hp, "rb") as f:
                    st.download_button("⬇ Download HTML", f, "travel_itinerary.html",
                                       "text/html", use_container_width=True)
        except Exception:
            pass
    with ec3:
        try:
            from services.pdf_export import export_itinerary_to_pdf_bytes
            if md_out:
                pdf_bytes = export_itinerary_to_pdf_bytes(md_out)
                if pdf_bytes:
                    st.download_button("⬇ Download PDF", pdf_bytes, "travel_itinerary.pdf",
                                       "application/pdf", use_container_width=True)
        except Exception:
            pass

    st.markdown("---")
    st.markdown('<div class="section-hdr"><span class="icon">💾</span> Save This Trip</div>',
                unsafe_allow_html=True)
    sc1, sc2 = st.columns([3, 1])
    with sc1:
        title = st.text_input("Trip title",
                              value=f"{data.get('source', '')} → {data.get('destination', '')}",
                              key="planner_save_title")
    with sc2:
        if st.button("💾 Save", use_container_width=True, key="planner_save_btn"):
            payload = {
                "title": title,
                "route": route,
                "total_cost": cost,
                "markdown": md_out,
                "all_flights": flights,
                "all_hotels": hotels,
                "selected_flight_index": fi,
                "selected_hotel_index": hi,
                "source": data.get("source"),
                "destination": data.get("destination"),
                "recommendations": recs,
            }
            saved, err = post_json("/trips", {"title": title, "payload": payload}, timeout=20.0)
            if err:
                st.error(err)
            else:
                st.success(f"Trip saved (id: {saved.get('id', '?')[:8]}…)")

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("← Change Flight", use_container_width=True, key="planner_change_flight"):
            st.session_state.planner_step = "select_flight"
            st.rerun()
    with c2:
        if st.button("← Change Hotel", use_container_width=True, key="planner_change_hotel"):
            st.session_state.planner_step = "select_hotel"
            st.rerun()
    with c3:
        if st.button("🔄 New Trip", use_container_width=True, key="planner_new_trip", on_click=_clear_all):
            pass
