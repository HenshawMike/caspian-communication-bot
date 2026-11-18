"""Configuration management for Project Caspian Agent."""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


def _load_env_file(dotenv_path: Path) -> None:
    """Simple .env loader if python-dotenv is not yet loaded or as fallback."""
    if not dotenv_path.is_file():
        return
    try:
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


@dataclass
class Settings:
    """Application settings with environment variable overrides."""

    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    
    # OpenRouter API (Primary LLM)
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "baidu/ernie-5.5-flash-preview:free"
    openrouter_api_url: str = "https://openrouter.ai/api/v1/chat/completions"

    # Hugging Face Router API (Alternative)
    hf_token: Optional[str] = None
    hf_model: str = "Qwen/Qwen3-4B:featherless-ai"
    hf_api_url: str = "https://router.huggingface.co/v1/chat/completions"

    # Gemini API (Secondary / Fallback)
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    
    # Telegram Bot
    telegram_bot_token: Optional[str] = None
    telegram_authorized_user_id: Optional[str] = None
    
    # X (Twitter) API
    x_api_key: Optional[str] = None
    x_api_secret: Optional[str] = None
    x_access_token: Optional[str] = None
    x_access_token_secret: Optional[str] = None
    x_dry_run_mode: bool = True

    # Paths & Repositories
    caspian_repo_path: Optional[Path] = None
    database_path: str = "caspian_agent.db"
    skills_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "skills")
    documents_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "documents")
    
    # Execution & Security Limits
    max_tool_calls_per_request: int = 10
    max_workflow_duration_seconds: int = 60
    log_level: str = "INFO"

    def __post_init__(self):
        # Attempt to load .env if present
        env_path = self.base_dir / ".env"
        _load_env_file(env_path)

        # Populate from environment
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", self.openrouter_api_key)
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", self.openrouter_model)
        self.openrouter_api_url = os.getenv("OPENROUTER_API_URL", self.openrouter_api_url)

        self.hf_token = os.getenv("HF_TOKEN", self.hf_token)
        self.hf_model = os.getenv("HF_MODEL", self.hf_model)
        self.hf_api_url = os.getenv("HF_API_URL", self.hf_api_url)

        self.gemini_api_key = os.getenv("GEMINI_API_KEY", self.gemini_api_key)
        self.gemini_model = os.getenv("GEMINI_MODEL", self.gemini_model)
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", self.telegram_bot_token)
        self.telegram_authorized_user_id = os.getenv("TELEGRAM_AUTHORIZED_USER_ID", self.telegram_authorized_user_id)
        
        self.x_api_key = os.getenv("X_API_KEY", self.x_api_key)
        self.x_api_secret = os.getenv("X_API_SECRET", self.x_api_secret)
        self.x_access_token = os.getenv("X_ACCESS_TOKEN", self.x_access_token)
        self.x_access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET", self.x_access_token_secret)
        self.x_dry_run_mode = os.getenv("X_DRY_RUN_MODE", "true").lower() in ("true", "1", "yes")

        repo_env = os.getenv("CASPIAN_REPO_PATH")
        if repo_env and not repo_env.startswith(("http://", "https://", "git@")):
            self.caspian_repo_path = Path(repo_env)
            
        if "DATABASE_PATH" in os.environ and self.database_path == "caspian_agent.db":
            self.database_path = os.environ["DATABASE_PATH"]
        self.log_level = os.getenv("LOG_LEVEL", self.log_level).upper()
        
        try:
            self.max_tool_calls_per_request = int(
                os.getenv("MAX_TOOL_CALLS_PER_REQUEST", str(self.max_tool_calls_per_request))
            )
        except ValueError:
            pass

    def get_db_path(self) -> Path:
        """Resolve database path relative to base directory if not absolute."""
        p = Path(self.database_path)
        if not p.is_absolute():
            return self.base_dir / p
        return p

    def get_documents_dir(self) -> Path:
        """Resolve generated documents directory and ensure it exists."""
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        return self.documents_dir

    def __repr__(self) -> str:
        """Safe representation masking sensitive credentials."""
        masked_openrouter = "***" if self.openrouter_api_key else "None"
        masked_hf = "***" if self.hf_token else "None"
        masked_gemini = "***" if self.gemini_api_key else "None"
        masked_telegram = "***" if self.telegram_bot_token else "None"
        return (
            f"Settings(base_dir={self.base_dir}, "
            f"openrouter_model='{self.openrouter_model}', "
            f"openrouter_api_key={masked_openrouter}, "
            f"hf_model='{self.hf_model}', "
            f"hf_token={masked_hf}, "
            f"gemini_model='{self.gemini_model}', "
            f"gemini_api_key={masked_gemini}, "
            f"telegram_bot_token={masked_telegram}, "
            f"database_path='{self.database_path}', "
            f"max_tool_calls={self.max_tool_calls_per_request})"
        )


# Global settings singleton
settings = Settings()
