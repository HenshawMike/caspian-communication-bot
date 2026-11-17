"""Monochrome PDF export tool using ReportLab."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from xml.sax.saxutils import escape as xml_escape
from pydantic import BaseModel, Field

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

from agent.config import settings
from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from agent.logging_config import logger


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and stamp total page count in monochrome footer."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(HexColor("#888888"))

        # Running header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 11 * 72 - 36, "PROJECT CASPIAN  •  RESEARCH COMMUNICATIONS")
            self.setStrokeColor(HexColor("#D9D9D9"))
            self.setLineWidth(0.5)
            self.line(54, 11 * 72 - 42, 8.5 * 72 - 54, 11 * 72 - 42)

        # Running footer
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * 72 - 54, 36, page_str)
        self.drawString(54, 36, "CONFIDENTIAL & VERIFIED  •  PROJECT CASPIAN")

        # Footer divider line
        self.setStrokeColor(HexColor("#D9D9D9"))
        self.setLineWidth(0.5)
        self.line(54, 46, 8.5 * 72 - 54, 46)

        self.restoreState()


class ExportPdfInput(BaseModel):
    """Input parameters for export_pdf."""
    formatted_document: Dict[str, Any] = Field(description="Formatted document structure from format_document.")
    output_filename: Optional[str] = Field(default=None, description="Optional custom filename ending in .pdf.")


class ExportPdfOutput(BaseModel):
    """Output schema for export_pdf."""
    success: bool
    document_id: str
    file_path: str
    file_size_bytes: int
    message: str


@register_tool(
    name="export_pdf",
    description="Renders and exports a formatted monochrome document model to a PDF file adhering strictly to black, white, and grey design rules.",
    permission=PermissionScope.CONTENT_GENERATE,
    args_model=ExportPdfInput,
    output_model=ExportPdfOutput,
)
def export_pdf(
    formatted_document: Dict[str, Any],
    output_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate professional monochrome PDF document."""
    doc_id = formatted_document.get("document_id", "DOC-UNKNOWN")
    title = formatted_document.get("title", "Project Caspian Document")
    elements_data = formatted_document.get("elements", [])

    # Setup output destination
    docs_dir = settings.get_documents_dir()
    if output_filename:
        clean_name = output_filename if output_filename.endswith(".pdf") else f"{output_filename}.pdf"
    else:
        clean_name = f"{doc_id.lower().replace('-', '_')}.pdf"

    pdf_path = docs_dir / clean_name

    # Document geometry: Letter, 0.75 in (54 pt) margins
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
        title=title,
        author="Project Caspian",
    )

    # Reusable monochrome styles
    style_title = ParagraphStyle(
        "DocTitle",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=HexColor("#111111"),
        spaceAfter=4,
    )
    style_subtitle = ParagraphStyle(
        "DocSubtitle",
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=HexColor("#666666"),
        spaceAfter=10,
    )
    style_meta = ParagraphStyle(
        "DocMeta",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=HexColor("#888888"),
        spaceAfter=10,
    )
    style_h1 = ParagraphStyle(
        "DocH1",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=HexColor("#111111"),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    )
    style_h2 = ParagraphStyle(
        "DocH2",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=HexColor("#666666"),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )
    style_body = ParagraphStyle(
        "DocBody",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=HexColor("#111111"),
        spaceAfter=6,
    )
    style_bullet = ParagraphStyle(
        "DocBullet",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=HexColor("#111111"),
        leftIndent=14,
        spaceAfter=3,
    )
    style_callout = ParagraphStyle(
        "DocCallout",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=HexColor("#111111"),
    )
    style_tbl_hdr = ParagraphStyle(
        "TblHdr",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=HexColor("#111111"),
    )
    style_tbl_cell = ParagraphStyle(
        "TblCell",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=HexColor("#111111"),
    )

    story = []

    for elem in elements_data:
        e_type = elem.get("type")

        if e_type == "title":
            story.append(Paragraph(xml_escape(elem.get("content", "")), style_title))

        elif e_type == "subtitle":
            story.append(Paragraph(xml_escape(elem.get("content", "")), style_subtitle))

        elif e_type == "metadata":
            story.append(Paragraph(xml_escape(elem.get("content", "")), style_meta))

        elif e_type == "divider":
            story.append(Spacer(1, 4))
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=HexColor("#D9D9D9"),
                    spaceBefore=2,
                    spaceAfter=8,
                )
            )

        elif e_type == "heading_1":
            story.append(Paragraph(xml_escape(elem.get("content", "")), style_h1))

        elif e_type == "heading_2":
            story.append(Paragraph(xml_escape(elem.get("content", "")), style_h2))

        elif e_type == "paragraph":
            story.append(Paragraph(xml_escape(elem.get("content", "")), style_body))

        elif e_type == "bullets":
            for b in elem.get("items", []):
                bullet_text = f"• {xml_escape(b)}"
                story.append(Paragraph(bullet_text, style_bullet))
            story.append(Spacer(1, 4))

        elif e_type == "callout":
            content_p = Paragraph(f"<b>NOTE:</b> {xml_escape(elem.get('content', ''))}", style_callout)
            callout_tbl = Table([[content_p]], colWidths=[504])
            callout_tbl.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F4F4F4")),
                    ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#D9D9D9")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ])
            )
            story.append(Spacer(1, 4))
            story.append(callout_tbl)
            story.append(Spacer(1, 6))

        elif e_type == "table":
            headers = elem.get("headers", [])
            rows = elem.get("rows", [])
            if headers:
                table_data = []
                hdr_row = [Paragraph(f"<b>{xml_escape(str(h))}</b>", style_tbl_hdr) for h in headers]
                table_data.append(hdr_row)
                for r in rows:
                    row_cells = [Paragraph(xml_escape(str(c)), style_tbl_cell) for c in r]
                    table_data.append(row_cells)

                col_w = 504.0 / max(len(headers), 1)
                t = Table(table_data, colWidths=[col_w] * len(headers))
                t.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#F4F4F4")),
                        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#D9D9D9")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#D9D9D9")),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ])
                )
                story.append(Spacer(1, 4))
                story.append(t)
                story.append(Spacer(1, 6))

    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)

    file_size = pdf_path.stat().st_size
    logger.info(f"Successfully generated PDF '{pdf_path}' ({file_size} bytes).")

    return {
        "success": True,
        "document_id": doc_id,
        "file_path": str(pdf_path),
        "file_size_bytes": file_size,
        "message": f"Successfully exported monochrome PDF to {pdf_path.name} ({file_size} bytes).",
    }
