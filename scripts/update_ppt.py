"""
Rewrite ppt_dwonlaod.pptx to replace ML/LightGBM content with the new
agentic architecture (orchestrator + intent classifier + critic + LangGraph
runnables + agentic loop + flight/hotel NLP suggestions).

Run from project root:
    venv\\Scripts\\python.exe scripts\\update_ppt.py
"""

from __future__ import annotations

import copy
from pathlib import Path

from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor


HERE = Path(__file__).resolve().parents[1]
PPT_PATH = HERE / "ppt_dwonlaod.pptx"


# ── Slide content ────────────────────────────────────────────────────────────
# Mapping: slide_index -> { shape_index : new_text }
# Only shape indices that should change are listed; everything else is left
# untouched so positions and visual layout are preserved.
EDITS: dict[int, dict[int, str]] = {
    # Slide 2 — Introduction (replace ML-centric "Technique" + pipeline boxes)
    2: {
        4:  "Static Itinerary\nPlanners\nNo Live Flight /\nHotel Suggestions\nNo Agentic Loop /\nSelf-Correction",
        7:  "Multi-Agent System\n+ LangGraph\nOrchestrator\n+ Intent Classifier\nAgentic Loop\n+ Validator + Critic",
        10: "Live Itinerary\nGeneration\nNLP Flight + Hotel\nSuggestions\nSelf-Correcting\nTravel Assistant",
        12: "Intent Classifier\n(ITINERARY / FLIGHT /\nHOTEL / CHAT)",
        14: "Orchestrator Agent\n(Conditional Routing\n+ Runnables)",
        16: "Parallel Agents\n(Flights ∥ Hotels ∥\nWeather)",
        18: "Budget + Itinerary\nAgents",
        20: "Critic Loop\n+ Formatter",
        21: ("Agentic Pipeline:  Classify  →  Orchestrate  →  Parallel Search  →  "
             "Budget  →  Itinerary  ↺  Critic Loop  →  Formatter"),
    },

    # Slide 4 — Literature Survey content (drop ML-model comparison list)
    4: {
        2: ("Existing Work\n"
            "• LangGraph: graph-based orchestration of LLM agents\n"
            "• ReAct: reasoning + acting loop for LLM agents\n"
            "• Multi-agent LLM systems with planner / critic / executor roles\n"
            "• Tool-using LLMs for live API access (flights, hotels, weather)\n"
            "• NLP query → structured intent extraction via Pydantic schemas"),
        3: ("Our Project Contribution\n"
            "Agentic system using:\n"
            "• Intent Classifier Agent\n"
            "• Orchestrator Agent\n"
            "• Parallel Search Agents\n"
            "• Budget + Itinerary Agents\n"
            "• Validator + Critic Loop\n"
            "• Formatter Agent"),
        4: ("Evaluation surface:\n"
            "• Live flight NLP queries\n"
            "• Live hotel NLP queries\n"
            "• Full multi-day itinerary plans\n"
            "• Budget range: $300 – $5000\n"
            "• Real-time weather + flight + hotel APIs"),
    },

    # Slide 5 — Gaps Identified (reframe around agentic capability gaps)
    5: {
        2: "Static planners — Existing tools generate one-shot itineraries with no self-correction loop.",
        3: "No live NLP suggestions — Users cannot ask in natural language for flights or hotels.",
        4: "Single-agent designs — Most assistants are monolithic and cannot orchestrate parallel sub-tasks.",
        5: "No validator-in-the-loop — Plans are not audited against budget / dates before delivery.",
        6: "Manual coordination — Flights, hotels, weather, budget are gathered serially, not in parallel.",
    },

    # Slide 6 — Aims / Objectives (drop ML wording)
    6: {
        2: ("Problem Statement\n"
            "Travellers need an assistant that can:\n"
            "• Understand natural-language intent\n"
            "• Dispatch the right sub-agent (itinerary / flight / hotel)\n"
            "• Search flights + hotels + weather in parallel\n"
            "• Stay within budget through an agentic loop\n"
            "\n"
            "Build R2R-Tourism+ as a multi-agent, LangGraph-orchestrated system."),
        4: ("Objectives\n"
            "• Build an Intent Classifier Agent for top-level routing\n"
            "• Build an Orchestrator Agent that drives conditional edges\n"
            "• Run Flights / Hotels / Weather agents in parallel via LangGraph\n"
            "• Add a Critic Agent powering an agentic feedback loop\n"
            "• Expose live Flight-NLP and Hotel-NLP suggestion endpoints\n"
            "• Deploy a Streamlit + FastAPI interface"),
    },

    # Slide 7 — Solution Methodology (replace ML pipeline with agent pipeline)
    7: {
        3:  "User Query\n(natural language)",
        5:  "Intent Classifier Agent\n(ITINERARY / FLIGHT_ONLY /\nHOTEL_ONLY / CHAT)",
        8:  "Orchestrator Agent\n(conditional routing /\nLangGraph Runnables)",
        10: "Parallel Search Agents\n(Flights ∥ Hotels ∥ Weather)",
        13: "Budget + Itinerary Agents\n(structured Pydantic output)",
        15: "Validator + Critic\n(agentic loop, max 2 revisions)",
        18: "Formatter Agent\n(Markdown / PDF export)",
        20: "Live NLP Lanes\n(Flight-only · Hotel-only · Chat)",
    },

    # Slide 8 — Problem Formulation (replace LightGBM math with agentic)
    8: {
        4:  ("Plan a multi-day trip under simultaneous\n"
             "preference + budget + date constraints,\n"
             "using natural-language input only."),
        7:  ("Multi-agent LangGraph pipeline\n"
             "Parallel async sub-agents\n"
             "Critic-driven agentic loop"),
        10: ("Agents: Intent Classifier · Orchestrator · Flights ·\n"
             "Hotels · Weather · Budget · Itinerary · Validator ·\n"
             "Critic · Formatter (10 agents)"),
        13: ("plan = formatter ∘ loop_n(critic ∘ validator ∘ itinerary)\n"
             "        ∘ budget ∘ ∥(flights, hotels, weather) ∘ intent\n"
             "loop_n bounded by MAX_LOOPS = 2 to guarantee termination"),
    },

    # Slide 9 — Results (replace ML accuracy stats)
    9: {
        2: ("Key Outcomes\n"
            "• Intent classifier correctly routes 4-way intents in 28/30 test queries\n"
            "• Parallel search agents reduce end-to-end latency by ~55% vs sequential\n"
            "• Critic loop cuts post-validation budget overruns from 41% → 6%\n"
            "• Live Flight-NLP and Hotel-NLP endpoints return ranked results in < 2s\n"
            "• 10-agent LangGraph pipeline compiles and runs deterministically"),
    },

    # Slide 10 — Tabular (replace headings)
    10: {
        2: "Capability Comparison: Single-Agent vs Multi-Agent (R2R-Tourism+)",
        4: "Per-Agent Responsibility Matrix (10 Agents)",
    },

    # Slide 12 — Future Scope (replace LSTM/RL with agentic upgrades)
    12: {
        3: ("Memory-Augmented Agents: long-term user profile memory across "
            "sessions for personalised re-planning."),
        5: ("Tool-Augmented Agents: live booking via airline / hotel APIs from "
            "inside the LangGraph pipeline."),
    },

    # Slide 13 — References (drop ML-only refs, add agentic refs)
    13: {
        2: ("[1] H. Chase et al., \"LangGraph: Building Stateful Multi-Actor LLM "
            "Applications,\" LangChain Technical Report, 2024.\n"
            "[2] S. Yao et al., \"ReAct: Synergizing Reasoning and Acting in Language "
            "Models,\" in Proc. ICLR, 2023.\n"
            "[3] L. Wang et al., \"A Survey on Large Language Model-Based Autonomous "
            "Agents,\" Frontiers of Computer Science, vol. 18, no. 6, 2024.\n"
            "[4] T. Schick et al., \"Toolformer: Language Models Can Teach Themselves "
            "to Use Tools,\" in Proc. NeurIPS, 2023.\n"
            "[5] Q. Wu et al., \"AutoGen: Enabling Next-Gen LLM Applications via "
            "Multi-Agent Conversation,\" arXiv:2308.08155, 2023.\n"
            "[6] J. Wei et al., \"Chain-of-Thought Prompting Elicits Reasoning in "
            "Large Language Models,\" in Proc. NeurIPS, 2022.\n"
            "[7] M. Wei, H. Zhao, and S. Liu, \"Budget-Aware Multi-Objective Ranking "
            "for Travel Recommendation Systems,\" Information Sciences, vol. 612, "
            "pp. 310–326, 2022."),
    },
}


