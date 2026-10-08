"""
ORGE Desktop GUI Application
Cross-platform desktop interface built on Python standard library Tkinter/ttk.
Uses the identical core architecture (Config, Classifier, Planner, SafetyValidator, Executor, History).
"""
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from orge import __version__, __app_name__
from orge.config.manager import ConfigManager
from orge.classifier.engine import Classifier
from orge.planner.engine import Planner
from orge.safety.validator import SafetyValidator
from orge.history.journal import HistoryManager
from orge.executor.runner import FileExecutor
from orge.core.models import ActionType, OperationPlan

class OrgeGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"ORGE - Folder Organizer v{__version__}")
        self.geometry("900x650")
        self.minsize(750, 500)

        # Shared Core Subsystems
        self.config_manager = ConfigManager()
        self.classifier = Classifier(self.config_manager)
        self.planner = Planner(self.classifier, self.config_manager)
        self.validator = SafetyValidator()
        self.history_manager = HistoryManager()
        self.executor = FileExecutor(self.history_manager)

        self.current_plan: OperationPlan = None
        self._init_ui()

    def _init_ui(self):
        # Configure style
        style = ttk.Style(self)
        try:
            if "clam" in style.theme_names():
                style.theme_use("clam")
        except Exception:
            pass

        # Top Frame: Directory Selection
        top_frame = ttk.LabelFrame(self, text=" Target Directory ", padding=10)
        top_frame.pack(fill=tk.X, padx=15, pady=(10, 5))

        self.folder_var = tk.StringVar(value=str(Path.home()))
        folder_entry = ttk.Entry(top_frame, textvariable=self.folder_var, font=("Segoe UI", 10))
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        browse_btn = ttk.Button(top_frame, text="Browse...", command=self._browse_folder)
        browse_btn.pack(side=tk.RIGHT)

        # Options Frame
        opt_frame = ttk.Frame(self, padding=(15, 5))
        opt_frame.pack(fill=tk.X)

        self.recursive_var = tk.BooleanVar(value=False)
        rec_chk = ttk.Checkbutton(opt_frame, text="Recursive Scan", variable=self.recursive_var)
        rec_chk.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(opt_frame, text="Age Filter (Days):").pack(side=tk.LEFT, padx=(0, 5))
        self.days_var = tk.IntVar(value=0)
        days_spin = ttk.Spinbox(opt_frame, from_=0, to=3650, textvariable=self.days_var, width=6)
        days_spin.pack(side=tk.LEFT, padx=(0, 20))

        scan_btn = ttk.Button(opt_frame, text="Scan & Preview", command=self._on_preview)
        scan_btn.pack(side=tk.LEFT, padx=5)

        self.org_btn = ttk.Button(opt_frame, text="Organize Files", command=self._on_organize, state=tk.DISABLED)
        self.org_btn.pack(side=tk.LEFT, padx=5)

        undo_btn = ttk.Button(opt_frame, text="Undo Last", command=self._on_undo)
        undo_btn.pack(side=tk.RIGHT, padx=5)

        history_btn = ttk.Button(opt_frame, text="History", command=self._show_history)
        history_btn.pack(side=tk.RIGHT, padx=5)

        # Middle Notebook: Plan Tree & Summary
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        # Tab 1: Planned Operations Tree
        tree_frame = ttk.Frame(self.notebook)
        self.notebook.add(tree_frame, text=" Planned Operations ")

        columns = ("file", "category", "target", "reason")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("file", text="File Name")
        self.tree.heading("category", text="Category")
        self.tree.heading("target", text="Target Path")
        self.tree.heading("reason", text="Match Reason")

        self.tree.column("file", width=220, anchor=tk.W)
        self.tree.column("category", width=120, anchor=tk.W)
        self.tree.column("target", width=280, anchor=tk.W)
        self.tree.column("reason", width=180, anchor=tk.W)

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Tab 2: Category Summary Table
        summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(summary_frame, text=" Category Summary ")

        sum_cols = ("category", "count")
        self.summary_tree = ttk.Treeview(summary_frame, columns=sum_cols, show="headings")
        self.summary_tree.heading("category", text="Category")
        self.summary_tree.heading("count", text="File Count")
        self.summary_tree.column("category", width=250, anchor=tk.W)
        self.summary_tree.column("count", width=150, anchor=tk.E)
        self.summary_tree.pack(fill=tk.BOTH, expand=True)

        # Status Bar
        self.status_var = tk.StringVar(value="Ready. Select a folder and click 'Scan & Preview'.")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=6)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _browse_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.folder_var.get())
        if chosen:
            self.folder_var.set(chosen)
            self._on_preview()

    def _on_preview(self):
        target_path = Path(self.folder_var.get()).resolve()
        if not target_path.exists() or not target_path.is_dir():
            messagebox.showerror("Error", f"Invalid directory path: {target_path}")
            return

        self.status_var.set("Scanning directory and generating plan...")
        self.update_idletasks()

        plan = self.planner.create_plan(
            target_folder=target_path,
            days_threshold=self.days_var.get(),
            recursive=self.recursive_var.get()
        )
        validation = self.validator.validate(plan)

        # Clear existing views
        for item in self.tree.get_children():
            self.tree.delete(item)
        for item in self.summary_tree.get_children():
            self.summary_tree.delete(item)

        self.current_plan = plan
        executable = plan.executable_steps

        # Populate tree
        category_counts = {}
        for step in executable:
            try:
                rel_target = step.target_path.relative_to(target_path)
            except ValueError:
                rel_target = step.target_path.name
            self.tree.insert("", tk.END, values=(
                step.source_path.name,
                step.category,
                str(rel_target),
                step.reason
            ))
            category_counts[step.category] = category_counts.get(step.category, 0) + 1

        for cat, cnt in sorted(category_counts.items()):
            self.summary_tree.insert("", tk.END, values=(cat, cnt))

        if not validation.is_safe:
            error_msgs = "\n".join(i.message for i in validation.issues if i.severity == "ERROR")
            messagebox.showerror("Safety Violation", f"Cannot organize this folder:\n\n{error_msgs}")
            self.org_btn.config(state=tk.DISABLED)
            self.status_var.set("Plan generated with safety errors. Organizing blocked.")
            return

        if not executable:
            self.status_var.set("All files are already organized! Nothing to move.")
            self.org_btn.config(state=tk.DISABLED)
        else:
            self.org_btn.config(state=tk.NORMAL)
            self.status_var.set(f"Plan ready: {len(executable)} files staged for organization.")

    def _on_organize(self):
        if not self.current_plan or not self.current_plan.executable_steps:
            return

        step_count = len(self.current_plan.executable_steps)
        if not messagebox.askyesno("Confirm Organization", f"Move {step_count} files into categorized folders?"):
            return

        self.status_var.set(f"Organizing {step_count} files...")
        self.update_idletasks()

        successful, errors = self.executor.execute(self.current_plan)

        if errors:
            err_text = "\n".join(errors[:5])
            if len(errors) > 5:
                err_text += f"\n...and {len(errors) - 5} more."
            messagebox.showwarning("Execution Completed with Errors", f"Moved {len(successful)} files.\nErrors:\n{err_text}")
        else:
            messagebox.showinfo("Success", f"Successfully organized {len(successful)} files!")

        self._on_preview()

    def _on_undo(self):
        latest = self.history_manager.get_latest_active()
        if not latest:
            messagebox.showinfo("Undo", "No active organization history found to undo.")
            return

        ops_count = len(latest.pending_operations)
        if not messagebox.askyesno("Confirm Undo", f"Revert previous run ({ops_count} files) to original locations?"):
            return

        reverted, errors, record = self.executor.undo_latest()
        if errors:
            err_text = "\n".join(errors[:5])
            messagebox.showwarning("Undo Results", f"Restored {reverted} files.\nErrors:\n{err_text}")
        else:
            messagebox.showinfo("Undo Complete", f"Successfully restored {reverted} files!")

        self._on_preview()

    def _show_history(self):
        records = self.history_manager.list_history()
        win = tk.Toplevel(self)
        win.title("ORGE Run History")
        win.geometry("600x350")

        cols = ("id", "time", "ops", "folder")
        t = ttk.Treeview(win, columns=cols, show="headings")
        t.heading("id", text="Run ID")
        t.heading("time", text="Timestamp")
        t.heading("ops", text="Files")
        t.heading("folder", text="Target Folder")
        t.column("id", width=180)
        t.column("time", width=140)
        t.column("ops", width=60)
        t.column("folder", width=200)

        for r in records[:20]:
            t.insert("", tk.END, values=(r.id, r.timestamp[:19], len(r.pending_operations), r.target_folder))
        t.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

def main():
    app = OrgeGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
