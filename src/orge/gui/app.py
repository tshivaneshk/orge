"""
ORGE Desktop GUI Application
Modern, responsive desktop interface built on Tkinter and ttk with worker thread isolation.
Preserves the complete ORGE core pipeline (Planner, Classifier, SafetyValidator, Executor, History).
"""
import sys
import threading
import queue
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

# Modern Color Palette
PALETTE = {
    "bg": "#f8fafc",            # Slate 50
    "card_bg": "#ffffff",       # White
    "sidebar_bg": "#0f172a",    # Slate 900
    "sidebar_text": "#e2e8f0",  # Slate 200
    "sidebar_hover": "#1e293b", # Slate 800
    "sidebar_active": "#3b82f6",# Blue 500
    "primary": "#2563eb",       # Blue 600
    "primary_hover": "#1d4ed8", # Blue 700
    "secondary": "#64748b",     # Slate 500
    "success": "#16a34a",       # Green 600
    "warning": "#d97706",       # Amber 600
    "danger": "#dc2626",        # Red 600
    "border": "#e2e8f0",        # Slate 200
    "text_main": "#0f172a",     # Slate 900
    "text_muted": "#64748b",    # Slate 500
    "accent_bg": "#f1f5f9",     # Slate 100
}

class OrgeGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"ORGE — Safe Folder Organizer v{__version__}")
        self.geometry("960x680")
        self.minsize(820, 560)
        self.configure(bg=PALETTE["bg"])

        # Core subsystems
        self.config_manager = ConfigManager()
        self.classifier = Classifier(self.config_manager)
        self.planner = Planner(self.classifier, self.config_manager)
        self.validator = SafetyValidator()
        self.history_manager = HistoryManager()
        self.executor = FileExecutor(self.history_manager)

        self.current_plan: OperationPlan = None
        self.selected_folder: Path = None
        self.task_queue = queue.Queue()
        self.is_working = False

        self._setup_styles()
        self._build_layout()
        self._poll_task_queue()

    def _setup_styles(self):
        self.style = ttk.Style(self)
        try:
            if "clam" in self.style.theme_names():
                self.style.theme_use("clam")
        except Exception:
            pass

        # Card & frame styles
        self.style.configure("Card.TFrame", background=PALETTE["card_bg"], relief="flat")
        self.style.configure("App.TFrame", background=PALETTE["bg"])
        self.style.configure("Sidebar.TFrame", background=PALETTE["sidebar_bg"])

        # Typography & Labels
        self.style.configure("Header.TLabel", background=PALETTE["card_bg"], foreground=PALETTE["text_main"], font=("Segoe UI", 16, "bold"))
        self.style.configure("Subheader.TLabel", background=PALETTE["card_bg"], foreground=PALETTE["text_muted"], font=("Segoe UI", 10))
        self.style.configure("CardText.TLabel", background=PALETTE["card_bg"], foreground=PALETTE["text_main"], font=("Segoe UI", 10))
        self.style.configure("MutedText.TLabel", background=PALETTE["card_bg"], foreground=PALETTE["text_muted"], font=("Segoe UI", 9))
        self.style.configure("Status.TLabel", background=PALETTE["accent_bg"], foreground=PALETTE["text_muted"], font=("Segoe UI", 9), padding=6)

        # Buttons
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background=PALETTE["primary"], foreground="#ffffff", padding=(14, 8), borderwidth=0)
        self.style.map("Primary.TButton", background=[("active", PALETTE["primary_hover"]), ("disabled", PALETTE["border"])])

        self.style.configure("Secondary.TButton", font=("Segoe UI", 10), background=PALETTE["accent_bg"], foreground=PALETTE["text_main"], padding=(12, 6))
        self.style.map("Secondary.TButton", background=[("active", PALETTE["border"])])

        # Modern Treeview
        self.style.configure("Modern.Treeview", background="#ffffff", fieldbackground="#ffffff", foreground=PALETTE["text_main"], font=("Segoe UI", 9), rowheight=26, borderwidth=0)
        self.style.configure("Modern.Treeview.Heading", font=("Segoe UI", 9, "bold"), background=PALETTE["accent_bg"], foreground=PALETTE["text_main"], relief="flat", padding=(6, 4))
        self.style.map("Modern.Treeview", background=[("selected", "#dbeafe")], foreground=[("selected", "#1e3a8a")])

    def _build_layout(self):
        # Top-level container
        main_box = ttk.Frame(self, style="App.TFrame")
        main_box.pack(fill=tk.BOTH, expand=True)

        # Left Sidebar Navigation
        self.sidebar = tk.Frame(main_box, bg=PALETTE["sidebar_bg"], width=200)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Logo / Brand Header in Sidebar
        brand_frame = tk.Frame(self.sidebar, bg=PALETTE["sidebar_bg"], padx=16, pady=24)
        brand_frame.pack(fill=tk.X)

        tk.Label(brand_frame, text="ORGE", bg=PALETTE["sidebar_bg"], fg="#ffffff", font=("Segoe UI", 20, "bold")).pack(anchor=tk.W)
        tk.Label(brand_frame, text="Safe File Organizer", bg=PALETTE["sidebar_bg"], fg="#94a3b8", font=("Segoe UI", 9)).pack(anchor=tk.W)

        # Nav Buttons container
        nav_container = tk.Frame(self.sidebar, bg=PALETTE["sidebar_bg"], padx=8, pady=10)
        nav_container.pack(fill=tk.X)

        self.nav_buttons = {}
        pages = [
            ("home", "Organize Folder"),
            ("preview", "Preview Plan"),
            ("history", "History & Undo"),
            ("settings", "Settings"),
            ("about", "About ORGE"),
        ]

        for key, label in pages:
            btn = tk.Button(
                nav_container,
                text=label,
                font=("Segoe UI", 10),
                bg=PALETTE["sidebar_bg"],
                fg=PALETTE["sidebar_text"],
                activebackground=PALETTE["sidebar_hover"],
                activeforeground="#ffffff",
                relief=tk.FLAT,
                anchor=tk.W,
                padx=12,
                pady=8,
                cursor="hand2",
                command=lambda k=key: self._switch_page(k)
            )
            btn.pack(fill=tk.X, pady=2)
            self.nav_buttons[key] = btn

        # Bottom sidebar info
        bottom_side = tk.Frame(self.sidebar, bg=PALETTE["sidebar_bg"], padx=16, pady=16)
        bottom_side.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Label(bottom_side, text=f"v{__version__} Stable", bg=PALETTE["sidebar_bg"], fg="#64748b", font=("Segoe UI", 8)).pack(anchor=tk.W)

        # Right Content View Area
        self.content_area = tk.Frame(main_box, bg=PALETTE["bg"])
        self.content_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Status Bar at bottom
        self.status_var = tk.StringVar(value="Ready. Select a folder to begin.")
        self.status_bar = tk.Label(self, textvariable=self.status_var, bg=PALETTE["accent_bg"], fg=PALETTE["text_muted"], font=("Segoe UI", 9), anchor=tk.W, padx=12, pady=6)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Page Frames Dictionary
        self.pages = {}
        self._init_home_page()
        self._init_preview_page()
        self._init_history_page()
        self._init_settings_page()
        self._init_about_page()

        self._switch_page("home")

    def _switch_page(self, page_key):
        # Update nav button highlights
        for key, btn in self.nav_buttons.items():
            if key == page_key:
                btn.configure(bg=PALETTE["sidebar_active"], fg="#ffffff", font=("Segoe UI", 10, "bold"))
            else:
                btn.configure(bg=PALETTE["sidebar_bg"], fg=PALETTE["sidebar_text"], font=("Segoe UI", 10))

        # Show target page
        for key, page in self.pages.items():
            if key == page_key:
                page.pack(fill=tk.BOTH, expand=True)
            else:
                page.pack_forget()

    # --- Page 1: Home Screen ---
    def _init_home_page(self):
        page = tk.Frame(self.content_area, bg=PALETTE["bg"])
        self.pages["home"] = page

        # Hero Card
        card = tk.Frame(page, bg=PALETTE["card_bg"], padx=30, pady=30, highlightbackground=PALETTE["border"], highlightthickness=1)
        card.pack(fill=tk.X, pady=(0, 20))

        tk.Label(card, text="Organize your folders safely", bg=PALETTE["card_bg"], fg=PALETTE["text_main"], font=("Segoe UI", 18, "bold")).pack(anchor=tk.W)
        tk.Label(card, text="Automatically sort loose files into categorized folders with instant rollback protection.", bg=PALETTE["card_bg"], fg=PALETTE["text_muted"], font=("Segoe UI", 10)).pack(anchor=tk.W, pady=(4, 20))

        # Folder Chooser Box
        choose_box = tk.Frame(card, bg=PALETTE["accent_bg"], padx=20, pady=20, highlightbackground=PALETTE["border"], highlightthickness=1)
        choose_box.pack(fill=tk.X)

        self.home_path_var = tk.StringVar(value="")
        self.folder_stats_var = tk.StringVar(value="No folder selected yet.")

        path_row = tk.Frame(choose_box, bg=PALETTE["accent_bg"])
        path_row.pack(fill=tk.X)

        self.path_entry = ttk.Entry(path_row, textvariable=self.home_path_var, font=("Segoe UI", 10))
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        browse_btn = ttk.Button(path_row, text="Browse Folder...", style="Secondary.TButton", command=self._browse_folder)
        browse_btn.pack(side=tk.RIGHT)

        tk.Label(choose_box, textvariable=self.folder_stats_var, bg=PALETTE["accent_bg"], fg=PALETTE["text_muted"], font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(8, 0))

        # Quick Actions
        action_row = tk.Frame(card, bg=PALETTE["card_bg"])
        action_row.pack(fill=tk.X, pady=(20, 0))

        self.scan_btn = ttk.Button(action_row, text="Scan & Preview Changes", style="Primary.TButton", command=self._start_scan_thread)
        self.scan_btn.pack(side=tk.LEFT)

        # Quick Links / Recent Folders Card
        recent_card = tk.Frame(page, bg=PALETTE["card_bg"], padx=24, pady=20, highlightbackground=PALETTE["border"], highlightthickness=1)
        recent_card.pack(fill=tk.BOTH, expand=True)

        tk.Label(recent_card, text="Quick Shortcuts", bg=PALETTE["card_bg"], fg=PALETTE["text_main"], font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))

        shortcuts = [
            ("Downloads", Path.home() / "Downloads"),
            ("Documents", Path.home() / "Documents"),
            ("Desktop", Path.home() / "Desktop"),
        ]

        sc_row = tk.Frame(recent_card, bg=PALETTE["card_bg"])
        sc_row.pack(fill=tk.X)

        for label, p in shortcuts:
            if p.exists():
                b = ttk.Button(sc_row, text=f"📂  {label}", style="Secondary.TButton", command=lambda path=p: self._set_folder(path))
                b.pack(side=tk.LEFT, padx=(0, 10))

    # --- Page 2: Preview & Organize ---
    def _init_preview_page(self):
        page = tk.Frame(self.content_area, bg=PALETTE["bg"])
        self.pages["preview"] = page

        # Header with Summary & Organize Button
        top_card = tk.Frame(page, bg=PALETTE["card_bg"], padx=24, pady=16, highlightbackground=PALETTE["border"], highlightthickness=1)
        top_card.pack(fill=tk.X, pady=(0, 15))

        self.preview_summary_var = tk.StringVar(value="Select a folder and run 'Scan & Preview' to inspect changes.")
        tk.Label(top_card, textvariable=self.preview_summary_var, bg=PALETTE["card_bg"], fg=PALETTE["text_main"], font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)

        self.organize_btn = ttk.Button(top_card, text="Organize Files Now", style="Primary.TButton", state=tk.DISABLED, command=self._start_organize_thread)
        self.organize_btn.pack(side=tk.RIGHT)

        # Treeview Display
        tree_card = tk.Frame(page, bg=PALETTE["card_bg"], padx=10, pady=10, highlightbackground=PALETTE["border"], highlightthickness=1)
        tree_card.pack(fill=tk.BOTH, expand=True)

        cols = ("file", "category", "target", "reason")
        self.plan_tree = ttk.Treeview(tree_card, columns=cols, show="headings", style="Modern.Treeview")
        self.plan_tree.heading("file", text="File Name")
        self.plan_tree.heading("category", text="Category")
        self.plan_tree.heading("target", text="Planned Destination")
        self.plan_tree.heading("reason", text="Matched Rule")

        self.plan_tree.column("file", width=200, anchor=tk.W)
        self.plan_tree.column("category", width=110, anchor=tk.W)
        self.plan_tree.column("target", width=280, anchor=tk.W)
        self.plan_tree.column("reason", width=180, anchor=tk.W)

        scroll = ttk.Scrollbar(tree_card, orient=tk.VERTICAL, command=self.plan_tree.yview)
        self.plan_tree.configure(yscrollcommand=scroll.set)
        self.plan_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    # --- Page 3: History & Undo ---
    def _init_history_page(self):
        page = tk.Frame(self.content_area, bg=PALETTE["bg"])
        self.pages["history"] = page

        top_card = tk.Frame(page, bg=PALETTE["card_bg"], padx=24, pady=16, highlightbackground=PALETTE["border"], highlightthickness=1)
        top_card.pack(fill=tk.X, pady=(0, 15))

        tk.Label(top_card, text="Organization History & Rollbacks", bg=PALETTE["card_bg"], fg=PALETTE["text_main"], font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)

        self.undo_btn = ttk.Button(top_card, text="Undo Last Operation", style="Secondary.TButton", command=self._start_undo_thread)
        self.undo_btn.pack(side=tk.RIGHT)

        # History table
        hist_card = tk.Frame(page, bg=PALETTE["card_bg"], padx=10, pady=10, highlightbackground=PALETTE["border"], highlightthickness=1)
        hist_card.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "time", "status", "ops", "folder")
        self.hist_tree = ttk.Treeview(hist_card, columns=cols, show="headings", style="Modern.Treeview")
        self.hist_tree.heading("id", text="Run ID")
        self.hist_tree.heading("time", text="Timestamp")
        self.hist_tree.heading("status", text="Status")
        self.hist_tree.heading("ops", text="Files")
        self.hist_tree.heading("folder", text="Folder")

        self.hist_tree.column("id", width=180)
        self.hist_tree.column("time", width=140)
        self.hist_tree.column("status", width=100)
        self.hist_tree.column("ops", width=60, anchor=tk.E)
        self.hist_tree.column("folder", width=260)

        h_scroll = ttk.Scrollbar(hist_card, orient=tk.VERTICAL, command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=h_scroll.set)
        self.hist_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        h_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._refresh_history_table()

    # --- Page 4: Settings ---
    def _init_settings_page(self):
        page = tk.Frame(self.content_area, bg=PALETTE["bg"])
        self.pages["settings"] = page

        card = tk.Frame(page, bg=PALETTE["card_bg"], padx=30, pady=30, highlightbackground=PALETTE["border"], highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True)

        tk.Label(card, text="Application Settings", bg=PALETTE["card_bg"], fg=PALETTE["text_main"], font=("Segoe UI", 14, "bold")).pack(anchor=tk.W, pady=(0, 15))

        self.recursive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(card, text="Enable Recursive Scanning (search subdirectories)", variable=self.recursive_var).pack(anchor=tk.W, pady=6)

        age_row = tk.Frame(card, bg=PALETTE["card_bg"])
        age_row.pack(fill=tk.X, pady=10)
        tk.Label(age_row, text="Only move files older than (days):", bg=PALETTE["card_bg"], font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 10))
        self.days_var = tk.IntVar(value=0)
        ttk.Spinbox(age_row, from_=0, to=3650, textvariable=self.days_var, width=6).pack(side=tk.LEFT)

        tk.Label(card, text="Configuration File Location:", bg=PALETTE["card_bg"], fg=PALETTE["text_muted"], font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(20, 2))
        tk.Label(card, text=str(self.config_manager.config_path), bg=PALETTE["card_bg"], fg=PALETTE["text_main"], font=("Segoe UI", 9)).pack(anchor=tk.W)

    # --- Page 5: About ---
    def _init_about_page(self):
        page = tk.Frame(self.content_area, bg=PALETTE["bg"])
        self.pages["about"] = page

        card = tk.Frame(page, bg=PALETTE["card_bg"], padx=30, pady=30, highlightbackground=PALETTE["border"], highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True)

        tk.Label(card, text=f"ORGE v{__version__}", bg=PALETTE["card_bg"], fg=PALETTE["text_main"], font=("Segoe UI", 16, "bold")).pack(anchor=tk.W)
        tk.Label(card, text="Safe, Deterministic, Cross-Platform File Organization Engine", bg=PALETTE["card_bg"], fg=PALETTE["text_muted"], font=("Segoe UI", 10)).pack(anchor=tk.W, pady=(4, 15))

        info_text = (
            "• Pure client-side local execution: Your files never leave your computer.\n"
            "• Deterministic collision prevention: Renames collisions before any moves occur.\n"
            "• Eight-point safety pipeline: Blocks path traversal, symlink loops, and system roots.\n"
            "• Atomic history records: Full undo rollback capability.\n\n"
            "Licensed under the MIT License."
        )
        tk.Label(card, text=info_text, bg=PALETTE["card_bg"], fg=PALETTE["text_main"], font=("Segoe UI", 9), justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 20))

    # --- Threading & UI Handlers ---
    def _poll_task_queue(self):
        try:
            while True:
                task_fn = self.task_queue.get_nowait()
                task_fn()
        except queue.Empty:
            pass
        self.after(50, self._poll_task_queue)

    def _browse_folder(self):
        initial = self.home_path_var.get() or str(Path.home())
        chosen = filedialog.askdirectory(initialdir=initial)
        if chosen:
            self._set_folder(Path(chosen))

    def _set_folder(self, path: Path):
        self.selected_folder = path.resolve()
        self.home_path_var.set(str(self.selected_folder))
        # Update file count quick metric
        try:
            count = sum(1 for p in self.selected_folder.iterdir() if p.is_file())
            self.folder_stats_var.set(f"Selected: {self.selected_folder.name} ({count} loose files ready to evaluate)")
        except Exception:
            self.folder_stats_var.set(f"Selected: {self.selected_folder}")

    def _start_scan_thread(self):
        folder_str = self.home_path_var.get()
        if not folder_str:
            messagebox.showwarning("No Folder Selected", "Please select a folder to organize first.")
            return

        target = Path(folder_str).resolve()
        if not target.exists() or not target.is_dir():
            messagebox.showerror("Invalid Path", f"'{target}' is not a valid directory.")
            return

        self.selected_folder = target
        self.status_var.set("Scanning directory and evaluating safety constraints...")
        self.scan_btn.config(state=tk.DISABLED)

        # Worker thread
        threading.Thread(target=self._worker_scan, args=(target,), daemon=True).start()

    def _worker_scan(self, target: Path):
        plan = self.planner.create_plan(
            target_folder=target,
            days_threshold=self.days_var.get(),
            recursive=self.recursive_var.get()
        )
        validation = self.validator.validate(plan)

        def on_complete():
            self.scan_btn.config(state=tk.NORMAL)
            self.current_plan = plan

            # Clear tree
            for item in self.plan_tree.get_children():
                self.plan_tree.delete(item)

            executable = plan.executable_steps

            for step in executable:
                try:
                    rel_target = step.target_path.relative_to(target)
                except ValueError:
                    rel_target = step.target_path.name
                self.plan_tree.insert("", tk.END, values=(
                    step.source_path.name,
                    step.category,
                    str(rel_target),
                    step.reason
                ))

            if not validation.is_safe:
                errs = "\n".join(i.message for i in validation.issues if i.severity == "ERROR")
                messagebox.showerror("Safety Restriction", f"Cannot organize folder:\n\n{errs}")
                self.preview_summary_var.set("Plan generated with safety errors. Organizing blocked.")
                self.organize_btn.config(state=tk.DISABLED)
                self.status_var.set("Safety validation failed.")
                return

            if not executable:
                self.preview_summary_var.set("All files are already organized! No actions required.")
                self.organize_btn.config(state=tk.DISABLED)
                self.status_var.set("Directory is clean and organized.")
            else:
                self.preview_summary_var.set(f"{len(executable)} file(s) staged to move safely.")
                self.organize_btn.config(state=tk.NORMAL)
                self.status_var.set(f"Plan ready: {len(executable)} files staged.")

            # Switch to preview page automatically
            self._switch_page("preview")

        self.task_queue.put(on_complete)

    def _start_organize_thread(self):
        if not self.current_plan or not self.current_plan.executable_steps:
            return

        count = len(self.current_plan.executable_steps)
        if not messagebox.askyesno("Confirm Safe Move", f"Move {count} files into organized category folders?"):
            return

        self.organize_btn.config(state=tk.DISABLED)
        self.status_var.set(f"Safely moving {count} files...")

        threading.Thread(target=self._worker_organize, daemon=True).start()

    def _worker_organize(self):
        successful, errors = self.executor.execute(self.current_plan)

        def on_complete():
            self.organize_btn.config(state=tk.NORMAL)
            self._refresh_history_table()

            if errors:
                err_text = "\n".join(errors[:5])
                messagebox.showwarning("Completed with Errors", f"Moved {len(successful)} files.\nErrors:\n{err_text}")
            else:
                messagebox.showinfo("Success", f"Successfully organized {len(successful)} files!")

            # Re-scan folder to show clean state
            self._start_scan_thread()

        self.task_queue.put(on_complete)

    def _start_undo_thread(self):
        latest = self.history_manager.get_latest_active()
        if not latest:
            messagebox.showinfo("Undo", "No active organization history found to undo.")
            return

        ops_count = len(latest.pending_operations)
        if not messagebox.askyesno("Confirm Undo", f"Safely restore {ops_count} files back to their original locations?"):
            return

        self.undo_btn.config(state=tk.DISABLED)
        self.status_var.set(f"Rolling back {ops_count} files...")

        def worker():
            reverted, errors, record = self.executor.undo_latest()

            def on_done():
                self.undo_btn.config(state=tk.NORMAL)
                self._refresh_history_table()
                if errors:
                    err_text = "\n".join(errors[:5])
                    messagebox.showwarning("Undo Results", f"Restored {reverted} files.\nErrors:\n{err_text}")
                else:
                    messagebox.showinfo("Undo Complete", f"Successfully restored {reverted} files to their original locations!")
                self.status_var.set(f"Rollback complete: {reverted} files restored.")

            self.task_queue.put(on_done)

        threading.Thread(target=worker, daemon=True).start()

    def _refresh_history_table(self):
        for item in self.hist_tree.get_children():
            self.hist_tree.delete(item)

        records = self.history_manager.list_history()
        for r in records[:25]:
            status_text = "Completed" if r.status == "completed_undo" else f"Active ({len(r.pending_operations)})"
            self.hist_tree.insert("", tk.END, values=(
                r.id,
                r.timestamp[:19].replace("T", " "),
                status_text,
                r.total_operations,
                r.target_folder
            ))

def main():
    app = OrgeGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
