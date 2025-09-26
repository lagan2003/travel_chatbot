# app.py — Streamlit UI for Groq-powered Travel Itinerary Builder

import os
from datetime import date
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

# ---- Local modules (fail friendly) ----
MISSING_DEPS_HINT = (
    "One or more project files are missing. Make sure these exist next to app.py:\n"
    " - itinerary_engine.py\n - utils.py\n - schema.py\n - prompts/system_prompt.md\n"
    "Then run:  pip install -r requirements.txt"
)

try:
    from itinerary_engine import ItineraryEngine
    from utils import itinerary_to_markdown, markdown_to_pdf_bytes
except Exception as e:
    # We still allow the app to render and show a helpful message later
    ItineraryEngine = None  # type: ignore
    itinerary_to_markdown = None  # type: ignore
    markdown_to_pdf_bytes = None  # type: ignore
    _import_error = e
else:
    _import_error = None

# ---- Env & page ----
load_dotenv()  # loads .env if present
APP_TITLE = os.getenv("APP_TITLE", "Travel Itinerary Chatbot (Groq)")
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "INR")
DEFAULT_TZ = os.getenv("DEFAULT_TIMEZONE", "Asia/Kolkata")

st.set_page_config(page_title=APP_TITLE, page_icon="🗺️", layout="wide")
st.title(APP_TITLE)

# ---- Sidebar inputs ----
with st.sidebar:
    st.header("Trip Inputs")

    destination = st.text_input(
        "Destination (city/country)",
        placeholder="Tokyo, Japan",
    )

    currency = st.text_input("Currency", DEFAULT_CURRENCY)

    budget = st.number_input(
        "Total Budget",
        min_value=0.0,
        step=100.0,
        value=50000.0,
        help="Overall trip budget in the selected currency.",
    )

    days = st.number_input(
        "Days",
        min_value=1,
        max_value=30,
        value=5,
        help="Total number of trip days.",
    )

    # Streamlit returns a datetime.date (or today's date if not set and shown)
    start_date: Optional[date] = st.date_input(
        "Start Date",
        format="YYYY-MM-DD",
        help="Optional. Leave as-is if you don't have fixed dates.",
    )

    travelers = st.number_input(
        "Travelers",
        min_value=1,
        max_value=10,
        value=2,
        help="Total number of people traveling.",
    )

    interests = st.text_area(
        "Interests (comma separated)",
        "food, culture, landmarks",
        height=96,
    )

    pace = st.selectbox("Pace", ["relaxed", "balanced", "packed"], index=1)

    dietary = st.text_input("Dietary needs (optional)", "")

    timezone = st.text_input("Timezone", DEFAULT_TZ)

    generate = st.button("Generate Itinerary", type="primary")

# ---- Dependency check (show once) ----
if _import_error:
    with st.expander("⚠️ Module import error (click for details)"):
        st.exception(_import_error)
    st.info(MISSING_DEPS_HINT)

# ---- Main action ----
if generate:
    # Validate required inputs early
    if not destination.strip():
        st.error("Please enter a destination.")
        st.stop()

    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        st.error(
            "GROQ_API_KEY is not set. Create a `.env` file with `GROQ_API_KEY=your_key` "
            "or set it in your environment."
        )
        st.stop()

    if ItineraryEngine is None or itinerary_to_markdown is None or markdown_to_pdf_bytes is None:
        st.error("Local project modules not available. See the import error above.")
        st.stop()

    # Convert date to ISO string or None
    start_iso = start_date.isoformat() if isinstance(start_date, date) else None

    engine = ItineraryEngine()

    with st.spinner("Planning your trip with Groq…"):
        try:
            itin = engine.generate(
                destination=destination.strip(),
                budget=float(budget),
                currency=currency.strip() or DEFAULT_CURRENCY,
                days=int(days),
                start_date=start_iso,
                travelers=int(travelers),
                interests=interests.strip(),
                pace=pace,
                dietary=dietary.strip(),
                timezone=timezone.strip() or DEFAULT_TZ,
            )
        except Exception as e:
            st.error("Failed to generate itinerary from Groq.")
            with st.expander("Error details"):
                st.exception(e)
            st.stop()

    # Render + downloads
    try:
        md = itinerary_to_markdown(itin.model_dump())
    except Exception as e:
        st.error("Itinerary parsed but failed to convert to Markdown.")
        with st.expander("Conversion error details"):
            st.exception(e)
        st.stop()

    st.success("Itinerary ready!")

    st.download_button("⬇️ Download Markdown", data=md, file_name="itinerary.md")

    try:
        pdf_bytes = markdown_to_pdf_bytes(md)
        st.download_button("⬇️ Download PDF", data=pdf_bytes, file_name="itinerary.pdf")
    except Exception as e:
        st.warning("PDF export unavailable (ReportLab not installed or render failed).")
        with st.expander("PDF error details"):
            st.exception(e)

    st.divider()
    st.subheader("Preview")
    st.markdown(md)

    with st.expander("Raw JSON (debug)"):
        # Pydantic model -> dict pretty print
        st.json(itin.model_dump())

else:
    st.info("Enter details in the sidebar and click **Generate Itinerary** to create your plan.")
