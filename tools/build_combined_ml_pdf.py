"""Build the combined beginner guide and submission report as a polished PDF."""

from __future__ import annotations

import html
import re
import textwrap
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    XPreformatted,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "vision_pro_sign_language_ml_guide_and_report.pdf"
GUIDE = ROOT / "ML_BEGINNER_GUIDE_JA.md"
REPORT = ROOT / "AOI_ML_REPORT.md"

PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 19 * mm
RIGHT_MARGIN = 19 * mm
TOP_MARGIN = 18 * mm
BOTTOM_MARGIN = 18 * mm
CONTENT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2563A7")
PALE_BLUE = colors.HexColor("#EAF3FB")
PALE_CYAN = colors.HexColor("#E8F7F7")
PALE_GOLD = colors.HexColor("#FFF4D8")
INK = colors.HexColor("#17212B")
MUTED = colors.HexColor("#52606D")
LIGHT_LINE = colors.HexColor("#D7E0E8")
ROW_ALT = colors.HexColor("#F6F8FA")


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("JP", r"C:\Windows\Fonts\meiryo.ttc"))
    pdfmetrics.registerFont(TTFont("JP-Bold", r"C:\Windows\Fonts\meiryob.ttc"))
    pdfmetrics.registerFontFamily("JP", normal="JP", bold="JP-Bold")


def normalize_text(value: str) -> str:
    return (
        value.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2011", "-")
        .replace("\u2212", "-")
    )


def inline_markup(value: str) -> str:
    value = normalize_text(value.strip())
    value = re.sub(r"!\[([^]]*)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", value)
    value = value.replace("<br/>", "___LINE_BREAK___")
    value = html.escape(value)
    value = value.replace("___LINE_BREAK___", "<br/>")
    value = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    return value


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "body": ParagraphStyle(
            "BodyJP",
            parent=base["BodyText"],
            fontName="JP",
            fontSize=9.4,
            leading=15.2,
            textColor=INK,
            spaceAfter=5.5,
            wordWrap="CJK",
        ),
        "small": ParagraphStyle(
            "SmallJP",
            parent=base["BodyText"],
            fontName="JP",
            fontSize=7.7,
            leading=11.5,
            textColor=MUTED,
            wordWrap="CJK",
        ),
        "table_body": ParagraphStyle(
            "TableBodyJP",
            parent=base["BodyText"],
            fontName="JP",
            fontSize=9.1,
            leading=13.2,
            textColor=INK,
            wordWrap="CJK",
        ),
        "table_header": ParagraphStyle(
            "TableHeaderJP",
            parent=base["BodyText"],
            fontName="JP-Bold",
            fontSize=9.1,
            leading=13.2,
            textColor=colors.white,
            wordWrap="CJK",
        ),
        "h1": ParagraphStyle(
            "Heading1JP",
            parent=base["Heading1"],
            fontName="JP-Bold",
            fontSize=20,
            leading=27,
            textColor=NAVY,
            spaceBefore=3,
            spaceAfter=14,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "h2": ParagraphStyle(
            "Heading2JP",
            parent=base["Heading2"],
            fontName="JP-Bold",
            fontSize=14.2,
            leading=20,
            textColor=NAVY,
            spaceBefore=12,
            spaceAfter=7,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "h3": ParagraphStyle(
            "Heading3JP",
            parent=base["Heading3"],
            fontName="JP-Bold",
            fontSize=11.2,
            leading=16,
            textColor=BLUE,
            spaceBefore=9,
            spaceAfter=4,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "h4": ParagraphStyle(
            "Heading4JP",
            parent=base["Heading4"],
            fontName="JP-Bold",
            fontSize=9.8,
            leading=14,
            textColor=INK,
            spaceBefore=7,
            spaceAfter=3,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "bullet": ParagraphStyle(
            "BulletJP",
            parent=base["BodyText"],
            fontName="JP",
            fontSize=9.2,
            leading=14.5,
            leftIndent=13,
            firstLineIndent=-8,
            textColor=INK,
            spaceAfter=3,
            wordWrap="CJK",
        ),
        "quote": ParagraphStyle(
            "QuoteJP",
            parent=base["BodyText"],
            fontName="JP",
            fontSize=9.2,
            leading=15,
            leftIndent=12,
            rightIndent=12,
            borderColor=BLUE,
            borderWidth=0,
            borderPadding=8,
            backColor=PALE_BLUE,
            textColor=INK,
            spaceBefore=5,
            spaceAfter=8,
            wordWrap="CJK",
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName="JP",
            fontSize=7.7,
            leading=10.5,
            leftIndent=8,
            rightIndent=8,
            borderPadding=7,
            backColor=colors.HexColor("#F2F4F7"),
            textColor=colors.HexColor("#27313A"),
            spaceBefore=4,
            spaceAfter=7,
        ),
        "caption": ParagraphStyle(
            "CaptionJP",
            parent=base["BodyText"],
            fontName="JP",
            fontSize=7.8,
            leading=11,
            alignment=TA_CENTER,
            textColor=INK,
            spaceBefore=3,
            spaceAfter=8,
            wordWrap="CJK",
        ),
    }


class MLDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str, styles: dict[str, ParagraphStyle]) -> None:
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=LEFT_MARGIN,
            rightMargin=RIGHT_MARGIN,
            topMargin=TOP_MARGIN,
            bottomMargin=BOTTOM_MARGIN,
            title="Apple Vision Pro Sign Language ML Guide and Report",
            author="Aoi Yamamoto",
            subject="CNN and LSTM evaluation with Apple Vision Pro hand tracking",
        )
        self.styles_map = styles
        frame = Frame(
            LEFT_MARGIN,
            BOTTOM_MARGIN,
            CONTENT_WIDTH,
            PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN,
            id="normal",
        )
        self.addPageTemplates(PageTemplate(id="main", frames=[frame], onPage=draw_page_chrome))

    def afterFlowable(self, flowable) -> None:  # noqa: N802
        if isinstance(flowable, Paragraph):
            style_name = flowable.style.name
            if style_name in {"Heading1JP", "Heading2JP"}:
                level = 0 if style_name == "Heading1JP" else 1
                text = flowable.getPlainText()
                key = f"section-{self.seq.nextf('section')}"
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=level, closed=False)
                self.notify("TOCEntry", (level, text, self.page, key))


