# src/storage/db.py

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict


class SQLiteStorage:
    """
    SQLite storage:
    - initialize database
    - migrate schema if needed
    - write activity chunks
    - read daily totals
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity_date TEXT NOT NULL,
                    process_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    activity_state TEXT NOT NULL DEFAULT 'active',
                    seconds INTEGER NOT NULL CHECK(seconds >= 0),
                    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
                )
                """
            )
            conn.commit()

            self._migrate_add_activity_state_if_needed(conn)

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_activity_logs_date
                ON activity_logs(activity_date)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_activity_logs_date_category
                ON activity_logs(activity_date, category)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_activity_logs_date_process
                ON activity_logs(activity_date, process_name)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_activity_logs_date_state
                ON activity_logs(activity_date, activity_state)
                """
            )
            conn.commit()

    def _migrate_add_activity_state_if_needed(self, conn: sqlite3.Connection) -> None:
        columns = conn.execute("PRAGMA table_info(activity_logs)").fetchall()
        column_names = {row["name"] for row in columns}

        if "activity_state" not in column_names:
            conn.execute(
                """
                ALTER TABLE activity_logs
                ADD COLUMN activity_state TEXT NOT NULL DEFAULT 'active'
                """
            )
            conn.commit()

    def log_activity(
            self,
            activity_date: str,
            process_name: str,
            category: str,
            activity_state: str,
            seconds: int,
    ) -> None:
        if seconds <= 0:
            return

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO activity_logs (
                    activity_date,
                    process_name,
                    category,
                    activity_state,
                    seconds,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
                """,
                (activity_date, process_name, category, activity_state, seconds),
            )
            conn.commit()

    def get_daily_totals_by_category(self, activity_date: str) -> Dict[str, int]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT category, COALESCE(SUM(seconds), 0) AS total_seconds
                FROM activity_logs
                WHERE activity_date = ?
                GROUP BY category
                """,
                (activity_date,),
            ).fetchall()

        return {row["category"]: int(row["total_seconds"]) for row in rows}

    def get_daily_totals_by_process(self, activity_date: str) -> Dict[str, int]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT process_name, COALESCE(SUM(seconds), 0) AS total_seconds
                FROM activity_logs
                WHERE activity_date = ?
                GROUP BY process_name
                """,
                (activity_date,),
            ).fetchall()

        return {row["process_name"]: int(row["total_seconds"]) for row in rows}

    def get_daily_totals_by_state(self, activity_date: str) -> Dict[str, int]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT activity_state, COALESCE(SUM(seconds), 0) AS total_seconds
                FROM activity_logs
                WHERE activity_date = ?
                GROUP BY activity_state
                """,
                (activity_date,),
            ).fetchall()

        return {row["activity_state"]: int(row["total_seconds"]) for row in rows}

    def get_category_total(self, activity_date: str, category: str) -> int:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(seconds), 0) AS total_seconds
                FROM activity_logs
                WHERE activity_date = ? AND category = ?
                """,
                (activity_date, category),
            ).fetchone()

        return int(row["total_seconds"]) if row else 0

    def get_process_total(self, activity_date: str, process_name: str) -> int:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(seconds), 0) AS total_seconds
                FROM activity_logs
                WHERE activity_date = ? AND process_name = ?
                """,
                (activity_date, process_name),
            ).fetchone()

        return int(row["total_seconds"]) if row else 0

    def get_all_totals_for_date(self, activity_date: str) -> Dict[str, Dict[str, int]]:
        return {
            "by_category": self.get_daily_totals_by_category(activity_date),
            "by_process": self.get_daily_totals_by_process(activity_date),
            "by_state": self.get_daily_totals_by_state(activity_date),
        }