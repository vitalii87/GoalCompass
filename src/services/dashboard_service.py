# src/services/dashboard_service.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from src.services.current_state_service import (
    CurrentState,
    is_current_state_stale,
    read_current_state,
)
from src.services.goal_progress_service import (
    build_goal_progress_day_view,
    format_seconds,
)
from src.services.panel_status_service import (
    PanelStatusTotals,
    get_panel_status_totals,
)


@dataclass(frozen=True)
class DashboardGoalProgress:
    goal_id: str
    title: str
    goal_type: str
    today_seconds: int
    week_seconds: int
    target_seconds: int
    limit_seconds: int
    status: str
    message: str


@dataclass(frozen=True)
class DashboardWarning:
    warning_type: str
    message: str


@dataclass(frozen=True)
class DashboardView:
    activity_date: str
    week_start_date: str
    week_end_date: str
    current_state: CurrentState | None
    current_state_stale: bool
    panel_totals_today: PanelStatusTotals
    goals: list[DashboardGoalProgress]
    warnings: list[DashboardWarning]


def today_iso() -> str:
    return date.today().isoformat()


def parse_date(value: str | None) -> date:
    if not value:
        return date.today()

    return datetime.strptime(value, "%Y-%m-%d").date()


def get_week_start(target_date: date) -> date:
    # Monday as week start.
    return target_date - timedelta(days=target_date.weekday())


def get_week_dates(target_date: date) -> list[date]:
    week_start = get_week_start(target_date)
    return [week_start + timedelta(days=offset) for offset in range(7)]


def safe_get_attr(obj: Any, names: list[str], default: Any = None) -> Any:
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)

    if isinstance(obj, dict):
        for name in names:
            if name in obj:
                return obj[name]

    return default


def extract_goal_results(day_view: Any) -> list[Any]:
    possible_names = [
        "results",
        "goals",
        "goal_results",
        "progress_results",
        "items",
    ]

    value = safe_get_attr(day_view, possible_names, default=[])

    if isinstance(value, list):
        return value

    return []


def goal_result_to_dict(result: Any) -> dict[str, Any]:
    goal_id = str(
        safe_get_attr(
            result,
            ["goal_id", "id"],
            "unknown_goal",
        )
    )

    title = str(
        safe_get_attr(
            result,
            ["title", "goal_title", "name"],
            goal_id,
        )
    )

    goal_type = str(
        safe_get_attr(
            result,
            ["goal_type", "type"],
            "target",
        )
    )

    total_seconds = int(
        safe_get_attr(
            result,
            ["total_seconds", "seconds", "progress_seconds"],
            0,
        )
        or 0
    )

    target_seconds = int(
        safe_get_attr(
            result,
            ["target_seconds", "target"],
            0,
        )
        or 0
    )

    limit_seconds = int(
        safe_get_attr(
            result,
            ["limit_seconds", "limit"],
            0,
        )
        or 0
    )

    return {
        "goal_id": goal_id,
        "title": title,
        "goal_type": goal_type,
        "total_seconds": total_seconds,
        "target_seconds": target_seconds,
        "limit_seconds": limit_seconds,
    }


def get_goal_progress_for_date(activity_date: str) -> list[dict[str, Any]]:
    day_view = build_goal_progress_day_view(activity_date)
    results = extract_goal_results(day_view)

    return [goal_result_to_dict(result) for result in results]


def get_week_goal_totals(target_date: date) -> dict[str, int]:
    totals: dict[str, int] = {}

    for day in get_week_dates(target_date):
        day_results = get_goal_progress_for_date(day.isoformat())

        for result in day_results:
            goal_id = result["goal_id"]
            totals[goal_id] = totals.get(goal_id, 0) + int(
                result.get("total_seconds", 0)
            )

    return totals


