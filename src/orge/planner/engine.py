"""
orge.planner - Deterministic Operation Planning Subsystem
Ensures that both Dry-Run and Real Execution operate on the exact same
pre-calculated paths with full collision resolution during planning.
"""
from pathlib import Path
import datetime
import fnmatch
from typing import Set, Dict, Optional, List
from orge.core.models import FileItem, OperationPlan, OperationStep, ActionType
from orge.classifier.engine import Classifier
from orge.config.manager import ConfigManager

def is_reparse_point_or_symlink(path: Path) -> bool:
    """Detects symlinks, Windows junctions, and reparse points without following them."""
    try:
        if path.is_symlink():
            return True
        stat_res = path.lstat()
        # Windows reparse point flag check if available
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
    ) -> OperationPlan:
        target_folder = target_folder.resolve()
        plan = OperationPlan(target_folder=target_folder)

        if not target_folder.exists() or not target_folder.is_dir():
            return plan

        now = datetime.datetime.now()
        threshold_delta = datetime.timedelta(days=days_threshold) if days_threshold > 0 else None

        # Track destination filenames allocated in this plan to guarantee unique paths
        allocated_destinations: Set[Path] = set()

        # Enumerate files
        if recursive:
            entries = self._walk_recursive(target_folder)
        else:
            entries = [p for p in target_folder.iterdir() if p.is_file()]

        for p in sorted(entries, key=lambda x: str(x)):
            # Skip reparse points and symlinks for safety
            if is_reparse_point_or_symlink(p):
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

            try:
                stat = p.stat()
                modified_at = datetime.datetime.fromtimestamp(stat.st_mtime)
                created_at = datetime.datetime.fromtimestamp(stat.st_ctime)
                size_bytes = stat.st_size
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
            if p.parent.resolve() == destination_dir.resolve():
                plan.steps.append(OperationStep(
                    source_path=p,
                    target_path=p,
                    category=classification.category,
                    action=ActionType.SKIP,
                    reason="already_organized"
                ))
                continue

            # Determine destination with deterministic collision resolution
            target_file_path = self._resolve_target_path(
                source_path=p,
                dest_dir=destination_dir,
                allocated_destinations=allocated_destinations
            )
            allocated_destinations.add(target_file_path.resolve())

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

    def _resolve_target_path(
        self,
        source_path: Path,
        dest_dir: Path,
        allocated_destinations: Set[Path]
    ) -> Path:
        """
        Calculates collision-free destination path.
        If dest/foo.txt exists or is already claimed, calculates foo_1.txt, foo_2.txt, etc.
        """
        dest_dir.mkdir(parents=True, exist_ok=True)
        candidate = dest_dir / source_path.name

        # If candidate does not exist on disk AND is not claimed by earlier step in plan
        if not candidate.exists() and candidate.resolve() not in allocated_destinations:
            return candidate

        # Collision resolution
        stem = source_path.stem
        suffix = source_path.suffix
        counter = 1
        while True:
            candidate = dest_dir / f"{stem}_{counter}{suffix}"
            if not candidate.exists() and candidate.resolve() not in allocated_destinations:
                return candidate
            counter += 1

    def _is_ignored(self, path: Path, root: Path) -> bool:
        rel = path.relative_to(root)
        for part in rel.parts:
            for pattern in self.config.ignored_patterns:
                if fnmatch.fnmatch(part.lower(), pattern.lower()):
                    return True
        return False

    def _walk_recursive(self, target_folder: Path) -> List[Path]:
        results: List[Path] = []
        for p in target_folder.rglob("*"):
            if p.is_file():
                results.append(p)
        return results
