"""
API Status Dashboard.
"""

from __future__ import annotations

import streamlit as st

from frontend.common import get_json, html


def _badge(live: bool, configured: bool) -> str:
    if live:
        color, label = "var(--accent)", "HEALTHY"
    elif configured:
        color, label = "var(--warning)", "DEGRADED"
    else:
        color, label = "var(--text-dim)", "NOT CONFIGURED"
    return (f'<span style="background:{color};color:#111;font-weight:700;font-size:11px;'
            f'padding:3px 10px;border-radius:6px;letter-spacing:0.5px">{label}</span>')


def render() -> None:
    st.markdown("""
    <div class="hero-wrap">
        <div class="hero-icon">📡</div>
        <div class="hero-title">API Status Dashboard</div>
        <div class="hero-sub">Live health of every dependency the backend talks to.</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🔄 Refresh", key="status_refresh"):
        st.rerun()

    with st.spinner("Probing services…"):
        data, err = get_json("/status", timeout=30.0)
    if err:
        st.error(err)
        return

    overall = data.get("overall", "unknown")
    overall_color = {"healthy": "var(--accent)", "degraded": "var(--warning)", "down": "#EF4444"}.get(overall, "#9CA3AF")
    st.markdown(
        f'<div class="cost-strip">'
        f'<div class="cost-chip"><div class="val" style="color:{overall_color}">{overall.upper()}</div>'
        f'<div class="lbl">Overall</div></div>'
        f'<div class="cost-chip"><div class="val">{data.get("healthy_services", 0)}/{data.get("total_services", 0)}</div>'
        f'<div class="lbl">Services live</div></div>'
        f'<div class="cost-chip"><div class="val">{data.get("cache", {}).get("live_entries", 0)}</div>'
        f'<div class="lbl">Cache (live)</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    for s in data.get("services", []):
        live = bool(s.get("live"))
        configured = bool(s.get("configured"))
        note = s.get("note") or "OK"
        extras = ""
        if s.get("provider"):
            extras += f' • {s["provider"]}'
        if s.get("model"):
            extras += f' • {s["model"]}'

        if live:
            label, color = "✅ HEALTHY", "green"
        elif configured:
            label, color = "⚠️ DEGRADED", "orange"
        else:
            label, color = "○ NOT CONFIGURED", "gray"

        with st.container(border=True):
            col_info, col_badge = st.columns([4, 1])
            with col_info:
                st.markdown(f"### {s.get('name', '?').title()}{extras}")
                st.caption(note)
            with col_badge:
                st.markdown(f"### :{color}[{label}]")
