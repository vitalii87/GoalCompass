# gui/activity_rules_panel.py

from __future__ import annotations

import json
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


ROOT_DIR = Path(__file__).resolve().parents[1]
CURRENT_STATE_PATH = ROOT_DIR / "data" / "runtime" / "current_state.json"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.services.activity_rules_service import (  # noqa: E402
    add_activity_rule,
    delete_activity_rule,
    list_rules,
    normalize_rule_value,
    update_activity_rule,
)


RULE_TYPES = [
    "process",
    "title_contains",
    "domain",
    "url_contains",
]

CATEGORIES = [
    "productive",
    "personal",
    "neutral",
    "distracting",
    "time_wasting",
    "unknown",
    "ignored",
]


RULE_TYPE_EXPLANATIONS = {
    "process": (
        "Exact app process name.\n\n"
        "Best for apps and games.\n\n"
        "Examples:\n"
        "worldoftanks.exe\n"
        "wgc.exe\n"
        "chrome.exe\n"
        "pycharm64.exe\n\n"
        "Important: process rules need the real .exe name."
    ),
    "title_contains": (
        "Text inside the window title.\n\n"
        "Best for browser tabs and pages when URL is not available.\n\n"
        "Examples:\n"
        "ChatGPT\n"
        "Deutsch\n"
        "LinkedIn\n"
        "WoT Client"
    ),
    "domain": (
        "Website domain.\n\n"
        "Examples:\n"
        "github.com\n"
        "youtube.com\n"
        "chatgpt.com\n\n"
        "You may paste full URL; GoalCompass will trim it.\n\n"
        "Note: this will work best later with browser extension."
    ),
    "url_contains": (
        "Part of a URL.\n\n"
        "Examples:\n"
        "/jobs/\n"
        "/watch\n"
        "/search\n\n"
        "This is mostly for future browser-extension mode."
    ),
}


RULE_TYPE_HINTS = {
    "process": "Example: worldoftanks.exe, wgc.exe, chrome.exe, pycharm64.exe",
    "title_contains": "Example: ChatGPT, Deutsch, LinkedIn, WoT Client",
    "domain": "Example: github.com, youtube.com, chatgpt.com. Full URLs will be trimmed.",
    "url_contains": "Future browser-extension mode. Example: /jobs/ or /watch",
}


