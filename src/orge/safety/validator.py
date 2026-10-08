"""
orge.safety - Comprehensive Safety Validation Pipeline
Pipeline:
  Target validation
        |
  Path resolution
        |
  Protected-root validation
        |
  Source validation
        |
  Destination containment validation
        |
  Symlink/junction validation
        |
  Collision validation
        |
  Permission validation
        |
  Plan approved

Optimized for high throughput on large file sets with cached permission checks.
"""
from pathlib import Path
import os
import sys
from typing import Set, Dict
from orge.core.models import OperationPlan, ValidationReport, ValidationIssue, ActionType
from orge.planner.engine import is_reparse_point_or_symlink
from orge.core.paths import get_runtime_protected_paths

def get_system_protected_paths() -> Set[Path]:
    """Returns absolute paths of system-critical operating system directories and ORGE runtime."""
    paths = set()
    if sys.platform == "win32":
        # Windows System Roots
        for var in ["SystemRoot", "windir", "ProgramFiles", "ProgramFiles(x86)", "ProgramData"]:
            val = os.environ.get(var)
            if val:
                try:
                    paths.add(Path(val).resolve())
                except Exception:
                    pass
        # Drive roots like C:\, D:\
        for drive in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            p = Path(f"{drive}:\\")
            if p.exists():
                try:
                    paths.add(p.resolve())
                except Exception:
                    pass
    else:
        # POSIX System Roots
        for posix_dir in ["/", "/bin", "/sbin", "/usr", "/usr/bin", "/etc", "/var", "/boot", "/sys", "/proc", "/dev", "/root"]:
            p = Path(posix_dir)
            if p.exists():
                try:
                    paths.add(p.resolve())
                except Exception:
                    pass

    # Add ORGE installation and runtime paths
    paths.update(get_runtime_protected_paths())
    return paths

class SafetyValidator:
    """Verifies that an OperationPlan is strictly safe for execution."""

    def __init__(self):
        self.protected_roots = get_system_protected_paths()

    def validate(self, plan: OperationPlan) -> ValidationReport:
        report = ValidationReport()
        target_root = plan.target_folder.resolve()

        # 1. Target Validation
        if not target_root.exists() or not target_root.is_dir():
            report.issues.append(ValidationIssue(
                severity="ERROR",
                source_path=target_root,
                target_path=None,
                message=f"Target folder does not exist or is not a directory: {target_root}"
            ))
            return report

        # 2. Protected Root Validation (Target folder itself cannot be a system root)
        if target_root in self.protected_roots:
            report.issues.append(ValidationIssue(
                severity="ERROR",
                source_path=target_root,
                target_path=None,
                message=f"Refusing to organize protected system directory: {target_root}"
            ))
            return report

        # Check write permissions on target directory
        if not os.access(target_root, os.W_OK):
            report.issues.append(ValidationIssue(
                severity="ERROR",
                source_path=target_root,
                target_path=None,
                message=f"Target directory is not writable: {target_root}"
            ))

        seen_destinations: Set[Path] = set()
        checked_writable_parents: Dict[Path, bool] = {}

        for step in plan.executable_steps:
            src = step.source_path
            dst = step.target_path

            # 3. Source Validation
            if not src.exists():
                report.issues.append(ValidationIssue(
                    severity="ERROR",
                    source_path=src,
                    target_path=dst,
                    message=f"Source file does not exist: {src}"
                ))
                continue

            # 4. Destination Containment Validation (Prevent Path Traversal)
            try:
                # Fast check: target_root in dst.parents or dst.relative_to
                dst.relative_to(target_root)
            except ValueError:
                report.issues.append(ValidationIssue(
                    severity="ERROR",
                    source_path=src,
                    target_path=dst,
                    message=f"Path traversal detected! Destination '{dst}' escapes target directory '{target_root}'"
                ))

            # 5. Symlink / Junction / Reparse Point Validation
            if is_reparse_point_or_symlink(src):
                report.issues.append(ValidationIssue(
                    severity="ERROR",
                    source_path=src,
                    target_path=dst,
                    message=f"Refusing to manipulate symlink or junction: {src}"
                ))

            # 6. Collision Validation: duplicate target in the same batch
            if dst in seen_destinations:
                report.issues.append(ValidationIssue(
                    severity="ERROR",
                    source_path=src,
                    target_path=dst,
                    message=f"Collision detected: Multiple operations targeted at identical destination: {dst}"
                ))
            seen_destinations.add(dst)

            # 7. Collision Validation: target already exists on disk and is distinct from source
            if dst.exists() and dst != src:
                report.issues.append(ValidationIssue(
                    severity="ERROR",
                    source_path=src,
                    target_path=dst,
                    message=f"Target destination already exists on disk: {dst}"
                ))

            # 8. Permission Validation on Destination Parent (Cached per category parent)
            dst_parent = dst.parent
            if dst_parent not in checked_writable_parents:
                if dst_parent.exists():
                    is_writable = os.access(dst_parent, os.W_OK)
                    checked_writable_parents[dst_parent] = is_writable
                    if not is_writable:
                        report.issues.append(ValidationIssue(
                            severity="ERROR",
                            source_path=src,
                            target_path=dst,
                            message=f"Destination directory parent is not writable: {dst_parent}"
                        ))
                else:
                    checked_writable_parents[dst_parent] = True
            elif not checked_writable_parents[dst_parent]:
                report.issues.append(ValidationIssue(
                    severity="ERROR",
                    source_path=src,
                    target_path=dst,
                    message=f"Destination directory parent is not writable: {dst_parent}"
                ))

        return report
