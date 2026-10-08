"""
orge.ui - Terminal Presentation and Formatting
Provides ANSI colored output, tables, banners, and structured views.
"""
from typing import List, Sequence
import sys

CYAN = "\033[0;36m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

BANNER = f"""{CYAN}{BOLD}
====================
        ORGE
  Folder Organizer
===================={RESET}"""

class TerminalUI:
    """Handles terminal rendering with quiet, verbose, and plain text support."""

    def __init__(self, quiet: bool = False, verbose: bool = False):
        self.quiet = quiet
        self.verbose = verbose

    def print_banner(self):
        if not self.quiet:
            print(BANNER)

    def info(self, msg: str):
        if not self.quiet:
            print(f"{CYAN}{msg}{RESET}")

    def success(self, msg: str):
        if not self.quiet:
            print(f"{GREEN}{msg}{RESET}")

    def warning(self, msg: str):
        if not self.quiet:
            print(f"{YELLOW}Warning: {msg}{RESET}", file=sys.stderr)

    def error(self, msg: str):
        print(f"{RED}Error: {msg}{RESET}", file=sys.stderr)

    def debug(self, msg: str):
        if self.verbose and not self.quiet:
            print(f"{DIM}[DEBUG] {msg}{RESET}")

    def format_table(self, rows: Sequence[Sequence[str]], headers: Sequence[str]) -> str:
        str_rows = [[str(cell) for cell in row] for row in rows]
        widths = [len(h) for h in headers]
        for row in str_rows:
            for i, val in enumerate(row):
                widths[i] = max(widths[i], len(val))

        header_line = " | ".join(f"{h:<{widths[i]}}" for i, h in enumerate(headers))
        sep_line = "-+-".join("-" * widths[i] for i in range(len(headers)))
        content_lines = [
            " | ".join(f"{val:<{widths[i]}}" for i, val in enumerate(row))
            for row in str_rows
        ]
        return f"{header_line}\n{sep_line}\n" + "\n".join(content_lines)
