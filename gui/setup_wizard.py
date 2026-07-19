# gui/setup_wizard.py

from __future__ import annotations

import calendar
import json
import re
import sys
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.services.goal_profile_service import (  # noqa: E402
    MAX_LIMITS_PER_GOAL,
    MAX_MAIN_GOALS,
    MAX_SUBGOALS_PER_GOAL,
    build_ai_assisted_prompt,
    create_profile_from_manual_goals,
    get_goal_templates,
    parse_goal_profile_json,
    save_goal_profile,
    validate_goal_profile,
)
from src.services.settings_service import load_settings, save_settings  # noqa: E402


def normalize_date_input(value: str) -> str:
    """
    Accepts:
        2027-03-01
        2027.03.01
        2027/03/01
        01.03.2027
        01-03-2027
        01/03/2027

    Returns:
        YYYY-MM-DD

    Empty or invalid value returns original stripped value.
    """
    raw = value.strip()

    if not raw:
        return ""

    patterns = [
        "%Y-%m-%d",
        "%Y.%m.%d",
        "%Y/%m/%d",
        "%d.%m.%Y",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ]

    for date_format in patterns:
        try:
            parsed = datetime.strptime(raw, date_format)
            return parsed.strftime("%Y-%m-%d")
        except Exception:
            pass

    normalized = re.sub(r"[./]", "-", raw)

    try:
        parsed = datetime.strptime(normalized, "%Y-%m-%d")
        return parsed.strftime("%Y-%m-%d")
    except Exception:
        return raw


class DatePicker(tk.Toplevel):
    def __init__(self, parent: tk.Widget, target_var: tk.StringVar) -> None:
        super().__init__(parent)

        self.target_var = target_var

        self.title("Choose date")
        self.geometry("320x300")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        today = date.today()

        current_value = normalize_date_input(target_var.get())

        try:
            parsed = datetime.strptime(current_value, "%Y-%m-%d").date()
            self.year = parsed.year
            self.month = parsed.month
        except Exception:
            self.year = today.year
            self.month = today.month

        self.header = ttk.Frame(self, padding=8)
        self.header.pack(fill="x")

        ttk.Button(
            self.header,
            text="‹",
            width=3,
            command=self.previous_month,
        ).pack(side="left")

        self.title_label = ttk.Label(
            self.header,
            text="",
            font=("Segoe UI", 11, "bold"),
            anchor="center",
        )
        self.title_label.pack(side="left", fill="x", expand=True)

        ttk.Button(
            self.header,
            text="›",
            width=3,
            command=self.next_month,
        ).pack(side="right")

        self.days_frame = ttk.Frame(self, padding=(8, 0, 8, 8))
        self.days_frame.pack(fill="both", expand=True)

        bottom = ttk.Frame(self, padding=(8, 0, 8, 8))
        bottom.pack(fill="x")

        ttk.Button(
            bottom,
            text="Today",
            command=self.select_today,
        ).pack(side="left")

        ttk.Button(
            bottom,
            text="Clear",
            command=self.clear_date,
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            bottom,
            text="Cancel",
            command=self.destroy,
        ).pack(side="right")

        self.render_calendar()

    def render_calendar(self) -> None:
        for widget in self.days_frame.winfo_children():
            widget.destroy()

        self.title_label.config(text=f"{calendar.month_name[self.month]} {self.year}")

        week_days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

        for col, day_name in enumerate(week_days):
            ttk.Label(
                self.days_frame,
                text=day_name,
                anchor="center",
                font=("Segoe UI", 9, "bold"),
            ).grid(row=0, column=col, sticky="nsew", padx=2, pady=2)

        month_calendar = calendar.monthcalendar(self.year, self.month)

        for row_index, week in enumerate(month_calendar, start=1):
            for col_index, day_number in enumerate(week):
                if day_number == 0:
                    ttk.Label(self.days_frame, text="").grid(
                        row=row_index,
                        column=col_index,
                        sticky="nsew",
                        padx=2,
                        pady=2,
                    )
                    continue

                ttk.Button(
                    self.days_frame,
                    text=str(day_number),
                    width=4,
                    command=lambda d=day_number: self.select_day(d),
                ).grid(
                    row=row_index,
                    column=col_index,
                    sticky="nsew",
                    padx=2,
                    pady=2,
                )

        for col in range(7):
            self.days_frame.columnconfigure(col, weight=1)

    def previous_month(self) -> None:
        self.month -= 1

        if self.month < 1:
            self.month = 12
            self.year -= 1

        self.render_calendar()

    def next_month(self) -> None:
        self.month += 1

        if self.month > 12:
            self.month = 1
            self.year += 1

        self.render_calendar()

    def select_day(self, day_number: int) -> None:
        selected = date(self.year, self.month, day_number)
        self.target_var.set(selected.strftime("%Y-%m-%d"))
        self.destroy()

    def select_today(self) -> None:
        self.target_var.set(date.today().strftime("%Y-%m-%d"))
        self.destroy()

    def clear_date(self) -> None:
        self.target_var.set("")
        self.destroy()


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)

        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview,
        )

        self.inner = ttk.Frame(self.canvas)
        self.inner_id = self.canvas.create_window(
            (0, 0),
            window=self.inner,
            anchor="nw",
        )

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.inner.bind("<Configure>", self.on_inner_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

    def on_inner_configure(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfig(self.inner_id, width=event.width)

    def on_mousewheel(self, event: tk.Event) -> None:
        try:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass


class DynamicTextList:
    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        add_button_text: str,
        max_items: int,
        info_callback,
    ) -> None:
        self.parent = parent
        self.title = title
        self.add_button_text = add_button_text
        self.max_items = max_items
        self.info_callback = info_callback
        self.vars: list[tk.StringVar] = []

        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="x", pady=(10, 4))

        header = ttk.Frame(self.frame)
        header.pack(fill="x")

        ttk.Label(
            header,
            text=title,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        ttk.Button(
            header,
            text="ⓘ",
            width=3,
            command=info_callback,
        ).pack(side="left", padx=(6, 0))

        self.items_frame = ttk.Frame(self.frame)
        self.items_frame.pack(fill="x", pady=(4, 0))

        self.buttons_frame = ttk.Frame(self.frame)
        self.buttons_frame.pack(fill="x", pady=(4, 0))

        ttk.Button(
            self.buttons_frame,
            text=add_button_text,
            command=self.add_item,
        ).pack(anchor="w")

    def add_item(self, value: str = "") -> None:
        if len(self.vars) >= self.max_items:
            messagebox.showwarning(
                "Limit reached",
                f"Maximum allowed: {self.max_items}",
            )
            return

        var = tk.StringVar(value=value)
        self.vars.append(var)
        self.render_items()

    def remove_item(self, index: int) -> None:
        if 0 <= index < len(self.vars):
            self.vars.pop(index)
            self.render_items()

    def render_items(self) -> None:
        for widget in self.items_frame.winfo_children():
            widget.destroy()

        for index, var in enumerate(self.vars, start=1):
            row = ttk.Frame(self.items_frame)
            row.pack(fill="x", pady=2)

            ttk.Label(row, text=f"{index}.", width=3).pack(side="left")

            ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)

            ttk.Button(
                row,
                text="×",
                width=3,
                command=lambda idx=index - 1: self.remove_item(idx),
            ).pack(side="left", padx=(6, 0))

    def get_values(self) -> list[str]:
        return [var.get().strip() for var in self.vars if var.get().strip()]

    def set_values(self, values: list[str]) -> None:
        self.vars = []

        for value in values[: self.max_items]:
            clean_value = str(value).strip()

            if clean_value:
                self.vars.append(tk.StringVar(value=clean_value))

        if not self.vars:
            self.vars.append(tk.StringVar())

        self.render_items()