def build_goal_status(
    goal_type: str,
    today_seconds: int,
    week_seconds: int,
    target_seconds: int,
    limit_seconds: int,
) -> tuple[str, str]:
    normalized_type = goal_type.lower().strip()

    if normalized_type == "limit" or limit_seconds > 0:
        if limit_seconds <= 0:
            return "info", "Limit goal has no limit_seconds configured."

        ratio = today_seconds / limit_seconds

        if today_seconds >= limit_seconds:
            return (
                "exceeded",
                f"Limit exceeded today: {format_seconds(today_seconds)} / "
                f"{format_seconds(limit_seconds)}",
            )

        if ratio >= 0.8:
            return (
                "warning",
                f"Close to daily limit: {format_seconds(today_seconds)} / "
                f"{format_seconds(limit_seconds)}",
            )

        return (
            "ok",
            f"Within limit: {format_seconds(today_seconds)} / "
            f"{format_seconds(limit_seconds)}",
        )

    if target_seconds <= 0:
        return "info", f"Progress today: {format_seconds(today_seconds)}"

    ratio = today_seconds / target_seconds

    if today_seconds >= target_seconds:
        return (
            "done",
            f"Target reached today: {format_seconds(today_seconds)} / "
            f"{format_seconds(target_seconds)}",
        )

    if ratio >= 0.5:
        return (
            "progress",
            f"Good progress today: {format_seconds(today_seconds)} / "
            f"{format_seconds(target_seconds)}",
        )

    return (
        "behind",
        f"Low progress today: {format_seconds(today_seconds)} / "
        f"{format_seconds(target_seconds)}",
    )


def build_dashboard_goals(target_date: date) -> list[DashboardGoalProgress]:
    today_results = get_goal_progress_for_date(target_date.isoformat())
    week_totals = get_week_goal_totals(target_date)

    dashboard_goals: list[DashboardGoalProgress] = []

    for result in today_results:
        goal_id = result["goal_id"]
        title = result["title"]
        goal_type = result["goal_type"]
        today_seconds = int(result["total_seconds"])
        week_seconds = int(week_totals.get(goal_id, today_seconds))
        target_seconds = int(result["target_seconds"])
        limit_seconds = int(result["limit_seconds"])

        status, message = build_goal_status(
            goal_type=goal_type,
            today_seconds=today_seconds,
            week_seconds=week_seconds,
            target_seconds=target_seconds,
            limit_seconds=limit_seconds,
        )

        dashboard_goals.append(
            DashboardGoalProgress(
                goal_id=goal_id,
                title=title,
                goal_type=goal_type,
                today_seconds=today_seconds,
                week_seconds=week_seconds,
                target_seconds=target_seconds,
                limit_seconds=limit_seconds,
                status=status,
                message=message,
            )
        )

    return dashboard_goals


def build_dashboard_warnings(
    current_state: CurrentState | None,
    current_state_stale: bool,
    panel_totals_today: PanelStatusTotals,
    goals: list[DashboardGoalProgress],
) -> list[DashboardWarning]:
    warnings: list[DashboardWarning] = []

    if current_state is None:
        warnings.append(
            DashboardWarning(
                warning_type="tracker",
                message="No current state found. Tracker may not be running.",
            )
        )
    elif current_state_stale:
        warnings.append(
            DashboardWarning(
                warning_type="tracker",
                message="Current state is stale. Tracker may be stopped or frozen.",
            )
        )

    if panel_totals_today.negative_seconds >= 3600:
        warnings.append(
            DashboardWarning(
                warning_type="time_wasting",
                message=(
                    "Time-wasting is already over 1 hour today: "
                    f"{format_seconds(panel_totals_today.negative_seconds)}"
                ),
            )
        )

    for goal in goals:
        if goal.status in {"warning", "exceeded", "behind"}:
            warnings.append(
                DashboardWarning(
                    warning_type=f"goal:{goal.goal_id}",
                    message=f"{goal.title}: {goal.message}",
                )
            )

    return warnings


def build_dashboard_view(
    activity_date: str | None = None,
) -> DashboardView:
    target_date = parse_date(activity_date)
    resolved_date = target_date.isoformat()

    week_start = get_week_start(target_date)
    week_end = week_start + timedelta(days=6)

    current_state = read_current_state()
    current_state_stale = False

    if current_state is not None:
        current_state_stale = is_current_state_stale(
            current_state,
            stale_after_seconds=10,
        )

    panel_totals_today = get_panel_status_totals(resolved_date)
    goals = build_dashboard_goals(target_date)

    warnings = build_dashboard_warnings(
        current_state=current_state,
        current_state_stale=current_state_stale,
        panel_totals_today=panel_totals_today,
        goals=goals,
    )

    return DashboardView(
        activity_date=resolved_date,
        week_start_date=week_start.isoformat(),
        week_end_date=week_end.isoformat(),
        current_state=current_state,
        current_state_stale=current_state_stale,
        panel_totals_today=panel_totals_today,
        goals=goals,
        warnings=warnings,
    )