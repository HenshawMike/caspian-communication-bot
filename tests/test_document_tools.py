"""Unit tests for document generation and monochrome formatting tools."""

import os
from pathlib import Path
import pytest
from agent.permissions import PermissionContext, PermissionScope
from tools.documents.create_document import create_document
from tools.documents.format_document import format_document, MONOCHROME_THEME
from tools.documents.export_pdf import export_pdf
from tools.documents.export_docx import export_docx


@pytest.fixture
def sample_document_structure():
    """Build a standard structured document for testing."""
    sections = [
        {
            "heading": "1. Executive Summary",
            "subheading": "Key breakthrough findings",
            "paragraphs": [
                "Recent evaluations demonstrate consistent convergence on multi-step reasoning benchmarks.",
                "Tool calling precision improved significantly over baseline configurations.",
            ],
            "bullet_points": [
                "Decoupled observation-thought loop architecture.",
                "Deterministic routing for known operational triggers.",
            ],
            "callouts": [
                "All evaluations adhere to Project Caspian public disclosure boundaries."
            ],
        },
        {
            "heading": "2. Benchmark Results",
            "subheading": "Quantitative evaluation matrix",
            "paragraphs": ["Empirical comparison across multiple reasoning tasks."],
            "table": {
                "headers": ["Metric", "Baseline", "Caspian Model", "Delta"],
                "rows": [
                    ["Accuracy", "74.2%", "88.5%", "+14.3%"],
                    ["Latency", "420 ms", "290 ms", "-130 ms"],
                ],
            },
        },
    ]

    res = create_document(
        title="Project Caspian Empirical Evaluation",
        document_type="research_report",
        subtitle="Monochrome Document Generation Test Suite",
        sections=sections,
        metadata={"author": "Test Author", "classification": "PUBLIC"},
        sources=["https://arxiv.org/abs/2301.00000", "Commit SHA: abc12345"],
    )
    return res["document_structure"]


def test_create_document_structure():
    """Verify create_document builds a valid structured representation."""
    sections = [
        {
            "heading": "Introduction",
            "paragraphs": ["Testing document creation."],
            "bullet_points": ["Point A", "Point B"],
        }
    ]
    res = create_document(
        title="Test Report",
        document_type="technical_doc",
        subtitle="Subtitle text",
        sections=sections,
    )
    assert res["success"] is True
    assert res["document_id"].startswith("DOC-")
    assert res["section_count"] == 1
    assert res["document_type"] == "technical_doc"
    assert res["title"] == "Test Report"


def test_format_document_monochrome_palette(sample_document_structure):
    """Verify format_document enforces the strict Section 7 monochrome palette."""
    res = format_document(sample_document_structure, include_dividers=True)
    assert res["success"] is True
    assert res["theme_name"] == "Project Caspian Monochrome"

    palette = res["palette"]
    assert palette["background"] == "#FFFFFF"
    assert palette["primary"] == "#111111"
    assert palette["secondary"] == "#666666"
    assert palette["borders"] == "#D9D9D9"
    assert palette["surfaces"] == "#F4F4F4"

    elements = res["formatted_document"]["elements"]
    assert len(elements) > 5

    # Check that colors in typography are strictly monochrome
    for typo_key, style in MONOCHROME_THEME["typography"].items():
        if "color" in style:
            assert style["color"] in ("#111111", "#666666", "#888888", "#FFFFFF")


def test_export_pdf_generation(sample_document_structure, tmp_path, monkeypatch):
    """Verify export_pdf produces a valid, readable PDF file."""
    # Patch documents_dir to temporary test path
    from agent.config import settings
    monkeypatch.setattr(settings, "documents_dir", tmp_path)

    fmt_res = format_document(sample_document_structure)
    pdf_res = export_pdf(fmt_res["formatted_document"], output_filename="test_output.pdf")

    assert pdf_res["success"] is True
    pdf_path = Path(pdf_res["file_path"])
    assert pdf_path.exists()
    assert pdf_res["file_size_bytes"] > 0

    # Verify standard PDF magic header
    with open(pdf_path, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-"


def test_export_docx_generation(sample_document_structure, tmp_path, monkeypatch):
    """Verify export_docx produces a valid, readable DOCX file."""
    from agent.config import settings
    monkeypatch.setattr(settings, "documents_dir", tmp_path)

    fmt_res = format_document(sample_document_structure)
    docx_res = export_docx(fmt_res["formatted_document"], output_filename="test_output.docx")

    assert docx_res["success"] is True
    docx_path = Path(docx_res["file_path"])
    assert docx_path.exists()
    assert docx_res["file_size_bytes"] > 0

    # Verify standard ZIP/DOCX magic header
    with open(docx_path, "rb") as f:
        header = f.read(4)
        assert header == b"PK\x03\x04"
