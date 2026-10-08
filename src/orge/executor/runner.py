"""
orge.executor - File Movement and Undo Execution Subsystem
Executes validated plans, updates journals, and handles rollback operations.
Uses pure Python APIs (shutil, pathlib) — zero external shell commands.
"""
from pathlib import Path
import shutil
from typing import List, Tuple, Optional
from orge.core.models import OperationPlan, HistoryRecord
from orge.history.journal import HistoryManager

class FileExecutor:
    """Executes validated operation plans and coordinates safe rollbacks."""

    def __init__(self, history_manager: HistoryManager):
        self.history_manager = history_manager

    def execute(self, plan: OperationPlan) -> Tuple[List[Tuple[Path, Path]], List[str]]:
        """
        Executes moves strictly according to the validated plan.
        Returns: (successful_moves, errors)
        """
        successful_moves: List[Tuple[Path, Path]] = []
        errors: List[str] = []

        for step in plan.executable_steps:
            src = step.source_path
            dst = step.target_path

            # Guard against sudden disappearance or race condition
            if not src.exists():
                errors.append(f"Source file not found during execution: {src}")
                continue

            # Target directory creation
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
            except OSError as err:
                errors.append(f"Failed to create target directory '{dst.parent}': {err}")
                continue

            # Destination check: if target appeared between planning and execution (race condition)
            if dst.exists() and dst != src:
                errors.append(f"Race condition detected: Destination already exists before move: {dst}")
                continue

            try:
                shutil.move(str(src), str(dst))
                successful_moves.append((src, dst))
            except OSError as err:
                errors.append(f"Error moving '{src.name}' -> '{dst}': {err}")

        # Record in history journal
        if successful_moves:
            self.history_manager.record_run(plan.target_folder, successful_moves)

        return successful_moves, errors

    def undo_latest(self) -> Tuple[int, List[str], Optional[HistoryRecord]]:
        """
        Rolls back the most recent active operation.
        Guarantees:
        - History record is NOT removed if any file fails to restore.
        - Destination collision during undo will never overwrite an existing file.
        Returns: (restored_count, error_messages, updated_history_record)
        """
        record = self.history_manager.get_latest_active()
        if not record:
            return 0, ["No active organization history found to undo."], None

        return self.undo_record(record)

    def undo_record(self, record: HistoryRecord) -> Tuple[int, List[str], HistoryRecord]:
        """
        Reverses pending operations in a specific history record.
        Maintains granular state of completed vs pending restores.
        """
        pending = list(record.pending_operations)
        new_pending = []
        restored_count = 0
        errors: List[str] = []

        for op in reversed(pending):
            orig_src = Path(op["source"])
            current_target = Path(op["target"])

            # 1. Check current file presence
            if not current_target.exists():
                errors.append(f"Cannot undo: file missing at '{current_target}'")
                new_pending.append(op)
                continue

            # 2. Guard against overwriting an existing file at original location
            if orig_src.exists() and orig_src.resolve() != current_target.resolve():
                errors.append(
                    f"Conflict during undo: A file already exists at original path '{orig_src}'. "
                    f"Skipping restore to prevent data loss."
                )
                new_pending.append(op)
                continue

            # 3. Perform atomic restoration
            try:
                orig_src.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(current_target), str(orig_src))
                restored_count += 1
                record.completed_operations.append(op)
            except OSError as err:
                errors.append(f"Failed to restore '{current_target.name}' to '{orig_src}': {err}")
                new_pending.append(op)

        # Update record with remaining pending ops
        record.pending_operations = new_pending

        # Clean empty folders if complete
        target_root = Path(record.target_folder)
        for op in record.completed_operations:
            parent_dir = Path(op["target"]).parent
            try:
                if parent_dir.exists() and parent_dir.resolve() != target_root.resolve():
                    if not any(parent_dir.iterdir()):
                        parent_dir.rmdir()
            except OSError:
                pass

        if len(record.pending_operations) == 0:
            record.status = "completed_undo"
            self.history_manager.save_record(record)
        else:
            record.status = "partial_undo"
            self.history_manager.save_record(record)

        return restored_count, errors, record
