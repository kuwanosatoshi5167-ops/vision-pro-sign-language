"""Build a simple PDF containing only the submission report."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate

from build_combined_ml_pdf import (
    BOTTOM_MARGIN,
    LEFT_MARGIN,
    LIGHT_LINE,
    MUTED,
    NAVY,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    REPORT,
    RIGHT_MARGIN,
    ROOT,
    TOP_MARGIN,
    build_styles,
    parse_markdown,
    register_fonts,
)


OUTPUT = ROOT / "output" / "pdf" / "aoi_ml_submission_report.pdf"


def draw_page(canvas, document) -> None:
    canvas.saveState()
    if document.page > 1:
        canvas.setStrokeColor(LIGHT_LINE)
        canvas.setLineWidth(0.5)
        canvas.line(LEFT_MARGIN, PAGE_HEIGHT - 13 * mm, PAGE_WIDTH - RIGHT_MARGIN, PAGE_HEIGHT - 13 * mm)
        canvas.setFont("JP", 7.2)
        canvas.setFillColor(NAVY)
        canvas.drawString(LEFT_MARGIN, PAGE_HEIGHT - 10.5 * mm, "Aoi ML Report - CNN and LSTM")
    canvas.setFont("JP", 7.2)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(PAGE_WIDTH - RIGHT_MARGIN, 9.5 * mm, str(document.page))
    canvas.restoreState()


def build_pdf() -> Path:
    register_fonts()
    styles = build_styles()
    styles["code"].fontName = "Courier"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    story = parse_markdown(REPORT, styles, "Aoi ML Report - CNN and LSTM")

    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title="Aoi ML Report - CNN and LSTM",
        author="Aoi Yamamoto",
        subject="CNN and LSTM evaluation with Apple Vision Pro hand tracking",
    )
    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return OUTPUT


if __name__ == "__main__":
    print(build_pdf())
