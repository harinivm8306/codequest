"""Settings from environment variables. Nothing secret has a default."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass
class Settings:
    database_url: str = field(default_factory=lambda: _env("DATABASE_URL", f"sqlite:///{REPO_ROOT / 'backend' / 'schemesathi.db'}"))
    schemes_dir: str = field(default_factory=lambda: _env("SCHEMES_DIR", str(REPO_ROOT / "schemes")))
    frontend_dist: str = field(default_factory=lambda: _env("FRONTEND_DIST", str(REPO_ROOT / "frontend" / "out")))
    cors_origins: list[str] = field(default_factory=lambda: [o for o in _env("CORS_ORIGINS", "http://localhost:3000").split(",") if o])

    # LLM (Claude) — optional; without it a deterministic keyword extractor is used
    anthropic_api_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    anthropic_model: str = field(default_factory=lambda: _env("ANTHROPIC_MODEL", "claude-haiku-5-5"))
    llm_timeout_s: float = field(default_factory=lambda: float(_env("LLM_TIMEOUT_S", "8")))

    # Bhashini — optional; without it the browser's speech APIs are used
    bhashini_user_id: str = field(default_factory=lambda: _env("BHASHINI_USER_ID"))
    bhashini_api_key: str = field(default_factory=lambda: _env("BHASHINI_API_KEY"))
    bhashini_pipeline_id: str = field(default_factory=lambda: _env("BHASHINI_PIPELINE_ID", "64392f96daac500b55c543cd"))
    bhashini_timeout_s: float = field(default_factory=lambda: float(_env("BHASHINI_TIMEOUT_S", "6")))

    # privacy / limits
    hash_salt: str = field(default_factory=lambda: _env("HASH_SALT", "dev-only-salt-change-me"))
    document_retention_hours: int = field(default_factory=lambda: int(_env("DOCUMENT_RETENTION_HOURS", "24")))
    profile_inactive_days: int = field(default_factory=lambda: int(_env("PROFILE_INACTIVE_DAYS", "90")))
    rate_limit_per_minute: int = field(default_factory=lambda: int(_env("RATE_LIMIT_PER_MINUTE", "30")))
    max_upload_mb: int = field(default_factory=lambda: int(_env("MAX_UPLOAD_MB", "5")))

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def bhashini_enabled(self) -> bool:
        return bool(self.bhashini_user_id and self.bhashini_api_key)


settings = Settings()
