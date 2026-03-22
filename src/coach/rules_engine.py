RULES = {
    "productive": {
        "mode": "instant",
        "threshold_seconds": 0,
        "notify_on_enter": True,
        "message": "Добре, продовжуй.",
    },
    "distracting": {
        "mode": "instant",
        "threshold_seconds": 60,
        "notify_on_enter": False,
        "message": "Ти вже занадто довго відволікаєшся. Повернись до роботи.",
    },
    "time_wasting": {
        "mode": "daily_accumulate",
        "threshold_seconds": 3600,
        "notify_on_enter": False,
        "message": "Сьогодні ти вже перевищив ліміт часу на цю активність.",
    },
    "unknown": {
        "mode": "none",
        "threshold_seconds": 0,
        "notify_on_enter": False,
        "message": "",
    },
}


def get_rule(state: str) -> dict:
    return RULES.get(
        state,
        {
            "mode": "none",
            "threshold_seconds": 0,
            "notify_on_enter": False,
            "message": "",
        },
    )