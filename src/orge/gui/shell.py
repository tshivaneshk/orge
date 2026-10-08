"""
orge.gui.shell - Main Window Shell with Signature Background Gradient, Logo & State Machine
Workflow States:
- HOME_IDLE: No folder or folder chosen, idle
- HOME_SCANNING: Background scan + plan + validation running; Review button disabled, scanning indicator visible
- PLAN_READY: Plan computed & validated in memory
- REVIEW: User inspecting changes (Review never rescans filesystem)
- ORGANIZING: File relocation running in background
- COMPLETED: Summary of relocated files
- ERROR: Controlled error dialog, returns to Home or stays on Review

Navigation is locked during HOME_SCANNING, ORGANIZING, and UNDO.
Stale background results are rejected via generation IDs.
"""
from pathlib import Path
from typing import Optional
from enum import Enum
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QStackedWidget, QVBoxLayout, QFileDialog, QApplication
)
from PySide6.QtCore import Qt, QPoint, QSize, QEvent
from PySide6.QtGui import QKeySequence, QShortcut

from orge.gui.tokens import SPACING, LIGHT_PALETTE
from orge.gui.theme import theme_mgr
from orge.gui.gradients import BackgroundGradientWidget
from orge.gui.icons import get_logo_icon
from orge.gui.components import FloatingPillNav, ToastNotification
from orge.gui.screens import (
    HomeScreen, ReviewScreen, OrganizingScreen, CompletedScreen,
    HistoryScreen, SettingsScreen, AboutScreen
)
from orge.gui.adapter import EngineAdapter
from orge.gui.dialogs import ConfirmDialog, UndoConfirmDialog, ErrorDialog
from orge.core.models import OperationPlan, ValidationReport

class AppWorkflowState(str, Enum):
    HOME_IDLE = "HOME_IDLE"
    HOME_SCANNING = "HOME_SCANNING"
    PLAN_READY = "PLAN_READY"
    REVIEW = "REVIEW"
    ORGANIZING = "ORGANIZING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"

