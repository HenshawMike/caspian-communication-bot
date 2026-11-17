"""Factual claim verification tool checking statements against ground truth sources."""

import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from agent.logging_config import logger


EXAGGERATION_PATTERNS = [
    re.compile(r"\b(flawless|perfect|completely\s+solved|infinitely\s+better|undefeated)\b", re.IGNORECASE),
    re.compile(r"\b(world['’]s\s+first\s+ever\s+flawless)\b", re.IGNORECASE),
]


class VerifyClaimsInput(BaseModel):
    """Input parameters for verify_claims."""
    claims: List[str] = Field(description="List of factual claims or generated draft statements to verify.")
    source_text: str = Field(description="Ground truth reference text, paper abstract, or report findings.")


class VerifyClaimsOutput(BaseModel):
    """Output schema for verify_claims."""
    success: bool
    is_verified: bool
    verification_status: str
    verified_claims: List[str] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    accuracy_score: float
    notes: List[str] = Field(default_factory=list)


def _extract_numbers(text: str) -> List[str]:
    """Extract metrics and numerical percentages from text."""
    return re.findall(r"\b\d+(?:\.\d+)?%?\b", text)


@register_tool(
    name="verify_claims",
    description="Verify factual statements and numerical claims in generated drafts against ground truth source texts.",
    permission=PermissionScope.CONTENT_GENERATE,
    args_model=VerifyClaimsInput,
    output_model=VerifyClaimsOutput,
)
def verify_claims(
    claims: List[str],
    source_text: str,
) -> Dict[str, Any]:
    """Verify claims against source text."""
    if not claims:
        return {
            "success": True,
            "is_verified": True,
            "verification_status": "VERIFIED",
            "verified_claims": [],
            "unsupported_claims": [],
            "accuracy_score": 1.0,
            "notes": ["No claims submitted for verification."],
        }

    clean_source = source_text.lower()
    source_numbers = set(_extract_numbers(clean_source))

    verified: List[str] = []
    unsupported: List[str] = []
    notes: List[str] = []

    for claim in claims:
        claim_clean = claim.strip()
        if not claim_clean:
            continue

        # 1. Check for exaggerated superlatives
        has_exaggeration = False
        for ex_pat in EXAGGERATION_PATTERNS:
            if ex_pat.search(claim_clean):
                unsupported.append(claim_clean)
                notes.append(f"Claim rejected due to ungrounded superlative assertion: '{claim_clean}'")
                has_exaggeration = True
                break

        if has_exaggeration:
            continue

        # 2. Check numerical / metric assertions
        claim_numbers = set(_extract_numbers(claim_clean.lower()))
        missing_numbers = claim_numbers - source_numbers
        if missing_numbers:
            unsupported.append(claim_clean)
            notes.append(
                f"Numerical claim mismatch: metrics {missing_numbers} not found in source reference."
            )
            continue

        # 3. Check keyword token overlap
        claim_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", claim_clean.lower()))
        source_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", clean_source))
        if claim_words:
            overlap = claim_words.intersection(source_words)
            overlap_ratio = len(overlap) / len(claim_words)
            if overlap_ratio >= 0.3:
                verified.append(claim_clean)
            else:
                unsupported.append(claim_clean)
                notes.append(
                    f"Low semantic grounding ({overlap_ratio:.1%}): words not adequately supported by source."
                )
        else:
            verified.append(claim_clean)

    total_valid = len(verified) + len(unsupported)
    accuracy = (len(verified) / total_valid) if total_valid > 0 else 1.0
    is_fully_verified = len(unsupported) == 0

    return {
        "success": True,
        "is_verified": is_fully_verified,
        "verification_status": "VERIFIED" if is_fully_verified else "UNSUPPORTED_CLAIMS",
        "verified_claims": verified,
        "unsupported_claims": unsupported,
        "accuracy_score": round(accuracy, 2),
        "notes": notes,
    }
