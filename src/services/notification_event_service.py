# src/services/notification_event_service.py

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
RUNTIME_DIR = ROOT_DIR / "data" / "runtime"
NOTIFICATION_EVENT_PATH = RUNTIME_DIR / "notification_event.json"


@dataclass(frozen=True)
class NotificationEvent:
    event_id: str
    created_at: str
    level: str
    icon: str
    title: str
    message: str
    popup_expires_after_seconds: int
    badge_expires_after_seconds: int


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def ensure_runtime_dir() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def parse_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def get_event_age_seconds(event: NotificationEvent) -> int:
    created_at = parse_datetime(event.created_at)

    if created_at is None:
        return 999999

    return int((datetime.now() - created_at).total_seconds())


def is_popup_expired(event: NotificationEvent) -> bool:
    return get_event_age_seconds(event) > event.popup_expires_after_seconds


def is_badge_expired(event: NotificationEvent) -> bool:
    return get_event_age_seconds(event) > event.badge_expires_after_seconds


def build_notification_event(
    level: str,
    title: str,
    message: str,
    icon: str | None = None,
    popup_expires_after_seconds: int = 8,
    badge_expires_after_seconds: int = 3600,
) -> NotificationEvent:
    normalized_level = level.strip().lower()

    if icon is None:
        if normalized_level == "warning":
            icon = "⚠"
        elif normalized_level == "success":
            icon = "✓"
        elif normalized_level == "error":
            icon = "!"
        else:
            icon = "•"

    return NotificationEvent(
        event_id=f"{now_iso()}_{uuid.uuid4().hex[:8]}",
        created_at=now_iso(),
        level=normalized_level,
        icon=icon,
        title=title.strip(),
        message=message.strip(),
        popup_expires_after_seconds=max(int(popup_expires_after_seconds), 1),
        badge_expires_after_seconds=max(int(badge_expires_after_seconds), 1),
    )


def validate_json_text(json_text: str) -> bool:
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return False

    if not isinstance(data, dict):
        return False

    required_keys = {
        "event_id",
        "created_at",
        "level",
        "icon",
        "title",
        "message",
        "popup_expires_after_seconds",
        "badge_expires_after_seconds",
    }

    return required_keys.issubset(set(data.keys()))


def write_json_with_retry(
    path: Path,
    data: dict[str, Any],
    retries: int = 5,
    delay_seconds: float = 0.05,
) -> bool:
    ensure_runtime_dir()

    json_text = json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
    )

    if not validate_json_text(json_text):
        return False

    last_error: Exception | None = None

    for attempt in range(retries):
        temp_path = path.with_name(
            f"{path.stem}.{os.getpid()}.{int(time.time() * 1000)}.{attempt}.tmp"
        )

        try:
            temp_path.write_text(json_text, encoding="utf-8")

            # Validate tmp file before replacing the public file.
            temp_text = temp_path.read_text(encoding="utf-8")
            if not validate_json_text(temp_text):
                try:
                    temp_path.unlink()
                except OSError:
                    pass
                return False

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

    if last_error is not None:
        print(
            f"[notification_event_service] Failed to write notification event: "
            f"{last_error}",
            flush=True,
        )

    return False


def write_notification_event(
    level: str,
    title: str,
    message: str,
    icon: str | None = None,
    popup_expires_after_seconds: int = 8,
    badge_expires_after_seconds: int = 3600,
) -> NotificationEvent:
    event = build_notification_event(
        level=level,
        title=title,
        message=message,
        icon=icon,
        popup_expires_after_seconds=popup_expires_after_seconds,
        badge_expires_after_seconds=badge_expires_after_seconds,
    )

    write_json_with_retry(
        path=NOTIFICATION_EVENT_PATH,
        data=asdict(event),
    )

    return event


def read_notification_event() -> NotificationEvent | None:
    if not NOTIFICATION_EVENT_PATH.exists():
        return None

    try:
        data: Any = json.loads(
            NOTIFICATION_EVENT_PATH.read_text(encoding="utf-8")
        )

        if not isinstance(data, dict):
            return None

        return NotificationEvent(
            event_id=str(data.get("event_id", "")),
            created_at=str(data.get("created_at", "")),
            level=str(data.get("level", "info")),
            icon=str(data.get("icon", "•")),
            title=str(data.get("title", "")),
            message=str(data.get("message", "")),
            popup_expires_after_seconds=int(
                data.get("popup_expires_after_seconds", 8)
            ),
            badge_expires_after_seconds=int(
                data.get("badge_expires_after_seconds", 3600)
            ),
        )

    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return None