def draw_page_chrome(canvas, doc) -> None:
    canvas.saveState()
    if doc.page > 1:
        canvas.setStrokeColor(LIGHT_LINE)
        canvas.setLineWidth(0.5)
        canvas.line(LEFT_MARGIN, PAGE_HEIGHT - 13 * mm, PAGE_WIDTH - RIGHT_MARGIN, PAGE_HEIGHT - 13 * mm)
        canvas.setFont("JP", 7.2)
        canvas.setFillColor(MUTED)
        canvas.drawString(LEFT_MARGIN, PAGE_HEIGHT - 10.5 * mm, "Apple Vision Pro 手話認識 - MLガイド・提出用レポート")
        canvas.drawRightString(PAGE_WIDTH - RIGHT_MARGIN, 9.5 * mm, f"{doc.page}")
    canvas.restoreState()


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(inline_markup(text), style)


def metric_table(styles: dict[str, ParagraphStyle]) -> Table:
    data = [
        [paragraph("評価対象", styles["small"]), paragraph("6名・339ウィンドウ", styles["small"])],
        [paragraph("評価方法", styles["small"]), paragraph("6-fold LOSO", styles["small"])],
        [paragraph("CNN Accuracy", styles["small"]), paragraph("77.2 ± 2.4%", styles["small"])],
        [paragraph("LSTM Accuracy", styles["small"]), paragraph("80.9 ± 2.7%", styles["small"])],
    ]
    table = Table(data, colWidths=[42 * mm, 63 * mm], hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def cover_story(styles: dict[str, ParagraphStyle]) -> list:
    title = ParagraphStyle(
        "CoverTitle",
        fontName="JP-Bold",
        fontSize=27,
        leading=38,
        textColor=NAVY,
        alignment=TA_LEFT,
        wordWrap="CJK",
    )
    subtitle = ParagraphStyle(
        "CoverSubtitle",
        fontName="JP",
        fontSize=13,
        leading=21,
        textColor=BLUE,
        alignment=TA_LEFT,
        wordWrap="CJK",
    )
    meta = ParagraphStyle(
        "CoverMeta",
        fontName="JP",
        fontSize=9,
        leading=15,
        textColor=MUTED,
        alignment=TA_LEFT,
        wordWrap="CJK",
    )
    return [
        Spacer(1, 32 * mm),
        Paragraph("Apple Vision Pro<br/>手話認識MLガイド", title),
        Spacer(1, 5 * mm),
        Paragraph("初心者向け解説 + CNN/LSTM提出用レポート", subtitle),
        Spacer(1, 16 * mm),
        metric_table(styles),
        Spacer(1, 24 * mm),
        Paragraph("Aoi Yamamoto", meta),
        Paragraph("Summer Camp ML Development", meta),
        Paragraph("2026年9月2日", meta),
        PageBreak(),
    ]


def toc_story(styles: dict[str, ParagraphStyle]) -> list:
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            "TOC1",
            fontName="JP-Bold",
            fontSize=10,
            leading=16,
            leftIndent=0,
            firstLineIndent=0,
            textColor=NAVY,
            spaceBefore=4,
        ),
        ParagraphStyle(
            "TOC2",
            fontName="JP",
            fontSize=8.4,
            leading=13,
            leftIndent=13,
            firstLineIndent=0,
            textColor=INK,
        ),
    ]
    return [
        Paragraph("目次", styles["h1"]),
        Spacer(1, 4 * mm),
        toc,
        PageBreak(),
    ]


