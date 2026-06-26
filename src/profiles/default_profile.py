# src/profiles/default_profile.py

PROFILE = {
    "productive": {
        "pycharm64.exe",
        "code.exe",
        "chrome.exe",
    },
    "personal": {
        "vlc.exe",
        "explorer.exe",
    },
    "time_wasting": {
        "worldoftanks.exe",
        "minecraft.exe",
        "javaw.exe",
        "mow2.exe",
        "wgc.exe",
        "steamwebhelper.exe",
    },
    "distracting": {
        "telegram.exe",
        "discord.exe",
    },
}

TITLE_RULES = {
    "chrome.exe": {
        "productive": [
            "chatgpt",
            "github",
            "stackoverflow",
            "stack overflow",
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
            "linkedin",
            "qa вакансії",
            "remote qa",
            "glassdoor",
            "middle qa engineer",
            "automation testing",
            "splitmetrics",
            "штучний інтелект",
            "новизна",
            "німець",
            "deutsch",
            "a1",
            "b1",
        ],
        "personal": [
            "google maps",
            "карти google",
            "kleinanzeigen",
            "ebay",
            "audi",
            "roller",
            "scooter",
            "badeparadies",
            "jobcenter",
            "bank",
            "btc",
            "bitcoin",
            "usdt",
            "exmo",
            "pornhub",
        ],
        "time_wasting": [
            "youtube",
            "twitch",
            "netflix",
            "tiktok",
            "facebook",
            "instagram",
            "anime",
            "аніме",
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
    }
}

GOALS = [
    {
        "goal_id": "reduce_gaming_001",
        "goal_type": "reduce_gaming",
        "title": "Reduce gaming time",
        "related_outcomes": [],
        "conflicting_outcomes": [
            "time_wasted",
        ],
    },
    {
        "goal_id": "build_project_001",
        "goal_type": "build_project",
        "title": "Build GoalCompass",
        "related_outcomes": [
            "focus_session",
        ],
        "conflicting_outcomes": [],
    },
    {
        "goal_id": "german_b1_001",
        "goal_type": "german_b1",
        "title": "Reach German B1",
        "related_outcomes": [
            "learning_session",
        ],
        "conflicting_outcomes": [],
    },
]