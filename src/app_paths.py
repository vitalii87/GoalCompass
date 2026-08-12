from __future__ import annotations

import sys
from pathlib import Path


IS_FROZEN = bool(getattr(sys, "frozen", False))

if IS_FROZEN:
    APP_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR)).resolve()
else:
    APP_DIR = Path(__file__).resolve().parents[1]
    RESOURCE_DIR = APP_DIR

DATA_DIR = APP_DIR / "data"
RUNTIME_DIR = DATA_DIR / "runtime"
USER_CONFIG_DIR = DATA_DIR / "user_config"
VERSION_PATH = RESOURCE_DIR / "VERSION"