def arrow_shape(x1: float, y: float, x2: float) -> list:
    return [
        Line(x1, y, x2 - 5, y, strokeColor=BLUE, strokeWidth=1.5),
        Polygon([x2 - 5, y + 3, x2, y, x2 - 5, y - 3], fillColor=BLUE, strokeColor=BLUE),
    ]


def labeled_box(drawing: Drawing, x: float, y: float, width: float, height: float, label: str, fill) -> None:
    drawing.add(Rect(x, y, width, height, rx=5, ry=5, fillColor=fill, strokeColor=LIGHT_LINE, strokeWidth=0.7))
    lines = label.split("\n")
    center_y = y + height / 2 + (len(lines) - 1) * 5
    for index, line in enumerate(lines):
        drawing.add(
            String(
                x + width / 2,
                center_y - index * 11,
                line,
                fontName="JP-Bold" if index == 0 else "JP",
                fontSize=7.7,
                textAnchor="middle",
                fillColor=INK,
            )
        )


def diagram_flow(index: int) -> Drawing:
    width = CONTENT_WIDTH
    if index == 0:
        drawing = Drawing(width, 75)
        boxes = [
            (0, 50 * mm, "約3秒の\n両手の動き", PALE_BLUE),
            (70 * mm, 40 * mm, "CNN / LSTM", PALE_CYAN),
            (130 * mm, 40 * mm, "6クラスを\n予測", PALE_GOLD),
        ]
        x_positions = [5 * mm, 72 * mm, 130 * mm]
        widths = [48 * mm, 42 * mm, 40 * mm]
        for x, w, (_, _, label, fill) in zip(x_positions, widths, boxes):
            labeled_box(drawing, x, 20, w, 38, label, fill)
        for item in arrow_shape(x_positions[0] + widths[0] + 3, 39, x_positions[1] - 3):
            drawing.add(item)
        for item in arrow_shape(x_positions[1] + widths[1] + 3, 39, x_positions[2] - 3):
            drawing.add(item)
        return drawing

    if index == 1:
        drawing = Drawing(width, 225)
        steps = [
            "1  Vision ProのCSV",
            "2  採用された本番データだけ残す",
            "3  window_idごとに約3秒へまとめる",
            "4  頭基準の座標へ変換",
            "5  90フレームへ統一",
            "6  未追跡を補間し追跡マスクを追加",
            "7  被験者単位でTrain / Validation / Testへ分割",
            "8  CNNとLSTMを学習・評価",
        ]
        box_width = 132 * mm
        box_height = 19
        x = (width - box_width) / 2
        y = 202
        for step_index, label in enumerate(steps):
            fill = PALE_BLUE if step_index < 4 else PALE_CYAN
            labeled_box(drawing, x, y, box_width, box_height, label, fill)
            if step_index < len(steps) - 1:
                drawing.add(Line(width / 2, y, width / 2, y - 7, strokeColor=BLUE, strokeWidth=1.2))
                drawing.add(Polygon([width / 2 - 3, y - 5, width / 2, y - 9, width / 2 + 3, y - 5], fillColor=BLUE, strokeColor=BLUE))
            y -= 27
        return drawing

    drawing = Drawing(width, 105)
    columns = [
        (5 * mm, 54 * mm, "Train\nS03・S04・S05・S07", PALE_BLUE),
        (68 * mm, 45 * mm, "Validation\nS02", PALE_GOLD),
        (124 * mm, 40 * mm, "Test\nS01", PALE_CYAN),
    ]
    for x, w, label, fill in columns:
        labeled_box(drawing, x, 45, w, 40, label, fill)
    for item in arrow_shape(columns[0][0] + columns[0][1] + 3, 65, columns[1][0] - 3):
        drawing.add(item)
    for item in arrow_shape(columns[1][0] + columns[1][1] + 3, 65, columns[2][0] - 3):
        drawing.add(item)
    drawing.add(String(width / 2, 20, "テスト担当を交代して6回繰り返す", fontName="JP", fontSize=8.2, textAnchor="middle", fillColor=MUTED))
    return drawing


