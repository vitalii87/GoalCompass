# gui/overlay_widget.py

from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from src.app_paths import APP_DIR, IS_FROZEN  # noqa: E402

ROOT_DIR = APP_DIR
CONTROL_PANEL_PATH = ROOT_DIR / "gui" / "control_panel.py"
from src.services.current_state_service import (  # noqa: E402
    is_current_state_stale,
    read_current_state,
)
from src.services.interaction_policy_service import (  # noqa: E402
    load_interaction_policy,
)
from src.services.notification_event_service import (  # noqa: E402
    NotificationEvent,
    is_badge_expired,
    is_popup_expired,
    read_notification_event,
)


STATUS_COLORS = {
    "positive": "#2ecc71",  # green
    "neutral": "#f1c40f",   # yellow
    "negative": "#e74c3c",  # red
    "idle": "#95a5a6",      # gray
    "stale": "#7f8c8d",     # darker gray
    "error": "#e74c3c",
}


NOTIFICATION_COLORS = {
    "warning": "#f1c40f",
    "success": "#2ecc71",
    "error": "#e74c3c",
    "info": "#95a5a6",
}


def format_seconds_as_hours_minutes(seconds: int) -> str:
    safe_seconds = max(int(seconds), 0)

    hours = safe_seconds // 3600
    minutes = (safe_seconds % 3600) // 60

    return f"{hours:02d}:{minutes:02d}"


def get_creation_flags() -> int:
    if sys.platform.startswith("win"):
        return subprocess.CREATE_NEW_PROCESS_GROUP

    return 0


