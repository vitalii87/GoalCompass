from src.config.config import PRODUCTIVE, DISTRACTING, TIME_WASTING


def classify(process_name: str) -> str:
    process_name = process_name.lower()

    if process_name in PRODUCTIVE:
        return "productive"
    if process_name in DISTRACTING:
        return "distracting"
    if process_name in TIME_WASTING:
        return "time_wasting"

    return "unknown"