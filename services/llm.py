"""
LLM service — Groq API integration using langchain-groq.
Provides a reusable ChatGroq instance and a helper that returns
Pydantic-validated structured output from any prompt.
"""

import os
import logging
from typing import Any, Type
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def get_llm() -> ChatGroq:
    """Returns the ChatGroq model instance."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not found in environment variables. Calls will fail.")

    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=api_key,
        temperature=0.2,
        max_retries=2,
    )


def generate_structured_data(prompt: str, schema: Type[Any]) -> Any:
    """
    Utility: generate structured output matching a Pydantic schema.
    Uses with_structured_output (tool-calling under the hood).
    Returns None on failure so callers can fall back gracefully.
    """
    llm = get_llm()
    structured_llm = llm.with_structured_output(schema)
    try:
        response = structured_llm.invoke(prompt)
        return response
    except Exception as e:
        logger.error(f"Error generating structured data: {e}")
        return None
