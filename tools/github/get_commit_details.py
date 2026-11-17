"""Read-only commit details retrieval tool."""

import re
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.config import settings
from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from agent.logging_config import logger
from tools.github.scan_repository import _validate_repo_path


class CommitDetailsInput(BaseModel):
    """Input parameters for get_commit_details."""
    commit_hash: str = Field(description="Commit hash to inspect (SHA).", min_length=4, max_length=40)
    repository_path: Optional[str] = Field(
        default=None,
        description="Path to git repository. Defaults to configured repository.",
    )


class CommitDetailsOutput(BaseModel):
    """Output schema for get_commit_details."""
    success: bool
    commit_hash: str
    author: str
    date: str
    message: str
    changed_files: List[str] = Field(default_factory=list)
    stats: str = ""
    error: Optional[str] = None


@register_tool(
    name="get_commit_details",
    description="Retrieve detailed metadata and changed files for a specific Git commit (read-only).",
    permission=PermissionScope.REPOSITORY_READ,
    args_model=CommitDetailsInput,
    output_model=CommitDetailsOutput,
)
def get_commit_details(
    commit_hash: str,
    repository_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve details for a specific commit."""
    # Sanitize commit hash
    if not re.match(r"^[0-9a-fA-F]{4,40}$", commit_hash.strip()):
        return {
            "success": False,
            "commit_hash": commit_hash,
            "author": "",
            "date": "",
            "message": "",
            "changed_files": [],
            "stats": "",
            "error": "Invalid commit hash format.",
        }

    clean_hash = commit_hash.strip()

    try:
        path = _validate_repo_path(repository_path)
    except Exception as e:
        return {
            "success": False,
            "commit_hash": clean_hash,
            "author": "",
            "date": "",
            "message": "",
            "changed_files": [],
            "stats": "",
            "error": str(e),
        }

    try:
        # Show commit info and stat
        proc = subprocess.run(
            ["git", "show", "--stat", "--pretty=format:%H|||%an|||%ad|||%B|||STAT_START", clean_hash],
            cwd=str(path),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )

        output = proc.stdout
        parts = output.split("|||")
        if len(parts) >= 5:
            c_hash = parts[0].strip()
            author = parts[1].strip()
            date = parts[2].strip()
            message = parts[3].strip()
            stat_part = parts[4].replace("STAT_START", "").strip()
        else:
            c_hash = clean_hash
            author = ""
            date = ""
            message = output
            stat_part = ""

        # Get changed file names
        files_proc = subprocess.run(
            ["git", "show", "--name-only", "--pretty=format:", clean_hash],
            cwd=str(path),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        files = [f.strip() for f in files_proc.stdout.strip().splitlines() if f.strip()]

        return {
            "success": True,
            "commit_hash": c_hash,
            "author": author,
            "date": date,
            "message": message,
            "changed_files": files,
            "stats": stat_part,
            "error": None,
        }

    except Exception as ex:
        logger.error(f"Failed to get commit details for {clean_hash}: {ex}")
        return {
            "success": False,
            "commit_hash": clean_hash,
            "author": "",
            "date": "",
            "message": "",
            "changed_files": [],
            "stats": "",
            "error": str(ex),
        }
