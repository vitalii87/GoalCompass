

from src.config.config import PRODUCTIVE, DISTRACTING


def classify(process_name):
    process_name = process_name.lower()

    if process_name in PRODUCTIVE:
        return "productive"
    elif process_name in DISTRACTING:
        return "distracting"
    else:
        return "unknown"