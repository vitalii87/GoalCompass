from __future__ import annotations

from pathlib import Path

from src.app_paths import VERSION_PATH



def read_version(path: Path = VERSION_PATH) -> str:
    try:
        version = path.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0+unknown"

    return version or "0.0.0+unknown"


__version__ = read_version()
