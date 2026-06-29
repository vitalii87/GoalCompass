# src/services/manual_activity_service.py

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "data" / "lazy_coach.db"
PRESETS_PATH = ROOT_DIR / "data" / "user_config" / "manual_presets.json"


@dataclass(frozen=True)
class ManualActivityPreset:
    preset_id: str
    goal_id: str
    title: str
    category: str
    seconds: int


@dataclass(frozen=True)
class ManualActivityEntry:
    id: int
    activity_date: str
    goal_id: str
    category: str
    title: str
    seconds: int
    note: str
    source: str
    created_at: str


@dataclass(frozen=True)
class ManualActivityInput:
    activity_date: str
    goal_id: str
    category: str
    title: str
    seconds: int
    note: str = ""
    source: str = "manual"


def today_iso() -> str:
    return date.today().isoformat()


def format_seconds(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def ensure_manual_activity_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS manual_activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_date TEXT NOT NULL,
            goal_id TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            seconds INTEGER NOT NULL CHECK(seconds >= 0),
            note TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_manual_activity_logs_date
        ON manual_activity_logs(activity_date)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_manual_activity_logs_goal
        ON manual_activity_logs(goal_id)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_manual_activity_logs_date_goal
        ON manual_activity_logs(activity_date, goal_id)
        """
    )

    conn.commit()


def load_raw_presets() -> list[dict[str, Any]]:
    if not PRESETS_PATH.exists():
        return []

    with PRESETS_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("manual_presets.json must contain a list")

    return [item for item in data if isinstance(item, dict)]


def raw_preset_to_model(item: dict[str, Any]) -> ManualActivityPreset | None:
    preset_id = item.get("preset_id")
    goal_id = item.get("goal_id")
    title = item.get("title")
    seconds = item.get("seconds")

    if not isinstance(preset_id, str):
        return None

    if not isinstance(goal_id, str):
        return None

    if not isinstance(title, str):
        return None

    if not isinstance(seconds, int):
        return None

    return ManualActivityPreset(
        preset_id=preset_id,
        goal_id=goal_id,
        title=title,
        category=str(item.get("category", "manual")),
        seconds=seconds,
    )


def load_presets() -> list[ManualActivityPreset]:
    raw_items = load_raw_presets()
    presets: list[ManualActivityPreset] = []

    for item in raw_items:
        preset = raw_preset_to_model(item)

        if preset is not None:
            presets.append(preset)

    return presets


def find_preset(preset_id: str) -> ManualActivityPreset | None:
    for preset in load_presets():
        if preset.preset_id == preset_id:
            return preset

    return None


def row_to_manual_activity_entry(row: sqlite3.Row) -> ManualActivityEntry:
    return ManualActivityEntry(
        id=int(row["id"]),
        activity_date=str(row["activity_date"]),
        goal_id=str(row["goal_id"]),
        category=str(row["category"]),
        title=str(row["title"]),
        seconds=int(row["seconds"]),
        note=str(row["note"] or ""),
        source=str(row["source"]),
        created_at=str(row["created_at"]),
    )


def add_manual_activity(activity: ManualActivityInput) -> ManualActivityEntry:
    if activity.seconds <= 0:
        raise ValueError("seconds must be greater than 0")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ensure_manual_activity_table(conn)

        cursor = conn.execute(
            """
            INSERT INTO manual_activity_logs (
                activity_date,
                goal_id,
                category,
                title,
                seconds,
                note,
                source,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """,
            (
                activity.activity_date,
                activity.goal_id,
                activity.category,
                activity.title,
                activity.seconds,
                activity.note,
                activity.source,
            ),
        )

        entry_id = int(cursor.lastrowid)
        conn.commit()

        row = conn.execute(
            """
            SELECT
                id,
                activity_date,
                goal_id,
                category,
                title,
                seconds,
                note,
                source,
                created_at
            FROM manual_activity_logs
            WHERE id = ?
            """,
            (entry_id,),
        ).fetchone()

    if row is None:
        raise RuntimeError("Manual activity was inserted but could not be loaded")

    return row_to_manual_activity_entry(row)


def add_manual_activity_from_preset(
    preset_id: str,
    activity_date: str | None = None,
    note: str = "",
) -> ManualActivityEntry:
    preset = find_preset(preset_id)

    if preset is None:
        raise ValueError(f"Preset not found: {preset_id}")

    return add_manual_activity(
        ManualActivityInput(
            activity_date=activity_date or today_iso(),
            goal_id=preset.goal_id,
            category=preset.category,
            title=preset.title,
            seconds=preset.seconds,
            note=note,
            source="manual",
        )
    )


def list_manual_activities(
    activity_date: str | None = None,
    limit: int = 50,
) -> list[ManualActivityEntry]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ensure_manual_activity_table(conn)

        if activity_date:
            rows = conn.execute(
                """
                SELECT
                    id,
                    activity_date,
                    goal_id,
                    category,
                    title,
                    seconds,
                    note,
                    source,
                    created_at
                FROM manual_activity_logs
                WHERE activity_date = ?
                ORDER BY activity_date DESC, id DESC
                """,
                (activity_date,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT
                    id,
                    activity_date,
                    goal_id,
                    category,
                    title,
                    seconds,
                    note,
                    source,
                    created_at
                FROM manual_activity_logs
                ORDER BY activity_date DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    return [row_to_manual_activity_entry(row) for row in rows]


def get_manual_activity_by_id(entry_id: int) -> ManualActivityEntry | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ensure_manual_activity_table(conn)

        row = conn.execute(
            """
            SELECT
                id,
                activity_date,
                goal_id,
                category,
                title,
                seconds,
                note,
                source,
                created_at
            FROM manual_activity_logs
            WHERE id = ?
            """,
            (entry_id,),
        ).fetchone()

    if row is None:
        return None

    return row_to_manual_activity_entry(row)


def delete_manual_activity(entry_id: int) -> ManualActivityEntry | None:
    entry = get_manual_activity_by_id(entry_id)

    if entry is None:
        return None

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ensure_manual_activity_table(conn)

        conn.execute(
            """
            DELETE FROM manual_activity_logs
            WHERE id = ?
            """,
            (entry_id,),
        )

        conn.commit()

    return entry


def get_manual_total_for_goal(
    activity_date: str,
    goal_id: str,
) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ensure_manual_activity_table(conn)

        row = conn.execute(
            """
            SELECT COALESCE(SUM(seconds), 0) AS total_seconds
            FROM manual_activity_logs
            WHERE activity_date = ?
              AND goal_id = ?
            """,
            (
                activity_date,
                goal_id,
            ),
        ).fetchone()

    if row is None:
        return 0

    return int(row["total_seconds"] or 0)