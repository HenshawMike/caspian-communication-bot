"""Monochrome visual design formatting engine for Project Caspian documents."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from agent.logging_config import logger


# Section 7.2 Strict Monochrome Colour Palette
MONOCHROME_THEME = {
    "name": "Project Caspian Monochrome",
    "background_color": "#FFFFFF",
    "primary_text": "#111111",
    "secondary_text": "#666666",
    "muted_text": "#888888",
    "border_color": "#D9D9D9",
    "surface_color": "#F4F4F4",
    "dark_surface": "#181818",
    "text_on_dark": "#FFFFFF",
    "divider_thickness": 0.5,
    "margins_pt": {
        "top": 54,     # 0.75 in
        "bottom": 54,  # 0.75 in
        "left": 54,    # 0.75 in
        "right": 54,   # 0.75 in
    },
    "typography": {
        "title": {"font": "Helvetica-Bold", "size": 22, "color": "#111111", "leading": 26, "space_after": 6},
        "subtitle": {"font": "Helvetica", "size": 11, "color": "#666666", "leading": 15, "space_after": 14},
        "meta": {"font": "Helvetica", "size": 8.5, "color": "#888888", "leading": 12, "space_after": 12},
        "h1": {"font": "Helvetica-Bold", "size": 13.5, "color": "#111111", "leading": 17, "space_before": 12, "space_after": 6},
        "h2": {"font": "Helvetica-Bold", "size": 10.5, "color": "#666666", "leading": 14, "space_before": 8, "space_after": 4},
        "body": {"font": "Helvetica", "size": 9.5, "color": "#111111", "leading": 14, "space_after": 8},
        "bullet": {"font": "Helvetica", "size": 9.0, "color": "#111111", "leading": 13, "space_after": 3, "indent": 12},
        "callout": {"font": "Helvetica", "size": 9.0, "color": "#111111", "leading": 13, "bg": "#F4F4F4", "border": "#D9D9D9"},
        "table_header": {"font": "Helvetica-Bold", "size": 9.0, "color": "#111111", "bg": "#F4F4F4"},
        "table_cell": {"font": "Helvetica", "size": 8.5, "color": "#111111", "bg": "#FFFFFF"},
        "footer": {"font": "Helvetica", "size": 8.0, "color": "#888888"},
    },
}


class FormatDocumentInput(BaseModel):
    """Input parameters for format_document."""
    document_structure: Dict[str, Any] = Field(description="Structured document data from create_document.")
    include_dividers: bool = Field(default=True, description="Whether to place light grey dividers between sections.")
    show_header_footer: bool = Field(default=True, description="Whether to include monochrome headers and footers.")


class FormatDocumentOutput(BaseModel):
    """Output schema for format_document."""
    success: bool
    document_id: str
    theme_name: str
    palette: Dict[str, Any]
    formatted_elements_count: int
    formatted_document: Dict[str, Any]
    message: str


@register_tool(
    name="format_document",
    description="Applies the strict Section 7 monochrome visual design system (black, white, grey) to a structured document model, without modifying any underlying content.",
    permission=PermissionScope.CONTENT_GENERATE,
    args_model=FormatDocumentInput,
    output_model=FormatDocumentOutput,
)
def format_document(
    document_structure: Dict[str, Any],
    include_dividers: bool = True,
    show_header_footer: bool = True,
) -> Dict[str, Any]:
    """Apply the monochrome visual formatting specifications to structured content."""
    doc_id = document_structure.get("document_id", "DOC-UNKNOWN")
    title = document_structure.get("title", "Untitled Document")
    subtitle = document_structure.get("subtitle")
    sections = document_structure.get("sections", [])
    metadata = document_structure.get("metadata", {})
    sources = document_structure.get("sources", [])

    # Format into sequential display elements preserving raw content
    elements: List[Dict[str, Any]] = []

    # 1. Document Title Block
    elements.append({
        "type": "title",
        "content": title,
        "style": MONOCHROME_THEME["typography"]["title"],
    })

    if subtitle:
        elements.append({
            "type": "subtitle",
            "content": subtitle,
            "style": MONOCHROME_THEME["typography"]["subtitle"],
        })

    # Metadata row
    meta_parts = []
    if "date" in metadata or "created_at" in metadata:
        meta_parts.append(f"Date: {metadata.get('date') or metadata.get('created_at')[:10]}")
    if "classification" in metadata:
        meta_parts.append(f"Classification: {metadata.get('classification')}")
    if "author" in metadata:
        meta_parts.append(f"Author: {metadata.get('author')}")
    if "document_id" in metadata:
        meta_parts.append(f"ID: {metadata.get('document_id')}")

    if meta_parts:
        elements.append({
            "type": "metadata",
            "content": "  •  ".join(meta_parts),
            "style": MONOCHROME_THEME["typography"]["meta"],
        })

    # Top divider
    if include_dividers:
        elements.append({
            "type": "divider",
            "color": MONOCHROME_THEME["border_color"],
            "thickness": MONOCHROME_THEME["divider_thickness"],
        })

    # 2. Iterate through sections
    for sec_idx, sec in enumerate(sections):
        # Section Heading
        heading = sec.get("heading")
        if heading:
            elements.append({
                "type": "heading_1",
                "content": heading,
                "style": MONOCHROME_THEME["typography"]["h1"],
            })

        # Section Subheading
        subheading = sec.get("subheading")
        if subheading:
            elements.append({
                "type": "heading_2",
                "content": subheading,
                "style": MONOCHROME_THEME["typography"]["h2"],
            })

        # Paragraphs
        for p in sec.get("paragraphs", []):
            if p:
                elements.append({
                    "type": "paragraph",
                    "content": p,
                    "style": MONOCHROME_THEME["typography"]["body"],
                })

        # Bullet Points
        bullets = sec.get("bullet_points", [])
        if bullets:
            elements.append({
                "type": "bullets",
                "items": bullets,
                "style": MONOCHROME_THEME["typography"]["bullet"],
            })

        # Callouts
        for c in sec.get("callouts", []):
            if c:
                elements.append({
                    "type": "callout",
                    "content": c,
                    "style": MONOCHROME_THEME["typography"]["callout"],
                })

        # Table
        tbl = sec.get("table")
        if tbl and tbl.get("headers") and tbl.get("rows"):
            elements.append({
                "type": "table",
                "headers": tbl.get("headers"),
                "rows": tbl.get("rows"),
                "header_style": MONOCHROME_THEME["typography"]["table_header"],
                "cell_style": MONOCHROME_THEME["typography"]["table_cell"],
                "border_color": MONOCHROME_THEME["border_color"],
            })

        # Section divider (except after the final section if sources follow)
        if include_dividers and sec_idx < len(sections) - 1:
            elements.append({
                "type": "divider",
                "color": MONOCHROME_THEME["border_color"],
                "thickness": MONOCHROME_THEME["divider_thickness"],
            })

    # 3. Sources Section if provided
    if sources:
        if include_dividers:
            elements.append({
                "type": "divider",
                "color": MONOCHROME_THEME["border_color"],
                "thickness": MONOCHROME_THEME["divider_thickness"],
            })
        elements.append({
            "type": "heading_1",
            "content": "References & Sources",
            "style": MONOCHROME_THEME["typography"]["h1"],
        })
        elements.append({
            "type": "bullets",
            "items": sources,
            "style": MONOCHROME_THEME["typography"]["bullet"],
        })

    formatted_document = {
        "document_id": doc_id,
        "title": title,
        "theme": MONOCHROME_THEME,
        "elements": elements,
        "show_header_footer": show_header_footer,
        "raw_structure": document_structure,
    }

    logger.info(f"Formatted document '{doc_id}' into {len(elements)} styled monochrome elements.")

    return {
        "success": True,
        "document_id": doc_id,
        "theme_name": MONOCHROME_THEME["name"],
        "palette": {
            "background": MONOCHROME_THEME["background_color"],
            "primary": MONOCHROME_THEME["primary_text"],
            "secondary": MONOCHROME_THEME["secondary_text"],
            "borders": MONOCHROME_THEME["border_color"],
            "surfaces": MONOCHROME_THEME["surface_color"],
        },
        "formatted_elements_count": len(elements),
        "formatted_document": formatted_document,
        "message": f"Successfully applied monochrome design system to document '{doc_id}'.",
    }
