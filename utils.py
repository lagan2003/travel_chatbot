# utils.py

import io
from typing import List
from markdownify import markdownify as md
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import cm


def make_budget_allocation(total: float) -> dict:
    # 35% lodging, 25% food, 20% transport, 15% attractions, 5% buffer
    return {
        "lodging": round(total * 0.35, 2),
        "food": round(total * 0.25, 2),
        "transport": round(total * 0.20, 2),
        "attractions": round(total * 0.15, 2),
        "buffer_misc": round(total * 0.05, 2),
    }


def itinerary_to_markdown(itin: dict) -> str:
    lines: List[str] = []
    lines.append(f"# Itinerary: {itin.get('destination')} ({itin.get('days')} days)")
    if itin.get("start_date"):
        lines.append(f"**Start Date:** {itin['start_date']}")

    bb = itin.get("budget", {})
    lines.append("\n## Budget")
    lines.append(f"- Currency: {bb.get('currency')}")
    lines.append(f"- Total: {bb.get('total_budget')}")

    for k in ["lodging", "food", "transport", "attractions", "buffer_misc"]:
        if k in bb:
            lines.append(f"  - {k.title()}: {bb[k]}")

    lines.append("\n## Plan")
    for d in itin.get("day_plans", []):
        lines.append(f"\n### Day {d.get('day')}{' — ' + d['date'] if d.get('date') else ''}")
        if d.get("summary"):
            lines.append(f"*{d['summary']}*")
        for a in d.get("activities", []):
            lines.append(f"- **[{a.get('time_block','')}] {a.get('title','')}** — {a.get('description','')}")
            meta = []
            if a.get("neighborhood"):
                meta.append(a["neighborhood"])
            if a.get("transport"):
                meta.append(a["transport"])
            if a.get("est_cost") is not None:
                meta.append(f"~{a['est_cost']} {bb.get('currency','')}")
            if meta:
                lines.append("  - " + ", ".join(meta))
            if a.get("tips"):
                lines.append(f"  - Tip: {a['tips']}")
        if d.get("est_daily_cost") is not None:
            lines.append(f"  - **Est. daily cost:** {d['est_daily_cost']} {bb.get('currency','')}")

    if itin.get("packing_list"):
        lines.append("\n## Packing list")
        for p in itin["packing_list"]:
            lines.append(f"- {p}")

    if itin.get("safety_notes"):
        lines.append("\n## Safety notes")
        for s in itin["safety_notes"]:
            lines.append(f"- {s}")

    if itin.get("local_tips"):
        lines.append("\n## Local tips")
        for t in itin["local_tips"]:
            lines.append(f"- {t}")

    return "\n".join(lines)


def markdown_to_pdf_bytes(markdown_text: str) -> bytes:
    htmlish = md(markdown_text)
    buff = io.BytesIO()
    doc = SimpleDocTemplate(
        buff,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []
    for para in htmlish.split("\n\n"):
        story.append(Paragraph(para, styles["Normal"]))
        story.append(Spacer(1, 0.3 * cm))
    doc.build(story)
    return buff.getvalue()
