"""
orge.gui.adapter - Thin Thread-Safe Adapter between Engine and GUI
Runs scanning, organizing, history listing, and undo operations on QThreadPool/QRunnable workers.
Includes operation generation IDs to discard stale results.
Throttles progress signals to ~10 updates/second to avoid flooding the UI thread.
"""
from pathlib import Path
import time
from typing import List, Tuple, Optional, Dict, Any, Callable
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool

from orge.config.manager import ConfigManager
from orge.classifier.engine import Classifier
from orge.planner.engine import Planner
from orge.safety.validator import SafetyValidator
from orge.history.journal import HistoryManager
from orge.executor.runner import FileExecutor
from orge.core.models import OperationPlan, HistoryRecord, ValidationReport

class WorkerSignals(QObject):
    """Reusable signal carrier for background QRunnables."""
    started = Signal()
    progress = Signal(int, int, str, str)  # current, total, src_name, dst_name
    scan_progress = Signal(int, int)       # current, total
    finished = Signal(object)              # payload result
    error = Signal(str)

class FunctionRunnable(QRunnable):
    """QRunnable that runs a target function with arbitrary arguments."""
    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        self.signals.started.emit()
        try:
            res = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(res)
        except Exception as e:
            self.signals.error.emit(str(e))

class EngineAdapter(QObject):
    """
    Adapter orchestrating all ORGE core services.
    Preserves all existing safety checks, duplicate handling, and journal persistence.
    """
    # High-level engine signals with generation tracking
    scan_progress = Signal(int, int, int)              # current, total, generation_id
    scan_completed = Signal(OperationPlan, ValidationReport, int)  # plan, report, generation_id
    scan_failed = Signal(str, int)                     # error_msg, generation_id

    organize_progress = Signal(int, int, str, str)     # current, total, src_name, dst_name
    organize_completed = Signal(list, list)            # successful_moves, errors
    organize_failed = Signal(str)

    undo_completed = Signal(int, list, object)         # restored_count, errors, record
    undo_failed = Signal(str)

    history_updated = Signal(list)

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        super().__init__()
        self.config_manager = config_manager or ConfigManager()
        self.classifier = Classifier(self.config_manager)
        self.planner = Planner(self.classifier, self.config_manager)
        self.validator = SafetyValidator()
        self.history_manager = HistoryManager()
        self.executor = FileExecutor(self.history_manager)
        self.thread_pool = QThreadPool.globalInstance()
        self._current_generation = 0
        self._active_runnables = set()

    def _track_runnable(self, runnable: FunctionRunnable):
        self._active_runnables.add(runnable)
        def _cleanup(*args):
            self._active_runnables.discard(runnable)
        runnable.signals.finished.connect(_cleanup)
        runnable.signals.error.connect(_cleanup)

    def next_generation(self) -> int:
        self._current_generation += 1
        return self._current_generation

    @property
    def current_generation(self) -> int:
        return self._current_generation

    # -------------------------------------------------------------------------
    # Fast Folder Pre-Inspection (Single-pass os.scandir for quick home stats)
    # -------------------------------------------------------------------------
    def inspect_folder_fast(self, folder: Path) -> Tuple[int, Dict[str, int]]:
        """
        Quickly inspects top-level directory entries in a single pass without planning.
        Used to display file count and category tiles on Home immediately upon folder selection.
        """
        import os
        count = 0
        categories: Dict[str, int] = {}
        lookup = self.config_manager.extension_lookup
        try:
            with os.scandir(folder) as it:
                for entry in it:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            count += 1
                            name = entry.name
                            dot_idx = name.rfind(".")
                            ext = name[dot_idx + 1:].lower() if dot_idx != -1 else ""
                            cat = lookup.get(ext, "Misc")
                            categories[cat] = categories.get(cat, 0) + 1
                    except OSError:
                        continue
        except OSError:
            pass
        return count, categories

    # -------------------------------------------------------------------------
    # Scan & Plan Worker
    # -------------------------------------------------------------------------
    def scan_folder_async(self, target: Path, days_threshold: int = 0, recursive: bool = False, gen_id: Optional[int] = None):
        """Asynchronously creates an operation plan and validates safety."""
        generation = gen_id if gen_id is not None else self.next_generation()
        signals = WorkerSignals()

        # Throttled progress callback
        last_progress_time = [0.0]

        def scan_progress_cb(cur: int, tot: int):
            now = time.perf_counter()
            if now - last_progress_time[0] >= 0.1 or cur == tot:
                last_progress_time[0] = now
                signals.scan_progress.emit(cur, tot)

        def worker_fn():
            plan = self.planner.create_plan(
                target_folder=target,
                days_threshold=days_threshold,
                recursive=recursive,
                progress_callback=scan_progress_cb
            )
            report = self.validator.validate(plan)
            return plan, report

        runnable = FunctionRunnable(worker_fn)
        runnable.signals = signals

        signals.scan_progress.connect(lambda c, t, g=generation: self.scan_progress.emit(c, t, g))
        signals.finished.connect(lambda res, g=generation: self._on_scan_finished(res[0], res[1], g))
        signals.error.connect(lambda err, g=generation: self.scan_failed.emit(err, g))
        self._track_runnable(runnable)
        self.thread_pool.start(runnable)

    def _on_scan_finished(self, plan: OperationPlan, report: ValidationReport, generation: int):
        if generation == self._current_generation:
            self.scan_completed.emit(plan, report, generation)

    # -------------------------------------------------------------------------
    # Organize Execution Worker (Throttled Progress: ~10 UI updates/sec)
    # -------------------------------------------------------------------------
    def execute_plan_async(self, plan: OperationPlan):
        """Asynchronously executes an operation plan with throttled live progress reporting."""
        signals = WorkerSignals()
        last_ui_update = [0.0]

        def progress_cb(cur: int, tot: int, src: Path, dst: Path):
            now = time.perf_counter()
            # Throttle to max 10 updates per second or final item
            if now - last_ui_update[0] >= 0.1 or cur == tot:
                last_ui_update[0] = now
                signals.progress.emit(cur, tot, src.name, dst.name)

        def worker_fn():
            return self.executor.execute(plan, progress_callback=progress_cb)

        runnable = FunctionRunnable(worker_fn)
        runnable.signals = signals

        signals.progress.connect(self.organize_progress.emit)
        signals.finished.connect(lambda res: self._on_organize_finished(res[0], res[1]))
        signals.error.connect(self.organize_failed.emit)
        self._track_runnable(runnable)
        self.thread_pool.start(runnable)

    def _on_organize_finished(self, successful: list, errors: list):
        self.organize_completed.emit(successful, errors)
        self.refresh_history_async()

    # -------------------------------------------------------------------------
    # Undo Worker
    # -------------------------------------------------------------------------
    def undo_latest_async(self):
        """Asynchronously rolls back the most recent active operation."""
        def worker_fn():
            return self.executor.undo_latest()

        runnable = FunctionRunnable(worker_fn)
        runnable.signals.finished.connect(lambda res: self._on_undo_finished(res[0], res[1], res[2]))
        runnable.signals.error.connect(self.undo_failed.emit)
        self.thread_pool.start(runnable)

    def _on_undo_finished(self, restored: int, errors: list, record: Optional[HistoryRecord]):
        self.undo_completed.emit(restored, errors, record)
        self.refresh_history_async()

    # -------------------------------------------------------------------------
    # History Operations
    # -------------------------------------------------------------------------
    def refresh_history_async(self, force_reload: bool = False):
        """Fetches history records asynchronously, or emits immediately from in-memory cache."""
        if not force_reload and self.history_manager._records_cache is not None:
            self.history_updated.emit(list(self.history_manager._records_cache))
            return

        def worker_fn():
            return self.history_manager.list_history(force_reload=force_reload)

        runnable = FunctionRunnable(worker_fn)
        runnable.signals.finished.connect(self.history_updated.emit)
        self._track_runnable(runnable)
        self.thread_pool.start(runnable)

    def clear_records(self, record_ids: List[str]) -> int:
        deleted = self.history_manager.clear_records(record_ids)
        self.refresh_history_async()
        return deleted

    def clear_all(self) -> int:
        deleted = self.history_manager.clear_all()
        self.refresh_history_async()
        return deleted

    def get_latest_active(self) -> Optional[HistoryRecord]:
        return self.history_manager.get_latest_active()