def markdown_table(rows: list[list[str]], styles: dict[str, ParagraphStyle]) -> Table:
    column_count = max(len(row) for row in rows)
    normalized = [row + [""] * (column_count - len(row)) for row in rows]
    cells = []
    for row_index, row in enumerate(normalized):
        cell_style = styles["table_header"] if row_index == 0 else styles["table_body"]
        cells.append([paragraph(cell, cell_style) for cell in row])
    if column_count == 2:
        widths = [CONTENT_WIDTH * 0.34, CONTENT_WIDTH * 0.66]
    elif column_count == 3:
        widths = [CONTENT_WIDTH * 0.34, CONTENT_WIDTH * 0.33, CONTENT_WIDTH * 0.33]
    elif column_count == 4:
        widths = [CONTENT_WIDTH * 0.20, CONTENT_WIDTH * 0.22, CONTENT_WIDTH * 0.29, CONTENT_WIDTH * 0.29]
    else:
        widths = [CONTENT_WIDTH / column_count] * column_count
    table = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "JP-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, LIGHT_LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for row_index in range(1, len(cells)):
        if row_index % 2 == 0:
            commands.append(("BACKGROUND", (0, row_index), (-1, row_index), ROW_ALT))
    table.setStyle(TableStyle(commands))
    return table


def image_flow(path_text: str, alt: str, styles: dict[str, ParagraphStyle]) -> list:
    path = ROOT / path_text
    if not path.exists():
        return [paragraph(f"[画像が見つかりません: {path_text}]", styles["small"])]
    image = Image(str(path))
    max_width = CONTENT_WIDTH * 0.82
    max_height = 112 * mm
    scale = min(max_width / image.imageWidth, max_height / image.imageHeight)
    image.drawWidth = image.imageWidth * scale
    image.drawHeight = image.imageHeight * scale
    image.hAlign = "CENTER"
    return [image, paragraph(alt, styles["caption"])]


