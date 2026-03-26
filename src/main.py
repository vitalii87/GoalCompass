# src/main.py

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from src.classifier.classifier import classify_process_name
from src.config.config import (
    CHECK_INTERVAL_SECONDS,
    DB_PATH,
    LIVE_COUNTER_PRINT_INTERVAL_SECONDS,
    RULES,
)
from src.monitor.process_monitor import get_foreground_process_info
from src.notifier.notifier import notify
from src.storage.db import SQLiteStorage
from src.tracker.live_counter import LiveCounter


def log_message(message: str) -> None:
    """
    Fallback-safe logger wrapper.
    Replace with your logger import if needed.
    """
    try:
        from src.logger.logger import log
        log(message)
    except Exception:
        print(message)


def get_rule_for_category(category: str) -> Dict[str, Any]:
    """
    Thin rule accessor.
    If your Sprint 1 already has a rules engine function,
    you can switch this wrapper to it.
    """
    try:
        from src.coach.rules_engine import get_rule_for_category as real_get_rule
        return real_get_rule(category)
    except Exception:
        return RULES.get(
            category,
            {
                "mode": "none",
                "threshold_seconds": 0,
                "notify_on_enter": False,
                "message": "",
            },
        )


def safe_get_process_info() -> Dict[str, str]:
    """
    Expected normalized output:
    {
        "process_name": "...",
        "window_title": "..."
    }
    """
    info = get_foreground_process_info()

    if isinstance(info, dict):
        return {
            "process_name": str(info.get("process_name", "unknown.exe")).lower(),
            "window_title": str(info.get("window_title", "")),
        }

    raise ValueError(
        "get_foreground_process_info() must return dict with "
        "'process_name' and 'window_title'"
    )


def safe_classify(process_name: str) -> str:
    category = classify_process_name(process_name)
    if not isinstance(category, str):
        raise ValueError("classify_process_name() must return a string category")
    return category


def should_notify(
    rule: Dict[str, Any],
    current_session_seconds: int,
    daily_category_total_seconds: int,
) -> bool:
    mode = rule.get("mode", "none")
    threshold = int(rule.get("threshold_seconds", 0))

    if mode == "none":
        return False

    if mode == "instant":
        return current_session_seconds >= threshold

    if mode == "daily_accumulate":
        return daily_category_total_seconds >= threshold

    return False


def format_seconds(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def print_live_stats(counter: LiveCounter) -> None:
    session = counter.get_current_session_info()
    category_totals = counter.get_daily_totals_by_category()

    log_message("=" * 60)
    log_message("LIVE STATS")

    if session:
        log_message(
            f"Current: process={session['process_name']} | "
            f"category={session['category']} | "
            f"session={format_seconds(session['seconds'])}"
        )
    else:
        log_message("Current: no active session")

    if not category_totals:
        log_message("Daily totals: empty")
    else:
        for category, total in sorted(category_totals.items()):
            log_message(f"Daily total [{category}] = {format_seconds(total)}")

    log_message("=" * 60)


def main() -> None:
    storage = SQLiteStorage(DB_PATH)
    counter = LiveCounter(storage)

    last_print_time = time.time()

    last_notified_key: Optional[tuple[str, str]] = None
    # key format: (process_name, mode)
    # prevents spam while user stays in same already-thresholded state

    log_message("lazy_coach started")

    try:
        while True:
            process_info = safe_get_process_info()
            process_name = process_info["process_name"]
            window_title = process_info["window_title"]

            category = safe_classify(process_name)

            counter.update(
                process_name=process_name,
                category=category,
                seconds=CHECK_INTERVAL_SECONDS,
            )

            rule = get_rule_for_category(category)
            session = counter.get_current_session_info()

            current_session_seconds = 0
            if session and session["process_name"] == process_name:
                current_session_seconds = int(session["seconds"])

            daily_category_total_seconds = counter.get_daily_total_by_category(category)

            notify_now = should_notify(
                rule=rule,
                current_session_seconds=current_session_seconds,
                daily_category_total_seconds=daily_category_total_seconds,
            )

            notify_key = (process_name, str(rule.get("mode", "none")))

            if notify_now:
                if last_notified_key != notify_key:
                    message = rule.get("message", "Повернись до роботи.")
                    full_message = (
                        f"{message}\n"
                        f"Process: {process_name}\n"
                        f"Category: {category}\n"
                        f"Window: {window_title}\n"
                        f"Session: {format_seconds(current_session_seconds)}\n"
                        f"Daily total [{category}]: {format_seconds(daily_category_total_seconds)}"
                    )
                    notify(full_message)
                    log_message(f"NOTIFY -> {full_message}")
                    last_notified_key = notify_key
            else:
                # reset when below threshold or harmless state
                if session and session["process_name"] != process_name:
                    last_notified_key = None
                elif rule.get("mode") == "none":
                    last_notified_key = None

            now = time.time()
            if now - last_print_time >= LIVE_COUNTER_PRINT_INTERVAL_SECONDS:
                print_live_stats(counter)
                last_print_time = now

            time.sleep(CHECK_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        log_message("lazy_coach stopped by user")

    finally:
        counter.shutdown()
        log_message("Current session flushed to database")


if __name__ == "__main__":
    main()