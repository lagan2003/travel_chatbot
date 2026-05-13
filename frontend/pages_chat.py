"""
Chat — token-streamed conversation with the LLM (no agent pipeline).
Useful for quick questions: "What's the visa policy for Bali?", "Pack list for
Iceland in winter?", etc.
"""

from __future__ import annotations

import httpx
import streamlit as st

from frontend.common import BACKEND


def render() -> None:
    st.markdown("""
    <div class="hero-wrap">
        <div class="hero-icon">💬</div>
        <div class="hero-title">Travel Chat</div>
        <div class="hero-sub">Ask anything about travel — visas, packing, customs, food, safety.</div>
    </div>
    """, unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(msg)

    prompt = st.chat_input("Ask anything about your trip…")
    if not prompt:
        return

    st.session_state.chat_history.append(("user", prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    full_prompt = "You are a friendly, expert travel assistant. Be concise and practical.\n\nUser: " + prompt
    with st.chat_message("assistant"):
        placeholder = st.empty()
        chunks: list[str] = []
        try:
            with httpx.stream("POST", f"{BACKEND}/chat/stream",
                              json={"prompt": full_prompt}, timeout=120.0) as r:
                if r.status_code >= 400:
                    placeholder.error(f"Server error ({r.status_code})")
                    return
                for chunk in r.iter_text():
                    if chunk:
                        chunks.append(chunk)
                        placeholder.markdown("".join(chunks))
        except httpx.ConnectError:
            placeholder.error(f"❌ Cannot connect to backend at {BACKEND}.")
            return
        except Exception as e:
            placeholder.error(f"❌ Streaming error: {e}")
            return

    st.session_state.chat_history.append(("assistant", "".join(chunks)))
