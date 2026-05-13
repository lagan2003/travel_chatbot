"""
Critic Agent — drives the agentic loop.

After the validation agent has produced hard errors, the critic decides
whether to:

  - APPROVE  : the plan is good enough, move on to the formatter.
  - REVISE   : there are fixable problems, loop back to the itinerary agent
               with a `revision_hint` describing what to change.

Hard caps the loop at MAX_LOOPS to guarantee termination.
"""

from __future__ import annotations

import logging
from models.state import AgentState
from models.schemas import CriticVerdict
from services.llm import generate_structured_data
from prompts.system_prompts import CRITIC_PROMPT

logger = logging.getLogger(__name__)


MAX_LOOPS = 2


def critic_agent(state: AgentState) -> dict:
    itinerary = state.get("itinerary")
    errors = state.get("validation_errors", []) or []
    loop_count = int(state.get("loop_count", 0))

    if not itinerary:
        logger.warning("Critic: no itinerary to review — approving by default.")
        return {"critic_verdict": "APPROVE", "loop_count": loop_count}

    budget = float(state.get("original_budget", 0.0) or 0.0)
    daily_budget = float(state.get("daily_activity_budget", 0.0) or 0.0)
    duration = int(itinerary.intent.duration_days)
    day_count = len(itinerary.daily_plans)
    total_cost = float(itinerary.total_estimated_cost)

    # Cheap deterministic checks — saves the LLM round-trip in the obvious cases.
    deterministic_issues: list[str] = []
    if budget > 0 and total_cost > budget * 1.02:
        deterministic_issues.append(
            f"Total cost ${total_cost:.2f} exceeds budget ${budget:.2f}."
        )
    if duration and day_count != duration:
        deterministic_issues.append(
            f"Day count mismatch — got {day_count}, expected {duration}."
        )
    if not itinerary.flights:
        deterministic_issues.append("No flight selected.")
    if not itinerary.hotels:
        deterministic_issues.append("No hotel selected.")

    prompt = CRITIC_PROMPT.format(
        budget=budget,
        duration=duration,
        daily_budget=daily_budget,
        total_cost=total_cost,
        day_count=day_count,
        errors=errors + deterministic_issues,
    )
    verdict = generate_structured_data(prompt, CriticVerdict)

    if verdict is None:
        verdict = CriticVerdict(
            verdict="REVISE" if deterministic_issues else "APPROVE",
            issues=deterministic_issues,
            revision_hint=(
                "Trim activity costs to fit the budget and re-distribute across days."
                if deterministic_issues else ""
            ),
        )

    # Merge deterministic issues so the planner sees everything.
    merged_issues = list(dict.fromkeys([*verdict.issues, *deterministic_issues]))
    verdict.issues = merged_issues

    # Force-approve once we've burned the loop budget — prevents infinite cycles.
    if verdict.verdict == "REVISE" and loop_count >= MAX_LOOPS:
        logger.warning(
            f"Critic: REVISE requested but loop_count={loop_count} >= "
            f"MAX_LOOPS={MAX_LOOPS} — force-approving."
        )
        verdict.verdict = "APPROVE"

    new_loop = loop_count + (1 if verdict.verdict == "REVISE" else 0)
    logger.info(
        f"Critic verdict={verdict.verdict} | issues={len(verdict.issues)} | "
        f"loop_count={new_loop}/{MAX_LOOPS}"
    )

    return {
        "critic_verdict": verdict.verdict,
        "loop_count": new_loop,
        "revision_hint": verdict.revision_hint,
        # Surface critic issues into the same channel as validation errors.
        "validation_errors": verdict.issues,
    }


def critic_route_selector(state: AgentState) -> str:
    """LangGraph conditional edge: loop back or move on to the formatter."""
    verdict = state.get("critic_verdict") or "APPROVE"
    return "itinerary" if verdict == "REVISE" else "formatter"
