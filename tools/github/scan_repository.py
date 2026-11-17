"""Read-only Git repository scanning tool."""

import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.config import settings
from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from agent.logging_config import logger


class ScanRepositoryInput(BaseModel):
    """Input parameters for scan_repository."""
    repository_path: Optional[str] = Field(
        default=None,
        description="Path to the authorised Git repository. If None, uses configured caspian_repo_path or workspace.",
    )
    since_commit: Optional[str] = Field(
        default=None,
        description="Optional commit hash to scan changes since. If None, retrieves latest commit and recent history.",
    )


class ScanRepositoryOutput(BaseModel):
    """Output schema for scan_repository."""
    success: bool
    repository_path: str
    latest_commit: str
    new_commits: List[Dict[str, str]] = Field(default_factory=list)
    changed_files: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


def _validate_repo_path(repo_path: Optional[str]) -> Path:
    """Validate that repository path exists and is an authorised git repository."""
    target_path = Path(repo_path) if repo_path else (settings.caspian_repo_path or settings.base_dir)
    target_path = target_path.resolve()

    if not target_path.exists():
        raise ValueError(f"Repository path does not exist: {target_path}")

    git_dir = target_path / ".git"
    if not git_dir.exists() and not (target_path / "HEAD").exists():
        raise ValueError(f"Path is not a valid Git repository: {target_path}")

    return target_path


@register_tool(
    name="scan_repository",
    description="Scan the authorised Caspian Git repository to identify new commits and changed files (read-only).",
    permission=PermissionScope.REPOSITORY_READ,
    args_model=ScanRepositoryInput,
    output_model=ScanRepositoryOutput,
)
def scan_repository(
    repository_path: Optional[str] = None,
    since_commit: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute read-only scan of git repository."""
    try:
        path = _validate_repo_path(repository_path)
    except Exception as e:
        return {
            "success": False,
            "repository_path": str(repository_path or ""),
            "latest_commit": "",
            "new_commits": [],
            "changed_files": [],
            "errors": [str(e)],
        }

    try:
        # 1. Get latest commit hash
        head_proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(path),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        latest_commit = head_proc.stdout.strip()

        # 2. Get commits
        new_commits: List[Dict[str, str]] = []
        if since_commit and since_commit != latest_commit:
            log_cmd = ["git", "log", f"{since_commit}..HEAD", "--pretty=format:%H|||%an|||%ad|||%s"]
            diff_cmd = ["git", "diff", "--name-only", f"{since_commit}..HEAD"]
        else:
            log_cmd = ["git", "log", "-n", "10", "--pretty=format:%H|||%an|||%ad|||%s"]
            diff_cmd = ["git", "show", "--name-only", "--pretty=format:", latest_commit]

        log_proc = subprocess.run(
            log_cmd,
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if log_proc.returncode == 0 and log_proc.stdout.strip():
            for line in log_proc.stdout.strip().splitlines():
                parts = line.split("|||")
                if len(parts) >= 4:
                    new_commits.append({
                        "commit_hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3],
                    })

        # 3. Get changed files
        changed_files: List[str] = []
        diff_proc = subprocess.run(
            diff_cmd,
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if diff_proc.returncode == 0 and diff_proc.stdout.strip():
            changed_files = [f.strip() for f in diff_proc.stdout.strip().splitlines() if f.strip()]

        return {
            "success": True,
            "repository_path": str(path),
            "latest_commit": latest_commit,
            "new_commits": new_commits,
            "changed_files": changed_files,
            "errors": [],
        }

    except Exception as ex:
        logger.error(f"Failed to scan repository at {path}: {ex}")
        return {
            "success": False,
            "repository_path": str(path),
            "latest_commit": "",
            "new_commits": [],
            "changed_files": [],
            "errors": [str(ex)],
        }
