# src/tools/unknown_report.py

from __future__ import annotations

from src.config.config import DB_PATH
from src.storage.db import SQLiteStorage


def format_seconds(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def main() -> None:
    storage = SQLiteStorage(DB_PATH)
    rows = storage.get_top_unknown_titles(limit=20)

    print("=" * 80)
    print("TOP UNKNOWN CANDIDATES")
    print("=" * 80)

    if not rows:
        print("No unknown candidates found.")
        return

    for index, row in enumerate(rows, start=1):
        print(
            f"{index}. {row['process_name']} | "
            f"{format_seconds(int(row['total_seconds']))} | "
            f"seen={row['times_seen']}"
        )
        print(f"   title: {row['window_title']}")
        print(f"   first_seen: {row['first_seen']}")
        print(f"   last_seen:  {row['last_seen']}")
        print("-" * 80)


if __name__ == "__main__":
    main()