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
UNKNOWN_SAVE_THRESHOLD_SECONDS = 30
# --------------------------------------------------
# Ignored processes
# --------------------------------------------------

# --------------------------------------------------
# Feature flags
# --------------------------------------------------

ENABLE_UNKNOWN_TRACKING = True

# Future modules.
# Keep disabled by default to avoid API costs and unwanted auto-changes.
ENABLE_AI_ANALYTICS = False
ENABLE_AUTO_SORTER = False

# Print top unknown
TOP_UNKNOWN_PRINT_EVERY_SECONDS = 300
TOP_UNKNOWN_LIMIT = 5

IGNORED_PROCESSES = {
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
# Process categories (LEVEL 1)
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
    "worldoftanks.exe",
    "minecraft.exe",
    "javaw.exe",
    "mow2.exe",
    "wgc.exe",
    "steamwebhelper.exe",
}

# додай після TIME_WASTING

PERSONAL = {
    "vlc.exe",
}

UNKNOWN_CATEGORY = "unknown"
IGNORED_CATEGORY = "ignored"
PERSONAL_CATEGORY = "personal"

# --------------------------------------------------
# Title-aware rules (LEVEL 2)
# --------------------------------------------------

TITLE_RULES = {
    "chrome.exe": {
        "productive": [
            "chatgpt",
            "gmail",
            "stackoverflow",
            "stack overflow",
            "github",
            "docs",
            "documentation",
            "fastapi",
            "pytest",
            "python",
            "pycharm",
            "lazy_coach",
            "агресів коуч",
            "архітектура",
            "sprint",
            "німець",
            "deutsch",
            "fragewörter",
            "а1",
            "a1",
            "linkedin",
            "штучний інтелект",
            "новизна",
        ],
        "personal": [
            "google maps",
            "карти google",
            "kleinanzeigen",
            "ebay classifieds",
            "audi",
            "roller",
            "scooter",
            "badeparadies",
            "jobcenter",
            "bank",
            "exmo",
            "btc",
            "usdt",
            "bitcoin",
            "pornhub",
        ],
        "time_wasting": [
            "youtube",
            "twitch",
            "netflix",
            "tiktok",
            "facebook",
            "instagram",
            "shorts",
            "аніме",
            "anime",
            "людина-бензопила",
            "wargaming",
            "premium shop",
        ],
        "distracting": [
            "telegram",
            "discord",
            "messenger",
            "whatsapp",
        ],
    },
    "msedge.exe": {
        "productive": [
            "chatgpt",
            "gmail",
            "stackoverflow",
            "github",
            "docs",
            "deutsch",
            "німець",
            "a1",
        ],
        "time_wasting": [
            "youtube",
            "twitch",
            "netflix",
            "tiktok",
        ],
    },
}

# --------------------------------------------------
# Rules (coaching logic)
# --------------------------------------------------

RULES = {
    "productive": {
        "mode": "none",
        "threshold_seconds": 0,
        "notify_on_enter": False,
        "message": "",
    },
    "personal": {
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