def parse_markdown(
    path: Path,
    styles: dict[str, ParagraphStyle],
    title_override: str,
) -> list:
    lines = path.read_text(encoding="utf-8").splitlines()
    story: list = []
    paragraph_buffer: list[str] = []
    diagram_index = 0
    first_h1 = True
    index = 0

    def flush_paragraph() -> None:
        if paragraph_buffer:
            text = " ".join(part.strip() for part in paragraph_buffer)
            story.append(paragraph(text, styles["body"]))
            paragraph_buffer.clear()

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            language = stripped[3:].strip()
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(normalize_text(lines[index]))
                index += 1
            if language == "mermaid":
                story.append(KeepTogether([Spacer(1, 3 * mm), diagram_flow(diagram_index), Spacer(1, 4 * mm)]))
                diagram_index += 1
            else:
                wrapped_code: list[str] = []
                for code_line in code_lines:
                    wrapped_code.extend(
                        textwrap.wrap(
                            code_line,
                            width=96,
                            subsequent_indent="  ",
                            break_long_words=False,
                            break_on_hyphens=False,
                        )
                        or [""]
                    )
                story.append(XPreformatted("\n".join(wrapped_code), styles["code"]))
            index += 1
            continue

        image_match = re.fullmatch(r"!\[([^]]*)\]\(([^)]+)\)", stripped)
        if image_match:
            flush_paragraph()
            story.extend(image_flow(image_match.group(2), image_match.group(1), styles))
            index += 1
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph()
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            parsed_rows: list[list[str]] = []
            for table_line in table_lines:
                values = [cell.strip() for cell in table_line.strip("|").split("|")]
                if all(re.fullmatch(r":?-{3,}:?", value) for value in values):
                    continue
                parsed_rows.append(values)
            if parsed_rows:
                story.append(markdown_table(parsed_rows, styles))
                story.append(Spacer(1, 3 * mm))
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            quote_lines: list[str] = []
            while index < len(lines) and (lines[index].strip().startswith(">") or not lines[index].strip()):
                current = lines[index].strip()
                if current.startswith(">"):
                    quote_lines.append(current[1:].strip())
                index += 1
            story.append(paragraph("<br/>".join(quote_lines), styles["quote"]))
            continue

        heading_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading_match:
            flush_paragraph()
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            if title_override.startswith("第1部") and text == "関連ファイル":
                break
            if level == 1 and first_h1:
                text = title_override
                first_h1 = False
            story.append(paragraph(text, styles[f"h{level}"]))
            index += 1
            continue

        list_match = re.match(r"^[-*]\s+(.+)$", stripped)
        numbered_match = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if list_match or numbered_match:
            flush_paragraph()
            if list_match:
                marker, text = "•", list_match.group(1)
            else:
                marker, text = f"{numbered_match.group(1)}.", numbered_match.group(2)
            story.append(Paragraph(f"{marker} {inline_markup(text)}", styles["bullet"]))
            index += 1
            continue

        if stripped == "---":
            flush_paragraph()
            story.append(Spacer(1, 2 * mm))
            index += 1
            continue

        if not stripped:
            flush_paragraph()
        else:
            paragraph_buffer.append(stripped)
        index += 1

    flush_paragraph()
    return story


def build_pdf() -> Path:
    register_fonts()
    styles = build_styles()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    story: list = []
    story.extend(cover_story(styles))
    story.extend(toc_story(styles))
    story.extend(parse_markdown(GUIDE, styles, "第1部 ML初心者向けガイド"))
    story.append(PageBreak())
    story.extend(parse_markdown(REPORT, styles, "第2部 提出用MLレポート"))

    document = MLDocTemplate(str(OUTPUT), styles)
    document.multiBuild(story)
    return OUTPUT


if __name__ == "__main__":
    print(build_pdf())
