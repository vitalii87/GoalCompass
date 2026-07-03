# src/main.py

from __future__ import annotations

import time
from datetime import date
from typing import Any, Dict, Optional

from src.activity.user_activity import UserActivityMonitor
from src.classifier.classifier import classify_process_name
from src.config.config import (
    CHECK_INTERVAL_SECONDS,
    DB_PATH,
    ENABLE_AI_ANALYTICS,
    ENABLE_AUTO_SORTER,
    ENABLE_UNKNOWN_TRACKING,
    IDLE_THRESHOLD_SECONDS,
    IGNORED_CATEGORY,
    IGNORED_PROCESSES,
    LIVE_COUNTER_PRINT_INTERVAL_SECONDS,
    RULES,
)
from src.goals.goal_alignment import GoalAlignmentEngine
from src.goals.goal_loader import load_goals
from src.monitor.process_monitor import get_foreground_process_info
from src.notifier.notifier import notify
from src.outcomes.outcome_engine import OutcomeEngine
from src.services.current_state_service import write_current_state
from src.services.notification_event_service import write_notification_event
from src.signals.signals_engine import SignalsEngine
from src.storage.db import SQLiteStorage
from src.tracker.live_counter import LiveCounter
from src.unknown.unknown_tracker import UnknownTracker


def log_message(message: str) -> None:
    try:
        from src.logger.logger import log

        log(message)
    except Exception:
        print(message)


def get_rule_for_category(category: str) -> Dict[str, Any]:
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
    info = get_foreground_process_info()

    if isinstance(info, dict):
        return {
            "process_name": str(info.get("process_name", "unknown.exe")).lower(),
            "window_title": str(info.get("window_title", "")).strip(),
        }

    raise ValueError(
        "get_foreground_process_info() must return dict with "
        "'process_name' and 'window_title'"
    )


def safe_classify(process_name: str, window_title: str) -> str:
    try:
        category = classify_process_name(process_name, window_title)
    except TypeError:
        category = classify_process_name(process_name)

    if not isinstance(category, str):
        raise ValueError("classify_process_name() must return a string category")

    return category


def is_goalcompass_overlay_window(
    process_name: str,
    window_title: str,
) -> bool:
    """
    Prevent the always-on-top overlay itself from becoming tracked activity.

    When overlay_widget.py is focused, Windows reports something like:
        python3.10.exe | GoalCompass

    We do not want this to pollute activity_logs or current_state.
    """
    normalized_process = process_name.lower().strip()
    normalized_title = window_title.lower().strip()

    python_processes = {
        "python.exe",
        "pythonw.exe",
        "python3.exe",
        "python3.10.exe",
        "python3.11.exe",
        "python3.12.exe",
    }

    if normalized_process not in python_processes:
        return False

    return normalized_title == "goalcompass"


def get_daily_idle_seconds(counter: LiveCounter) -> int:
    state_totals = counter.get_daily_totals_by_state()
    return int(state_totals.get("idle", 0))


def get_daily_display_seconds(
    counter: LiveCounter,
    category: str,
    activity_state: str,
) -> int:
    """
    Value shown in the mini overlay.

    Active:
        show today's total for the current category.

    Idle:
        do not count/display productive or wasted time.
        Idle is a pause state for the mini overlay.
    """
    if activity_state == "idle":
        return 0

    return int(counter.get_daily_total_by_category(category))


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


def build_notification_key(
    rule: Dict[str, Any],
    process_name: str,
    category: str,
) -> tuple[str, str, str]:
    """
    Build notification de-duplication key.

    daily_accumulate:
        notify once per date + category + mode.

    instant / other:
        notify once per process + category + mode.
    """
    mode = str(rule.get("mode", "none"))

    if mode == "daily_accumulate":
        return (
            date.today().isoformat(),
            category,
            mode,
        )

    return (
        process_name,
        category,
        mode,
    )


def format_seconds(seconds: int) -> str:
    seconds = max(int(seconds), 0)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def print_live_stats(counter: LiveCounter, current_window_title: str = "") -> None:
    session = counter.get_current_session_info()
    category_totals = counter.get_daily_totals_by_category()
    state_totals = counter.get_daily_totals_by_state()

    log_message("=" * 60)
    log_message("LIVE STATS")

    if session:
        log_message(
            f"Current: process={session['process_name']} | "
            f"category={session['category']} | "
            f"state={session['activity_state']} | "
            f"session={format_seconds(session['seconds'])}"
        )
        log_message(f"Window title: {current_window_title or '[empty]'}")
    else:
        log_message("Current: no active session")

    if not category_totals:
        log_message("Daily totals by category: empty")
    else:
        for category, total in sorted(category_totals.items()):
            log_message(f"Daily total [{category}] = {format_seconds(total)}")

    if not state_totals:
        log_message("Daily totals by state: empty")
    else:
        for state, total in sorted(state_totals.items()):
            log_message(f"Daily total state [{state}] = {format_seconds(total)}")

    log_message("=" * 60)


