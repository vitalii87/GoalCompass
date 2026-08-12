# gui/control_panel.py

from __future__ import annotations

import json
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.app_paths import IS_FROZEN  # noqa: E402
from src.services.current_state_service import CURRENT_STATE_PATH  # noqa: E402
from src.services.activity_rules_service import (  # noqa: E402
    add_activity_rule,
    delete_activity_rule,
    list_rules,
    normalize_rule_value,
    update_activity_rule,
)
from src.services.goal_profile_service import load_goal_profile  # noqa: E402
from src.services.limit_rules_service import (  # noqa: E402
    add_limit_rule,
    delete_limit_rule,
    list_limit_rules,
    pause_limit_rule,
    replace_limit_rule,
    seed_starter_limits_if_empty,
)
from src.services.interaction_policy_service import (  # noqa: E402
    InteractionPolicy,
    build_interaction_policy,
)
from src.services.settings_service import load_settings, save_settings  # noqa: E402
from src.services.stats_service import (  # noqa: E402
    get_dashboard_snapshot,
    get_today_top_unknown,
)
from src.services.update_service import (  # noqa: E402
    UpdateError,
    check_for_updates,
    install_update,
)
from src.version import __version__  # noqa: E402
from gui.ai_assistant_tab import AIAssistantTab  # noqa: E402


ACTIVITY_RULE_TYPES = [
    "process",
    "title_contains",
    "domain",
    "url_contains",
]

ACTIVITY_CATEGORIES = [
    "productive",
    "personal",
    "neutral",
    "distracting",
    "time_wasting",
    "unknown",
    "ignored",
]

LIMIT_TARGET_TYPES = [
    "category",
    "process",
    "title_contains",
    "goal",
]

LIMIT_PERIODS = [
    "daily",
    "weekly",
]

LIMIT_SEVERITIES = [
    "badge",
    "warning",
    "strict",
]


def format_seconds(seconds: int | float | None) -> str:
    total = int(seconds or 0)

    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60

    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def read_current_state() -> dict:
    if not CURRENT_STATE_PATH.exists():
        return {}

    try:
        raw = CURRENT_STATE_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)

        if isinstance(data, dict):
            return data

    except Exception:
        return {}

    return {}


class ActivityRuleDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        initial_rule: dict | None = None,
    ) -> None:
        super().__init__(parent)

        self.result: dict | None = None
        self.initial_rule = initial_rule or {}

        self.title(title)
        self.geometry("620x360")
        self.minsize(560, 340)
        self.resizable(True, True)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self.rule_type_var = tk.StringVar(
            value=str(self.initial_rule.get("type", "title_contains"))
        )
        self.value_var = tk.StringVar(
            value=str(self.initial_rule.get("value", ""))
        )
        self.category_var = tk.StringVar(
            value=str(self.initial_rule.get("category", "neutral"))
        )
        self.reason_var = tk.StringVar(
            value=str(self.initial_rule.get("reason", ""))
        )
        self.enabled_var = tk.BooleanVar(
            value=bool(self.initial_rule.get("enabled", True))
        )

        self.build_ui()
        self.value_entry.focus_set()

        self.bind("<Return>", lambda _event: self.save())
        self.bind("<Escape>", lambda _event: self.cancel())

    def build_ui(self) -> None:
        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)

        root.columnconfigure(1, weight=1)

        ttk.Label(root, text="Rule type:").grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 8),
        )

        ttk.Combobox(
            root,
            textvariable=self.rule_type_var,
            values=ACTIVITY_RULE_TYPES,
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(root, text="Value:").grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 8),
        )

        self.value_entry = ttk.Entry(root, textvariable=self.value_var)
        self.value_entry.grid(row=1, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(root, text="Category:").grid(
            row=2,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 8),
        )

        ttk.Combobox(
            root,
            textvariable=self.category_var,
            values=ACTIVITY_CATEGORIES,
            state="readonly",
        ).grid(row=2, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(root, text="Reason / note:").grid(
            row=3,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 8),
        )

        ttk.Entry(root, textvariable=self.reason_var).grid(
            row=3,
            column=1,
            sticky="ew",
            pady=(0, 8),
        )

        ttk.Checkbutton(
            root,
            text="Enabled",
            variable=self.enabled_var,
        ).grid(row=4, column=1, sticky="w", pady=(0, 12))

        ttk.Label(
            root,
            text="Manual rules override built-in rules.",
            foreground="gray",
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 12))

        buttons = ttk.Frame(root)
        buttons.grid(row=6, column=0, columnspan=2, sticky="ew")

        ttk.Button(buttons, text="Save", command=self.save).pack(side="right")
        ttk.Button(buttons, text="Cancel", command=self.cancel).pack(
            side="right",
            padx=(0, 8),
        )

    def save(self) -> None:
        rule_type = self.rule_type_var.get().strip()
        raw_value = self.value_var.get().strip()
        category = self.category_var.get().strip()
        reason = self.reason_var.get().strip()
        enabled = bool(self.enabled_var.get())

        normalized_value = normalize_rule_value(rule_type, raw_value)

        if not normalized_value:
            messagebox.showerror(
                "Missing value",
                "Rule value is required.",
                parent=self,
            )
            return

        self.result = {
            "type": rule_type,
            "value": normalized_value,
            "category": category,
            "reason": reason,
            "enabled": enabled,
        }

        self.destroy()

    def cancel(self) -> None:
        self.result = None
        self.destroy()


class LimitRuleDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        initial_rule: dict | None = None,
    ) -> None:
        super().__init__(parent)

        self.result: dict | None = None
        self.initial_rule = initial_rule or {}

        self.title(title)
        self.geometry("640x420")
        self.minsize(580, 380)
        self.resizable(True, True)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self.target_type_var = tk.StringVar(
            value=str(self.initial_rule.get("target_type", "category"))
        )
        self.target_value_var = tk.StringVar(
            value=str(self.initial_rule.get("target_value", "time_wasting"))
        )
        self.period_var = tk.StringVar(
            value=str(self.initial_rule.get("period", "daily"))
        )
        self.limit_minutes_var = tk.StringVar(
            value=str(self.initial_rule.get("limit_minutes", "60"))
        )
        self.severity_var = tk.StringVar(
            value=str(self.initial_rule.get("severity", "warning"))
        )
        self.goal_id_var = tk.StringVar(
            value=str(self.initial_rule.get("goal_id", ""))
        )
        self.reason_var = tk.StringVar(
            value=str(self.initial_rule.get("reason", ""))
        )

        self.build_ui()
        self.target_value_entry.focus_set()

        self.bind("<Return>", lambda _event: self.save())
        self.bind("<Escape>", lambda _event: self.cancel())

    def build_ui(self) -> None:
        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)

        root.columnconfigure(1, weight=1)

        ttk.Label(root, text="Target type:").grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 8),
        )

        ttk.Combobox(
            root,
            textvariable=self.target_type_var,
            values=LIMIT_TARGET_TYPES,
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(root, text="Target value:").grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 8),
        )

        self.target_value_entry = ttk.Entry(
            root,
            textvariable=self.target_value_var,
        )
        self.target_value_entry.grid(row=1, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(
            root,
            text=(
                "Examples: category=time_wasting, process=worldoftanks.exe, "
                "title_contains=WoT Client"
            ),
            foreground="gray",
            wraplength=520,
        ).grid(row=2, column=1, sticky="w", pady=(0, 12))

        ttk.Label(root, text="Period:").grid(
            row=3,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 8),
        )

        ttk.Combobox(
            root,
            textvariable=self.period_var,
            values=LIMIT_PERIODS,
            state="readonly",
        ).grid(row=3, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(root, text="Limit minutes:").grid(
            row=4,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 8),
        )

        ttk.Entry(root, textvariable=self.limit_minutes_var).grid(
            row=4,
            column=1,
            sticky="ew",
            pady=(0, 8),
        )

        ttk.Label(root, text="Severity:").grid(
            row=5,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 8),
        )

        ttk.Combobox(
            root,
            textvariable=self.severity_var,
            values=LIMIT_SEVERITIES,
            state="readonly",
        ).grid(row=5, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(root, text="Goal ID optional:").grid(
            row=6,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 8),
        )

        ttk.Entry(root, textvariable=self.goal_id_var).grid(
            row=6,
            column=1,
            sticky="ew",
            pady=(0, 8),
        )

        ttk.Label(root, text="Reason / note:").grid(
            row=7,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 8),
        )

        ttk.Entry(root, textvariable=self.reason_var).grid(
            row=7,
            column=1,
            sticky="ew",
            pady=(0, 8),
        )

        ttk.Label(
            root,
            text=(
                "Editing a limit creates a new version and closes the old one. "
                "History is preserved."
            ),
            foreground="gray",
            wraplength=520,
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(0, 12))

        buttons = ttk.Frame(root)
        buttons.grid(row=9, column=0, columnspan=2, sticky="ew")

        ttk.Button(buttons, text="Save", command=self.save).pack(side="right")
        ttk.Button(buttons, text="Cancel", command=self.cancel).pack(
            side="right",
            padx=(0, 8),
        )

    def save(self) -> None:
        target_type = self.target_type_var.get().strip()
        target_value = self.target_value_var.get().strip()
        period = self.period_var.get().strip()
        severity = self.severity_var.get().strip()
        goal_id = self.goal_id_var.get().strip()
        reason = self.reason_var.get().strip()

        try:
            limit_minutes = int(self.limit_minutes_var.get().strip())
        except Exception:
            messagebox.showerror(
                "Invalid minutes",
                "Limit minutes must be an integer.",
                parent=self,
            )
            return

        if limit_minutes <= 0:
            messagebox.showerror(
                "Invalid minutes",
                "Limit minutes must be greater than zero.",
                parent=self,
            )
            return

        if not target_value:
            messagebox.showerror(
                "Missing target",
                "Target value is required.",
                parent=self,
            )
            return

        self.result = {
            "target_type": target_type,
            "target_value": target_value,
            "period": period,
            "limit_minutes": limit_minutes,
            "severity": severity,
            "goal_id": goal_id,
            "reason": reason,
        }

        self.destroy()

    def cancel(self) -> None:
        self.result = None
        self.destroy()


