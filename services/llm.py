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
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        api_key=api_key,
        temperature=0.2,
        max_retries=2,
    )


def generate_structured_data(prompt: str, schema: Type[Any]) -> Any:
    """
    Generate structured output matching a Pydantic schema.

    Two-tier strategy:
      1. with_structured_output (tool-calling).
      2. If that fails (Groq sometimes rejects complex nested schemas), fall
         back to plain text generation + manual JSON parse.

    Returns None if both attempts fail so callers can fall back further.
    """
    import json
    import re

    llm = get_llm()

    # Attempt 1 — structured output via tool calling
    try:
        structured_llm = llm.with_structured_output(schema)
        return structured_llm.invoke(prompt)
    except Exception as e:
        logger.warning(
            f"with_structured_output failed for {schema.__name__}: "
            f"{type(e).__name__}: {str(e)[:300]}"
        )

    # Attempt 2 — plain text JSON parsing
    try:
        json_schema = schema.model_json_schema()
        fallback_prompt = (
            prompt
            + "\n\nReturn ONLY a single JSON object matching this schema (no markdown, no prose):\n"
            + json.dumps(json_schema, indent=2)
        )
        resp = llm.invoke(fallback_prompt)
        text = (resp.content or "").strip()
        # Strip optional ```json fences
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        # Find the outermost JSON object
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            return schema(**data)
    except Exception as e:
        logger.warning(
            f"JSON-fallback also failed for {schema.__name__}: "
            f"{type(e).__name__}: {str(e)[:300]}"
        )

    return None