def seed_existing_signal_milestones(
    signals_engine: SignalsEngine,
    emitted_signal_keys: set[tuple[str, str, str, int]],
    process_name: str,
    category: str,
    activity_state: str,
    current_session_seconds: int,
) -> None:
    """
    Prevent old/restored session milestones from firing immediately
    when GoalCompass starts.

    Example:
        Tracker starts while PyCharm session already has 600s.
        Without seeding, 60/300/600 signals are emitted immediately.
        With seeding, they are considered already passed.
    """
    signals = signals_engine.generate_for_session(
        process_name=process_name,
        category=category,
        seconds=current_session_seconds,
        activity_state=activity_state,
    )

    for signal in signals:
        threshold_seconds = int(signal.metadata.get("threshold_seconds", 0))

        signal_key = (
            signal.process_name,
            signal.category,
            signal.signal_type,
            threshold_seconds,
        )

        emitted_signal_keys.add(signal_key)


def process_goal_pipeline(
    storage: SQLiteStorage,
    signals_engine: SignalsEngine,
    outcome_engine: OutcomeEngine,
    goal_alignment_engine: GoalAlignmentEngine,
    goals: list,
    process_name: str,
    category: str,
    activity_state: str,
    current_session_seconds: int,
    emitted_signal_keys: set[tuple[str, str, str, int]],
) -> None:
    """
    Sprint 4.2 pipeline:

    process/category/session/activity_state
        -> milestone Signal
        -> Outcome
        -> GoalAlignmentResult
        -> goal_events DB

    goal_events are raw alignment events.
    They are NOT effectiveness conclusions.
    """

    signals = signals_engine.generate_for_session(
        process_name=process_name,
        category=category,
        seconds=current_session_seconds,
        activity_state=activity_state,
    )

    for signal in signals:
        threshold_seconds = int(signal.metadata.get("threshold_seconds", 0))

        signal_key = (
            signal.process_name,
            signal.category,
            signal.signal_type,
            threshold_seconds,
        )

        if signal_key in emitted_signal_keys:
            continue

        emitted_signal_keys.add(signal_key)

        log_message("")
        log_message("SIGNAL:")
        log_message(str(signal))

        outcome = outcome_engine.generate_from_signal(signal)

        if outcome is None:
            log_message("")
            log_message("OUTCOME:")
            log_message("No outcome generated from signal")
            continue

        log_message("")
        log_message("OUTCOME:")
        log_message(str(outcome))

        log_message("")
        log_message("GOAL ALIGNMENTS:")

        active_goals = [goal for goal in goals if getattr(goal, "is_active", True)]

        if not active_goals:
            log_message("No active goals found")
            continue

        for goal in active_goals:
            alignment = goal_alignment_engine.evaluate(
                goal=goal,
                outcome=outcome,
            )
            log_message(str(alignment))

            if alignment.alignment_score != 0:
                storage.log_goal_event(
                    event_date=date.today().isoformat(),
                    goal_id=alignment.goal_id,
                    outcome_type=alignment.outcome_type,
                    alignment_score=alignment.alignment_score,
                    process_name=signal.process_name,
                    category=signal.category,
                    signal_type=signal.signal_type,
                    seconds=signal.seconds,
                    message=alignment.message,
                )