class DashboardTab(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, padding=14)

        self.current_var = tk.StringVar(value="Current: unknown")

        self.build_ui()
        self.refresh()

    def build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))

        ttk.Label(
            top,
            text="Dashboard",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")

        ttk.Button(
            top,
            text="Refresh",
            command=self.refresh,
        ).pack(side="right")

        ttk.Label(
            self,
            textvariable=self.current_var,
            font=("Segoe UI", 10, "bold"),
            wraplength=1000,
        ).pack(anchor="w", pady=(0, 12))

        self.metrics_frame = ttk.Frame(self)
        self.metrics_frame.pack(fill="both", expand=True)

    def clear_metrics(self) -> None:
        for widget in self.metrics_frame.winfo_children():
            widget.destroy()

    def add_section(self, title: str) -> ttk.Frame:
        section = ttk.LabelFrame(
            self.metrics_frame,
            text=title,
            padding=10,
        )
        section.pack(fill="x", pady=(0, 10))
        return section

    def add_text_lines(self, parent: tk.Widget, lines: list[str]) -> None:
        if not lines:
            ttk.Label(
                parent,
                text="No data.",
                foreground="gray",
            ).pack(anchor="w")
            return

        ttk.Label(
            parent,
            text="\n".join(lines),
            justify="left",
        ).pack(anchor="w")

    def refresh(self) -> None:
        state = read_current_state()

        process_name = state.get("process_name") or state.get("process") or ""
        category = state.get("category", "")
        activity_state = state.get("activity_state") or state.get("state") or ""
        session_seconds = (
            state.get("current_session_seconds")
            or state.get("session_seconds")
            or 0
        )
        window_title = state.get("window_title") or state.get("title") or ""

        self.current_var.set(
            f"Current: {process_name} | {category} | {activity_state} | "
            f"session={format_seconds(session_seconds)}\n{window_title}"
        )

        self.clear_metrics()

        try:
            snapshot = get_dashboard_snapshot()
        except Exception as error:
            section = self.add_section("Error")
            ttk.Label(
                section,
                text=str(error),
                foreground="red",
                wraplength=900,
            ).pack(anchor="w")
            return

        today_section = self.add_section(f"Today — {snapshot.get('today', '')}")

        category_lines = []
        for item in snapshot.get("totals_by_category", []):
            category_lines.append(f"{item['category']}: {item['display']}")

        self.add_text_lines(today_section, category_lines)

        state_section = self.add_section("Activity states")

        state_lines = []
        for item in snapshot.get("totals_by_state", []):
            state_lines.append(f"{item['activity_state']}: {item['display']}")

        self.add_text_lines(state_section, state_lines)

        limits_section = self.add_section("Active limits")

        limit_lines = []
        for item in snapshot.get("limit_progress", []):
            limit_lines.append(
                f"{item['target_type']}={item['target_value']}: "
                f"{item['used_display']} / {item['limit_display']} "
                f"({item['percent']}%) [{item['severity']}]"
            )

        self.add_text_lines(limits_section, limit_lines)

        top_section = self.add_section("Top processes today")

        top_lines = []
        for item in snapshot.get("top_processes", []):
            top_lines.append(
                f"{item['process_name']} | {item['category']}: {item['display']}"
            )

        self.add_text_lines(top_section, top_lines)

        unknown_section = self.add_section("Top unknown today")

        unknown_lines = []
        for item in snapshot.get("top_unknown", []):
            title = item["window_title"] or "[no title]"
            unknown_lines.append(
                f"{item['process_name']}: {item['display']} | {title}"
            )

        self.add_text_lines(unknown_section, unknown_lines)


class ActivityRulesTab(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, padding=14)

        self.status_var = tk.StringVar(value="Ready.")

        self.build_ui()
        self.refresh_rules()

    def build_ui(self) -> None:
        ttk.Label(
            self,
            text="Activity Rules",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(
            self,
            text="Built-in rules are visible and read-only. Manual rules override them.",
            wraplength=980,
        ).pack(anchor="w", pady=(0, 12))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 10))

        ttk.Button(
            toolbar,
            text="+ Add rule",
            command=self.add_rule_dialog,
        ).pack(side="left")

        ttk.Button(
            toolbar,
            text="+ Use current app",
            command=self.add_rule_from_current_app,
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            toolbar,
            text="+ Use current title",
            command=self.add_rule_from_current_title,
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            toolbar,
            text="Edit selected",
            command=self.edit_selected_rule,
        ).pack(side="left", padx=(16, 0))

        ttk.Button(
            toolbar,
            text="Delete selected",
            command=self.delete_selected_rule,
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            toolbar,
            text="Refresh",
            command=self.refresh_rules,
        ).pack(side="right")

        self.build_rules_table()

        ttk.Label(
            self,
            textvariable=self.status_var,
            foreground="gray",
        ).pack(anchor="w", pady=(8, 0))

    def build_rules_table(self) -> None:
        table_frame = ttk.LabelFrame(self, text="Current rules", padding=8)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "source",
            "enabled",
            "type",
            "value",
            "category",
            "reason",
        )

        self.rules_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=18,
        )

        for column, title in [
            ("source", "Source"),
            ("enabled", "On"),
            ("type", "Type"),
            ("value", "Value"),
            ("category", "Category"),
            ("reason", "Reason"),
        ]:
            self.rules_tree.heading(column, text=title)

        self.rules_tree.column("source", width=90, anchor="w")
        self.rules_tree.column("enabled", width=48, anchor="center", stretch=False)
        self.rules_tree.column("type", width=140, anchor="w")
        self.rules_tree.column("value", width=280, anchor="w")
        self.rules_tree.column("category", width=140, anchor="w")
        self.rules_tree.column("reason", width=420, anchor="w")

        y_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.rules_tree.yview,
        )

        x_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.rules_tree.xview,
        )

        self.rules_tree.configure(
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set,
        )

        self.rules_tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.rules_tree.bind("<Double-1>", lambda _event: self.edit_selected_rule())

    def get_current_process_and_title(self) -> tuple[str, str]:
        state = read_current_state()

        process_name = (
            state.get("process_name")
            or state.get("process")
            or state.get("current_process")
            or ""
        )

        window_title = (
            state.get("window_title")
            or state.get("title")
            or state.get("current_window_title")
            or ""
        )

        return str(process_name).strip(), str(window_title).strip()

    def get_selected_rule_id(self) -> str | None:
        selected = self.rules_tree.selection()
        return str(selected[0]) if selected else None

    def refresh_rules(self) -> None:
        for row in self.rules_tree.get_children():
            self.rules_tree.delete(row)

        try:
            rules = list_rules(include_builtin=True)
        except Exception as error:
            messagebox.showerror("Load failed", str(error), parent=self)
            self.status_var.set("Failed to load rules.")
            return

        for rule in rules:
            rule_id = str(rule.get("id", ""))

            if not rule_id:
                continue

            self.rules_tree.insert(
                "",
                "end",
                iid=rule_id,
                values=(
                    str(rule.get("source", "manual")),
                    "yes" if bool(rule.get("enabled", True)) else "no",
                    str(rule.get("type", "")),
                    str(rule.get("value", "")),
                    str(rule.get("category", "unknown")),
                    str(rule.get("reason", "")),
                ),
            )

        self.status_var.set(f"Loaded rules: {len(rules)}")

    def find_rule_by_id(self, rule_id: str) -> dict | None:
        try:
            rules = list_rules(include_builtin=True)
        except Exception as error:
            messagebox.showerror("Load failed", str(error), parent=self)
            return None

        for rule in rules:
            if str(rule.get("id", "")) == rule_id:
                return rule

        return None

    def add_rule_dialog(self) -> None:
        dialog = ActivityRuleDialog(
            parent=self,
            title="Add manual rule",
            initial_rule={
                "type": "title_contains",
                "category": "neutral",
                "enabled": True,
            },
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        self.save_dialog_result_as_new_rule(dialog.result)

    def add_rule_from_current_app(self) -> None:
        process_name, window_title = self.get_current_process_and_title()

        if not process_name:
            messagebox.showwarning(
                "No process",
                "Current process name is empty.",
                parent=self,
            )
            return

        dialog = ActivityRuleDialog(
            parent=self,
            title="Add rule from current app",
            initial_rule={
                "type": "process",
                "value": process_name,
                "category": "neutral",
                "reason": f"From current activity: {window_title}",
                "enabled": True,
            },
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        self.save_dialog_result_as_new_rule(dialog.result)

    def add_rule_from_current_title(self) -> None:
        process_name, window_title = self.get_current_process_and_title()

        if not window_title:
            messagebox.showwarning(
                "No title",
                "Current window title is empty.",
                parent=self,
            )
            return

        dialog = ActivityRuleDialog(
            parent=self,
            title="Add rule from current title",
            initial_rule={
                "type": "title_contains",
                "value": window_title,
                "category": "neutral",
                "reason": f"From current process: {process_name}",
                "enabled": True,
            },
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        self.save_dialog_result_as_new_rule(dialog.result)

    def save_dialog_result_as_new_rule(self, result: dict) -> None:
        try:
            saved_rule = add_activity_rule(
                rule_type=result["type"],
                value=result["value"],
                category=result["category"],
                reason=result["reason"],
                enabled=result["enabled"],
            )
        except Exception as error:
            messagebox.showerror("Add failed", str(error), parent=self)
            self.status_var.set("Add failed.")
            return

        saved_rule_id = str(saved_rule.get("id", ""))

        self.refresh_rules()
        self.select_rule(saved_rule_id)
        self.status_var.set(f"Added manual rule: {saved_rule_id}")

    def edit_selected_rule(self) -> None:
        rule_id = self.get_selected_rule_id()

        if not rule_id:
            messagebox.showwarning("No selection", "Select a rule first.", parent=self)
            return

        rule = self.find_rule_by_id(rule_id)

        if rule is None:
            messagebox.showerror("Rule not found", rule_id, parent=self)
            self.refresh_rules()
            return

        if str(rule.get("source", "manual")) == "built_in":
            messagebox.showinfo(
                "Built-in rule",
                (
                    "Built-in rules are read-only.\n\n"
                    "Create a manual rule with the same process/title/domain "
                    "and another category. Manual rules override built-in rules."
                ),
                parent=self,
            )
            return

        dialog = ActivityRuleDialog(
            parent=self,
            title="Edit manual rule",
            initial_rule=rule,
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        try:
            saved_rule = update_activity_rule(
                rule_id=rule_id,
                updates=dialog.result,
            )
        except Exception as error:
            messagebox.showerror("Update failed", str(error), parent=self)
            self.status_var.set("Update failed.")
            return

        saved_rule_id = str(saved_rule.get("id", rule_id))

        self.refresh_rules()
        self.select_rule(saved_rule_id)
        self.status_var.set(f"Updated manual rule: {saved_rule_id}")

    def delete_selected_rule(self) -> None:
        rule_id = self.get_selected_rule_id()

        if not rule_id:
            messagebox.showwarning("No selection", "Select a rule first.", parent=self)
            return

        rule = self.find_rule_by_id(rule_id)

        if rule is None:
            messagebox.showerror("Rule not found", rule_id, parent=self)
            self.refresh_rules()
            return

        if str(rule.get("source", "manual")) == "built_in":
            messagebox.showinfo(
                "Built-in rule",
                "Built-in rules cannot be deleted. Create a manual override instead.",
                parent=self,
            )
            return

        confirm = messagebox.askyesno(
            "Delete rule",
            "Delete selected manual rule?",
            parent=self,
        )

        if not confirm:
            return

        try:
            delete_activity_rule(rule_id)
        except Exception as error:
            messagebox.showerror("Delete failed", str(error), parent=self)
            return

        self.refresh_rules()
        self.status_var.set(f"Deleted manual rule: {rule_id}")

    def select_rule(self, rule_id: str) -> None:
        if not rule_id:
            return

        try:
            self.rules_tree.selection_set(rule_id)
            self.rules_tree.focus(rule_id)
            self.rules_tree.see(rule_id)
        except Exception:
            pass


class LimitsTab(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, padding=14)

        self.status_var = tk.StringVar(value="Ready.")

        self.build_ui()
        self.refresh_limits()

    def build_ui(self) -> None:
        ttk.Label(
            self,
            text="Limits",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(
            self,
            text=(
                "Limits define how much of an activity/category is acceptable. "
                "Editing creates a new version and preserves history."
            ),
            wraplength=980,
        ).pack(anchor="w", pady=(0, 12))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 10))

        ttk.Button(
            toolbar,
            text="+ Add limit",
            command=self.add_limit_dialog,
        ).pack(side="left")

        ttk.Button(
            toolbar,
            text="+ Create starter limits",
            command=self.create_starter_limits,
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            toolbar,
            text="Edit selected",
            command=self.edit_selected_limit,
        ).pack(side="left", padx=(16, 0))

        ttk.Button(
            toolbar,
            text="Pause selected",
            command=self.pause_selected_limit,
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            toolbar,
            text="Delete selected",
            command=self.delete_selected_limit,
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            toolbar,
            text="Refresh",
            command=self.refresh_limits,
        ).pack(side="right")

        self.build_limits_table()

        ttk.Label(
            self,
            textvariable=self.status_var,
            foreground="gray",
        ).pack(anchor="w", pady=(8, 0))

    def build_limits_table(self) -> None:
        table_frame = ttk.LabelFrame(self, text="Limits and history", padding=8)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "status",
            "source",
            "target_type",
            "target_value",
            "period",
            "minutes",
            "severity",
            "active_from",
            "active_to",
            "reason",
        )

        self.limits_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=18,
        )

        headings = {
            "status": "Status",
            "source": "Source",
            "target_type": "Target type",
            "target_value": "Target value",
            "period": "Period",
            "minutes": "Minutes",
            "severity": "Severity",
            "active_from": "Active from",
            "active_to": "Active to",
            "reason": "Reason",
        }

        for column, title in headings.items():
            self.limits_tree.heading(column, text=title)

        self.limits_tree.column("status", width=90, anchor="w")
        self.limits_tree.column("source", width=90, anchor="w")
        self.limits_tree.column("target_type", width=110, anchor="w")
        self.limits_tree.column("target_value", width=180, anchor="w")
        self.limits_tree.column("period", width=80, anchor="w")
        self.limits_tree.column("minutes", width=80, anchor="center")
        self.limits_tree.column("severity", width=90, anchor="w")
        self.limits_tree.column("active_from", width=160, anchor="w")
        self.limits_tree.column("active_to", width=160, anchor="w")
        self.limits_tree.column("reason", width=280, anchor="w")

        y_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.limits_tree.yview,
        )

        x_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.limits_tree.xview,
        )

        self.limits_tree.configure(
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set,
        )

        self.limits_tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.limits_tree.bind("<Double-1>", lambda _event: self.edit_selected_limit())

    def create_starter_limits(self) -> None:
        try:
            created = seed_starter_limits_if_empty()
        except Exception as error:
            messagebox.showerror(
                "Starter limits failed",
                str(error),
                parent=self,
            )
            self.status_var.set("Starter limits failed.")
            return

        self.refresh_limits()

        if created:
            self.status_var.set(f"Created starter limits: {len(created)}")
        else:
            self.status_var.set("Starter limits already exist.")

    def refresh_limits(self) -> None:
        for row in self.limits_tree.get_children():
            self.limits_tree.delete(row)

        try:
            rules = list_limit_rules(include_inactive=True)
        except Exception as error:
            messagebox.showerror("Load failed", str(error), parent=self)
            self.status_var.set("Failed to load limits.")
            return

        for rule in rules:
            rule_id = str(rule.get("id", ""))

            if not rule_id:
                continue

            self.limits_tree.insert(
                "",
                "end",
                iid=rule_id,
                values=(
                    str(rule.get("status", "")),
                    str(rule.get("source", "")),
                    str(rule.get("target_type", "")),
                    str(rule.get("target_value", "")),
                    str(rule.get("period", "")),
                    str(rule.get("limit_minutes", "")),
                    str(rule.get("severity", "")),
                    str(rule.get("active_from", "")),
                    str(rule.get("active_to") or ""),
                    str(rule.get("reason", "")),
                ),
            )

        self.status_var.set(f"Loaded limits/history records: {len(rules)}")

    def get_selected_limit_id(self) -> str | None:
        selected = self.limits_tree.selection()
        return str(selected[0]) if selected else None

    def find_limit_by_id(self, rule_id: str) -> dict | None:
        for rule in list_limit_rules(include_inactive=True):
            if str(rule.get("id", "")) == rule_id:
                return rule

        return None

    def add_limit_dialog(self) -> None:
        dialog = LimitRuleDialog(
            parent=self,
            title="Add limit",
            initial_rule={
                "target_type": "category",
                "target_value": "time_wasting",
                "period": "daily",
                "limit_minutes": 60,
                "severity": "warning",
            },
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        try:
            saved = add_limit_rule(
                target_type=dialog.result["target_type"],
                target_value=dialog.result["target_value"],
                period=dialog.result["period"],
                limit_minutes=dialog.result["limit_minutes"],
                severity=dialog.result["severity"],
                goal_id=dialog.result["goal_id"],
                reason=dialog.result["reason"],
                source="manual",
            )
        except Exception as error:
            messagebox.showerror("Add failed", str(error), parent=self)
            return

        self.refresh_limits()
        self.select_limit(str(saved.get("id", "")))
        self.status_var.set(f"Added limit: {saved.get('id', '')}")

    def edit_selected_limit(self) -> None:
        rule_id = self.get_selected_limit_id()

        if not rule_id:
            messagebox.showwarning("No selection", "Select a limit first.", parent=self)
            return

        rule = self.find_limit_by_id(rule_id)

        if rule is None:
            messagebox.showerror("Not found", f"Limit not found: {rule_id}", parent=self)
            self.refresh_limits()
            return

        if str(rule.get("status", "")) != "active":
            messagebox.showinfo(
                "Inactive limit",
                "Only active limits can be edited. Old records are history.",
                parent=self,
            )
            return

        dialog = LimitRuleDialog(
            parent=self,
            title="Edit limit",
            initial_rule=rule,
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        try:
            saved = replace_limit_rule(
                rule_id=rule_id,
                updates=dialog.result,
                reason=dialog.result.get("reason", ""),
            )
        except Exception as error:
            messagebox.showerror("Update failed", str(error), parent=self)
            return

        self.refresh_limits()
        self.select_limit(str(saved.get("id", "")))
        self.status_var.set(f"Updated limit version: {saved.get('id', '')}")

    def pause_selected_limit(self) -> None:
        rule_id = self.get_selected_limit_id()

        if not rule_id:
            messagebox.showwarning("No selection", "Select a limit first.", parent=self)
            return

        confirm = messagebox.askyesno(
            "Pause limit",
            "Pause selected active limit?",
            parent=self,
        )

        if not confirm:
            return

        try:
            paused = pause_limit_rule(rule_id, reason="Paused manually")
        except Exception as error:
            messagebox.showerror("Pause failed", str(error), parent=self)
            return

        self.refresh_limits()
        self.select_limit(str(paused.get("id", "")))
        self.status_var.set(f"Paused limit: {rule_id}")

    def delete_selected_limit(self) -> None:
        rule_id = self.get_selected_limit_id()

        if not rule_id:
            messagebox.showwarning("No selection", "Select a limit first.", parent=self)
            return

        confirm = messagebox.askyesno(
            "Delete limit",
            "Mark selected limit as deleted?",
            parent=self,
        )

        if not confirm:
            return

        try:
            deleted = delete_limit_rule(rule_id, reason="Deleted manually")
        except Exception as error:
            messagebox.showerror("Delete failed", str(error), parent=self)
            return

        self.refresh_limits()
        self.select_limit(str(deleted.get("id", "")))
        self.status_var.set(f"Deleted limit: {rule_id}")

    def select_limit(self, rule_id: str) -> None:
        if not rule_id:
            return

        try:
            self.limits_tree.selection_set(rule_id)
            self.limits_tree.focus(rule_id)
            self.limits_tree.see(rule_id)
        except Exception:
            pass


class GoalsTab(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, padding=14)

        self.text = tk.Text(self, wrap="word")
        self.build_ui()
        self.refresh()

    def build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))

        ttk.Label(
            top,
            text="Goals",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")

        ttk.Button(
            top,
            text="Refresh",
            command=self.refresh,
        ).pack(side="right")

        self.text.pack(fill="both", expand=True)

    def refresh(self) -> None:
        self.text.delete("1.0", "end")

        try:
            profile = load_goal_profile()
        except Exception as error:
            self.text.insert("end", f"Failed to load goal profile:\n{error}")
            return

        main_goals = profile.get("main_goals", [])

        if not main_goals:
            self.text.insert("end", "No goals found.")
            return

        for index, goal in enumerate(main_goals, start=1):
            self.text.insert("end", f"{index}. {goal.get('title', '')}\n")
            self.text.insert("end", f"   status: {goal.get('status', '')}\n")
            self.text.insert("end", f"   priority: {goal.get('priority', '')}\n")

            horizon = goal.get("time_horizon", {})
            if isinstance(horizon, dict):
                self.text.insert(
                    "end",
                    f"   time horizon: {horizon.get('type', '')}, "
                    f"review: {horizon.get('review_interval', '')}\n",
                )

            why = goal.get("why", "")
            if why:
                self.text.insert("end", f"   why: {why}\n")

            success = goal.get("success_definition", "")
            if success:
                self.text.insert("end", f"   success: {success}\n")

            subgoals = goal.get("subgoals", [])
            self.text.insert("end", f"   subgoals: {len(subgoals)}\n")

            for subgoal in subgoals:
                self.text.insert("end", f"      - {subgoal.get('title', '')}\n")

            limits = goal.get("limits", [])
            self.text.insert("end", f"   profile limits: {len(limits)}\n")

            for limit in limits:
                self.text.insert("end", f"      - {limit.get('title', '')}\n")

            self.text.insert("end", "\n")


class UnknownReviewTab(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, padding=14)

        self.status_var = tk.StringVar(value="Ready.")
        self.category_var = tk.StringVar(value="neutral")

        self.build_ui()
        self.refresh_unknown()

    def build_ui(self) -> None:
        ttk.Label(
            self,
            text="Unknown Review",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(
            self,
            text=(
                "Review unknown activities and create manual classification rules. "
                "Unknown/private/unclear activity is not punished automatically."
            ),
            wraplength=980,
        ).pack(anchor="w", pady=(0, 12))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 10))

        ttk.Label(toolbar, text="Classify as:").pack(side="left")

        ttk.Combobox(
            toolbar,
            textvariable=self.category_var,
            values=ACTIVITY_CATEGORIES,
            state="readonly",
            width=18,
        ).pack(side="left", padx=(8, 16))

        ttk.Button(
            toolbar,
            text="Create process rule",
            command=self.create_process_rule,
        ).pack(side="left")

        ttk.Button(
            toolbar,
            text="Create title rule",
            command=self.create_title_rule,
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            toolbar,
            text="Refresh",
            command=self.refresh_unknown,
        ).pack(side="right")

        self.build_unknown_table()

        ttk.Label(
            self,
            textvariable=self.status_var,
            foreground="gray",
        ).pack(anchor="w", pady=(8, 0))

    def build_unknown_table(self) -> None:
        table_frame = ttk.LabelFrame(self, text="Unknown activities today", padding=8)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "process_name",
            "seconds",
            "window_title",
        )

        self.unknown_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=18,
        )

        self.unknown_tree.heading("process_name", text="Process")
        self.unknown_tree.heading("seconds", text="Time")
        self.unknown_tree.heading("window_title", text="Window title")

        self.unknown_tree.column("process_name", width=220, anchor="w")
        self.unknown_tree.column("seconds", width=100, anchor="center")
        self.unknown_tree.column("window_title", width=720, anchor="w")

        y_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.unknown_tree.yview,
        )

        x_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.unknown_tree.xview,
        )

        self.unknown_tree.configure(
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set,
        )

        self.unknown_tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.unknown_tree.bind("<Double-1>", lambda _event: self.create_title_rule())

    def refresh_unknown(self) -> None:
        for row in self.unknown_tree.get_children():
            self.unknown_tree.delete(row)

        try:
            unknown_items = get_today_top_unknown(limit=50)
        except Exception as error:
            messagebox.showerror(
                "Load failed",
                str(error),
                parent=self,
            )
            self.status_var.set("Failed to load unknown activities.")
            return

        for index, item in enumerate(unknown_items, start=1):
            process_name = str(item.get("process_name", ""))
            window_title = str(item.get("window_title", ""))
            display = str(item.get("display", ""))

            row_id = f"unknown_{index}"

            self.unknown_tree.insert(
                "",
                "end",
                iid=row_id,
                values=(
                    process_name,
                    display,
                    window_title or "[no title]",
                ),
            )

        self.status_var.set(f"Loaded unknown items: {len(unknown_items)}")

    def get_selected_unknown(self) -> tuple[str, str] | None:
        selected = self.unknown_tree.selection()

        if not selected:
            messagebox.showwarning(
                "No selection",
                "Select an unknown activity first.",
                parent=self,
            )
            return None

        values = self.unknown_tree.item(selected[0], "values")

        if not values or len(values) < 3:
            messagebox.showerror(
                "Invalid selection",
                "Selected row has invalid data.",
                parent=self,
            )
            return None

        process_name = str(values[0]).strip()
        window_title = str(values[2]).strip()

        if window_title == "[no title]":
            window_title = ""

        return process_name, window_title

    def create_process_rule(self) -> None:
        selected = self.get_selected_unknown()

        if selected is None:
            return

        process_name, window_title = selected
        category = self.category_var.get().strip() or "neutral"

        if not process_name:
            messagebox.showwarning(
                "No process",
                "Selected item has empty process name.",
                parent=self,
            )
            return

        confirm = messagebox.askyesno(
            "Create process rule",
            (
                f"Create manual rule?\n\n"
                f"process = {process_name}\n"
                f"category = {category}\n\n"
                f"This will affect all future activity from this process."
            ),
            parent=self,
        )

        if not confirm:
            return

        try:
            saved_rule = add_activity_rule(
                rule_type="process",
                value=process_name,
                category=category,
                reason=f"Created from Unknown Review. Title: {window_title}",
                enabled=True,
            )
        except Exception as error:
            messagebox.showerror(
                "Create rule failed",
                str(error),
                parent=self,
            )
            self.status_var.set("Create process rule failed.")
            return

        self.status_var.set(f"Created process rule: {saved_rule.get('id', '')}")
        self.refresh_unknown()

    def create_title_rule(self) -> None:
        selected = self.get_selected_unknown()

        if selected is None:
            return

        process_name, window_title = selected
        category = self.category_var.get().strip() or "neutral"

        if not window_title:
            messagebox.showwarning(
                "No title",
                "Selected item has empty window title. Use process rule instead.",
                parent=self,
            )
            return

        suggested_title = self.suggest_title_rule_value(window_title)

        dialog = ActivityRuleDialog(
            parent=self,
            title="Create title rule from unknown activity",
            initial_rule={
                "type": "title_contains",
                "value": suggested_title,
                "category": category,
                "reason": f"Created from Unknown Review. Process: {process_name}",
                "enabled": True,
            },
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        try:
            saved_rule = add_activity_rule(
                rule_type=dialog.result["type"],
                value=dialog.result["value"],
                category=dialog.result["category"],
                reason=dialog.result["reason"],
                enabled=dialog.result["enabled"],
            )
        except Exception as error:
            messagebox.showerror(
                "Create rule failed",
                str(error),
                parent=self,
            )
            self.status_var.set("Create title rule failed.")
            return

        self.status_var.set(f"Created title rule: {saved_rule.get('id', '')}")
        self.refresh_unknown()

    def suggest_title_rule_value(self, window_title: str) -> str:
        title = window_title.strip()

        separators = [
            " - Google Chrome",
            " - Microsoft Edge",
            " - Mozilla Firefox",
            " — Mozilla Firefox",
            " — Google Chrome",
        ]

        for separator in separators:
            if separator in title:
                title = title.split(separator)[0].strip()
                break

        if len(title) > 80:
            title = title[:80].strip()

        return title


class ModesTab(ttk.Frame):
    AUTOMATION_LABELS = {
        "Manual": "manual",
        "AI-assisted": "ai_assisted",
    }
    INTERACTION_LABELS = {
        "Silent / Observer": "silent",
        "Standard / Balanced": "standard",
        "Proactive": "proactive",
        "Intensive / Accountability": "intensive",
    }
    COACH_LABELS = {
        "Soft": "soft",
        "Neutral": "neutral",
        "Strict": "strict",
        "Aggressive": "aggressive",
    }

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, padding=14)
        self.settings = load_settings()

        self.automation_var = tk.StringVar()
        self.interaction_var = tk.StringVar()
        self.coach_enabled_var = tk.BooleanVar()
        self.coach_style_var = tk.StringVar()
        self.notifications_var = tk.BooleanVar()
        self.show_popup_var = tk.BooleanVar()
        self.show_badge_var = tk.BooleanVar()
        self.daily_prompt_limit_var = tk.IntVar()
        self.cooldown_minutes_var = tk.IntVar()
        self.summary_var = tk.StringVar()

        self.build_ui()
        self.load_values()

    @staticmethod
    def label_for(mapping: dict[str, str], value: str, fallback: str) -> str:
        for label, mapped_value in mapping.items():
            if mapped_value == value:
                return label
        return fallback

    def build_ui(self) -> None:
        ttk.Label(
            self,
            text="Operating modes",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(0, 4))
        ttk.Label(
            self,
            text=(
                "Automation, interaction intensity and coach tone are independent. "
                "Silent mode never stops data collection."
            ),
            wraplength=900,
        ).pack(anchor="w", pady=(0, 14))

        form = ttk.Frame(self)
        form.pack(fill="x")

        ttk.Label(form, text="Automation:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Combobox(
            form,
            textvariable=self.automation_var,
            values=list(self.AUTOMATION_LABELS),
            state="readonly",
            width=30,
        ).grid(row=0, column=1, sticky="w", padx=(12, 0), pady=5)

        ttk.Label(form, text="Interaction:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Combobox(
            form,
            textvariable=self.interaction_var,
            values=list(self.INTERACTION_LABELS),
            state="readonly",
            width=30,
        ).grid(row=1, column=1, sticky="w", padx=(12, 0), pady=5)

        ttk.Checkbutton(
            form,
            text="Enable coach",
            variable=self.coach_enabled_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(12, 5))

        ttk.Label(form, text="Coach style:").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Combobox(
            form,
            textvariable=self.coach_style_var,
            values=list(self.COACH_LABELS),
            state="readonly",
            width=30,
        ).grid(row=3, column=1, sticky="w", padx=(12, 0), pady=5)

        ttk.Checkbutton(
            form,
            text="Enable warnings and notifications",
            variable=self.notifications_var,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 3))
        ttk.Checkbutton(
            form,
            text="Show popup warnings",
            variable=self.show_popup_var,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=3)
        ttk.Checkbutton(
            form,
            text="Show overlay badge",
            variable=self.show_badge_var,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=3)

        ttk.Label(form, text="Daily AI question limit:").grid(
            row=7, column=0, sticky="w", pady=(12, 5)
        )
        ttk.Spinbox(
            form,
            from_=0,
            to=50,
            textvariable=self.daily_prompt_limit_var,
            width=8,
        ).grid(row=7, column=1, sticky="w", padx=(12, 0), pady=(12, 5))

        ttk.Label(form, text="Question cooldown (minutes):").grid(
            row=8, column=0, sticky="w", pady=5
        )
        ttk.Spinbox(
            form,
            from_=0,
            to=1440,
            textvariable=self.cooldown_minutes_var,
            width=8,
        ).grid(row=8, column=1, sticky="w", padx=(12, 0), pady=5)

        ttk.Button(self, text="Save modes", command=self.save).pack(
            anchor="w", pady=(18, 10)
        )
        ttk.Label(self, textvariable=self.summary_var, wraplength=900).pack(anchor="w")

    def load_values(self) -> None:
        policy = build_interaction_policy(self.settings)
        self.automation_var.set(
            self.label_for(self.AUTOMATION_LABELS, policy.automation_mode, "Manual")
        )
        self.interaction_var.set(
            self.label_for(
                self.INTERACTION_LABELS,
                policy.interaction_mode,
                "Standard / Balanced",
            )
        )
        self.coach_enabled_var.set(policy.coach_enabled)
        self.coach_style_var.set(
            self.label_for(self.COACH_LABELS, policy.coach_style, "Neutral")
        )
        self.notifications_var.set(policy.notifications_enabled)
        self.show_popup_var.set(policy.show_popup)
        self.show_badge_var.set(policy.show_badge)
        self.daily_prompt_limit_var.set(policy.daily_prompt_limit)
        self.cooldown_minutes_var.set(policy.cooldown_minutes)
        self.update_summary(policy)

    def update_summary(self, policy: InteractionPolicy) -> None:
        self.summary_var.set(
            "Effective policy: "
            f"automation={policy.automation_mode}, "
            f"interaction={policy.interaction_mode}, "
            f"coach={'on' if policy.allows_coaching else 'off'}, "
            f"warnings={'on' if policy.allows_warning else 'off'}, "
            f"questions={'on' if policy.allow_questions else 'off'}."
        )

    def save(self) -> None:
        self.settings["automation"]["mode"] = self.AUTOMATION_LABELS.get(
            self.automation_var.get(), "manual"
        )
        self.settings["interaction"]["mode"] = self.INTERACTION_LABELS.get(
            self.interaction_var.get(), "standard"
        )
        try:
            daily_prompt_limit = self.daily_prompt_limit_var.get()
            cooldown_minutes = self.cooldown_minutes_var.get()
        except (tk.TclError, ValueError):
            messagebox.showerror(
                "Invalid mode settings",
                "Question limit and cooldown must be whole numbers.",
                parent=self,
            )
            return

        self.settings["interaction"]["daily_prompt_limit"] = daily_prompt_limit
        self.settings["interaction"]["cooldown_minutes"] = cooldown_minutes
        self.settings["coach"]["enabled"] = bool(self.coach_enabled_var.get())
        self.settings["coach"]["style"] = self.COACH_LABELS.get(
            self.coach_style_var.get(), "neutral"
        )
        self.settings["notifications"]["enabled"] = bool(
            self.notifications_var.get()
        )
        self.settings["overlay"]["show_popup"] = bool(self.show_popup_var.get())
        self.settings["overlay"]["show_badge"] = bool(self.show_badge_var.get())

        save_settings(self.settings)
        self.settings = load_settings()
        self.update_summary(build_interaction_policy(self.settings))
        messagebox.showinfo("Operating modes", "Settings saved.", parent=self)


class PlaceholderTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, title: str, message: str) -> None:
        super().__init__(parent, padding=14)

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(
            self,
            text=message,
            wraplength=900,
        ).pack(anchor="w")


class UpdatesTab(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, padding=14)
        self.status_var = tk.StringVar(value="Update status has not been checked.")
        self.build_ui()

    def build_ui(self) -> None:
        ttk.Label(
            self,
            text="GoalCompass updates",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            self,
            text=f"Installed version: {__version__}",
        ).pack(anchor="w", pady=(0, 6))
        ttk.Label(
            self,
            text=(
                (
                    "Installed builds are updated by running a newer GoalCompass "
                    "Setup file. "
                    if IS_FROZEN
                    else "Updates are downloaded from the configured GitHub repository. "
                )
                +
                "Personal data in data/user_config, runtime state, and the database "
                "are not replaced."
            ),
            wraplength=900,
        ).pack(anchor="w", pady=(0, 12))

        if IS_FROZEN:
            self.status_var.set(
                "To update, close GoalCompass and run the newer Setup executable."
            )
            ttk.Label(self, textvariable=self.status_var, wraplength=900).pack(
                anchor="w"
            )
            return

        actions = ttk.Frame(self)
        actions.pack(anchor="w", pady=(0, 12))
        ttk.Button(
            actions,
            text="Check for updates",
            command=self.check,
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Install update",
            command=self.install,
        ).pack(side="left", padx=(8, 0))

        ttk.Label(self, textvariable=self.status_var, wraplength=900).pack(anchor="w")
        ttk.Label(
            self,
            text=(
                "Close the tracker and overlay before installing. Restart "
                "GoalCompass after a successful update."
            ),
            wraplength=900,
        ).pack(anchor="w", pady=(12, 0))

    def check(self) -> None:
        self.configure(cursor="wait")
        self.update_idletasks()
        try:
            status = check_for_updates(fetch=True)
        except UpdateError as error:
            self.status_var.set(f"Update check failed: {error}")
            messagebox.showerror("Update check failed", str(error), parent=self)
            return
        finally:
            self.configure(cursor="")

        if status.update_available:
            self.status_var.set(
                f"Version {status.remote_version} is available "
                f"({status.commits_behind} commit(s) behind)."
            )
        else:
            self.status_var.set(
                f"GoalCompass is up to date ({status.local_version})."
            )

    def install(self) -> None:
        if not messagebox.askyesno(
            "Install GoalCompass update?",
            (
                "Install the newest version from GitHub?\n\n"
                "Close the tracker and overlay first. Personal data is preserved."
            ),
            parent=self,
        ):
            return

        self.configure(cursor="wait")
        self.update_idletasks()
        try:
            status = install_update()
        except UpdateError as error:
            self.status_var.set(f"Update failed: {error}")
            messagebox.showerror("Update failed", str(error), parent=self)
            return
        finally:
            self.configure(cursor="")

        if status.update_available:
            self.status_var.set(
                "Update is still available. Close GoalCompass and try again."
            )
            return

        self.status_var.set(
            f"Updated to {status.local_version}. Restart GoalCompass now."
        )
        messagebox.showinfo(
            "Update installed",
            f"GoalCompass {status.local_version} is installed. Restart the app.",
            parent=self,
        )


class GoalCompassControlCenter(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("GoalCompass Control Center")
        self.geometry("1180x760")
        self.minsize(960, 620)
        self.resizable(True, True)

        self.build_ui()

    def build_ui(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)

        ttk.Label(
            root,
            text="GoalCompass Control Center",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)

        notebook.add(DashboardTab(notebook), text="Dashboard")
        notebook.add(ActivityRulesTab(notebook), text="Activity Rules")
        notebook.add(LimitsTab(notebook), text="Limits")
        notebook.add(GoalsTab(notebook), text="Goals")
        notebook.add(UnknownReviewTab(notebook), text="Unknown Review")
        notebook.add(AIAssistantTab(notebook), text="AI Assistant")
        notebook.add(ModesTab(notebook), text="Modes")
        notebook.add(UpdatesTab(notebook), text="Updates")
        notebook.add(
            PlaceholderTab(
                notebook,
                title="Manual Activity",
                message=(
                    "Later: add offline activities such as German lesson, workout, "
                    "family time, reading, rest."
                ),
            ),
            text="Manual Activity",
        )


def main() -> None:
    app = GoalCompassControlCenter()
    app.mainloop()


if __name__ == "__main__":
    main()