class MainWindowShell(QMainWindow):
    """
    Main application shell with pre-rendered gradient wash, floating pill navigation,
    and single-source-of-truth state machine.
    """
    def __init__(self, adapter: Optional[EngineAdapter] = None):
        super().__init__()
        self.adapter = adapter or EngineAdapter()
        self.state: AppWorkflowState = AppWorkflowState.HOME_IDLE

        self.setWindowTitle("ORGE — File Organization")
        self.setWindowIcon(get_logo_icon())
        self.resize(SPACING["default_window_width"], SPACING["default_window_height"])
        self.setMinimumSize(SPACING["min_window_width"], SPACING["min_window_height"])

        # Cached background gradient widget as central root
        self.central_bg = BackgroundGradientWidget(self)
        self.setCentralWidget(self.central_bg)

        self.root_layout = QVBoxLayout(self.central_bg)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # Stacked view router
        self.stack = QStackedWidget(self.central_bg)
        self.stack.setStyleSheet("background: transparent;")
        self.root_layout.addWidget(self.stack)

        # Screens
        self.home_screen = HomeScreen(self)
        self.review_screen = ReviewScreen(self)
        self.organizing_screen = OrganizingScreen(self)
        self.completed_screen = CompletedScreen(self)
        self.history_screen = HistoryScreen(self)
        self.settings_screen = SettingsScreen(self)
        self.settings_screen.set_config(self.adapter.config_manager)
        self.about_screen = AboutScreen(self)

        self.stack.addWidget(self.home_screen)        # 0
        self.stack.addWidget(self.review_screen)      # 1
        self.stack.addWidget(self.organizing_screen)  # 2
        self.stack.addWidget(self.completed_screen)   # 3
        self.stack.addWidget(self.history_screen)     # 4
        self.stack.addWidget(self.settings_screen)    # 5
        self.stack.addWidget(self.about_screen)       # 6

        # Floating Bottom Navigation Bar (anchored inside central_bg)
        self.nav_bar = FloatingPillNav(self.central_bg)
        self.nav_bar.item_selected.connect(self._navigate_to)

        # Connect adapter & screens
        self._connect_adapter()
        self._connect_screens()

        # Keyboard shortcuts Ctrl+1..5
        self._setup_shortcuts()

        # Compile and apply global stylesheet
        self._apply_theme()

        # Initial history load (non-blocking)
        self.adapter.refresh_history_async()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position floating pill nav bottom-center, 24px above bottom edge
        self.nav_bar.adjustSize()
        nav_w = max(550, self.nav_bar.sizeHint().width())
        nav_h = 64
        self.nav_bar.setFixedSize(nav_w, nav_h)
        x = (self.width() - nav_w) // 2
        y = self.height() - nav_h - 24
        self.nav_bar.move(x, y)
        self.nav_bar.raise_()

    def _apply_theme(self):
        p = theme_mgr.palette
        qss = theme_mgr.build_stylesheet(p)
        self.setStyleSheet(qss)

    def _setup_shortcuts(self):
        shortcuts = [
            ("Ctrl+1", "home"),
            ("Ctrl+2", "review"),
            ("Ctrl+3", "history"),
            ("Ctrl+4", "settings"),
            ("Ctrl+5", "about"),
        ]
        for seq, target in shortcuts:
            sc = QShortcut(QKeySequence(seq), self)
            sc.activated.connect(lambda t=target: self._navigate_to(t))

    def _set_workflow_state(self, new_state: AppWorkflowState):
        self.state = new_state
        # Navigation is disabled during active background operations
        is_locked = (new_state in (AppWorkflowState.HOME_SCANNING, AppWorkflowState.ORGANIZING))
        self.nav_bar.setEnabled(not is_locked)
        self.nav_bar.setVisible(new_state != AppWorkflowState.ORGANIZING)

    def _navigate_to(self, key: str):
        # Do not allow navigation while background scanning or organizing
        if self.state in (AppWorkflowState.HOME_SCANNING, AppWorkflowState.ORGANIZING):
            return

        mapping = {
            "home": 0,
            "review": 1,
            "organizing": 2,
            "completed": 3,
            "history": 4,
            "settings": 5,
            "about": 6,
        }
        idx = mapping.get(key, 0)
        self.stack.setCurrentIndex(idx)
        if key in ["home", "review", "history", "settings", "about"]:
            self.nav_bar.set_active(key)

        if key == "home":
            self._set_workflow_state(AppWorkflowState.HOME_IDLE)
        elif key == "review":
            self._set_workflow_state(AppWorkflowState.REVIEW)
        elif key == "history":
            self.adapter.refresh_history_async()

    # -------------------------------------------------------------------------
    # Screen & Engine Signal Connections
    # -------------------------------------------------------------------------
    def _connect_screens(self):
        # Home
        self.home_screen.browse_clicked.connect(self._on_browse_folder)
        self.home_screen.change_folder_clicked.connect(self._on_browse_folder)
        self.home_screen.review_clicked.connect(self._on_start_scan)

        # Review
        self.review_screen.back_clicked.connect(lambda: self._navigate_to("home"))
        self.review_screen.organize_clicked.connect(self._on_confirm_organize)

        # Organizing
        self.organizing_screen.cancel_clicked.connect(self._on_cancel_organizing)

        # Completed
        self.completed_screen.done_clicked.connect(lambda: self._navigate_to("home"))
        self.completed_screen.history_clicked.connect(lambda: self._navigate_to("history"))
        self.completed_screen.undo_clicked.connect(self._on_undo_requested)

        # History
        self.history_screen.undo_requested.connect(self._on_undo_requested)
        self.history_screen.clear_selected_requested.connect(self._on_clear_selected_history)
        self.history_screen.clear_all_requested.connect(self._on_clear_all_history)

    def _connect_adapter(self):
        self.adapter.scan_progress.connect(self._on_scan_progress)
        self.adapter.scan_completed.connect(self._on_scan_completed)
        self.adapter.scan_failed.connect(self._on_scan_failed)

        self.adapter.organize_progress.connect(self.organizing_screen.set_progress)
        self.adapter.organize_completed.connect(self._on_organize_completed)
        self.adapter.organize_failed.connect(self._on_organize_failed)

        self.adapter.undo_completed.connect(self._on_undo_completed)
        self.adapter.undo_failed.connect(self._on_undo_failed)

        self.adapter.history_updated.connect(self.history_screen.set_records)

    # -------------------------------------------------------------------------
    # Handlers
    # -------------------------------------------------------------------------
    def _on_browse_folder(self):
        chosen = QFileDialog.getExistingDirectory(self, "Choose Folder to Organize")
        if chosen:
            folder = Path(chosen).resolve()
            # Fast inspection in a single pass without extra scans
            count, categories = self.adapter.inspect_folder_fast(folder)
            self.home_screen.set_folder(folder, count, categories)
            self._set_workflow_state(AppWorkflowState.HOME_IDLE)

    def _on_start_scan(self):
        if not self.home_screen.current_folder:
            return
        folder = self.home_screen.current_folder

        # 1. Transition state to HOME_SCANNING
        self._set_workflow_state(AppWorkflowState.HOME_SCANNING)
        self.home_screen.set_scanning_state(True)

        # 2. Start ONE background workflow with generation token
        gen_id = self.adapter.next_generation()
        recursive = self.settings_screen.subfolders_chk.isChecked()
        self.adapter.scan_folder_async(folder, days_threshold=0, recursive=recursive, gen_id=gen_id)

    def _on_scan_progress(self, current: int, total: int, gen_id: int):
        if gen_id == self.adapter.current_generation and self.state == AppWorkflowState.HOME_SCANNING:
            self.home_screen.sc_count_lbl.setText(f"Found {current} of {total} files")

    def _on_scan_completed(self, plan: OperationPlan, report: ValidationReport, gen_id: int):
        # Ignore stale generation results
        if gen_id != self.adapter.current_generation:
            return

        self.home_screen.set_scanning_state(False)

        if not report.is_safe:
            self._set_workflow_state(AppWorkflowState.ERROR)
            errs = "\n".join(i.message for i in report.issues if i.severity == "ERROR")
            dlg = ErrorDialog("That folder can't be used", "Windows isn't letting ORGE access it or it is protected.", errs, self)
            dlg.exec()
            self._set_workflow_state(AppWorkflowState.HOME_IDLE)
            return

        # 3. Store plan and transition to Review ONLY when plan is ready
        self._set_workflow_state(AppWorkflowState.PLAN_READY)
        self.review_screen.set_plan(plan)

        # 4. Automatically switch to Review page
        self.stack.setCurrentIndex(1)
        self.nav_bar.set_active("review")
        self._set_workflow_state(AppWorkflowState.REVIEW)

    def _on_scan_failed(self, error_msg: str, gen_id: int):
        if gen_id != self.adapter.current_generation:
            return

        self.home_screen.set_scanning_state(False)
        self._set_workflow_state(AppWorkflowState.ERROR)
        dlg = ErrorDialog("Scan couldn't be completed", "ORGE was unable to read this folder.", error_msg, self)
        dlg.exec()
        self._set_workflow_state(AppWorkflowState.HOME_IDLE)

    def _on_confirm_organize(self):
        plan = self.review_screen.current_plan
        if not plan or not plan.executable_steps:
            return

        self._set_workflow_state(AppWorkflowState.ORGANIZING)
        self.stack.setCurrentIndex(2)
        self.adapter.execute_plan_async(plan)

    def _on_cancel_organizing(self):
        self._set_workflow_state(AppWorkflowState.HOME_IDLE)
        self._navigate_to("history")

    def _on_organize_completed(self, successful: list, errors: list):
        self._set_workflow_state(AppWorkflowState.COMPLETED)
        self.review_screen.reset_state()
        self.completed_screen.set_results(successful, errors)
        self.stack.setCurrentIndex(3)
        self.show_toast(f"{len(successful)} files organized.")

    def _on_organize_failed(self, error_msg: str):
        self._set_workflow_state(AppWorkflowState.ERROR)
        self.stack.setCurrentIndex(1)
        dlg = ErrorDialog("Organization partly failed", "Some files couldn't be moved and remain in place.", error_msg, self)
        dlg.exec()
        self._set_workflow_state(AppWorkflowState.REVIEW)

    def _on_undo_requested(self):
        latest = self.adapter.get_latest_active()
        if not latest:
            dlg = ErrorDialog("Undo not available", "No active organization history available to undo.", parent=self)
            dlg.exec()
            return

        folder_name = Path(latest.target_folder).name if latest.target_folder else "your folder"
        count = len(latest.pending_operations)
        dlg = UndoConfirmDialog(folder_name, count, self)
        if dlg.exec():
            self.adapter.undo_latest_async()

    def _on_undo_completed(self, restored: int, errors: list, record):
        if errors:
            dlg = ErrorDialog("Some files weren't restored", f"{restored} files are back. Some couldn't be moved back because they were changed.", "; ".join(errors), self)
            dlg.exec()
        else:
            self.show_toast(f"{restored} files restored to their previous locations.")
        self._navigate_to("history")

    def _on_undo_failed(self, err_msg: str):
        dlg = ErrorDialog("Undo not completed", "Unable to complete file restoration.", err_msg, self)
        dlg.exec()

    def _on_clear_selected_history(self, selected_ids: list):
        deleted = self.adapter.clear_records(selected_ids)
        self.show_toast("History cleared.")

    def _on_clear_all_history(self):
        deleted = self.adapter.clear_all()
        self.show_toast("History cleared.")

    def show_toast(self, message: str):
        toast = ToastNotification(self.central_bg, message)
        toast.show()
        toast.adjustSize()
        x = (self.width() - toast.width()) // 2
        # Bottom-center 104px above bottom
        y = self.height() - 104
        toast.move(x, y)
        toast.raise_()