def main() -> None:
    storage = SQLiteStorage(DB_PATH)
    counter = LiveCounter(storage)
    unknown_tracker = UnknownTracker(storage) if ENABLE_UNKNOWN_TRACKING else None
    activity_monitor = UserActivityMonitor(IDLE_THRESHOLD_SECONDS)

    signals_engine = SignalsEngine()
    outcome_engine = OutcomeEngine()
    goal_alignment_engine = GoalAlignmentEngine()
    goals = load_goals()

    log_message(f"Unknown tracking: {'ON' if ENABLE_UNKNOWN_TRACKING else 'OFF'}")
    log_message(f"AI analytics: {'ON' if ENABLE_AI_ANALYTICS else 'OFF'}")
    log_message(f"Auto sorter: {'ON' if ENABLE_AUTO_SORTER else 'OFF'}")
    log_message(f"Loaded goals: {len(goals)}")
    log_message("lazy_coach started")

    last_print_time = time.time()

    # Notification de-duplication memory for the current tracker runtime.
    #
    # Examples:
    #   daily_accumulate -> ("2026-07-03", "time_wasting", "daily_accumulate")
    #   instant          -> ("worldoftanks.exe", "time_wasting", "instant")
    sent_notification_keys: set[tuple[str, str, str]] = set()

    emitted_signal_keys: set[tuple[str, str, str, int]] = set()
    last_session_identity: Optional[tuple[str, str, str, str]] = None

    # First real tracked iteration may see a restored/continued session
    # with already accumulated seconds. Seed passed signal milestones once.
    is_first_tracked_iteration = True

    is_in_ignored_mode = False
    ignored_started_at: Optional[float] = None
    ignored_last_process = ""
    ignored_last_window = ""

    try:
        while True:
            process_info = safe_get_process_info()
            process_name = process_info["process_name"]
            window_title = process_info["window_title"]

            if is_goalcompass_overlay_window(
                process_name=process_name,
                window_title=window_title,
            ):
                time.sleep(CHECK_INTERVAL_SECONDS)
                continue

            if process_name in IGNORED_PROCESSES:
                if not is_in_ignored_mode:
                    is_in_ignored_mode = True
                    ignored_started_at = time.time()
                    log_message(
                        f"Ignored mode entered: "
                        f"{process_name} | window={window_title or '[empty]'}"
                    )

                ignored_last_process = process_name
                ignored_last_window = window_title

                ignored_duration = 0
                if ignored_started_at is not None:
                    ignored_duration = int(time.time() - ignored_started_at)

                write_current_state(
                    process_name=process_name,
                    window_title=window_title,
                    category=IGNORED_CATEGORY,
                    activity_state="idle",
                    session_seconds=ignored_duration,
                    today_category_seconds=0,
                )

                time.sleep(CHECK_INTERVAL_SECONDS)
                continue

            if is_in_ignored_mode:
                ignored_duration = 0

                if ignored_started_at is not None:
                    ignored_duration = int(time.time() - ignored_started_at)

                log_message(
                    f"Ignored mode exited: "
                    f"last={ignored_last_process or '[unknown]'} | "
                    f"window={ignored_last_window or '[empty]'} | "
                    f"duration={format_seconds(ignored_duration)}"
                )

                is_in_ignored_mode = False
                ignored_started_at = None
                ignored_last_process = ""
                ignored_last_window = ""

            category = safe_classify(process_name, window_title)
            if not category:
                category = IGNORED_CATEGORY

            activity_state = activity_monitor.get_activity_state()

            session_identity = (
                process_name,
                category,
                activity_state,
                window_title,
            )

            if session_identity != last_session_identity:
                emitted_signal_keys.clear()
                last_session_identity = session_identity

            counter.update(
                process_name=process_name,
                window_title=window_title,
                category=category,
                activity_state=activity_state,
                seconds=CHECK_INTERVAL_SECONDS,
            )

            if unknown_tracker is not None:
                unknown_tracker.update(
                    process_name=process_name,
                    window_title=window_title,
                    category=category,
                    seconds=CHECK_INTERVAL_SECONDS,
                )

            rule = get_rule_for_category(category)
            session = counter.get_current_session_info()

            current_session_seconds = 0
            if session and session["process_name"] == process_name:
                current_session_seconds = int(session["seconds"])

            daily_category_total_seconds = counter.get_daily_total_by_category(category)
            daily_display_seconds = get_daily_display_seconds(
                counter=counter,
                category=category,
                activity_state=activity_state,
            )

            write_current_state(
                process_name=process_name,
                window_title=window_title,
                category=category,
                activity_state=activity_state,
                session_seconds=current_session_seconds,
                today_category_seconds=daily_display_seconds,
            )

            if is_first_tracked_iteration:
                seed_existing_signal_milestones(
                    signals_engine=signals_engine,
                    emitted_signal_keys=emitted_signal_keys,
                    process_name=process_name,
                    category=category,
                    activity_state=activity_state,
                    current_session_seconds=current_session_seconds,
                )
                is_first_tracked_iteration = False
            else:
                process_goal_pipeline(
                    storage=storage,
                    signals_engine=signals_engine,
                    outcome_engine=outcome_engine,
                    goal_alignment_engine=goal_alignment_engine,
                    goals=goals,
                    process_name=process_name,
                    category=category,
                    activity_state=activity_state,
                    current_session_seconds=current_session_seconds,
                    emitted_signal_keys=emitted_signal_keys,
                )

            notify_now = should_notify(
                rule=rule,
                current_session_seconds=current_session_seconds,
                daily_category_total_seconds=daily_category_total_seconds,
            )

            notify_key = build_notification_key(
                rule=rule,
                process_name=process_name,
                category=category,
            )

            if notify_now and notify_key not in sent_notification_keys:
                message = rule.get("message", "Повернись до роботи.")
                full_message = (
                    f"{message}\n"
                    f"Process: {process_name}\n"
                    f"Category: {category}\n"
                    f"State: {activity_state}\n"
                    f"Window: {window_title or '[empty]'}\n"
                    f"Session: {format_seconds(current_session_seconds)}\n"
                    f"Daily total [{category}]: "
                    f"{format_seconds(daily_category_total_seconds)}"
                )

                notify(full_message)
                log_message(f"NOTIFY -> {full_message}")

                write_notification_event(
                    level="warning",
                    icon="⚠",
                    title=f"{category} limit reached",
                    message=message,
                    popup_expires_after_seconds=8,
                    badge_expires_after_seconds=3600,
                )

                sent_notification_keys.add(notify_key)

            now = time.time()
            if now - last_print_time >= LIVE_COUNTER_PRINT_INTERVAL_SECONDS:
                print_live_stats(counter, current_window_title=window_title)
                last_print_time = now

            time.sleep(CHECK_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        log_message("lazy_coach stopped by user")

    finally:
        if unknown_tracker is not None:
            unknown_tracker.shutdown()
            log_message("Unknown session flushed to database")

        counter.shutdown()
        log_message("Current session flushed to database")


if __name__ == "__main__":
    main()