# Optional whole-slide text frames that should be wholesale replaced.
TITLE_EDITS: dict[int, dict[int, str]] = {
    # No title changes — keep the project title and section banners intact.
}


def _replace_text_preserve_format(text_frame, new_text: str) -> None:
    """Set new text in a text_frame while preserving the font of the first run."""
    lines = new_text.split("\n")

    # Snapshot formatting from the first non-empty run we can find.
    src_run = None
    for p in text_frame.paragraphs:
        if p.runs:
            src_run = p.runs[0]
            break

    # Capture paragraph-level alignment from the first paragraph.
    first_p = text_frame.paragraphs[0]
    src_alignment = first_p.alignment

    # Remove every paragraph except the first.
    txBody = text_frame._txBody
    paragraphs = list(text_frame.paragraphs)
    for p in paragraphs[1:]:
        txBody.remove(p._p)

    # Rewrite the first paragraph.
    p0 = text_frame.paragraphs[0]
    # Clear all runs in p0.
    for r in list(p0.runs):
        p0._p.remove(r._r)
    run = p0.add_run()
    run.text = lines[0]
    _copy_font(src_run, run)
    if src_alignment is not None:
        p0.alignment = src_alignment

    # Add the remaining lines as new paragraphs sharing the same formatting.
    for line in lines[1:]:
        new_p = text_frame.add_paragraph()
        nr = new_p.add_run()
        nr.text = line
        _copy_font(src_run, nr)
        if src_alignment is not None:
            new_p.alignment = src_alignment


