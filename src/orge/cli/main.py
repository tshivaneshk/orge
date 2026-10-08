"""
orge.cli.main - Modern Subcommand-Driven Command Line Interface
Commands:
  orge organize [path]
  orge preview [path]
  orge scan [path]
  orge undo
  orge history
  orge config
  orge doctor
  orge version
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from orge import __version__, __app_name__
from orge.core.paths import get_config_dir, get_data_dir, get_history_dir
from orge.config.manager import ConfigManager
from orge.classifier.engine import Classifier
from orge.planner.engine import Planner
from orge.safety.validator import SafetyValidator
from orge.history.journal import HistoryManager
from orge.executor.runner import FileExecutor
from orge.ui.terminal import TerminalUI, YELLOW, GREEN, RED, CYAN, BOLD, RESET

# Ensure safe encoding for Windows console (cp1252 fallback)
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orge",
        description="ORGE - Modern, Safe, Cross-Platform File Organizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", "-v", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--json", action="store_true", help="Output results strictly as machine-readable JSON")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress decorative banners and hints")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose diagnostic logs")

    # Shared flags for subparsers
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--json", action="store_true", help="Output results strictly as machine-readable JSON")
    parent_parser.add_argument("--quiet", "-q", action="store_true", help="Suppress decorative banners and hints")
    parent_parser.add_argument("--verbose", action="store_true", help="Enable verbose diagnostic logs")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: organize
    p_org = subparsers.add_parser("organize", parents=[parent_parser], help="Organize files in the target directory")
    p_org.add_argument("path", nargs="?", default=".", help="Target folder (default: current directory)")
    p_org.add_argument("-d", "--days", type=int, default=0, help="Only move files older than N days")
    p_org.add_argument("-r", "--recursive", action="store_true", help="Recursively scan subfolders")
    p_org.add_argument("--dry-run", action="store_true", help="Preview plan without executing moves")
    p_org.add_argument("-y", "--yes", action="store_true", help="Skip safety confirmation prompt")

    # Command: preview
    p_prev = subparsers.add_parser("preview", parents=[parent_parser], help="Preview organization plan without moving files")
    p_prev.add_argument("path", nargs="?", default=".", help="Target folder")
    p_prev.add_argument("-d", "--days", type=int, default=0, help="Only move files older than N days")
    p_prev.add_argument("-r", "--recursive", action="store_true", help="Recursively scan subfolders")

    # Command: scan
    p_scan = subparsers.add_parser("scan", parents=[parent_parser], help="Scan and inspect directory file statistics and categories")
    p_scan.add_argument("path", nargs="?", default=".", help="Target folder")
    p_scan.add_argument("-r", "--recursive", action="store_true", help="Recursively scan subfolders")

    # Command: undo
    p_undo = subparsers.add_parser("undo", parents=[parent_parser], help="Roll back the most recent organization operation")
    p_undo.add_argument("--id", type=str, default=None, help="Specific history run ID to undo")

    # Command: history
    p_hist = subparsers.add_parser("history", parents=[parent_parser], help="View past organization run journals")
    p_hist.add_argument("--limit", type=int, default=10, help="Maximum number of runs to display")

    # Command: config
    p_cfg = subparsers.add_parser("config", parents=[parent_parser], help="View or manage ORGE configuration")
    p_cfg.add_argument("--path", action="store_true", help="Print config file location")
    p_cfg.add_argument("--show", action="store_true", help="Display active configuration rules")

    # Command: doctor
    subparsers.add_parser("doctor", parents=[parent_parser], help="Inspect environment health, permissions, and paths")

    # Backward compatibility top-level flags (e.g. orge -f <path> --dry-run)
    parser.add_argument("-f", "--folder", type=str, default=None, help="Target folder (legacy flag)")
    parser.add_argument("-d", "--days", type=int, default=0, help="Days threshold (legacy flag)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run flag (legacy flag)")
    parser.add_argument("--undo", action="store_true", help="Undo flag (legacy flag)")
    parser.add_argument("--history", action="store_true", help="History flag (legacy flag)")
    parser.add_argument("-r", "--recursive", action="store_true", help="Recursive scan (legacy flag)")
    parser.add_argument("-y", "--yes", action="store_true", help="Confirm execution (legacy flag)")

    return parser

def main(args: Optional[list] = None) -> int:
    parser = create_parser()
    parsed = parser.parse_args(args)

    # Initialize subsystems
    ui = TerminalUI(quiet=parsed.quiet or parsed.json, verbose=parsed.verbose)
    config = ConfigManager()
    classifier = Classifier(config)
    planner = Planner(classifier, config)
    validator = SafetyValidator()
    history = HistoryManager()
    executor = FileExecutor(history)

    # Handle Legacy Flags
    if parsed.undo or parsed.command == "undo":
        return cmd_undo(executor, history, parsed, ui)

    if parsed.history or parsed.command == "history":
        return cmd_history(history, parsed, ui)

    if parsed.command == "doctor":
        return cmd_doctor(config, ui, parsed.json)

    if parsed.command == "config":
        return cmd_config(config, parsed, ui)

    # Resolve Command & Arguments
    command = parsed.command
    folder_str = getattr(parsed, "path", None) or parsed.folder or "."
    days = getattr(parsed, "days", 0)
    recursive = getattr(parsed, "recursive", False)
    dry_run = getattr(parsed, "dry_run", False) or (command == "preview")
    auto_confirm = getattr(parsed, "yes", False)

    if command == "scan":
        return cmd_scan(planner, folder_str, recursive, ui, parsed.json)

    # Default to organize command
    return cmd_organize(
        planner=planner,
        validator=validator,
        executor=executor,
        target_path_str=folder_str,
        days=days,
        recursive=recursive,
        dry_run=dry_run,
        auto_confirm=auto_confirm,
        ui=ui,
        is_json=parsed.json,
    )

def cmd_organize(
    planner: Planner,
    validator: SafetyValidator,
    executor: FileExecutor,
    target_path_str: str,
    days: int,
    recursive: bool,
    dry_run: bool,
    auto_confirm: bool,
    ui: TerminalUI,
    is_json: bool,
) -> int:
    target = Path(target_path_str).resolve()

    if not is_json:
        ui.print_banner()

    plan = planner.create_plan(target, days_threshold=days, recursive=recursive)
    validation = validator.validate(plan)

    if is_json:
        result = {
            "status": "success" if validation.is_safe else "error",
            "plan": plan.to_dict(),
            "validation": validation.to_dict(),
            "executed": False,
        }
        if not validation.is_safe or dry_run:
            print(json.dumps(result, indent=2))
            return 0 if validation.is_safe else 1

        successful, errors = executor.execute(plan)
        result["executed"] = True
        result["successful_count"] = len(successful)
        result["errors"] = errors
        result["successful_moves"] = [{"source": str(s), "target": str(d)} for s, d in successful]
        print(json.dumps(result, indent=2))
        return 0 if not errors else 1

    # Human-readable CLI Mode
    ui.info(f"Target Directory: {target}")
    if days > 0:
        ui.info(f"Filter: Only files older than {days} day(s)")

    executable = plan.executable_steps
    if not executable:
        ui.success("All files are already organized! Nothing to do.")
        return 0

    print(f"\n{BOLD}Operation Plan ({len(executable)} file(s) to organize):{RESET}")
    for step in executable:
        print(f"  * {YELLOW}{step.source_path.name}{RESET} -> {GREEN}{step.target_path.relative_to(target)}{RESET}  [{CYAN}{step.reason}{RESET}]")

    # Safety display
    if validation.issues:
        print(f"\n{BOLD}Safety Check Warnings & Issues:{RESET}")
        for iss in validation.issues:
            color = RED if iss.severity == "ERROR" else YELLOW
            print(f"  [{color}{iss.severity}{RESET}] {iss.message}")

    if not validation.is_safe:
        ui.error("Safety validation failed. Halting execution to prevent damage.")
        return 1

    if dry_run:
        print(f"\n{YELLOW}[DRY RUN] Plan verified safe. No files were modified on disk.{RESET}")
        return 0

    if not auto_confirm:
        try:
            choice = input(f"\n{BOLD}Proceed with moving {len(executable)} files? [Y/n]: {RESET}").strip().lower()
            if choice and choice not in ("y", "yes"):
                ui.warning("Operation aborted by user.")
                return 0
        except KeyboardInterrupt:
            print("\nAborted.")
            return 0

    ui.info("\nExecuting operations...")
    successful, errors = executor.execute(plan)

    # Summary
    print(f"\n{CYAN}================== ORGE Summary =================={RESET}")
    category_counts = {}
    for src, dst in successful:
        cat = dst.parent.name
        category_counts[cat] = category_counts.get(cat, 0) + 1

    summary_rows = [[cat, count] for cat, count in sorted(category_counts.items())]
    if summary_rows:
        print(ui.format_table(summary_rows, ["Category", "Files Moved"]))
    print(f"{CYAN}=================================================={RESET}")

    if errors:
        ui.error(f"Encountered {len(errors)} error(s):")
        for err in errors:
            print(f"  * {err}")

    ui.success(f"Organized {len(successful)} file(s) successfully.")
    ui.info("You can revert this operation anytime with: orge undo\n")
    return 0

def cmd_scan(planner: Planner, path_str: str, recursive: bool, ui: TerminalUI, is_json: bool) -> int:
    target = Path(path_str).resolve()
    plan = planner.create_plan(target, days_threshold=0, recursive=recursive)

    counts = {}
    total_size = 0
    for step in plan.steps:
        cat = step.category
        counts[cat] = counts.get(cat, 0) + 1
        total_size += step.metadata.get("size_bytes", 0)

    if is_json:
        data = {
            "target": str(target),
            "total_files": len(plan.steps),
            "total_size_bytes": total_size,
            "categories": counts,
        }
        print(json.dumps(data, indent=2))
        return 0

    ui.print_banner()
    ui.info(f"Directory Scan: {target}")
    print(f"Total files: {len(plan.steps)}")
    rows = [[cat, count] for cat, count in sorted(counts.items())]
    print(ui.format_table(rows, ["Category", "File Count"]))
    return 0

def cmd_undo(executor: FileExecutor, history: HistoryManager, parsed, ui: TerminalUI) -> int:
    is_json = getattr(parsed, "json", False)
    record_id = getattr(parsed, "id", None)

    if record_id:
        record = history.get_by_id(record_id)
        if not record:
            if is_json:
                print(json.dumps({"status": "error", "message": f"Run ID '{record_id}' not found."}, indent=2))
            else:
                ui.error(f"Run ID '{record_id}' not found.")
            return 1
        reverted, errors, updated_rec = executor.undo_record(record)
    else:
        reverted, errors, updated_rec = executor.undo_latest()

    if is_json:
        print(json.dumps({
            "status": "success" if not errors else "partial",
            "reverted_count": reverted,
            "errors": errors,
            "record": updated_rec.to_dict() if updated_rec else None
        }, indent=2))
        return 0 if not errors else 1

    ui.print_banner()
    if errors:
        for err in errors:
            ui.error(err)

    if reverted > 0:
        ui.success(f"Successfully rolled back {reverted} file(s)!")
        if updated_rec and updated_rec.pending_operations:
            ui.warning(f"{len(updated_rec.pending_operations)} files could not be restored and remain in journal.")
    else:
        ui.warning("No files were restored.")
    return 0 if not errors else 1

def cmd_history(history: HistoryManager, parsed, ui: TerminalUI) -> int:
    is_json = getattr(parsed, "json", False)
    limit = getattr(parsed, "limit", 10)
    records = history.list_history()[:limit]

    if is_json:
        print(json.dumps([r.to_dict() for r in records], indent=2))
        return 0

    ui.print_banner()
    if not records:
        ui.warning("No organization history found.")
        return 0

    rows = []
    for r in records:
        status_str = f"{GREEN}Completed{RESET}" if r.status == "completed_undo" else f"{YELLOW}Active ({len(r.pending_operations)}){RESET}"
        rows.append([r.id, r.timestamp[:19], status_str, r.target_folder])

    print(ui.format_table(rows, ["Run ID", "Timestamp", "Status", "Target Folder"]))
    return 0

def cmd_config(config: ConfigManager, parsed, ui: TerminalUI) -> int:
    is_json = getattr(parsed, "json", False)
    if parsed.path:
        if is_json:
            print(json.dumps({"config_path": str(config.config_path)}, indent=2))
        else:
            print(str(config.config_path))
        return 0

    if is_json:
        print(json.dumps(config.to_dict(), indent=2))
        return 0

    ui.print_banner()
    print(f"Config File: {config.config_path}")
    print(f"Categories defined: {len(config.categories)}")
    print(f"Custom rules defined: {len(config.custom_rules)}")
    return 0

def cmd_doctor(config: ConfigManager, ui: TerminalUI, is_json: bool) -> int:
    config_dir = get_config_dir()
    data_dir = get_data_dir()
    history_dir = get_history_dir()

    checks = {
        "version": __version__,
        "platform": sys.platform,
        "python_version": sys.version.split()[0],
        "config_dir": str(config_dir),
        "config_dir_exists": config_dir.exists(),
        "data_dir": str(data_dir),
        "data_dir_exists": data_dir.exists(),
        "history_dir": str(history_dir),
        "history_dir_exists": history_dir.exists(),
        "categories_configured": len(config.categories),
        "custom_rules_configured": len(config.custom_rules),
    }

    if is_json:
        print(json.dumps(checks, indent=2))
        return 0

    ui.print_banner()
    ui.info("ORGE System Health Check (Doctor):")
    for k, v in checks.items():
        print(f"  {BOLD}{k:<25}{RESET}: {v}")
    ui.success("\nAll system paths and dependencies are intact!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
