from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
VERSION_PATH = ROOT_DIR / "VERSION"


def read_version(path: Path = VERSION_PATH) -> str:
    try:
        version = path.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0+unknown"

    return version or "0.0.0+unknown"


__version__ = read_version()
