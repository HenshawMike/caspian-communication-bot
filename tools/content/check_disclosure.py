"""Disclosure verification and policy compliance tool."""

import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from agent.logging_config import redact_secrets


# Patterns indicating internal or non-public details
INTERNAL_INDICATORS = [
    re.compile(r"\bconfidential\b", re.IGNORECASE),
    re.compile(r"\binternal\s+only\b", re.IGNORECASE),
    re.compile(r"\bdo\s+not\s+disclose\b", re.IGNORECASE),
    re.compile(r"\bproprietary\b", re.IGNORECASE),
    re.compile(r"\bapi[_-]?key\b", re.IGNORECASE),
    re.compile(r"\bsecret\b", re.IGNORECASE),
    re.compile(r"\bpassword\b", re.IGNORECASE),
    re.compile(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),  # Private IP
    re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b"),     # Private IP
    re.compile(r"(\.internal|\.corp|\.local)\b", re.IGNORECASE),
]


class CheckDisclosureInput(BaseModel):
    """Input parameters for check_disclosure."""
    content: str = Field(description="Content text or research summary to verify for public sharing.")
    declared_status: Optional[str] = Field(
        default=None,
        description="Declared disclosure status from source report (PUBLIC, INTERNAL, SENSITIVE, REVIEW_REQUIRED).",
    )


class CheckDisclosureOutput(BaseModel):
    """Output schema for check_disclosure."""
    success: bool
    status: str
    is_public_approved: bool
    reasons: List[str] = Field(default_factory=list)
    sanitized_content: str


@register_tool(
    name="check_disclosure",
    description="Evaluate research content against Project Caspian public disclosure rules. Prevents leak of internal/sensitive info.",
    permission=PermissionScope.CONTENT_GENERATE,
    args_model=CheckDisclosureInput,
    output_model=CheckDisclosureOutput,
)
def check_disclosure(
    content: str,
    declared_status: Optional[str] = None,
) -> Dict[str, Any]:
    """Verify disclosure classification of content."""
    reasons: List[str] = []
    
    # 1. Check declared status
    norm_status = declared_status.upper().strip() if declared_status else None
    
    if not norm_status:
        norm_status = "REVIEW_REQUIRED"
        reasons.append("No explicit disclosure tag found in document; defaulted to REVIEW_REQUIRED.")
    elif norm_status in ("INTERNAL", "SENSITIVE"):
        reasons.append(f"Document is explicitly marked as {norm_status}.")
    elif norm_status not in ("PUBLIC", "INTERNAL", "SENSITIVE", "REVIEW_REQUIRED"):
        norm_status = "REVIEW_REQUIRED"
        reasons.append(f"Unrecognized disclosure status '{declared_status}'; defaulted to REVIEW_REQUIRED.")

    # 2. Check for internal indicators in content
    for pattern in INTERNAL_INDICATORS:
        if pattern.search(content):
            reasons.append(f"Content contains restricted pattern matching '{pattern.pattern}'.")
            if norm_status == "PUBLIC":
                norm_status = "REVIEW_REQUIRED"

    # 3. Sanitize content
    sanitized = redact_secrets(content)

    # 4. Final approval flag
    is_approved = (norm_status == "PUBLIC" and len(reasons) == 0)

    return {
        "success": True,
        "status": norm_status,
        "is_public_approved": is_approved,
        "reasons": reasons,
        "sanitized_content": sanitized,
    }
