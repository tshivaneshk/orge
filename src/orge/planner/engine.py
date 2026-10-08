"""
orge.planner - High-Performance Deterministic Operation Planning Subsystem
Ensures that both Dry-Run and Real Execution operate on the exact same
pre-calculated paths with full collision resolution during planning.
Optimized for one-pass scanning via os.scandir with cached directory lookups.
"""
from pathlib import Path
import os
import datetime
import fnmatch
from typing import Set, Dict, Optional, List, Tuple
from orge.core.models import FileItem, OperationPlan, OperationStep, ActionType
from orge.classifier.engine import Classifier
from orge.config.manager import ConfigManager

def is_reparse_point_or_symlink(path: Path) -> bool:
    """Detects symlinks, Windows junctions, and reparse points without following them."""
    try:
        if path.is_symlink():
            return True
        stat_res = path.lstat()
        if hasattr(stat_res, "st_file_attributes"):
            FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
            if bool(stat_res.st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT):
                return True
    except (OSError, ValueError):
        pass
    return False

class Planner:
    """Plans file organization operations with deterministic destination allocation."""

    def __init__(self, classifier: Classifier, config: ConfigManager):
        self.classifier = classifier
        self.config = config

    def create_plan(
        self,
        target_folder: Path,
        days_threshold: int = 0,
        recursive: bool = False,
        progress_callback: Optional[callable] = None,
    ) -> OperationPlan:
        target_folder = target_folder.resolve()
        plan = OperationPlan(target_folder=target_folder)

        if not target_folder.exists() or not target_folder.is_dir():
            return plan

        now = datetime.datetime.now()
        threshold_delta = datetime.timedelta(days=days_threshold) if days_threshold > 0 else None

        # Track destination filenames allocated in this plan to guarantee unique paths
        allocated_destinations: Set[Path] = set()
        created_dirs: Set[Path] = set()

        # Enumerate files using fast single-pass os.scandir
        if recursive:
            entries = self._walk_recursive_fast(target_folder)
        else:
            entries = self._scan_flat_fast(target_folder)

        # Sort by path string for deterministic order
        entries.sort(key=lambda x: str(x[0]))
        total_entries = len(entries)

        for idx, (p, stat_info, is_symlink) in enumerate(entries):
            if progress_callback and (idx % 100 == 0 or idx == total_entries - 1):
                progress_callback(idx + 1, total_entries)

            # Skip reparse points and symlinks for safety
            if is_symlink or is_reparse_point_or_symlink(p):
                plan.steps.append(OperationStep(
                    source_path=p,
                    target_path=p,
                    category="Skipped",
                    action=ActionType.SKIP,
                    reason="symlink_or_junction_skipped"
                ))
                continue

            # Skip ignored patterns
            if self._is_ignored(p, target_folder):
                plan.steps.append(OperationStep(
                    source_path=p,
                    target_path=p,
                    category="Skipped",
                    action=ActionType.SKIP,
                    reason="ignored_pattern"
                ))
                continue

            if stat_info is None:
                try:
                    stat_info = p.stat()
                except OSError as err:
                    plan.steps.append(OperationStep(
                        source_path=p,
                        target_path=p,
                        category="Skipped",
                        action=ActionType.SKIP,
                        reason=f"stat_error:{err}"
                    ))
                    continue

            try:
                modified_at = datetime.datetime.fromtimestamp(stat_info.st_mtime)
                created_at = datetime.datetime.fromtimestamp(stat_info.st_ctime)
                size_bytes = stat_info.st_size
            except OSError as err:
                plan.steps.append(OperationStep(
                    source_path=p,
                    target_path=p,
                    category="Skipped",
                    action=ActionType.SKIP,
                    reason=f"stat_error:{err}"
                ))
                continue

            # Days threshold filter
            if threshold_delta and (now - modified_at) < threshold_delta:
                plan.steps.append(OperationStep(
                    source_path=p,
                    target_path=p,
                    category="Skipped",
                    action=ActionType.SKIP,
                    reason=f"modified_within_{days_threshold}_days"
                ))
                continue

            item = FileItem(
                path=p,
                filename=p.name,
                extension=p.suffix,
                size_bytes=size_bytes,
                created_at=created_at,
                modified_at=modified_at,
                is_file=True,
            )

            classification = self.classifier.classify(item)
            destination_dir = target_folder / classification.category

            # Check if file is already organized in its destination folder
            if p.parent == destination_dir:
                plan.steps.append(OperationStep(
                    source_path=p,
                    target_path=p,
                    category=classification.category,
                    action=ActionType.SKIP,
                    reason="already_organized"
                ))
                continue

            # Determine destination with deterministic collision resolution
            target_file_path = self._resolve_target_path_fast(
                source_path=p,
                dest_dir=destination_dir,
                allocated_destinations=allocated_destinations,
                created_dirs=created_dirs
            )
            allocated_destinations.add(target_file_path)

            plan.steps.append(OperationStep(
                source_path=p,
                target_path=target_file_path,
                category=classification.category,
                action=ActionType.MOVE,
                reason=f"{classification.reason} ({classification.matched_rule or 'default'})",
                metadata={
                    "confidence": classification.confidence,
                    "size_bytes": size_bytes,
                }
            ))

        return plan

    def _resolve_target_path_fast(
        self,
        source_path: Path,
        dest_dir: Path,
        allocated_destinations: Set[Path],
        created_dirs: Set[Path]
    ) -> Path:
        """
        Calculates collision-free destination path without repeated mkdir/stat calls.
        """
        candidate = dest_dir / source_path.name

        # If candidate is not claimed in plan AND does not exist on disk
        if candidate not in allocated_destinations and not candidate.exists():
            return candidate

        # Collision resolution
        stem = source_path.stem
        suffix = source_path.suffix
        counter = 1
        while True:
            candidate = dest_dir / f"{stem}_{counter}{suffix}"
            if candidate not in allocated_destinations and not candidate.exists():
                return candidate
            counter += 1

    def _is_ignored(self, path: Path, root: Path) -> bool:
        try:
            rel = path.relative_to(root)
            for part in rel.parts:
                for pattern in self.config.ignored_patterns:
                    if fnmatch.fnmatch(part.lower(), pattern.lower()):
                        return True
        except ValueError:
            pass
        return False

    def _scan_flat_fast(self, target_folder: Path) -> List[Tuple[Path, Optional[os.stat_result], bool]]:
        results = []
        try:
            with os.scandir(target_folder) as it:
                for entry in it:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            stat = entry.stat(follow_symlinks=False)
                            is_symlink = entry.is_symlink()
                            results.append((Path(entry.path), stat, is_symlink))
                    except OSError:
                        continue
        except OSError:
            pass
        return results

    def _walk_recursive_fast(self, target_folder: Path) -> List[Tuple[Path, Optional[os.stat_result], bool]]:
        results = []
        try:
            for root, dirs, files in os.walk(str(target_folder)):
                root_path = Path(root)
                # Filter ignored directory names in-place
                dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d.lower(), pat.lower()) for pat in self.config.ignored_patterns)]
                for f in files:
                    fp = root_path / f
                    try:
                        stat = fp.stat()
                        is_symlink = fp.is_symlink()
                        results.append((fp, stat, is_symlink))
                    except OSError:
                        results.append((fp, None, False))
        except OSError:
            pass
        return results
