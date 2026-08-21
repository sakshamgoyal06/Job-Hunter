"""Application configuration loaded from environment."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# job_search_copilot/ directory (parent of src/)
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
EXPORTS_DIR = ROOT_DIR / "exports"
DB_PATH = DATA_DIR / "app.db"
ENV_PATH = ROOT_DIR / ".env"

load_dotenv(ENV_PATH)

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_TEMPERATURE_STRUCTURED: float = float(
    os.getenv("OPENAI_TEMPERATURE_STRUCTURED", "0.2")
)
OPENAI_TEMPERATURE_CREATIVE: float = float(
    os.getenv("OPENAI_TEMPERATURE_CREATIVE", "0.35")
)


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
