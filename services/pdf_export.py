"""
Itinerary export utilities.

  • export_itinerary_to_html(md, path) -> bool   (writes a styled HTML file)
  • export_itinerary_to_pdf_bytes(md) -> bytes   (real PDF via reportlab)
  • export_itinerary_to_pdf(md, path) -> bool    (writes PDF; falls back to HTML)
"""

from __future__ import annotations

import io
import logging
import re
from typing import Iterable

import markdown2

logger = logging.getLogger(__name__)


def export_itinerary_to_html(markdown_content: str, output_path: str) -> bool:
    """Convert Markdown → styled standalone HTML."""
    try:
        html_body = markdown2.markdown(
            markdown_content,
            extras=["tables", "fenced-code-blocks", "strike", "task_list"],
        )
        styled_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Travel Itinerary</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.7;
          margin: 40px; color: #333; max-width: 880px; }}
  h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
  h2 {{ color: #34495e; margin-top: 30px; }}
  h3 {{ color: #7f8c8d; }}
  table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
  th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
  th {{ background-color: #3498db; color: white; }}
  a {{ color: #3498db; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  blockquote {{ border-left: 4px solid #6C63FF; margin: 1em 0; padding: 6px 14px;
                background: #f5f3ff; color: #333; }}
  ul {{ padding-left: 22px; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(styled_html)
        logger.info(f"HTML itinerary saved to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to generate HTML: {e}")
        return False


# ─── Real PDF via reportlab ───

def _markdown_paragraphs(md_text: str) -> Iterable[tuple[str, str]]:
    """Yield (style_name, text) pairs from a markdown blob.
    Very small subset: headings, list items, paragraphs."""
    for raw in md_text.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            yield "Spacer", ""
            continue
        if line.startswith("### "):
            yield "Heading3", line[4:]
        elif line.startswith("## "):
            yield "Heading2", line[3:]
        elif line.startswith("# "):
            yield "Heading1", line[2:]
        elif re.match(r"^[-*]\s+", line):
            yield "Bullet", "• " + re.sub(r"^[-*]\s+", "", line)
        elif re.match(r"^\d+\.\s+", line):
            yield "Bullet", re.sub(r"^(\d+\.)\s+", r"\1 ", line)
        else:
            yield "Body", line


def export_itinerary_to_pdf_bytes(markdown_content: str) -> bytes:
    """Render a real PDF from markdown using reportlab. Returns bytes."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    except ImportError:
        logger.warning("reportlab not installed — cannot render PDF.")
        return b""

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="Travel Itinerary", author="AI Travel Planner",
    )
    base = getSampleStyleSheet()
    styles = {
        "Heading1": ParagraphStyle("h1", parent=base["Heading1"], textColor="#2c3e50", spaceAfter=12),
        "Heading2": ParagraphStyle("h2", parent=base["Heading2"], textColor="#34495e", spaceAfter=8),
        "Heading3": ParagraphStyle("h3", parent=base["Heading3"], textColor="#7f8c8d", spaceAfter=6),
        "Body": ParagraphStyle("body", parent=base["BodyText"], leading=15),
        "Bullet": ParagraphStyle("bullet", parent=base["BodyText"], leading=15, leftIndent=14),
    }

    story = []
    for style_name, text in _markdown_paragraphs(markdown_content):
        if style_name == "Spacer":
            story.append(Spacer(1, 0.25 * cm))
            continue
        # Light inline markdown handling: **bold** → <b>, *italic* → <i>
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*", r"<i>\1</i>", text)
        text = re.sub(r"`([^`]+)`", r"<font face='Courier'>\1</font>", text)
        # Escape unescaped ampersands & angle brackets that aren't tags
        text = re.sub(r"&(?!(?:amp|lt|gt|quot|#\d+);)", "&amp;", text)
        story.append(Paragraph(text, styles[style_name]))

    try:
        doc.build(story)
    except Exception as e:
        logger.error(f"reportlab build failed: {e}")
        return b""
    return buf.getvalue()


def export_itinerary_to_pdf(markdown_content: str, output_path: str) -> bool:
    pdf_bytes = export_itinerary_to_pdf_bytes(markdown_content)
    if not pdf_bytes:
        # Fall back to HTML next to the requested PDF path
        html_path = output_path.replace(".pdf", ".html")
        return export_itinerary_to_html(markdown_content, html_path)
    try:
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        return True
    except OSError as e:
        logger.error(f"Could not write PDF: {e}")
        return False
