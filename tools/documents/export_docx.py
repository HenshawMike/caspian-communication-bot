"""Monochrome DOCX export tool using python-docx."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

from agent.config import settings
from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from agent.logging_config import logger


# Monochrome RGB constants
COLOR_PRIMARY = RGBColor(0x11, 0x11, 0x11)
COLOR_SECONDARY = RGBColor(0x66, 0x66, 0x66)
COLOR_MUTED = RGBColor(0x88, 0x88, 0x88)
HEX_SURFACE = "F4F4F4"
HEX_BORDER = "D9D9D9"


class ExportDocxInput(BaseModel):
    """Input parameters for export_docx."""
    formatted_document: Dict[str, Any] = Field(description="Formatted document structure from format_document.")
    output_filename: Optional[str] = Field(default=None, description="Optional custom filename ending in .docx.")


class ExportDocxOutput(BaseModel):
    """Output schema for export_docx."""
    success: bool
    document_id: str
    file_path: str
    file_size_bytes: int
    message: str


def _set_cell_background(cell, hex_color: str):
    """Set background shading color on a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)


def _set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set internal cell padding (in dxa: 20 dxa = 1 pt)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def _set_table_borders(table, color="D9D9D9", sz="4", val="single"):
    """Apply clean light grey borders to a docx table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:right w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


@register_tool(
    name="export_docx",
    description="Renders and exports a formatted monochrome document model to a DOCX (Microsoft Word) file adhering strictly to black, white, and grey design rules.",
    permission=PermissionScope.CONTENT_GENERATE,
    args_model=ExportDocxInput,
    output_model=ExportDocxOutput,
)
def export_docx(
    formatted_document: Dict[str, Any],
    output_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate professional monochrome DOCX document."""
    doc_id = formatted_document.get("document_id", "DOC-UNKNOWN")
    title = formatted_document.get("title", "Project Caspian Document")
    elements_data = formatted_document.get("elements", [])

    # Setup output destination
    docs_dir = settings.get_documents_dir()
    if output_filename:
        clean_name = output_filename if output_filename.endswith(".docx") else f"{output_filename}.docx"
    else:
        clean_name = f"{doc_id.lower().replace('-', '_')}.docx"

    docx_path = docs_dir / clean_name

    doc = docx.Document()

    # Configure 0.75 inch (54 pt) margins on all sections
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

        # Running monochrome header & footer
        header = section.header
        header_p = header.paragraphs[0]
        header_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        h_run = header_p.add_run("PROJECT CASPIAN  •  RESEARCH COMMUNICATIONS")
        h_run.font.name = "Arial"
        h_run.font.size = Pt(8)
        h_run.font.color.rgb = COLOR_MUTED

        footer = section.footer
        footer_p = footer.paragraphs[0]
        footer_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        f_run = footer_p.add_run("CONFIDENTIAL & VERIFIED  •  PROJECT CASPIAN")
        f_run.font.name = "Arial"
        f_run.font.size = Pt(8)
        f_run.font.color.rgb = COLOR_MUTED

    # Iterate through elements
    for elem in elements_data:
        e_type = elem.get("type")

        if e_type == "title":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(4)
            run = p.add_run(elem.get("content", ""))
            run.font.name = "Arial"
            run.font.size = Pt(20)
            run.font.bold = True
            run.font.color.rgb = COLOR_PRIMARY

        elif e_type == "subtitle":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(8)
            run = p.add_run(elem.get("content", ""))
            run.font.name = "Arial"
            run.font.size = Pt(11)
            run.font.color.rgb = COLOR_SECONDARY

        elif e_type == "metadata":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(8)
            run = p.add_run(elem.get("content", ""))
            run.font.name = "Arial"
            run.font.size = Pt(8.5)
            run.font.color.rgb = COLOR_MUTED

        elif e_type == "divider":
            # Add a thin bottom border to paragraph
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(8)
            pPr = p._p.get_or_add_pPr()
            pBdr = parse_xml(
                f'<w:pBdr {nsdecls("w")}>'
                f'<w:bottom w:val="single" w:sz="4" w:space="1" w:color="{HEX_BORDER}"/>'
                f'</w:pBdr>'
            )
            pPr.append(pBdr)

        elif e_type == "heading_1":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(elem.get("content", ""))
            run.font.name = "Arial"
            run.font.size = Pt(13)
            run.font.bold = True
            run.font.color.rgb = COLOR_PRIMARY

        elif e_type == "heading_2":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(elem.get("content", ""))
            run.font.name = "Arial"
            run.font.size = Pt(10.5)
            run.font.bold = True
            run.font.color.rgb = COLOR_SECONDARY

        elif e_type == "paragraph":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(6)
            run = p.add_run(elem.get("content", ""))
            run.font.name = "Arial"
            run.font.size = Pt(9.5)
            run.font.color.rgb = COLOR_PRIMARY

        elif e_type == "bullets":
            for b in elem.get("items", []):
                p = doc.add_paragraph(style="List Bullet")
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(2)
                run = p.add_run(b)
                run.font.name = "Arial"
                run.font.size = Pt(9.0)
                run.font.color.rgb = COLOR_PRIMARY

        elif e_type == "callout":
            # 1x1 table callout box with #F4F4F4 background and #D9D9D9 border
            tbl = doc.add_table(rows=1, cols=1)
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            _set_table_borders(tbl, color=HEX_BORDER, sz="4")
            cell = tbl.cell(0, 0)
            _set_cell_background(cell, HEX_SURFACE)
            _set_cell_margins(cell, top=120, bottom=120, left=180, right=180)
            cp = cell.paragraphs[0]
            cp.paragraph_format.space_before = Pt(0)
            cp.paragraph_format.space_after = Pt(0)
            bold_run = cp.add_run("NOTE: ")
            bold_run.font.name = "Arial"
            bold_run.font.bold = True
            bold_run.font.size = Pt(9.0)
            bold_run.font.color.rgb = COLOR_PRIMARY
            run = cp.add_run(elem.get("content", ""))
            run.font.name = "Arial"
            run.font.size = Pt(9.0)
            run.font.color.rgb = COLOR_PRIMARY

            spacer = doc.add_paragraph()
            spacer.paragraph_format.space_before = Pt(0)
            spacer.paragraph_format.space_after = Pt(4)

        elif e_type == "table":
            headers = elem.get("headers", [])
            rows = elem.get("rows", [])
            if headers:
                tbl = doc.add_table(rows=len(rows) + 1, cols=len(headers))
                tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                _set_table_borders(tbl, color=HEX_BORDER, sz="4")

                # Header row
                hdr_cells = tbl.rows[0].cells
                for i, h in enumerate(headers):
                    _set_cell_background(hdr_cells[i], HEX_SURFACE)
                    _set_cell_margins(hdr_cells[i], top=80, bottom=80, left=120, right=120)
                    hp = hdr_cells[i].paragraphs[0]
                    hp.paragraph_format.space_before = Pt(0)
                    hp.paragraph_format.space_after = Pt(0)
                    hr = hp.add_run(str(h))
                    hr.font.name = "Arial"
                    hr.font.bold = True
                    hr.font.size = Pt(8.5)
                    hr.font.color.rgb = COLOR_PRIMARY

                # Data rows
                for r_idx, r in enumerate(rows):
                    row_cells = tbl.rows[r_idx + 1].cells
                    for c_idx, val in enumerate(r):
                        if c_idx < len(row_cells):
                            _set_cell_margins(row_cells[c_idx], top=60, bottom=60, left=120, right=120)
                            dp = row_cells[c_idx].paragraphs[0]
                            dp.paragraph_format.space_before = Pt(0)
                            dp.paragraph_format.space_after = Pt(0)
                            dr = dp.add_run(str(val))
                            dr.font.name = "Arial"
                            dr.font.size = Pt(8.0)
                            dr.font.color.rgb = COLOR_PRIMARY

                spacer = doc.add_paragraph()
                spacer.paragraph_format.space_before = Pt(0)
                spacer.paragraph_format.space_after = Pt(4)

    # Save DOCX
    doc.save(str(docx_path))
    file_size = docx_path.stat().st_size
    logger.info(f"Successfully generated DOCX '{docx_path}' ({file_size} bytes).")

    return {
        "success": True,
        "document_id": doc_id,
        "file_path": str(docx_path),
        "file_size_bytes": file_size,
        "message": f"Successfully exported monochrome DOCX to {docx_path.name} ({file_size} bytes).",
    }
