# gui/overlay_widget.py

from __future__ import annotations

import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from src.services.panel_status_service import (
    format_seconds_clock,
    get_current_panel_status,
    today_iso,
)


STATUS_COLORS = {
    "positive": "#2ecc71",  # green
    "neutral": "#f1c40f",   # yellow
    "negative": "#e74c3c",  # red
    "idle": "#95a5a6",      # gray
}


class GoalCompassOverlay(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("GoalCompass")

        self.geometry("170x44+1200+80")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self.configure(bg="#1e1e1e")

        self.drag_start_x = 0
        self.drag_start_y = 0

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
            fg=STATUS_COLORS["idle"],
            bg="#1e1e1e",
        )
        self.status_dot.pack(side=tk.LEFT, padx=(18, 4))

        self.status_timer_label = tk.Label(
            self.main_frame,
            text="00:00",
            font=("Segoe UI", 13, "bold"),
            fg="#ffffff",
            bg="#1e1e1e",
        )
        self.status_timer_label.pack(side=tk.LEFT)

    def _bind_drag(self) -> None:
        for widget in (
            self,
            self.main_frame,
            self.clock_label,
            self.status_dot,
            self.status_timer_label,
        ):
            widget.bind("<Button-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.drag_window)

    def start_drag(self, event: tk.Event) -> None:
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def drag_window(self, event: tk.Event) -> None:
        x = self.winfo_pointerx() - self.drag_start_x
        y = self.winfo_pointery() - self.drag_start_y
        self.geometry(f"+{x}+{y}")

    def refresh_loop(self) -> None:
        self.refresh_data()
        self.after(1000, self.refresh_loop)

    def refresh_data(self) -> None:
        self.clock_label.config(
            text=datetime.now().strftime("%H:%M")
        )

        try:
            current = get_current_panel_status(today_iso())
        except Exception:
            self.status_dot.config(fg=STATUS_COLORS["negative"])
            self.status_timer_label.config(text="ERR")
            return

        if current is None:
            self.status_dot.config(fg=STATUS_COLORS["idle"])
            self.status_timer_label.config(text="00:00")
            return

        color = STATUS_COLORS.get(
            current.panel_status,
            STATUS_COLORS["neutral"],
        )

        self.status_dot.config(fg=color)
        self.status_timer_label.config(
            text=format_seconds_clock(current.seconds)
        )


def main() -> None:
    app = GoalCompassOverlay()
    app.mainloop()


if __name__ == "__main__":
    main()
