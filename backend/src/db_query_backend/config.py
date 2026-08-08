from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "DB Query Generator"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    allow_origins: tuple[str, ...] = ("*",)
    sqlite_path: Path = Path(__file__).resolve().parents[3] / "backend" / "data" / "app.db"


settings = Settings()
