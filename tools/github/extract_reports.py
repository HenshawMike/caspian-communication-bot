"""Research document extraction tool (read-only)."""

import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.config import settings
from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from agent.logging_config import logger
from tools.github.scan_repository import _validate_repo_path


class ExtractReportsInput(BaseModel):
    """Input parameters for extract_reports."""
    file_paths: List[str] = Field(description="List of file paths relative to repository root to extract.")
    repository_path: Optional[str] = Field(default=None, description="Path to git repository.")


class ResearchReport(BaseModel):
    """Structured representation of an extracted research report."""
    file_path: str
    title: str
    experiment_id: Optional[str] = None
    hypothesis: Optional[str] = None
    findings: str
    limitations: str
    disclosure_status: str = "REVIEW_REQUIRED"
    raw_content: str


class ExtractReportsOutput(BaseModel):
    """Output schema for extract_reports."""
    success: bool
    reports_found: int
    reports: List[ResearchReport] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


def _parse_report_content(raw_text: str, file_path: str) -> ResearchReport:
    """Parse research document fields and disclosure metadata."""
    # 1. Extract title
    title = Path(file_path).stem.replace("_", " ").title()
    title_match = re.search(r"^#\s+(.+)$", raw_text, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()

    # 2. Extract disclosure status
    disclosure = "REVIEW_REQUIRED"
    disc_match = re.search(
        r"(?:<!--\s*DISCLOSURE:\s*(PUBLIC|INTERNAL|SENSITIVE|REVIEW_REQUIRED)\s*-->|"
        r"disclosure\s*:\s*(PUBLIC|INTERNAL|SENSITIVE|REVIEW_REQUIRED))",
        raw_text,
        re.IGNORECASE,
    )
    if disc_match:
        found_tag = disc_match.group(1) or disc_match.group(2)
        if found_tag:
            disclosure = found_tag.upper().strip()

    # 3. Extract experiment ID
    exp_id = None
    exp_match = re.search(r"(?:experiment[_\s-]?id|exp[_\s-]?id)\s*[:=]\s*([a-zA-Z0-9_\-\.]+)", raw_text, re.IGNORECASE)
    if exp_match:
        exp_id = exp_match.group(1).strip()

    # 4. Extract Hypothesis, Findings, Limitations
    def extract_section(section_name: str) -> str:
        pattern = re.compile(
            rf"^##\s+(?:.*?\b)?{section_name}(?:\b.*?)?$(.*?)(?=^##|\Z)",
            re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )
        m = pattern.search(raw_text)
        return m.group(1).strip() if m else ""

    hypothesis = extract_section("hypothesis") or None
    findings = extract_section("findings") or extract_section("results") or extract_section("observations")
    limitations = extract_section("limitations") or extract_section("unresolved") or extract_section("open questions")

    # If no explicit sections found, use summary/body
    if not findings:
        findings = raw_text[:500].strip()

    return ResearchReport(
        file_path=file_path,
        title=title,
        experiment_id=exp_id,
        hypothesis=hypothesis,
        findings=findings,
        limitations=limitations,
        disclosure_status=disclosure,
        raw_content=raw_text,
    )


def _validate_reports_dir(repo_path: Optional[str]) -> Path:
    """Validate directory for report extraction."""
    target_path = Path(repo_path) if repo_path else (settings.caspian_repo_path or settings.base_dir)
    target_path = target_path.resolve()

    if not target_path.exists() or not target_path.is_dir():
        raise ValueError(f"Reports directory does not exist or is not a directory: {target_path}")

    return target_path


@register_tool(
    name="extract_reports",
    description="Extract research findings, limitations, and disclosure classification from research files (read-only).",
    permission=PermissionScope.REPOSITORY_READ,
    args_model=ExtractReportsInput,
    output_model=ExtractReportsOutput,
)
def extract_reports(
    file_paths: List[str],
    repository_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Extract and parse research documents from repository."""
    try:
        repo_dir = _validate_reports_dir(repository_path)
    except Exception as e:
        return {
            "success": False,
            "reports_found": 0,
            "reports": [],
            "errors": [str(e)],
        }

    extracted: List[ResearchReport] = []
    errors: List[str] = []

    for rel_path in file_paths:
        clean_rel = rel_path.strip().lstrip("/")
        full_path = (repo_dir / clean_rel).resolve()

        # Security check: ensure path is within repository directory
        try:
            full_path.relative_to(repo_dir)
        except ValueError:
            errors.append(f"Security error: path '{clean_rel}' is outside the repository boundary.")
            continue

        if not full_path.is_file():
            # Skip non-files or removed files
            continue

        # Process markdown, text, or json files
        if full_path.suffix.lower() not in (".md", ".txt", ".json", ".tex"):
            continue

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            report = _parse_report_content(content, clean_rel)
            extracted.append(report)
        except Exception as file_err:
            logger.warning(f"Failed to parse report at {clean_rel}: {file_err}")
            errors.append(f"Failed reading {clean_rel}: {str(file_err)}")

    return {
        "success": True,
        "reports_found": len(extracted),
        "reports": [r.model_dump() for r in extracted],
        "errors": errors,
    }