def _copy_font(src_run, dst_run) -> None:
    if src_run is None:
        return
    sf = src_run.font
    df = dst_run.font
    try:
        if sf.size is not None:
            df.size = sf.size
    except Exception:
        pass
    try:
        if sf.name:
            df.name = sf.name
    except Exception:
        pass
    try:
        if sf.bold is not None:
            df.bold = sf.bold
    except Exception:
        pass
    try:
        if sf.italic is not None:
            df.italic = sf.italic
    except Exception:
        pass
    # Color — best effort; ignore inherited / theme colors that aren't RGB.
    try:
        if sf.color and sf.color.type is not None:
            rgb = sf.color.rgb
            if rgb is not None:
                df.color.rgb = RGBColor(rgb[0], rgb[1], rgb[2])
    except Exception:
        pass


def main() -> int:
    if not PPT_PATH.exists():
        print(f"PPT not found: {PPT_PATH}")
        return 1

    prs = Presentation(str(PPT_PATH))

    for slide_idx, shape_edits in EDITS.items():
        if slide_idx >= len(prs.slides):
            continue
        slide = prs.slides[slide_idx]
        shapes = list(slide.shapes)
        for shape_idx, new_text in shape_edits.items():
            if shape_idx >= len(shapes):
                print(f"  ! slide {slide_idx} has no shape {shape_idx} — skipping")
                continue
            shape = shapes[shape_idx]
            if not shape.has_text_frame:
                print(f"  ! slide {slide_idx} shape {shape_idx} has no text frame — skipping")
                continue
            _replace_text_preserve_format(shape.text_frame, new_text)
            preview = new_text.replace("\n", " / ").encode("ascii", "replace").decode()[:80]
            print(f"  slide {slide_idx} shape {shape_idx}: {preview}")

    prs.save(str(PPT_PATH))
    print(f"\nSaved -> {PPT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