class GoalCompassOverlay(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("GoalCompass")

        # Старий компактний стиль, лише трохи ширше під шестерню.
        self.geometry("210x44+1200+80")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self.configure(bg="#1e1e1e")

        self.drag_start_x = 0
        self.drag_start_y = 0

        self.last_popup_event_id: str | None = None
        self.active_popup: tk.Toplevel | None = None
        self.control_panel_process: subprocess.Popen | None = None

        self._build_layout()
        self._bind_drag()
        self.refresh_loop()

    def _build_layout(self) -> None:
        self.main_frame = tk.Frame(
            self,
            bg="#1e1e1e",
            padx=10,
            pady=6,
        )
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.clock_label = tk.Label(
            self.main_frame,
            text="--:--",
            font=("Segoe UI", 13, "bold"),
            fg="#ffffff",
            bg="#1e1e1e",
        )
        self.clock_label.pack(side=tk.LEFT)

        self.status_dot = tk.Label(
            self.main_frame,
            text="●",
            font=("Segoe UI", 16, "bold"),
            fg=STATUS_COLORS["stale"],
            bg="#1e1e1e",
        )
        self.status_dot.pack(side=tk.LEFT, padx=(18, 2))

        self.notification_badge = tk.Label(
            self.main_frame,
            text="",
            font=("Segoe UI", 11, "bold"),
            fg=NOTIFICATION_COLORS["warning"],
            bg="#1e1e1e",
            width=2,
        )
        self.notification_badge.pack(side=tk.LEFT, padx=(0, 2))

        self.status_timer_label = tk.Label(
            self.main_frame,
            text="--:--",
            font=("Segoe UI", 13, "bold"),
            fg="#ffffff",
            bg="#1e1e1e",
        )
        self.status_timer_label.pack(side=tk.LEFT)

        # Маленька шестерня, не ttk.Button, щоб не ламати висоту/лейаут.
        self.settings_label = tk.Label(
            self.main_frame,
            text="⚙",
            font=("Segoe UI", 10, "bold"),
            fg="#bdbdbd",
            bg="#1e1e1e",
            cursor="hand2",
            width=2,
        )
        self.settings_label.pack(side=tk.LEFT, padx=(8, 0))

        self.settings_label.bind(
            "<Button-1>",
            lambda _event: self.open_control_center(),
        )
        self.settings_label.bind("<Enter>", self.on_settings_hover)
        self.settings_label.bind("<Leave>", self.on_settings_leave)

    def _bind_drag(self) -> None:
        for widget in (
            self,
            self.main_frame,
            self.clock_label,
            self.status_dot,
            self.notification_badge,
            self.status_timer_label,
        ):
            widget.bind("<Button-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.drag_window)

    def on_settings_hover(self, _event: tk.Event) -> None:
        self.settings_label.config(fg="#ffffff")

    def on_settings_leave(self, _event: tk.Event) -> None:
        self.settings_label.config(fg="#bdbdbd")

    def start_drag(self, event: tk.Event) -> None:
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def drag_window(self, event: tk.Event) -> None:
        x = self.winfo_pointerx() - self.drag_start_x
        y = self.winfo_pointery() - self.drag_start_y
        self.geometry(f"+{x}+{y}")

    def open_control_center(self) -> None:
        if not CONTROL_PANEL_PATH.exists():
            self.show_simple_popup(
                title="Control Center not found",
                message=str(CONTROL_PANEL_PATH),
                level="error",
                icon="⚠",
            )
            return

        try:
            if (
                self.control_panel_process is not None
                and self.control_panel_process.poll() is None
            ):
                self.show_simple_popup(
                    title="Control Center",
                    message="Already running.",
                    level="info",
                    icon="⚙",
                )
                return

            command = (
                [sys.executable, "--component", "control-panel"]
                if IS_FROZEN
                else [sys.executable, str(CONTROL_PANEL_PATH)]
            )
            self.control_panel_process = subprocess.Popen(
                command,
                cwd=str(ROOT_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=get_creation_flags(),
            )

        except Exception as error:
            self.show_simple_popup(
                title="Failed to open Control Center",
                message=str(error),
                level="error",
                icon="⚠",
            )

    def refresh_loop(self) -> None:
        policy = load_interaction_policy()

        if policy.is_silent:
            self.withdraw()
            self.notification_badge.config(text="")
            self.after(3000, self.refresh_loop)
            return

        if self.state() == "withdrawn":
            self.deiconify()

        self.refresh_data()
        self.refresh_notification_event()

        # Mini overlay shows HH:MM, not seconds.
        # 3 seconds is enough and keeps UI very light.
        self.after(3000, self.refresh_loop)

    def refresh_data(self) -> None:
        self.clock_label.config(
            text=datetime.now().strftime("%H:%M")
        )

        try:
            state = read_current_state()
        except Exception:
            self.status_dot.config(fg=STATUS_COLORS["error"])
            self.status_timer_label.config(text="ERR")
            return

        if state is None:
            self.status_dot.config(fg=STATUS_COLORS["stale"])
            self.status_timer_label.config(text="--:--")
            return

        display_seconds = state.today_category_seconds

        if is_current_state_stale(state, stale_after_seconds=10):
            self.status_dot.config(fg=STATUS_COLORS["stale"])
            self.status_timer_label.config(text="--:--")
            return

        color = STATUS_COLORS.get(
            state.panel_status,
            STATUS_COLORS["neutral"],
        )

        self.status_dot.config(fg=color)

        if state.activity_state == "idle" or state.panel_status == "idle":
            self.status_timer_label.config(text="--:--")
        else:
            self.status_timer_label.config(
                text=format_seconds_as_hours_minutes(display_seconds)
            )

    def refresh_notification_event(self) -> None:
        policy = load_interaction_policy()

        if not policy.allows_warning:
            self.notification_badge.config(text="")
            return

        try:
            event = read_notification_event()
        except Exception:
            self.notification_badge.config(text="")
            return

        if event is None:
            self.notification_badge.config(text="")
            return

        if policy.allows_badge:
            self.update_notification_badge(event)
        else:
            self.notification_badge.config(text="")

        if policy.allows_popup:
            self.maybe_show_popup(event)

    def update_notification_badge(self, event: NotificationEvent) -> None:
        if is_badge_expired(event):
            self.notification_badge.config(text="")
            return

        color = NOTIFICATION_COLORS.get(
            event.level,
            NOTIFICATION_COLORS["info"],
        )

        self.notification_badge.config(
            text=event.icon,
            fg=color,
        )

    def maybe_show_popup(self, event: NotificationEvent) -> None:
        if is_popup_expired(event):
            return

        if self.last_popup_event_id == event.event_id:
            return

        self.last_popup_event_id = event.event_id
        self.show_popup(event)

    def show_simple_popup(
        self,
        title: str,
        message: str,
        level: str = "info",
        icon: str = "⚙",
    ) -> None:
        event = NotificationEvent(
            event_id=f"local_{datetime.now().timestamp()}",
            created_at=datetime.now().isoformat(sep=" ", timespec="seconds"),
            level=level,
            icon=icon,
            title=title,
            message=message,
            popup_expires_after_seconds=3,
            badge_expires_after_seconds=0,
        )
        self.show_popup(event)

    def show_popup(self, event: NotificationEvent) -> None:
        self.close_popup()

        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg="#252525")

        self.active_popup = popup

        color = NOTIFICATION_COLORS.get(
            event.level,
            NOTIFICATION_COLORS["info"],
        )

        outer = tk.Frame(
            popup,
            bg="#252525",
            padx=12,
            pady=10,
            highlightthickness=1,
            highlightbackground=color,
        )
        outer.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(outer, bg="#252525")
        header.pack(fill=tk.X)

        icon_label = tk.Label(
            header,
            text=event.icon,
            font=("Segoe UI", 14, "bold"),
            fg=color,
            bg="#252525",
        )
        icon_label.pack(side=tk.LEFT)

        title_label = tk.Label(
            header,
            text=event.title,
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg="#252525",
            anchor=tk.W,
        )
        title_label.pack(side=tk.LEFT, padx=(8, 0))

        message_label = tk.Label(
            outer,
            text=event.message,
            font=("Segoe UI", 9),
            fg="#dddddd",
            bg="#252525",
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=260,
        )
        message_label.pack(fill=tk.X, pady=(6, 0))

        self.update_idletasks()

        overlay_x = self.winfo_x()
        overlay_y = self.winfo_y()

        popup_width = 310
        popup_height = 86

        popup_x = max(10, overlay_x - popup_width + self.winfo_width())
        popup_y = overlay_y + self.winfo_height() + 8

        popup.geometry(f"{popup_width}x{popup_height}+{popup_x}+{popup_y}")

        popup.after(
            event.popup_expires_after_seconds * 1000,
            self.close_popup,
        )

    def close_popup(self) -> None:
        if self.active_popup is None:
            return

        try:
            self.active_popup.destroy()
        except tk.TclError:
            pass

        self.active_popup = None


def main() -> None:
    app = GoalCompassOverlay()
    app.mainloop()


if __name__ == "__main__":
    main()
