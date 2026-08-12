from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk

from src.services.ai_proposal_service import (
    apply_ai_proposal,
    build_ai_proposal_preview,
    build_ai_proposal_prompt,
    parse_ai_proposal_json,
)


class AIAssistantTab(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, padding=14)
        self.validated_proposal: dict | None = None
        self.build_ui()

    def build_ui(self) -> None:
        ttk.Label(
            self,
            text="AI-assisted configuration",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(0, 4))
        ttk.Label(
            self,
            text=(
                "AI can propose goal and mode changes, but GoalCompass validates and "
                "previews them before anything is applied."
            ),
            wraplength=950,
        ).pack(anchor="w", pady=(0, 10))
        ttk.Label(
            self,
            text=(
                "Privacy: the copied prompt includes your current goals and operating "
                "modes. Review it before pasting it into an external AI service."
            ),
            wraplength=950,
        ).pack(anchor="w", pady=(0, 10))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(
            toolbar,
            text="Copy proposal prompt",
            command=self.copy_prompt,
        ).pack(side="left")
        ttk.Button(
            toolbar,
            text="Validate and preview",
            command=self.validate_and_preview,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            toolbar,
            text="Apply validated proposal",
            command=self.apply_validated,
        ).pack(side="left", padx=(8, 0))

        panes = ttk.Panedwindow(self, orient="horizontal")
        panes.pack(fill="both", expand=True)

        input_frame = ttk.LabelFrame(panes, text="AI proposal JSON", padding=8)
        preview_frame = ttk.LabelFrame(panes, text="Local preview", padding=8)
        panes.add(input_frame, weight=1)
        panes.add(preview_frame, weight=1)

        self.proposal_text = tk.Text(input_frame, wrap="none", undo=True)
        self.proposal_text.pack(fill="both", expand=True)

        self.preview_text = tk.Text(
            preview_frame,
            wrap="none",
            state="disabled",
            bg="#f4f4f4",
        )
        self.preview_text.pack(fill="both", expand=True)

        self.status_var = tk.StringVar(
            value="No proposal validated. Existing data has not been changed."
        )
        ttk.Label(self, textvariable=self.status_var, wraplength=950).pack(
            anchor="w", pady=(8, 0)
        )

    def set_preview(self, text: str) -> None:
        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", text)
        self.preview_text.config(state="disabled")

    def copy_prompt(self) -> None:
        try:
            prompt = build_ai_proposal_prompt()
        except Exception as error:
            messagebox.showerror("Cannot build AI prompt", str(error), parent=self)
            return

        self.clipboard_clear()
        self.clipboard_append(prompt)
        self.update()
        self.status_var.set(
            "Prompt copied. Paste it into an AI, then paste the returned JSON here."
        )

    def validate_and_preview(self) -> None:
        raw = self.proposal_text.get("1.0", "end").strip()
        try:
            proposal = parse_ai_proposal_json(raw)
            preview = build_ai_proposal_preview(proposal)
        except Exception as error:
            self.validated_proposal = None
            self.set_preview("")
            messagebox.showerror("Invalid AI proposal", str(error), parent=self)
            return

        self.validated_proposal = proposal
        self.proposal_text.delete("1.0", "end")
        self.proposal_text.insert(
            "1.0",
            json.dumps(proposal, ensure_ascii=False, indent=2),
        )
        self.set_preview(preview)
        self.status_var.set(
            "Proposal is valid. Review the complete diff before applying it."
        )

    def apply_validated(self) -> None:
        if self.validated_proposal is None:
            messagebox.showwarning(
                "No validated proposal",
                "Validate and preview the JSON first.",
                parent=self,
            )
            return

        confirmed = messagebox.askyesno(
            "Apply AI proposal?",
            (
                "Apply the validated changes shown in the preview?\n\n"
                "The previous goal profile will be archived and an AI audit record "
                "will be created."
            ),
            parent=self,
        )
        if not confirmed:
            self.status_var.set("Proposal was not applied.")
            return

        try:
            audit_path = apply_ai_proposal(
                self.validated_proposal,
                confirmed=True,
            )
        except Exception as error:
            messagebox.showerror("AI proposal failed", str(error), parent=self)
            return

        self.status_var.set(f"Proposal applied. Audit: {audit_path.name}")
        messagebox.showinfo(
            "AI proposal applied",
            f"Changes saved. Audit record: {audit_path.name}",
            parent=self,
        )
