"""Configuration for markdown edit benchmarks."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from lmnr import Instruments, Laminar
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API settings - OpenRouter (used for all models including Morph)
    openrouter_api_key: str = Field(default="")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")

    # Paths - fixtures directory
    md_edit_bench_fixtures: Path | None = Field(default=None)

    # Laminar tracing
    lmnr_project_api_key: str | None = Field(default=None)

    @property
    def fixtures_dir(self) -> Path:
        """Get fixtures directory, defaulting to repo root fixtures/."""
        if self.md_edit_bench_fixtures:
            return self.md_edit_bench_fixtures
        return Path(__file__).parent.parent / "fixtures"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience accessors for backwards compatibility
_settings = get_settings()

API_KEY = _settings.openrouter_api_key
BASE_URL = _settings.openrouter_base_url
FIXTURES_DIR = _settings.fixtures_dir

# Default models for algorithms that accept model choice
DEFAULT_MODELS = [
    "anthropic/claude-sonnet-4",
    "openai/gpt-oss-120b",
]

# Morph model (fixed, doesn't accept model choice)
MORPH_MODEL = "morph/morph-v3-large"

# Categories
CATEGORIES = ["simple", "medium", "complex", "hard"]


def _init_laminar() -> bool:
    """Initialize Laminar tracing if API key is available."""
    if not _settings.lmnr_project_api_key:
        return False

    Laminar.initialize(
        project_api_key=_settings.lmnr_project_api_key,
        instruments={Instruments.OPENAI},
    )
    return True


LAMINAR_ENABLED = _init_laminar()
