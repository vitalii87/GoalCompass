# gui/control_panel.py

from __future__ import annotations

import sys
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import messagebox, ttk


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from src.services.dashboard_service import (
    DashboardView,
    build_dashboard_view,
)
from src.services.goal_progress_service import (
    build_goal_progress_day_view,
    format_seconds,
)
from src.services.manual_activity_service import (
    add_manual_activity_from_preset,
    delete_manual_activity,
    format_seconds as format_manual_seconds,
    list_manual_activities,
    load_presets,
)
from src.services.schedule_service import (
    build_schedule_day_view,
    format_minutes_as_duration,
)


DASHBOARD_AUTO_REFRESH_SECONDS = 15


class GoalCompassControlPanel(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("GoalCompass Control Panel")
        self.geometry("1000x700")
        self.minsize(900, 600)

        self.selected_date_var = tk.StringVar(value=date.today().isoformat())
        self.status_var = tk.StringVar(value="Ready")

        self._build_layout()
        self.refresh_all()
        self.dashboard_auto_refresh_loop()

    def _build_layout(self) -> None:
        top_bar = ttk.Frame(self)
        top_bar.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(top_bar, text="Date:").pack(side=tk.LEFT)

        date_entry = ttk.Entry(
            top_bar,
            textvariable=self.selected_date_var,
            width=14,
        )
        date_entry.pack(side=tk.LEFT, padx=(5, 10))

        refresh_button = ttk.Button(
            top_bar,
            text="Refresh",
            command=self.refresh_all,
        )
        refresh_button.pack(side=tk.LEFT)

        today_button = ttk.Button(
            top_bar,
            text="Today",
            command=self.set_today,
        )
        today_button.pack(side=tk.LEFT, padx=(5, 0))

        self.auto_refresh_label = ttk.Label(
            top_bar,
            text=f"Dashboard auto-refresh: {DASHBOARD_AUTO_REFRESH_SECONDS}s",
        )
        self.auto_refresh_label.pack(side=tk.LEFT, padx=(20, 0))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))

        self.dashboard_tab = ttk.Frame(self.notebook)
        self.goals_tab = ttk.Frame(self.notebook)
        self.manual_tab = ttk.Frame(self.notebook)
        self.schedule_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.notebook.add(self.goals_tab, text="Goals")
        self.notebook.add(self.manual_tab, text="Manual")
        self.notebook.add(self.schedule_tab, text="Schedule")

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.status_bar = ttk.Label(
            self,
            textvariable=self.status_var,
            anchor=tk.W,
        )
        self.status_bar.pack(fill=tk.X, padx=10, pady=(0, 8))

        self._build_dashboard_tab()
        self._build_goals_tab()
        self._build_manual_tab()
        self._build_schedule_tab()

    def _build_dashboard_tab(self) -> None:
        self.dashboard_text = tk.Text(
            self.dashboard_tab,
            wrap=tk.WORD,
            height=20,
        )
        self.dashboard_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _build_goals_tab(self) -> None:
        self.goals_text = tk.Text(
            self.goals_tab,
            wrap=tk.WORD,
            height=20,
        )
        self.goals_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _build_manual_tab(self) -> None:
        presets_frame = ttk.LabelFrame(
            self.manual_tab,
            text="Quick add presets",
        )
        presets_frame.pack(fill=tk.X, padx=10, pady=10)

        self.presets_buttons_frame = ttk.Frame(presets_frame)
        self.presets_buttons_frame.pack(fill=tk.X, padx=10, pady=10)

        entries_frame = ttk.LabelFrame(
            self.manual_tab,
            text="Manual entries for selected date",
        )
        entries_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        columns = (
            "id",
            "date",
            "goal",
            "title",
            "duration",
            "source",
        )

        self.manual_tree = ttk.Treeview(
            entries_frame,
            columns=columns,
            show="headings",
            height=12,
        )

        self.manual_tree.heading("id", text="ID")
        self.manual_tree.heading("date", text="Date")
        self.manual_tree.heading("goal", text="Goal")
        self.manual_tree.heading("title", text="Title")
        self.manual_tree.heading("duration", text="Duration")
        self.manual_tree.heading("source", text="Source")

        self.manual_tree.column("id", width=60, anchor=tk.CENTER)
        self.manual_tree.column("date", width=110, anchor=tk.CENTER)
        self.manual_tree.column("goal", width=180)
        self.manual_tree.column("title", width=260)
        self.manual_tree.column("duration", width=100, anchor=tk.CENTER)
        self.manual_tree.column("source", width=130, anchor=tk.CENTER)

        self.manual_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        manual_actions = ttk.Frame(entries_frame)
        manual_actions.pack(fill=tk.X, padx=10, pady=(0, 10))

        delete_button = ttk.Button(
            manual_actions,
            text="Delete selected",
            command=self.delete_selected_manual_entry,
        )
        delete_button.pack(side=tk.LEFT)

    def _build_schedule_tab(self) -> None:
        self.schedule_text = tk.Text(
            self.schedule_tab,
            wrap=tk.WORD,
            height=20,
        )
        self.schedule_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def get_selected_date(self) -> str:
        return self.selected_date_var.get().strip()

    def set_today(self) -> None:
        self.selected_date_var.set(date.today().isoformat())
        self.refresh_all()

    def get_active_tab_text(self) -> str:
        selected_tab_id = self.notebook.select()

        if not selected_tab_id:
            return ""

        return str(self.notebook.tab(selected_tab_id, "text"))

    def is_dashboard_active(self) -> bool:
        return self.get_active_tab_text() == "Dashboard"

    def is_window_minimized(self) -> bool:
        return self.state() == "iconic"

    def on_tab_changed(self, _event: tk.Event) -> None:
        if self.is_dashboard_active() and not self.is_window_minimized():
            self.refresh_dashboard()

    def dashboard_auto_refresh_loop(self) -> None:
        if self.is_dashboard_active() and not self.is_window_minimized():
            self.refresh_dashboard(auto=True)

        self.after(
            DASHBOARD_AUTO_REFRESH_SECONDS * 1000,
            self.dashboard_auto_refresh_loop,
        )

    def refresh_all(self) -> None:
        self.refresh_dashboard()
        self.refresh_goals()
        self.refresh_manual()
        self.refresh_schedule()
        self.refresh_preset_buttons()

    def refresh_dashboard(self, auto: bool = False) -> None:
        activity_date = self.get_selected_date()

        try:
            view = build_dashboard_view(activity_date)
        except Exception as error:
            self.dashboard_text.delete("1.0", tk.END)
            self.dashboard_text.insert(
                tk.END,
                f"Error loading dashboard:\n{error}",
            )
            self.status_var.set("Dashboard refresh failed")
            return

        self.render_dashboard(view)

        if auto:
            self.status_var.set(
                f"Dashboard auto-refreshed for {view.activity_date}"
            )
        else:
            self.status_var.set(
                f"Dashboard refreshed for {view.activity_date}"
            )

    def render_dashboard(self, view: DashboardView) -> None:
        self.dashboard_text.delete("1.0", tk.END)

        self.dashboard_text.insert(
            tk.END,
            f"GOALCOMPASS DASHBOARD | {view.activity_date}\n",
        )
        self.dashboard_text.insert(
            tk.END,
            f"Week: {view.week_start_date} → {view.week_end_date}\n",
        )
        self.dashboard_text.insert(tk.END, "=" * 70 + "\n\n")

        self.dashboard_text.insert(tk.END, "CURRENT\n")
        self.dashboard_text.insert(tk.END, "-" * 70 + "\n")

        if view.current_state is None:
            self.dashboard_text.insert(
                tk.END,
                "No current state found. Tracker may not be running.\n",
            )
        else:
            state = view.current_state
            live_state = "STALE" if view.current_state_stale else "LIVE"

            self.dashboard_text.insert(tk.END, f"state:    {live_state}\n")
            self.dashboard_text.insert(tk.END, f"status:   {state.panel_status}\n")
            self.dashboard_text.insert(tk.END, f"category: {state.category}\n")
            self.dashboard_text.insert(
                tk.END,
                f"activity: {state.activity_state}\n",
            )
            self.dashboard_text.insert(tk.END, f"process:  {state.process_name}\n")
            self.dashboard_text.insert(
                tk.END,
                f"title:    {state.window_title or '[empty]'}\n",
            )
            self.dashboard_text.insert(
                tk.END,
                f"session:  {format_seconds(state.session_seconds)}\n",
            )
            self.dashboard_text.insert(
                tk.END,
                f"today category: "
                f"{format_seconds(state.today_category_seconds)}\n",
            )
            self.dashboard_text.insert(tk.END, f"updated:  {state.updated_at}\n")

        self.dashboard_text.insert(tk.END, "\nTODAY TOTALS\n")
        self.dashboard_text.insert(tk.END, "-" * 70 + "\n")

        totals = view.panel_totals_today

        self.dashboard_text.insert(
            tk.END,
            f"positive: {format_seconds(totals.positive_seconds)}\n",
        )
        self.dashboard_text.insert(
            tk.END,
            f"neutral:  {format_seconds(totals.neutral_seconds)}\n",
        )
        self.dashboard_text.insert(
            tk.END,
            f"negative: {format_seconds(totals.negative_seconds)}\n",
        )
        self.dashboard_text.insert(
            tk.END,
            f"idle:     {format_seconds(totals.idle_seconds)}\n",
        )
        self.dashboard_text.insert(
            tk.END,
            f"tracked:  {format_seconds(totals.tracked_seconds)}\n",
        )

        self.dashboard_text.insert(tk.END, "\nGOALS\n")
        self.dashboard_text.insert(tk.END, "-" * 70 + "\n")

        if not view.goals:
            self.dashboard_text.insert(tk.END, "No goals found.\n")
        else:
            for goal in view.goals:
                self.dashboard_text.insert(tk.END, f"{goal.title}\n")
                self.dashboard_text.insert(tk.END, f"  id:     {goal.goal_id}\n")
                self.dashboard_text.insert(tk.END, f"  type:   {goal.goal_type}\n")
                self.dashboard_text.insert(
                    tk.END,
                    f"  today:  {format_seconds(goal.today_seconds)}\n",
                )
                self.dashboard_text.insert(
                    tk.END,
                    f"  week:   {format_seconds(goal.week_seconds)}\n",
                )

                if goal.target_seconds > 0:
                    self.dashboard_text.insert(
                        tk.END,
                        f"  target: {format_seconds(goal.target_seconds)}\n",
                    )

                if goal.limit_seconds > 0:
                    self.dashboard_text.insert(
                        tk.END,
                        f"  limit:  {format_seconds(goal.limit_seconds)}\n",
                    )

                self.dashboard_text.insert(
                    tk.END,
                    f"  status: {goal.status}\n",
                )
                self.dashboard_text.insert(
                    tk.END,
                    f"  note:   {goal.message}\n",
                )
                self.dashboard_text.insert(tk.END, "\n")

        self.dashboard_text.insert(tk.END, "WARNINGS\n")
        self.dashboard_text.insert(tk.END, "-" * 70 + "\n")

        if not view.warnings:
            self.dashboard_text.insert(tk.END, "No warnings.\n")
        else:
            for warning in view.warnings:
                self.dashboard_text.insert(
                    tk.END,
                    f"[{warning.warning_type}] {warning.message}\n",
                )

    def refresh_goals(self) -> None:
        activity_date = self.get_selected_date()

        self.goals_text.delete("1.0", tk.END)

        try:
            day_view = build_goal_progress_day_view(activity_date)
        except Exception as error:
            self.goals_text.insert(tk.END, f"Error loading goal progress:\n{error}")
            return

        self.goals_text.insert(
            tk.END,
            f"GOAL PROGRESS FOR {day_view.activity_date}\n",
        )
        self.goals_text.insert(tk.END, "=" * 60 + "\n\n")

        for result in day_view.results:
            self.goals_text.insert(tk.END, f"{result.title}\n")
            self.goals_text.insert(tk.END, f"id: {result.goal_id}\n")
            self.goals_text.insert(
                tk.END,
                f"desktop: {format_seconds(result.desktop_seconds)}\n",
            )
            self.goals_text.insert(
                tk.END,
                f"manual:  {format_seconds(result.manual_seconds)}\n",
            )
            self.goals_text.insert(
                tk.END,
                f"total:   {format_seconds(result.total_seconds)}\n",
            )

            if result.manual_entries:
                self.goals_text.insert(tk.END, "manual entries:\n")

                for entry in result.manual_entries:
                    self.goals_text.insert(
                        tk.END,
                        f"  - #{entry.id} {entry.title}: "
                        f"{format_seconds(entry.seconds)} [{entry.source}]\n",
                    )

            if result.limit_seconds is not None and result.status in {
                "within limit",
                "over limit",
            }:
                self.goals_text.insert(
                    tk.END,
                    f"limit:   {format_seconds(result.limit_seconds)}\n",
                )
                self.goals_text.insert(tk.END, f"status: {result.status}\n")

                if result.status == "within limit":
                    self.goals_text.insert(
                        tk.END,
                        f"remaining: {format_seconds(result.remaining_seconds)}\n",
                    )
                else:
                    self.goals_text.insert(
                        tk.END,
                        f"over by: {format_seconds(result.extra_seconds)}\n",
                    )

            elif result.target_seconds is not None:
                self.goals_text.insert(
                    tk.END,
                    f"target:  {format_seconds(result.target_seconds)}\n",
                )
                self.goals_text.insert(tk.END, f"status: {result.status}\n")

                if result.status == "below target":
                    self.goals_text.insert(
                        tk.END,
                        f"missing: {format_seconds(result.missing_seconds)}\n",
                    )
                elif result.status == "target reached":
                    self.goals_text.insert(
                        tk.END,
                        f"extra:   {format_seconds(result.extra_seconds)}\n",
                    )
            else:
                self.goals_text.insert(tk.END, "status: not configured\n")

            self.goals_text.insert(tk.END, "\n" + "-" * 60 + "\n\n")

    def refresh_manual(self) -> None:
        activity_date = self.get_selected_date()

        for item in self.manual_tree.get_children():
            self.manual_tree.delete(item)

        try:
            entries = list_manual_activities(activity_date=activity_date)
        except Exception as error:
            messagebox.showerror("Manual activity error", str(error))
            return

        for entry in entries:
            self.manual_tree.insert(
                "",
                tk.END,
                values=(
                    entry.id,
                    entry.activity_date,
                    entry.goal_id,
                    entry.title,
                    format_manual_seconds(entry.seconds),
                    entry.source,
                ),
            )

    def refresh_preset_buttons(self) -> None:
        for widget in self.presets_buttons_frame.winfo_children():
            widget.destroy()

        try:
            presets = load_presets()
        except Exception as error:
            ttk.Label(
                self.presets_buttons_frame,
                text=f"Error loading presets: {error}",
            ).pack(anchor=tk.W)
            return

        if not presets:
            ttk.Label(
                self.presets_buttons_frame,
                text="No presets found.",
            ).pack(anchor=tk.W)
            return

        for preset in presets:
            button_text = (
                f"+ {preset.title} "
                f"({format_manual_seconds(preset.seconds)})"
            )

            button = ttk.Button(
                self.presets_buttons_frame,
                text=button_text,
                command=lambda preset_id=preset.preset_id: self.add_preset(preset_id),
            )
            button.pack(side=tk.LEFT, padx=5, pady=5)

    def add_preset(self, preset_id: str) -> None:
        activity_date = self.get_selected_date()

        try:
            entry = add_manual_activity_from_preset(
                preset_id=preset_id,
                activity_date=activity_date,
            )
        except Exception as error:
            messagebox.showerror("Add manual activity error", str(error))
            return

        messagebox.showinfo(
            "Manual activity added",
            (
                f"Added:\n"
                f"#{entry.id} {entry.title}\n"
                f"{format_manual_seconds(entry.seconds)}"
            ),
        )

        self.refresh_all()

    def delete_selected_manual_entry(self) -> None:
        selected_items = self.manual_tree.selection()

        if not selected_items:
            messagebox.showwarning(
                "No selection",
                "Select a manual entry first.",
            )
            return

        item_id = selected_items[0]
        values = self.manual_tree.item(item_id, "values")

        if not values:
            return

        entry_id = int(values[0])

        confirmed = messagebox.askyesno(
            "Delete manual activity",
            f"Delete manual activity #{entry_id}?",
        )

        if not confirmed:
            return

        try:
            deleted_entry = delete_manual_activity(entry_id)
        except Exception as error:
            messagebox.showerror("Delete error", str(error))
            return

        if deleted_entry is None:
            messagebox.showwarning(
                "Not found",
                f"Manual activity #{entry_id} was not found.",
            )
        else:
            messagebox.showinfo(
                "Deleted",
                f"Deleted #{deleted_entry.id}: {deleted_entry.title}",
            )

        self.refresh_all()

    def refresh_schedule(self) -> None:
        activity_date = self.get_selected_date()

        self.schedule_text.delete("1.0", tk.END)

        try:
            day_view = build_schedule_day_view(
                date.fromisoformat(activity_date)
            )
        except Exception as error:
            self.schedule_text.insert(tk.END, f"Error loading schedule:\n{error}")
            return

        self.schedule_text.insert(
            tk.END,
            f"SCHEDULE FOR {day_view.activity_date.isoformat()} | "
            f"{day_view.weekday}\n",
        )
        self.schedule_text.insert(tk.END, "=" * 70 + "\n\n")

        if not day_view.events:
            self.schedule_text.insert(tk.END, "No scheduled activities found.\n")
            return

        for event in day_view.events:
            self.schedule_text.insert(
                tk.END,
                f"{event.start_time}–{event.end_time} | "
                f"{format_minutes_as_duration(event.duration_minutes)}\n",
            )
            self.schedule_text.insert(tk.END, f"title: {event.title}\n")
            self.schedule_text.insert(tk.END, f"id: {event.schedule_id}\n")
            self.schedule_text.insert(tk.END, f"goal: {event.goal_id or '[none]'}\n")
            self.schedule_text.insert(tk.END, f"category: {event.category}\n")
            self.schedule_text.insert(
                tk.END,
                f"counts_to_goal: {event.counts_to_goal}\n",
            )
            self.schedule_text.insert(
                tk.END,
                f"confirmation_mode: {event.confirmation_mode}\n",
            )
            self.schedule_text.insert(tk.END, f"blocking: {event.blocking}\n")
            self.schedule_text.insert(tk.END, "\n" + "-" * 70 + "\n\n")

        self.schedule_text.insert(tk.END, "SUMMARY\n")
        self.schedule_text.insert(
            tk.END,
            f"planned goal time:     "
            f"{format_minutes_as_duration(day_view.planned_goal_minutes)}\n",
        )
        self.schedule_text.insert(
            tk.END,
            f"planned non-goal time: "
            f"{format_minutes_as_duration(day_view.planned_non_goal_minutes)}\n",
        )
        self.schedule_text.insert(
            tk.END,
            f"planned total time:    "
            f"{format_minutes_as_duration(day_view.planned_total_minutes)}\n\n",
        )

        self.schedule_text.insert(tk.END, "CONFLICTS\n")

        if not day_view.conflicts:
            self.schedule_text.insert(tk.END, "No schedule conflicts found.\n")
        else:
            for conflict in day_view.conflicts:
                first = conflict.first_event
                second = conflict.second_event

                self.schedule_text.insert(
                    tk.END,
                    f"CONFLICT: {first.start_time}–{first.end_time} {first.title} "
                    f"overlaps with {second.start_time}–{second.end_time} "
                    f"{second.title}\n",
                )
                self.schedule_text.insert(
                    tk.END,
                    f"  first_id:  {first.schedule_id}\n",
                )
                self.schedule_text.insert(
                    tk.END,
                    f"  second_id: {second.schedule_id}\n",
                )


def main() -> None:
    app = GoalCompassControlPanel()
    app.mainloop()


if __name__ == "__main__":
    main()