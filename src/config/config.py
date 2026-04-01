# src/config/config.py

from pathlib import Path

# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = str(DATA_DIR / "lazy_coach.db")

# --------------------------------------------------
# Runtime
# --------------------------------------------------

CHECK_INTERVAL_SECONDS = 2
LIVE_COUNTER_PRINT_INTERVAL_SECONDS = 10
IDLE_THRESHOLD_SECONDS = 60

# --------------------------------------------------
# Ignored processes
# --------------------------------------------------

IGNORED_PROCESSES = {
    "explorer.exe",
    "searchhost.exe",
    "shellhost.exe",
    "shellexperiencehost.exe",
    "textinputhost.exe",
    "lockapp.exe",
    "dwm.exe",
    "asusoptimization.exe",
    "widgets.exe",
}

# --------------------------------------------------
# Process categories
# --------------------------------------------------

PRODUCTIVE = {
    "pycharm64.exe",
    "code.exe",
    "devenv.exe",
    "notepad++.exe",
    "cmd.exe",
    "powershell.exe",
    "windowsterminal.exe",
    "excel.exe",
    "winword.exe",
}

DISTRACTING = {
    "telegram.exe",
    "discord.exe",
    "whatsapp.exe",
    "slack.exe",
}

TIME_WASTING = {
    "steam.exe",
    "epicgameslauncher.exe",
    "riotclientservices.exe",
    "leagueclient.exe",
    "dota2.exe",
    "cs2.exe",
    "chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "opera.exe",
}

UNKNOWN_CATEGORY = "unknown"
IGNORED_CATEGORY = "ignored"

# --------------------------------------------------
# Rules
# --------------------------------------------------

RULES = {
    "productive": {
        "mode": "none",
        "threshold_seconds": 0,
        "notify_on_enter": False,
        "message": "",
    },
    "distracting": {
        "mode": "instant",
        "threshold_seconds": 60,
        "notify_on_enter": False,
        "message": "Ти завис у distracting-активності. Повернись до справи.",
    },
    "time_wasting": {
        "mode": "daily_accumulate",
        "threshold_seconds": 1800,
        "notify_on_enter": False,
        "message": "Денний ліміт на time-wasting майже або вже пробитий.",
    },
    "unknown": {
        "mode": "none",
        "threshold_seconds": 0,
        "notify_on_enter": False,
        "message": "",
    },
    "ignored": {
        "mode": "none",
        "threshold_seconds": 0,
        "notify_on_enter": False,
        "message": "",
    },
}