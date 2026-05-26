"""Render export rows as a printable A4-landscape PDF using reportlab."""

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


_PAGE_SIZE = landscape(A4)
_LEFT_MARGIN = 1.5 * cm
_RIGHT_MARGIN = 1.5 * cm
_TOP_MARGIN = 1.5 * cm
_BOTTOM_MARGIN = 1.5 * cm
_USABLE_WIDTH = _PAGE_SIZE[0] - _LEFT_MARGIN - _RIGHT_MARGIN

_BASE_COL_COUNT = 4  # Vorname, Nachname, Ticket-Option, Gast-Name
_MIN_COL_WIDTH = 2.0 * cm

_FONT_SIZE_STEPS = (9, 8, 7)
_TRUNCATE_BELOW_PT = 7
_TRUNCATE_LIMIT = 20


def _pick_font_size_and_truncate(num_columns: int) -> tuple[int, bool]:
    for size in _FONT_SIZE_STEPS:
        approx_width_per_col = _USABLE_WIDTH / num_columns
        if approx_width_per_col >= _MIN_COL_WIDTH * (size / 9):
            return size, False
    return _TRUNCATE_BELOW_PT, True


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def _format_event_starts_at(event_meta: dict[str, Any] | None) -> str:
    if not event_meta:
        return ""
    starts_at = event_meta.get("starts_at")
    if not starts_at:
        return ""
    if isinstance(starts_at, str):
        try:
            dt = datetime.fromisoformat(starts_at.replace("Z", "+00:00"))
        except ValueError:
            return starts_at
    elif isinstance(starts_at, datetime):
        dt = starts_at
    else:
        return str(starts_at)
    return dt.strftime("%d.%m.%Y %H:%M")


def render_pdf(
    headers: list[str],
    rows: list[list[str]],
    event_meta: dict[str, Any] | None = None,
) -> bytes:
    """Render headers + rows to a PDF (A4 landscape)."""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=_PAGE_SIZE,
        leftMargin=_LEFT_MARGIN,
        rightMargin=_RIGHT_MARGIN,
        topMargin=_TOP_MARGIN,
        bottomMargin=_BOTTOM_MARGIN,
        title="Gästeliste",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#444444"),
        spaceAfter=2,
    )

    event_name = (event_meta or {}).get("title") or (event_meta or {}).get("name") or "Event"
    starts_at_str = _format_event_starts_at(event_meta)
    generated_at = datetime.now().strftime("%d.%m.%Y %H:%M")
    ticket_count = len(rows)

    story: list[Any] = [
        Paragraph(f"Gästeliste – {event_name}", title_style),
    ]
    if starts_at_str:
        story.append(Paragraph(f"Event-Datum: {starts_at_str}", meta_style))
    story.append(Paragraph(f"Akzeptierte Tickets: {ticket_count}", meta_style))
    story.append(Paragraph(f"Erstellt am: {generated_at}", meta_style))
    story.append(Spacer(1, 0.5 * cm))

    num_columns = len(headers)
    font_size, truncate = _pick_font_size_and_truncate(num_columns)
    header_size = font_size + 1

    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["Normal"],
        fontSize=font_size,
        leading=font_size + 2,
    )
    header_cell_style = ParagraphStyle(
        "HeaderCell",
        parent=styles["Normal"],
        fontSize=header_size,
        leading=header_size + 2,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )

    def _cell(text: str, style: ParagraphStyle) -> Paragraph:
        if truncate:
            text = _truncate(text, _TRUNCATE_LIMIT)
        safe = (
            text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        return Paragraph(safe or "&nbsp;", style)

    table_data: list[list[Any]] = [
        [_cell(h, header_cell_style) for h in headers]
    ]
    for r in rows:
        table_data.append([_cell(c, cell_style) for c in r])

    col_widths = [_USABLE_WIDTH / num_columns] * num_columns
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table_style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
            ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#1F2937")),
            ("GRID", (0, 1), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
    )
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            table_style.add(
                "BACKGROUND", (0, i), (-1, i), colors.HexColor("#F5F5F5")
            )
    table.setStyle(table_style)
    story.append(table)

    def _footer(canvas: Any, doc_: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        page_num = canvas.getPageNumber()
        text = f"Seite {page_num}"
        canvas.drawRightString(
            _PAGE_SIZE[0] - _RIGHT_MARGIN, _BOTTOM_MARGIN / 2, text
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
