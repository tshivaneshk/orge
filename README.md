# ORGE — Open Resource & Good Organization Engine

[![CI](https://github.com/tshivaneshk/orge/actions/workflows/ci.yml/badge.svg)](https://github.com/tshivaneshk/orge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

**ORGE** is a modern, high-safety, cross-platform file organization engine. Built from the ground up for deterministic execution, ORGE classifies, stages, validates, and reorganizes filesystem directories with rollback capability.

> *Historical Note: ORGE evolved from the original dirtx prototype.*

---

## Architecture: ORGE

```text
                    ORGE
                     │
              ┌──────┴──────┐
              │   CLI / UI  │
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │   Planner   │
              └──────┬──────┘
                     │
          ┌──────────▼──────────┐
          │     Classifier      │
          └──────────┬──────────┘
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
   Extension      Metadata      Config
   Detection      Detection      Rules
       │             │             │
       └─────────────┼─────────────┘
                     ▼
             Operation Plan
                     │
             ┌───────▼───────┐
             │    Safety     │
             │  Validation   │
             └───────┬───────┘
                     ▼
              File Executor
                │       │
                ▼       ▼
             History   Undo
```

### Pipeline Breakdown
1. **CLI / UI**: Modern subcommand interface (`organize`, `scan`, `preview`, `undo`, `history`, `config`, `doctor`) with pure JSON mode and ANSI table presentation.
2. **Planner**: Analyzes directory state and deterministically calculates the target destination paths (resolving any name collisions during planning so that dry-run matches real execution 100%).
3. **Classifier**: Triple-tier classification engine:
   - **Config Rules**: Custom user rules matching via regex (`^INV-.*\.pdf$`), glob (`*.log`), or file size thresholds.
   - **Extension Detection**: Fast $O(1)$ lookup table for common document, media, archive, installer, and code types.
   - **Metadata Detection**: MIME-type heuristics and file timestamps.
   - **Misc Fallback**: Safely catches unclassified items.
4. **Operation Plan**: In-memory staging of executable moves and skipped actions.
5. **Safety Validation**: Eight-point safety check guarding against path traversal, symlinks/reparse points, system directories (`C:\Windows`, `/etc`, drive roots), and destination overwrites.
6. **File Executor**: Atomic moves executed purely through Python standard library APIs (`shutil`, `pathlib`) — no fragile shell scripts.
7. **History & Undo**: Complete journal of operations. If an undo encounters an external conflict, it preserves pending actions in the journal so rollbacks can be safely retried without data loss.

---

## Installation

### Using pip
```bash
pip install orge
```

### From Source (Editable Mode)
```bash
git clone https://github.com/tshivaneshk/orge.git
cd orge
pip install -e .
```

---

## CLI Usage

### 1. Preview Before Moving (Dry-Run)
Inspect what will happen without touching any files:
```bash
orge preview ~/Downloads
# or
orge organize ~/Downloads --dry-run
```

### 2. Organize Files
```bash
orge organize ~/Downloads
```
Skip the confirmation prompt:
```bash
orge organize ~/Downloads -y
```

### 3. Scan a Directory
Get a categorized inventory of files and counts:
```bash
orge scan ~/Downloads
```

### 4. Rollback / Undo
Reverse the most recent organization operation:
```bash
orge undo
```

### 5. View History
```bash
orge history
```

### 6. Filter by File Age
Only organize files modified more than 14 days ago:
```bash
orge organize ~/Downloads -d 14
```

### 7. JSON Output Mode
For scripting, automation, or integration:
```bash
orge organize ~/Downloads --dry-run --json
orge scan ~/Downloads --json
```

### 8. System Diagnostics
Inspect platform-specific configuration and journal directories:
```bash
orge doctor
```

---

## Configuration

ORGE respects standard cross-platform conventions:
- **Windows**: `%APPDATA%\orge\config.json`
- **Linux / macOS**: `$XDG_CONFIG_HOME/orge/config.json` or `~/.config/orge/config.json`

Check your config path with:
```bash
orge config --path
```

Example `config.json`:
```json
{
  "categories": {
    "Design": ["psd", "ai", "fig", "sketch"],
    "Archives": ["zip", "rar", "7z", "tar", "gz"]
  },
  "custom_rules": [
    {
      "category": "Invoices",
      "regex": "^INV-\\d+\\.pdf$"
    },
    {
      "category": "Logs",
      "glob": "*.log"
    },
    {
      "category": "LargeFiles",
      "min_size_bytes": 104857600
    }
  ],
  "ignored_patterns": [
    ".git", ".svn", ".venv", "node_modules", ".DS_Store", "Thumbs.db"
  ]
}
```

---

## Testing

Execute test discovery across all components:
```bash
python -m unittest discover -v -s tests
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
