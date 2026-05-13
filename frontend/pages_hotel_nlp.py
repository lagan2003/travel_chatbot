"""
Hotel Recommendation Assistant — free-form NL search.
"""

from __future__ import annotations

import streamlit as st

from frontend.common import post_json, stars, html

EXAMPLES = [
    "Best luxury hotels in Goa near beach",
    "Budget hotels under $80 in Manali",
    "Family hotels in Singapore with pool",
    "4-star business hotels in London with gym",
]


def render() -> None:
    st.markdown("""
    <div class="hero-wrap">
        <div class="hero-icon">🏨</div>
        <div class="hero-title">Hotel Recommendation Assistant</div>
        <div class="hero-sub">Tell us what kind of stay you want — we'll filter and rank.</div>
    </div>
    """, unsafe_allow_html=True)

    if "hotel_nlp_query" not in st.session_state:
        st.session_state.hotel_nlp_query = ""
    if "hotel_nlp_result" not in st.session_state:
        st.session_state.hotel_nlp_result = None

    st.markdown('<div class="section-hdr"><span class="icon">⚡</span> Try an Example</div>',
                unsafe_allow_html=True)
    cols = st.columns(2)
    for i, ex in enumerate(EXAMPLES):
        with cols[i % 2]:
            st.markdown('<div class="starter-btn">', unsafe_allow_html=True)
            if st.button(f"💡  {ex}", key=f"hnlp_ex_{i}", use_container_width=True):
                st.session_state.hotel_nlp_query = ex
                _do_search(ex)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    q = st.text_area(
        "Describe the hotel you want",
        value=st.session_state.hotel_nlp_query,
        height=80,
        key="hotel_nlp_query_input",
        placeholder="e.g. romantic beach hotels in Bali under $200/night with a pool",
    )

    if st.button("🔎 Search Hotels", use_container_width=True, key="hotel_nlp_search_btn"):
        if not q.strip():
            st.warning("Please describe what you're looking for.")
        else:
            st.session_state.hotel_nlp_query = q
            _do_search(q)

    if st.session_state.hotel_nlp_result:
        _render_results(st.session_state.hotel_nlp_result)


def _do_search(query: str) -> None:
    with st.spinner("🤖 Extracting filters and searching hotels…"):
        data, err = post_json("/hotels/search", {"query": query}, timeout=60.0)
    if err:
        st.error(err)
        return
    st.session_state.hotel_nlp_result = data
    st.rerun()


def _render_results(data: dict) -> None:
    ex = data.get("extracted", {})
    hotels = data.get("hotels", [])
    expl = data.get("explanation", "")

    st.markdown('<div class="section-hdr"><span class="icon">🧠</span> What I Understood</div>',
                unsafe_allow_html=True)
    chips = '<div class="cost-strip">'
    chips += f'<div class="cost-chip"><div class="val">{ex.get("destination") or "—"}</div><div class="lbl">Destination</div></div>'
    if ex.get("style"):
        chips += f'<div class="cost-chip"><div class="val">{ex["style"].title()}</div><div class="lbl">Style</div></div>'
    if ex.get("max_price_per_night"):
        chips += f'<div class="cost-chip"><div class="val">${ex["max_price_per_night"]:.0f}</div><div class="lbl">Max/night</div></div>'
    if ex.get("min_rating"):
        chips += f'<div class="cost-chip"><div class="val">{ex["min_rating"]}★+</div><div class="lbl">Min Rating</div></div>'
    if ex.get("amenities"):
        chips += f'<div class="cost-chip"><div class="val">{len(ex["amenities"])}</div><div class="lbl">Amenities</div></div>'
    chips += '</div>'
    st.markdown(chips, unsafe_allow_html=True)

    if ex.get("amenities"):
        st.caption("Required amenities: " + ", ".join(ex["amenities"]))

    st.info(expl)

    st.markdown('<div class="section-hdr"><span class="icon">🎯</span> Results</div>', unsafe_allow_html=True)
    if not hotels:
        st.warning("No hotels matched your filters.")
        return

    for h in hotels:
        star_str = stars(h["rating"])
        amens = h.get("amenities") or []
        amen_lbl = "  •  " + ", ".join(amens[:6]) if amens else ""
        dist_lbl = ""
        if h.get("distance_from_center_km") is not None:
            dist_lbl = f" • {h['distance_from_center_km']:.1f} km from center"
        badge = "  🏆 **RECOMMENDED**" if h.get("recommended") else ""
        url = h.get("booking_url") or "#"

        with st.container(border=True):
            col_info, col_price = st.columns([4, 1])
            with col_info:
                st.markdown(f"### {h['name']}{badge}")
                st.caption(f"{star_str} ({h['rating']})  •  {h['address']}{dist_lbl}{amen_lbl}")
                st.markdown(f"[Book ↗]({url})")
            with col_price:
                st.markdown(f"### :green[${h['price_per_night']:.0f}]")
                st.caption("per night")
