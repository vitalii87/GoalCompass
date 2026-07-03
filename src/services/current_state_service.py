# src/services/current_state_service.py

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.services.panel_status_service import category_to_panel_status


ROOT_DIR = Path(__file__).resolve().parents[2]
RUNTIME_DIR = ROOT_DIR / "data" / "runtime"
CURRENT_STATE_PATH = RUNTIME_DIR / "current_state.json"


@dataclass(frozen=True)
class CurrentState:
    updated_at: str
    process_name: str
    window_title: str
    category: str
    activity_state: str
    panel_status: str

    # Поточна безперервна сесія.
    session_seconds: int

    # Сумарний час за сьогодні в поточній категорії.
    # Саме це показує mini overlay.
    today_category_seconds: int


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def ensure_runtime_dir() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def build_state(
    process_name: str,
    window_title: str,
    category: str,
    activity_state: str,
    session_seconds: int,
    today_category_seconds: int,
) -> CurrentState:
    panel_status = category_to_panel_status(
        category=category,
        activity_state=activity_state,
    )

    return CurrentState(
        updated_at=now_iso(),
        process_name=process_name,
        window_title=window_title,
        category=category,
        activity_state=activity_state,
        panel_status=panel_status,
        session_seconds=max(int(session_seconds), 0),
        today_category_seconds=max(int(today_category_seconds), 0),
    )


def write_json_with_retry(
    path: Path,
    data: dict[str, Any],
    retries: int = 5,
    delay_seconds: float = 0.05,
) -> bool:
    """
    Robust JSON write for Windows.

    On Windows, os.replace / Path.replace may fail with PermissionError
    if another process is reading the target file at the same moment,
    or if antivirus/indexer briefly locks it.

    This function retries a few times and then gives up silently.
    The tracker must never crash just because live-state write failed once.
    """
    ensure_runtime_dir()

    json_text = json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
    )

    last_error: Exception | None = None

    for attempt in range(retries):
        temp_path = path.with_name(
            f"{path.stem}.{os.getpid()}.{int(time.time() * 1000)}.{attempt}.tmp"
        )

        try:
            temp_path.write_text(json_text, encoding="utf-8")

            # os.replace is atomic when possible, but can still fail on Windows
            # if the destination is temporarily locked.
            os.replace(temp_path, path)

            return True

        except PermissionError as error:
            last_error = error

            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass

            time.sleep(delay_seconds)

        except OSError as error:
            last_error = error

            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass

            time.sleep(delay_seconds)

    # Fallback: do not crash tracker.
    # The overlay will just keep the previous state until the next successful write.
    if last_error is not None:
        print(
            f"[current_state_service] Failed to write current state: {last_error}",
            flush=True,
        )

    return False


def write_current_state(
    process_name: str,
    window_title: str,
    category: str,
    activity_state: str,
    session_seconds: int,
    today_category_seconds: int,
) -> CurrentState:
    state = build_state(
        process_name=process_name,
        window_title=window_title,
        category=category,
        activity_state=activity_state,
        session_seconds=session_seconds,
        today_category_seconds=today_category_seconds,
    )

    write_json_with_retry(
        path=CURRENT_STATE_PATH,
        data=asdict(state),
    )

    return state


def read_current_state() -> CurrentState | None:
    if not CURRENT_STATE_PATH.exists():
        return None

    try:
        with CURRENT_STATE_PATH.open("r", encoding="utf-8") as file:
            data: Any = json.load(file)

        if not isinstance(data, dict):
            return None

        session_seconds = int(data.get("session_seconds", 0))

        return CurrentState(
            updated_at=str(data.get("updated_at", "")),
            process_name=str(data.get("process_name", "")),
            window_title=str(data.get("window_title", "")),
            category=str(data.get("category", "unknown")),
            activity_state=str(data.get("activity_state", "active")),
            panel_status=str(data.get("panel_status", "neutral")),
            session_seconds=session_seconds,
            today_category_seconds=int(
                data.get(
                    "today_category_seconds",
                    session_seconds,
                )
            ),
        )

    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return None


def is_current_state_stale(
    state: CurrentState,
    stale_after_seconds: int = 10,
) -> bool:
    try:
        updated_at = datetime.fromisoformat(state.updated_at)
    except ValueError:
        return True

    age_seconds = (datetime.now() - updated_at).total_seconds()

    return age_seconds > stale_after_seconds