class GoalCard:
    def __init__(
        self,
        parent: tk.Widget,
        index: int,
        remove_callback,
        info_callback,
        templates: dict[str, dict[str, Any]],
    ) -> None:
        self.parent = parent
        self.index = index
        self.remove_callback = remove_callback
        self.info_callback = info_callback
        self.templates = templates

        self.title_var = tk.StringVar()
        self.why_var = tk.StringVar()
        self.success_definition_var = tk.StringVar()
        self.priority_var = tk.StringVar(value="medium")

        self.time_horizon_type_var = tk.StringVar(value="open_ended")
        self.target_date_var = tk.StringVar()
        self.duration_days_var = tk.StringVar()
        self.review_interval_var = tk.StringVar(value="monthly")

        self.is_expanded = tk.BooleanVar(value=True)

        self.frame = ttk.LabelFrame(parent, text=f"Goal {index}")
        self.frame.pack(fill="x", pady=(0, 12), padx=(0, 8))

        self.header_frame = ttk.Frame(self.frame)
        self.header_frame.pack(fill="x", padx=10, pady=(8, 4))

        self.toggle_button = ttk.Button(
            self.header_frame,
            text="▼",
            width=3,
            command=self.toggle,
        )
        self.toggle_button.pack(side="left")

        ttk.Label(
            self.header_frame,
            text="Goal title:",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=(8, 4))

        ttk.Entry(
            self.header_frame,
            textvariable=self.title_var,
        ).pack(side="left", fill="x", expand=True)

        ttk.Button(
            self.header_frame,
            text="Template",
            command=self.choose_template,
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            self.header_frame,
            text="×",
            width=3,
            command=lambda: self.remove_callback(self),
        ).pack(side="left", padx=(6, 0))

        self.body = ttk.Frame(self.frame)
        self.body.pack(fill="x", padx=10, pady=(4, 10))

        self.render_body()

    def render_body(self) -> None:
        for widget in self.body.winfo_children():
            widget.destroy()

        why_row = ttk.Frame(self.body)
        why_row.pack(fill="x", pady=(4, 4))

        ttk.Label(why_row, text="Why is this important?").pack(side="left")

        ttk.Button(
            why_row,
            text="ⓘ",
            width=3,
            command=lambda: self.info_callback("why"),
        ).pack(side="left", padx=(6, 0))

        ttk.Entry(
            self.body,
            textvariable=self.why_var,
        ).pack(fill="x", pady=(0, 8))

        success_row = ttk.Frame(self.body)
        success_row.pack(fill="x", pady=(4, 4))

        ttk.Label(success_row, text="How will you know this goal is reached?").pack(
            side="left"
        )

        ttk.Button(
            success_row,
            text="ⓘ",
            width=3,
            command=lambda: self.info_callback("success"),
        ).pack(side="left", padx=(6, 0))

        ttk.Entry(
            self.body,
            textvariable=self.success_definition_var,
        ).pack(fill="x", pady=(0, 8))

        time_frame = ttk.LabelFrame(self.body, text="Time horizon")
        time_frame.pack(fill="x", pady=(8, 8))

        row = ttk.Frame(time_frame)
        row.pack(fill="x", padx=8, pady=(8, 4))

        ttk.Label(row, text="Type:").pack(side="left")

        horizon_combo = ttk.Combobox(
            row,
            textvariable=self.time_horizon_type_var,
            values=[
                "open_ended",
                "target_date",
                "duration",
                "ongoing",
            ],
            state="readonly",
            width=16,
        )
        horizon_combo.pack(side="left", padx=(8, 12))
        horizon_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self.update_time_fields(),
        )

        ttk.Button(
            row,
            text="ⓘ",
            width=3,
            command=lambda: self.info_callback("time_horizon"),
        ).pack(side="left")

        ttk.Label(row, text="Review:").pack(side="left", padx=(18, 4))

        ttk.Combobox(
            row,
            textvariable=self.review_interval_var,
            values=[
                "weekly",
                "monthly",
                "quarterly",
                "none",
            ],
            state="readonly",
            width=12,
        ).pack(side="left")

        self.time_extra_frame = ttk.Frame(time_frame)
        self.time_extra_frame.pack(fill="x", padx=8, pady=(4, 8))

        self.update_time_fields()

        priority_row = ttk.Frame(self.body)
        priority_row.pack(fill="x", pady=(4, 8))

        ttk.Label(priority_row, text="Priority:").pack(side="left")

        ttk.Combobox(
            priority_row,
            textvariable=self.priority_var,
            values=[
                "low",
                "medium",
                "high",
            ],
            state="readonly",
            width=12,
        ).pack(side="left", padx=(8, 0))

        self.subgoals_list = DynamicTextList(
            parent=self.body,
            title="Subgoals / ways to reach this goal",
            add_button_text="+ Add subgoal",
            max_items=MAX_SUBGOALS_PER_GOAL,
            info_callback=lambda: self.info_callback("subgoals"),
        )
        self.subgoals_list.add_item()

        self.limits_list = DynamicTextList(
            parent=self.body,
            title="Limits / behaviors that may reduce progress",
            add_button_text="+ Add limit",
            max_items=MAX_LIMITS_PER_GOAL,
            info_callback=lambda: self.info_callback("limits"),
        )
        self.limits_list.add_item()

    def update_time_fields(self) -> None:
        for widget in self.time_extra_frame.winfo_children():
            widget.destroy()

        horizon_type = self.time_horizon_type_var.get()

        if horizon_type == "open_ended":
            ttk.Label(
                self.time_extra_frame,
                text=(
                    "No fixed deadline. Review checks whether there is strategic progress."
                ),
            ).pack(anchor="w")
            return

        if horizon_type == "ongoing":
            ttk.Label(
                self.time_extra_frame,
                text=(
                    "Ongoing habit or maintenance goal. It may stay active without a final deadline."
                ),
            ).pack(anchor="w")
            return

        if horizon_type == "target_date":
            ttk.Label(self.time_extra_frame, text="Target date:").pack(side="left")

            date_entry = ttk.Entry(
                self.time_extra_frame,
                textvariable=self.target_date_var,
                width=16,
            )
            date_entry.pack(side="left", padx=(8, 0))

            def normalize_on_focus_out(_event: tk.Event) -> None:
                self.target_date_var.set(
                    normalize_date_input(self.target_date_var.get())
                )

            date_entry.bind("<FocusOut>", normalize_on_focus_out)

            ttk.Button(
                self.time_extra_frame,
                text="📅",
                width=3,
                command=lambda: DatePicker(self.frame, self.target_date_var),
            ).pack(side="left", padx=(6, 0))

            ttk.Label(
                self.time_extra_frame,
                text="Format: YYYY-MM-DD",
                foreground="gray",
            ).pack(side="left", padx=(8, 0))

            return

        if horizon_type == "duration":
            ttk.Label(self.time_extra_frame, text="Duration days:").pack(side="left")

            ttk.Entry(
                self.time_extra_frame,
                textvariable=self.duration_days_var,
                width=10,
            ).pack(side="left", padx=(8, 0))

            ttk.Label(
                self.time_extra_frame,
                text="Example: 30, 60, 90",
                foreground="gray",
            ).pack(side="left", padx=(8, 0))

            return

    def toggle(self) -> None:
        if self.is_expanded.get():
            self.body.forget()
            self.toggle_button.config(text="▶")
            self.is_expanded.set(False)
        else:
            self.body.pack(fill="x", padx=10, pady=(4, 10))
            self.toggle_button.config(text="▼")
            self.is_expanded.set(True)

    def choose_template(self) -> None:
        dialog = tk.Toplevel(self.parent)
        dialog.title("Choose template")
        dialog.geometry("420x280")
        dialog.resizable(False, False)
        dialog.transient(self.parent.winfo_toplevel())
        dialog.grab_set()

        ttk.Label(
            dialog,
            text="Choose editable starting point:",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", padx=16, pady=(16, 8))

        selected_key = tk.StringVar(value="")

        for key, template in self.templates.items():
            ttk.Radiobutton(
                dialog,
                text=str(template.get("label", key)),
                variable=selected_key,
                value=key,
            ).pack(anchor="w", padx=20, pady=3)

        buttons = ttk.Frame(dialog)
        buttons.pack(fill="x", padx=16, pady=16)

        def apply_template() -> None:
            key = selected_key.get()

            if not key:
                messagebox.showwarning("No template", "Choose a template first.")
                return

            template = self.templates[key]
            self.apply_template(template)
            dialog.destroy()

        ttk.Button(
            buttons,
            text="Apply",
            command=apply_template,
        ).pack(side="right")

        ttk.Button(
            buttons,
            text="Cancel",
            command=dialog.destroy,
        ).pack(side="right", padx=(0, 8))

    def apply_template(self, template: dict[str, Any]) -> None:
        self.title_var.set(str(template.get("title", "")))
        self.why_var.set(str(template.get("why", "")))
        self.success_definition_var.set(str(template.get("success_definition", "")))

        horizon = template.get("time_horizon", {})

        if isinstance(horizon, dict):
            self.time_horizon_type_var.set(str(horizon.get("type", "open_ended")))
            self.review_interval_var.set(str(horizon.get("review_interval", "monthly")))

            target_date = horizon.get("target_date")
            self.target_date_var.set("" if target_date is None else str(target_date))

            duration_days = horizon.get("duration_days")
            self.duration_days_var.set(
                "" if duration_days is None else str(duration_days)
            )

        self.update_time_fields()

        subgoal_titles = template.get("subgoal_titles", [])

        if isinstance(subgoal_titles, list):
            self.subgoals_list.set_values([str(item) for item in subgoal_titles])

        limit_titles = template.get("limit_titles", [])

        if isinstance(limit_titles, list):
            self.limits_list.set_values([str(item) for item in limit_titles])

    def get_time_horizon(self) -> dict[str, Any]:
        horizon_type = self.time_horizon_type_var.get().strip() or "open_ended"
        review_interval = self.review_interval_var.get().strip() or "monthly"

        horizon = {
            "type": horizon_type,
            "target_date": None,
            "duration_days": None,
            "review_interval": review_interval,
        }

        if horizon_type == "target_date":
            target_date = normalize_date_input(self.target_date_var.get())
            self.target_date_var.set(target_date)
            horizon["target_date"] = target_date or None

        if horizon_type == "duration":
            raw_duration = self.duration_days_var.get().strip()

            try:
                duration_days = int(raw_duration)
            except Exception:
                duration_days = None

            horizon["duration_days"] = duration_days

        return horizon

    def get_goal_data(self) -> dict[str, Any]:
        return {
            "title": self.title_var.get().strip(),
            "why": self.why_var.get().strip(),
            "success_definition": self.success_definition_var.get().strip(),
            "priority": self.priority_var.get().strip() or "medium",
            "time_horizon": self.get_time_horizon(),
            "subgoal_titles": self.subgoals_list.get_values(),
            "limit_titles": self.limits_list.get_values(),
        }


class GoalCompassSetupWizard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("GoalCompass Setup")
        self.geometry("900x740")
        self.minsize(840, 660)
        self.resizable(True, True)

        self.settings = load_settings()
        self.page_index = 0
        self.templates = get_goal_templates()

        self.setup_mode_var = tk.StringVar(value="manual")

        self.start_overlay_var = tk.BooleanVar(
            value=bool(self.settings["app"].get("start_overlay", True))
        )
        self.show_popup_var = tk.BooleanVar(
            value=bool(self.settings["overlay"].get("show_popup", True))
        )
        self.show_badge_var = tk.BooleanVar(
            value=bool(self.settings["overlay"].get("show_badge", True))
        )
        self.notifications_var = tk.BooleanVar(
            value=bool(self.settings["notifications"].get("enabled", True))
        )
        self.reset_hour_var = tk.IntVar(
            value=int(self.settings["activity_window"].get("reset_hour", 3))
        )
        self.coach_style_var = tk.StringVar(
            value=str(self.settings["coach"].get("style", "direct"))
        )

        self.ai_json_text = ""
        self.ai_json_textbox: tk.Text | None = None

        self.goal_cards: list[GoalCard] = []
        self.goals_container: ttk.Frame | None = None
        self.pending_goal_profile: dict[str, Any] | None = None

        self.pages = [
            self.page_welcome,
            self.page_setup_mode,
            self.page_goal_setup,
            self.page_preferences,
            self.page_finish,
        ]

        self.container = ttk.Frame(self, padding=14)
        self.container.pack(fill="both", expand=True)

        self.content = ttk.Frame(self.container)
        self.content.pack(fill="both", expand=True)

        self.footer = ttk.Frame(self.container)
        self.footer.pack(fill="x", pady=(10, 0))

        self.back_button = ttk.Button(
            self.footer,
            text="Back",
            command=self.go_back,
        )
        self.back_button.pack(side="left")

        self.next_button = ttk.Button(
            self.footer,
            text="Next",
            command=self.go_next,
        )
        self.next_button.pack(side="right")

        self.cancel_button = ttk.Button(
            self.footer,
            text="Cancel",
            command=self.cancel,
        )
        self.cancel_button.pack(side="right", padx=(0, 8))

        self.show_page(0)

    def clear_content(self) -> None:
        for widget in self.content.winfo_children():
            widget.destroy()

    def add_title(self, parent: tk.Widget, title: str, subtitle: str = "") -> None:
        ttk.Label(
            parent,
            text=title,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        if subtitle:
            ttk.Label(
                parent,
                text=subtitle,
                wraplength=820,
            ).pack(anchor="w", pady=(0, 14))

    def show_page(self, index: int) -> None:
        self.page_index = index
        self.clear_content()

        page_builder = self.pages[index]
        page_builder(self.content)

        self.back_button.config(state="normal" if index > 0 else "disabled")

        if index == len(self.pages) - 1:
            self.next_button.config(text="Finish")
        else:
            self.next_button.config(text="Next")

    def page_welcome(self, parent: tk.Widget) -> None:
        self.add_title(
            parent,
            "Welcome to GoalCompass",
            "GoalCompass tracks whether your real behavior moves you toward your goals.",
        )

        text = (
            "This setup creates your first goal profile.\n\n"
            "Important principles:\n"
            "• You may have several main goals at once.\n"
            "• Each goal has its own subgoals and limits.\n"
            "• Goals can change later without losing history.\n"
            "• Weekly/monthly review will later check whether your strategy works.\n\n"
            "Example:\n"
            "Goal: Get into IT market\n"
            "  Subgoals: improve CV, apply to jobs, practice interviews\n"
            "  Limits: uncontrolled gaming, passive scrolling\n\n"
            "Goal: Learn German\n"
            "  Subgoals: homework, speaking practice, B1 exam prep"
        )

        ttk.Label(
            parent,
            text=text,
            justify="left",
            wraplength=820,
        ).pack(anchor="w")

    def page_setup_mode(self, parent: tk.Widget) -> None:
        self.add_title(
            parent,
            "Choose setup mode",
            "All setup modes produce the same goal_profile.json structure.",
        )

        ttk.Radiobutton(
            parent,
            text="Manual setup",
            variable=self.setup_mode_var,
            value="manual",
        ).pack(anchor="w", pady=(4, 2))

        ttk.Label(
            parent,
            text=(
                "Enter goals manually. You can use editable templates. "
                "Best for MVP and privacy."
            ),
            wraplength=800,
        ).pack(anchor="w", padx=(24, 0), pady=(0, 12))

        ttk.Radiobutton(
            parent,
            text="AI-assisted setup",
            variable=self.setup_mode_var,
            value="ai_assisted",
        ).pack(anchor="w", pady=(4, 2))

        ttk.Label(
            parent,
            text=(
                "GoalCompass gives you a prompt. You paste it into any AI, "
                "then paste the returned JSON back here."
            ),
            wraplength=800,
        ).pack(anchor="w", padx=(24, 0), pady=(0, 12))

        ttk.Radiobutton(
            parent,
            text="Full AI setup — coming later",
            variable=self.setup_mode_var,
            value="full_ai",
            state="disabled",
        ).pack(anchor="w", pady=(4, 2))

        ttk.Label(
            parent,
            text=(
                "Later: GoalCompass asks questions and uses AI API directly. "
                "Requires API key / token management."
            ),
            wraplength=800,
        ).pack(anchor="w", padx=(24, 0), pady=(0, 12))

    def page_goal_setup(self, parent: tk.Widget) -> None:
        mode = self.setup_mode_var.get()

        if mode == "manual":
            self.page_manual_goal_setup(parent)
            return

        if mode == "ai_assisted":
            self.page_ai_assisted_goal_setup(parent)
            return

        self.add_title(
            parent,
            "Full AI setup",
            "This mode is planned for a later version.",
        )

        ttk.Label(
            parent,
            text="For now, choose Manual setup or AI-assisted setup.",
            wraplength=820,
        ).pack(anchor="w")

    def page_manual_goal_setup(self, parent: tk.Widget) -> None:
        self.add_title(
            parent,
            "Manual goal profile",
            "Add one or more goals. Each goal has its own subgoals, limits and time horizon.",
        )

        top_bar = ttk.Frame(parent)
        top_bar.pack(fill="x", pady=(0, 8))

        ttk.Button(
            top_bar,
            text="+ Add goal",
            command=self.add_goal_card,
        ).pack(side="left")

        ttk.Button(
            top_bar,
            text="ⓘ How to fill this",
            command=lambda: self.show_info("manual_setup"),
        ).pack(side="left", padx=(8, 0))

        ttk.Label(
            top_bar,
            text=f"Max goals: {MAX_MAIN_GOALS}",
        ).pack(side="right")

        scrollable = ScrollableFrame(parent)
        scrollable.pack(fill="both", expand=True)

        self.goals_container = scrollable.inner

        if not self.goal_cards:
            self.add_goal_card()

        self.render_goal_cards()

    def add_goal_card(self) -> None:
        if len(self.goal_cards) >= MAX_MAIN_GOALS:
            messagebox.showwarning(
                "Limit reached",
                f"Maximum allowed goals: {MAX_MAIN_GOALS}",
            )
            return

        if self.goals_container is None:
            return

        card = GoalCard(
            parent=self.goals_container,
            index=len(self.goal_cards) + 1,
            remove_callback=self.remove_goal_card,
            info_callback=self.show_info,
            templates=self.templates,
        )

        self.goal_cards.append(card)
        self.renumber_goal_cards()

    def remove_goal_card(self, card: GoalCard) -> None:
        if len(self.goal_cards) <= 1:
            messagebox.showwarning(
                "At least one goal required",
                "GoalCompass needs at least one main goal.",
            )
            return

        if card in self.goal_cards:
            self.goal_cards.remove(card)
            card.frame.destroy()
            self.renumber_goal_cards()

    def render_goal_cards(self) -> None:
        for card in self.goal_cards:
            try:
                card.frame.pack_forget()
                card.frame.pack(fill="x", pady=(0, 12), padx=(0, 8))
            except Exception:
                pass

        self.renumber_goal_cards()

    def renumber_goal_cards(self) -> None:
        for index, card in enumerate(self.goal_cards, start=1):
            card.index = index
            card.frame.config(text=f"Goal {index}")

    def page_ai_assisted_goal_setup(self, parent: tk.Widget) -> None:
        self.add_title(
            parent,
            "AI-assisted goal profile",
            "Copy the prompt, paste it into any AI, then paste the returned JSON here.",
        )

        button_row = ttk.Frame(parent)
        button_row.pack(fill="x", pady=(0, 8))

        ttk.Button(
            button_row,
            text="Copy AI Prompt",
            command=self.copy_ai_prompt,
        ).pack(side="left")

        ttk.Button(
            button_row,
            text="Validate JSON",
            command=self.validate_ai_json_button,
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            button_row,
            text="ⓘ",
            width=3,
            command=lambda: self.show_info("ai_assisted"),
        ).pack(side="left", padx=(8, 0))

        ttk.Label(
            parent,
            text=(
                "The AI must return ONLY valid JSON. No markdown, no explanations, "
                "no ``` blocks."
            ),
            wraplength=820,
        ).pack(anchor="w", pady=(0, 8))

        self.ai_json_textbox = tk.Text(
            parent,
            height=24,
            width=100,
            wrap="word",
        )
        self.ai_json_textbox.pack(fill="both", expand=True)

        if self.ai_json_text:
            self.ai_json_textbox.insert("1.0", self.ai_json_text)

    def page_preferences(self, parent: tk.Widget) -> None:
        self.add_title(
            parent,
            "Overlay and behavior",
            "Basic MVP settings. You can change these later.",
        )

        ttk.Checkbutton(
            parent,
            text="Start mini overlay with GoalCompass",
            variable=self.start_overlay_var,
        ).pack(anchor="w", pady=4)

        ttk.Checkbutton(
            parent,
            text="Show popup warnings",
            variable=self.show_popup_var,
        ).pack(anchor="w", pady=4)

        ttk.Checkbutton(
            parent,
            text="Show badge on overlay",
            variable=self.show_badge_var,
        ).pack(anchor="w", pady=4)

        ttk.Checkbutton(
            parent,
            text="Enable notifications",
            variable=self.notifications_var,
        ).pack(anchor="w", pady=4)

        reset_frame = ttk.Frame(parent)
        reset_frame.pack(anchor="w", pady=(18, 6))

        ttk.Label(reset_frame, text="Activity day reset hour:").pack(side="left")

        ttk.Spinbox(
            reset_frame,
            from_=0,
            to=23,
            width=5,
            textvariable=self.reset_hour_var,
        ).pack(side="left", padx=(8, 0))

        ttk.Label(
            parent,
            text=(
                "Recommended: 03:00. This affects live limits and overlay counters, "
                "not historical timestamps."
            ),
            wraplength=820,
        ).pack(anchor="w", pady=(0, 12))

        ttk.Label(
            parent,
            text="Coach style:",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(8, 4))

        for label, value in [
            ("Off", "off"),
            ("Soft", "soft"),
            ("Direct", "direct"),
            ("Aggressive", "aggressive"),
        ]:
            ttk.Radiobutton(
                parent,
                text=label,
                variable=self.coach_style_var,
                value=value,
            ).pack(anchor="w", pady=2)

    def page_finish(self, parent: tk.Widget) -> None:
        self.add_title(
            parent,
            "Ready to save",
            "GoalCompass will save your settings and goal profile.",
        )

        if self.pending_goal_profile is None:
            ttk.Label(
                parent,
                text="Goal profile was not prepared yet.",
                foreground="red",
            ).pack(anchor="w")
            return

        main_goals = self.pending_goal_profile.get("main_goals", [])

        summary_lines = [
            f"Setup mode: {self.setup_mode_var.get()}",
            "",
            f"Main goals: {len(main_goals)}",
            "",
        ]

        for index, goal in enumerate(main_goals, start=1):
            title = goal.get("title", "")
            horizon = goal.get("time_horizon", {})
            horizon_type = horizon.get("type", "open_ended")
            review_interval = horizon.get("review_interval", "monthly")

            summary_lines.append(f"{index}. {title}")
            summary_lines.append(f"   Time horizon: {horizon_type}")

            if horizon_type == "target_date":
                summary_lines.append(
                    f"   Target date: {horizon.get('target_date') or '[not set]'}"
                )

            if horizon_type == "duration":
                summary_lines.append(
                    f"   Duration days: {horizon.get('duration_days') or '[not set]'}"
                )

            summary_lines.append(f"   Review: {review_interval}")
            summary_lines.append(f"   Subgoals: {len(goal.get('subgoals', []))}")
            summary_lines.append(f"   Limits: {len(goal.get('limits', []))}")
            summary_lines.append("")

        summary_lines.extend(
            [
                f"Overlay: {'enabled' if self.start_overlay_var.get() else 'disabled'}",
                f"Notifications: {'enabled' if self.notifications_var.get() else 'disabled'}",
                f"Activity reset: {int(self.reset_hour_var.get()):02d}:00",
                f"Coach style: {self.coach_style_var.get()}",
            ]
        )

        ttk.Label(
            parent,
            text="\n".join(summary_lines),
            justify="left",
            wraplength=820,
        ).pack(anchor="w")

        ttk.Label(
            parent,
            text=(
                "Future edits will create archived versions, so progress history is not lost."
            ),
            wraplength=820,
        ).pack(anchor="w", pady=(12, 0))

    def show_info(self, topic: str) -> None:
        messages = {
            "manual_setup": (
                "Add separate goals for separate life directions.\n\n"
                "Good:\n"
                "• Get into IT market\n"
                "• Learn German\n"
                "• Improve physical fitness\n\n"
                "Avoid putting unrelated goals into one field.\n\n"
                "Each goal can have its own subgoals, limits and deadline."
            ),
            "why": (
                "This explains why the goal matters.\n\n"
                "It does not directly change the timer, but it helps future review and AI coaching.\n\n"
                "Example:\n"
                "I need stable income and want to return to IT career."
            ),
            "success": (
                "This is the condition that means the goal is reached.\n\n"
                "Examples:\n"
                "• Get a signed job contract\n"
                "• Pass B1 exam\n"
                "• Train 3 times per week for 3 months\n\n"
                "A clear success definition makes review much better."
            ),
            "time_horizon": (
                "Time horizon tells GoalCompass how to evaluate progress.\n\n"
                "open_ended:\n"
                "No fixed deadline. Review checks whether there is strategic progress.\n\n"
                "target_date:\n"
                "Goal should be reached by a specific date. Review can compare your pace with time left.\n\n"
                "duration:\n"
                "A fixed experiment for N days, for example: train for 90 days.\n\n"
                "ongoing:\n"
                "A habit or maintenance goal, for example: stay fit or keep German practice.\n\n"
                "This does not change historical logs. It affects future review and coaching."
            ),
            "subgoals": (
                "Subgoals are possible ways to reach the main goal.\n\n"
                "They are hypotheses, not guaranteed truth.\n\n"
                "Example for job goal:\n"
                "• Improve CV\n"
                "• Apply to jobs\n"
                "• Practice interviews"
            ),
            "limits": (
                "Limits are behaviors that may reduce progress toward this specific goal.\n\n"
                "Context matters.\n"
                "Gaming can be harmful for one user, but useful for a streamer.\n\n"
                "Example:\n"
                "• Limit uncontrolled gaming\n"
                "• Limit passive scrolling"
            ),
            "ai_assisted": (
                "AI-assisted setup does not use GoalCompass API.\n\n"
                "You copy a prompt, paste it into any AI, then paste the returned JSON here.\n\n"
                "GoalCompass validates the JSON before saving."
            ),
        }

        messagebox.showinfo(
            "GoalCompass help",
            messages.get(topic, "No help available for this field yet."),
        )

    def copy_ai_prompt(self) -> None:
        prompt = build_ai_assisted_prompt(language="uk")

        self.clipboard_clear()
        self.clipboard_append(prompt)
        self.update()

        messagebox.showinfo(
            "AI prompt copied",
            "Prompt copied to clipboard. Paste it into any AI, then paste the returned JSON here.",
        )

    def capture_ai_json_text(self) -> None:
        if self.ai_json_textbox is not None:
            self.ai_json_text = self.ai_json_textbox.get("1.0", "end").strip()

    def validate_ai_json_button(self) -> None:
        self.capture_ai_json_text()

        try:
            profile = parse_goal_profile_json(self.ai_json_text)
        except Exception as error:
            messagebox.showerror("Invalid JSON", str(error))
            return

        pretty = json.dumps(profile, ensure_ascii=False, indent=2)
        self.ai_json_text = pretty

        if self.ai_json_textbox is not None:
            self.ai_json_textbox.delete("1.0", "end")
            self.ai_json_textbox.insert("1.0", pretty)

        messagebox.showinfo(
            "Valid JSON",
            "Goal profile JSON is valid.",
        )

    def prepare_goal_profile(self) -> bool:
        mode = self.setup_mode_var.get()

        if mode == "manual":
            goals_data = [card.get_goal_data() for card in self.goal_cards]

            profile = create_profile_from_manual_goals(
                goals=goals_data,
                coach_style=self.coach_style_var.get(),
                language="uk",
            )

            errors = validate_goal_profile(profile)

            if errors:
                messagebox.showerror(
                    "Invalid goal profile",
                    "\n".join(errors),
                )
                return False

            self.pending_goal_profile = profile
            return True

        if mode == "ai_assisted":
            self.capture_ai_json_text()

            try:
                profile = parse_goal_profile_json(self.ai_json_text)
            except Exception as error:
                messagebox.showerror("Invalid AI JSON", str(error))
                return False

            profile["created_by"] = "ai_assisted"
            profile["source_mode"] = "ai_assisted"
            profile["coach"]["style"] = self.coach_style_var.get()
            profile["coach"]["language"] = "uk"

            self.pending_goal_profile = profile
            return True

        messagebox.showerror(
            "Setup mode unavailable",
            "Full AI setup is not available yet. Choose Manual or AI-assisted setup.",
        )
        return False

    def save_preferences(self) -> None:
        try:
            reset_hour = int(self.reset_hour_var.get())
        except Exception:
            reset_hour = 3

        reset_hour = max(0, min(23, reset_hour))

        self.settings["app"]["first_run_completed"] = True
        self.settings["app"]["start_overlay"] = bool(self.start_overlay_var.get())

        self.settings["activity_window"]["reset_hour"] = reset_hour

        self.settings["overlay"]["enabled"] = bool(self.start_overlay_var.get())
        self.settings["overlay"]["show_popup"] = bool(self.show_popup_var.get())
        self.settings["overlay"]["show_badge"] = bool(self.show_badge_var.get())

        self.settings["notifications"]["enabled"] = bool(self.notifications_var.get())

        self.settings["coach"]["style"] = str(self.coach_style_var.get())

        save_settings(self.settings)

    def go_back(self) -> None:
        if self.page_index > 0:
            self.show_page(self.page_index - 1)

    def go_next(self) -> None:
        current_page = self.pages[self.page_index]

        if current_page == self.page_goal_setup:
            if not self.prepare_goal_profile():
                return

        if self.page_index < len(self.pages) - 1:
            self.show_page(self.page_index + 1)
            return

        self.finish()

    def cancel(self) -> None:
        result = messagebox.askyesno(
            "Cancel setup",
            "Exit setup without saving first-run configuration?",
        )

        if result:
            self.destroy()
            raise SystemExit(1)

    def finish(self) -> None:
        if self.pending_goal_profile is None:
            messagebox.showerror(
                "Goal profile missing",
                "Goal profile was not prepared.",
            )
            return

        try:
            self.save_preferences()

            save_goal_profile(
                profile=self.pending_goal_profile,
                change_reason="Initial setup completed",
                archive_previous=True,
            )

        except Exception as error:
            messagebox.showerror(
                "Setup save failed",
                str(error),
            )
            return

        messagebox.showinfo(
            "GoalCompass",
            "Setup completed. GoalCompass will start now.",
        )

        self.destroy()
        raise SystemExit(0)


def main() -> None:
    app = GoalCompassSetupWizard()
    app.mainloop()


if __name__ == "__main__":
    main()
