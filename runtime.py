"""Process-local flags. Tests set the root override. Production leaves it empty."""

from __future__ import annotations

from pathlib import Path

ROOT_OVERRIDE: Path | None = None
SHOW_FULL: dict[tuple[str, str], bool] = {}