class RuleDialog(tk.Toplevel):
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
        self.update_hint()

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

        type_row = ttk.Frame(root)
        type_row.grid(row=0, column=1, sticky="ew", pady=(0, 8))
        type_row.columnconfigure(0, weight=1)

        self.rule_type_combo = ttk.Combobox(
            type_row,
            textvariable=self.rule_type_var,
            values=RULE_TYPES,
            state="readonly",
            width=24,
        )
        self.rule_type_combo.grid(row=0, column=0, sticky="ew")
        self.rule_type_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self.update_hint(),
        )

        ttk.Button(
            type_row,
            text="?",
            width=3,
            command=self.show_rule_type_help,
        ).grid(row=0, column=1, padx=(8, 0))

        ttk.Label(root, text="Value:").grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 4),
        )

        self.value_entry = ttk.Entry(
            root,
            textvariable=self.value_var,
        )
        self.value_entry.grid(row=1, column=1, sticky="ew", pady=(0, 4))

        self.hint_label = ttk.Label(
            root,
            text="",
            foreground="gray",
            wraplength=500,
        )
        self.hint_label.grid(row=2, column=1, sticky="w", pady=(0, 12))

        ttk.Label(root, text="Category:").grid(
            row=3,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 8),
        )

        self.category_combo = ttk.Combobox(
            root,
            textvariable=self.category_var,
            values=CATEGORIES,
            state="readonly",
            width=24,
        )
        self.category_combo.grid(row=3, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(root, text="Reason / note:").grid(
            row=4,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 8),
        )

        ttk.Entry(
            root,
            textvariable=self.reason_var,
        ).grid(row=4, column=1, sticky="ew", pady=(0, 8))

        ttk.Checkbutton(
            root,
            text="Enabled",
            variable=self.enabled_var,
        ).grid(row=5, column=1, sticky="w", pady=(0, 12))

        ttk.Label(
            root,
            text="Manual rules override built-in rules.",
            foreground="gray",
            wraplength=520,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 12))

        buttons = ttk.Frame(root)
        buttons.grid(row=7, column=0, columnspan=2, sticky="ew")

        ttk.Button(
            buttons,
            text="Save",
            command=self.save,
        ).pack(side="right")

        ttk.Button(
            buttons,
            text="Cancel",
            command=self.cancel,
        ).pack(side="right", padx=(0, 8))

    def update_hint(self) -> None:
        rule_type = self.rule_type_var.get()
        self.hint_label.config(text=RULE_TYPE_HINTS.get(rule_type, ""))

    def show_rule_type_help(self) -> None:
        rule_type = self.rule_type_var.get()
        messagebox.showinfo(
            f"Rule type: {rule_type}",
            RULE_TYPE_EXPLANATIONS.get(rule_type, "No explanation available."),
            parent=self,
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


class ActivityRulesPanel(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("GoalCompass Activity Rules")
        self.geometry("1120x680")
        self.minsize(900, 560)
        self.resizable(True, True)

        self.status_var = tk.StringVar(value="Ready.")

        self.build_ui()
        self.refresh_rules()

    def build_ui(self) -> None:
        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)

        title_row = ttk.Frame(root)
        title_row.pack(fill="x", pady=(0, 8))

        ttk.Label(
            title_row,
            text="Activity Rules",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")

        ttk.Button(
            title_row,
            text="Help",
            command=self.show_help,
        ).pack(side="right")

        ttk.Label(
            root,
            text=(
                "Built-in rules are visible and read-only. Manual rules override them. "
                "Unknown/private/unclear activity stays unknown unless you classify it."
            ),
            wraplength=1020,
        ).pack(anchor="w", pady=(0, 12))

        toolbar = ttk.Frame(root)
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

        self.build_rules_table(root)

        ttk.Label(
            root,
            textvariable=self.status_var,
            foreground="gray",
        ).pack(anchor="w", pady=(8, 0))

    def build_rules_table(self, parent: tk.Widget) -> None:
        table_frame = ttk.LabelFrame(parent, text="Current rules", padding=8)
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

        self.rules_tree.heading("source", text="Source")
        self.rules_tree.heading("enabled", text="On")
        self.rules_tree.heading("type", text="Type")
        self.rules_tree.heading("value", text="Value")
        self.rules_tree.heading("category", text="Category")
        self.rules_tree.heading("reason", text="Reason")

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

    def read_current_activity(self) -> dict:
        if not CURRENT_STATE_PATH.exists():
            raise FileNotFoundError(
                f"Current state file not found: {CURRENT_STATE_PATH}"
            )

        raw = CURRENT_STATE_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)

        if not isinstance(data, dict):
            raise ValueError("current_state.json root must be object")

        return data

    def get_current_process_and_title(self) -> tuple[str, str]:
        data = self.read_current_activity()

        process_name = (
            data.get("process_name")
            or data.get("process")
            or data.get("current_process")
            or ""
        )

        window_title = (
            data.get("window_title")
            or data.get("title")
            or data.get("current_window_title")
            or ""
        )

        return str(process_name).strip(), str(window_title).strip()

    def get_selected_rule_id(self) -> str | None:
        selected = self.rules_tree.selection()

        if not selected:
            return None

        return str(selected[0])

    def refresh_rules(self) -> None:
        for row in self.rules_tree.get_children():
            self.rules_tree.delete(row)

        try:
            rules = list_rules(include_builtin=True)
        except Exception as error:
            messagebox.showerror(
                "Load failed",
                str(error),
                parent=self,
            )
            self.status_var.set("Failed to load rules.")
            return

        for rule in rules:
            rule_id = str(rule.get("id", ""))

            if not rule_id:
                continue

            source = str(rule.get("source", "manual"))
            enabled = "yes" if bool(rule.get("enabled", True)) else "no"
            rule_type = str(rule.get("type", ""))
            value = str(rule.get("value", ""))
            category = str(rule.get("category", "unknown"))
            reason = str(rule.get("reason", ""))

            self.rules_tree.insert(
                "",
                "end",
                iid=rule_id,
                values=(
                    source,
                    enabled,
                    rule_type,
                    value,
                    category,
                    reason,
                ),
            )

        self.status_var.set(f"Loaded rules: {len(rules)}")

    def find_rule_by_id(self, rule_id: str) -> dict | None:
        try:
            rules = list_rules(include_builtin=True)
        except Exception as error:
            messagebox.showerror(
                "Load failed",
                str(error),
                parent=self,
            )
            return None

        for rule in rules:
            if str(rule.get("id", "")) == rule_id:
                return rule

        return None

    def add_rule_dialog(self) -> None:
        dialog = RuleDialog(
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
        try:
            process_name, window_title = self.get_current_process_and_title()
        except Exception as error:
            messagebox.showerror(
                "Current activity unavailable",
                str(error),
                parent=self,
            )
            return

        if not process_name:
            messagebox.showwarning(
                "No process",
                "Current process name is empty.",
                parent=self,
            )
            return

        dialog = RuleDialog(
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
        try:
            process_name, window_title = self.get_current_process_and_title()
        except Exception as error:
            messagebox.showerror(
                "Current activity unavailable",
                str(error),
                parent=self,
            )
            return

        if not window_title:
            messagebox.showwarning(
                "No title",
                "Current window title is empty.",
                parent=self,
            )
            return

        dialog = RuleDialog(
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
            messagebox.showerror(
                "Add failed",
                str(error),
                parent=self,
            )
            self.status_var.set("Add failed.")
            return

        saved_rule_id = str(saved_rule.get("id", ""))

        self.refresh_rules()
        self.select_rule(saved_rule_id)
        self.status_var.set(f"Added manual rule: {saved_rule_id}")

    def edit_selected_rule(self) -> None:
        rule_id = self.get_selected_rule_id()

        if not rule_id:
            messagebox.showwarning(
                "No selection",
                "Select a rule first.",
                parent=self,
            )
            return

        rule = self.find_rule_by_id(rule_id)

        if rule is None:
            messagebox.showerror(
                "Rule not found",
                f"Rule not found: {rule_id}",
                parent=self,
            )
            self.refresh_rules()
            return

        if str(rule.get("source", "manual")) == "built_in":
            messagebox.showinfo(
                "Built-in rule",
                (
                    "Built-in rules are read-only.\n\n"
                    "To change this behavior, create a manual rule with the same "
                    "process/title/domain and another category. Manual rules override built-in rules."
                ),
                parent=self,
            )
            return

        dialog = RuleDialog(
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
            messagebox.showerror(
                "Update failed",
                str(error),
                parent=self,
            )
            self.status_var.set("Update failed.")
            return

        saved_rule_id = str(saved_rule.get("id", rule_id))

        self.refresh_rules()
        self.select_rule(saved_rule_id)
        self.status_var.set(f"Updated manual rule: {saved_rule_id}")

    def delete_selected_rule(self) -> None:
        rule_id = self.get_selected_rule_id()

        if not rule_id:
            messagebox.showwarning(
                "No selection",
                "Select a rule first.",
                parent=self,
            )
            return

        rule = self.find_rule_by_id(rule_id)

        if rule is None:
            messagebox.showerror(
                "Rule not found",
                f"Rule not found: {rule_id}",
                parent=self,
            )
            self.refresh_rules()
            return

        if str(rule.get("source", "manual")) == "built_in":
            messagebox.showinfo(
                "Built-in rule",
                (
                    "Built-in rules cannot be deleted.\n\n"
                    "Create a manual override instead."
                ),
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
            deleted = delete_activity_rule(rule_id)
        except Exception as error:
            messagebox.showerror(
                "Delete failed",
                str(error),
                parent=self,
            )
            self.status_var.set("Delete failed.")
            return

        self.refresh_rules()

        if deleted:
            self.status_var.set(f"Deleted manual rule: {rule_id}")
        else:
            self.status_var.set(f"Rule not found: {rule_id}")

    def select_rule(self, rule_id: str) -> None:
        if not rule_id:
            return

        try:
            self.rules_tree.selection_set(rule_id)
            self.rules_tree.focus(rule_id)
            self.rules_tree.see(rule_id)
        except Exception:
            pass

    def show_help(self) -> None:
        messagebox.showinfo(
            "Activity Rules help",
            (
                "Activity Rules have two sources:\n\n"
                "built_in:\n"
                "  Starter/default GoalCompass rules. Visible but read-only.\n\n"
                "manual:\n"
                "  Rules added by the user. These override built-in rules.\n\n"
                "Buttons:\n\n"
                "+ Add rule:\n"
                "  Create a rule manually.\n\n"
                "+ Use current app:\n"
                "  Reads current_state.json and fills the real process name, "
                "for example worldoftanks.exe or wgc.exe.\n\n"
                "+ Use current title:\n"
                "  Reads the current window title and creates title_contains rule.\n\n"
                "Recommended MVP usage:\n\n"
                "process:\n"
                "  exact app name, e.g. worldoftanks.exe, wgc.exe\n\n"
                "title_contains:\n"
                "  part of window title, e.g. ChatGPT, Deutsch, WoT Client\n\n"
                "domain/url_contains:\n"
                "  mainly for future browser extension support."
            ),
            parent=self,
        )


def main() -> None:
    app = ActivityRulesPanel()
    app.mainloop()


if __name__ == "__main__":
    main()
