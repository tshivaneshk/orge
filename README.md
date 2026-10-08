# ORGE

[![CI](https://github.com/tshivaneshk/orge/actions/workflows/ci.yml/badge.svg)](https://github.com/tshivaneshk/orge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**ORGE** is a professional, safe, open-source desktop file organization application and CLI utility.

- **Windows**: Flagship Modern GUI (`ORGE.exe`) + Companion CLI (`orge.exe`)
- **Linux**: Standalone CLI (`orge`)
- **macOS**: Standalone CLI (`orge`)

Both the GUI and CLI share the exact same deterministic ORGE core engine: scanning, intelligent categorization, collision prevention, safety constraints, and full rollback capability.

---

## Windows Installation (Recommended)

Non-technical users can install and use ORGE immediately without Python, PowerShell, or terminals.

### 1. Windows Installer
1. Download **`ORGE-Setup-2.1.0.exe`** from [Releases](https://github.com/tshivaneshk/orge/releases).
2. Run the installer. It installs the application, adds an **ORGE** Start Menu shortcut, and registers `orge` in your system PATH.
3. Launch ORGE from your Start Menu to open the GUI.

### 2. Windows Portable Package
1. Download **`ORGE-Portable-2.1.0.zip`**.
2. Extract the archive anywhere on your PC.
3. Double-click **`ORGE.exe`** to launch the GUI (runs with no console window).
4. Power users can run **`orge.exe`** directly from any terminal.

---

## Linux & macOS (CLI Only)

Standalone CLI distributions are provided with zero Python dependency required:

### Linux
1. Download `orge-2.1.0-linux-x64.tar.gz` from [Releases](https://github.com/tshivaneshk/orge/releases).
2. Extract: `tar -xzf orge-2.1.0-linux-x64.tar.gz`
3. Run: `./orge --help` or `./orge organize /path/to/folder`

### macOS
1. Download `orge-2.1.0-macos.tar.gz` from [Releases](https://github.com/tshivaneshk/orge/releases).
2. Extract: `tar -xzf orge-2.1.0-macos.tar.gz`
3. Run: `./orge --help` or `./orge organize /path/to/folder`

---

## Python Package (Developers & Power Users)

If you have Python 3.10+ installed, you can also install ORGE via `pip`:

```bash
pip install orge
```

Or from source in editable mode:
```bash
git clone https://github.com/tshivaneshk/orge.git
cd orge
pip install -e .
```

---

## Desktop GUI

Launch the graphical user interface by running:
```bash
orge gui
```
Features:
- Select target directory with visual folder picker.
- Live scan & preview displaying categorized file trees.
- Safety error reporting before any disk modifications.
- Interactive run history browser and one-click undo rollback.

---

## Architecture: ORGE

```text
                  ORGE CORE
                      |
        +-------------+-------------+
        |                           |
       CLI                         GUI
        |                           |
        +-------------+-------------+
                      |
               Shared Services
                      |
       +--------------+--------------+
       |              |              |
    Planner       Safety         Executor
       |              |              |
    Classifier      History      Config
```

### Pipeline Breakdown
1. **CLI & GUI**: Dual interface sharing the identical core engine.
2. **Planner**: Analyzes directory state and deterministically calculates target paths. Pre-resolves collisions upfront so dry-run preview matches real execution 100%.
3. **Classifier**: Triple-tier classification engine:
   - **Config Rules**: Custom regex (`^INV-.*\.pdf$`), glob (`*.log`), or file size constraints.
   - **Extension Detection**: Fast $O(1)$ lookup hash tables for code, media, documents, and archives.
   - **Metadata Detection**: MIME-type heuristics and file timestamps.
   - **Misc Fallback**: Safely catches unclassified items.
4. **Safety Validation**: Multi-stage safety pipeline preventing path traversal, system directory tampering (`C:\Windows`, `/etc`, drive roots), and destination overwrites.
5. **File Executor**: Moves files using standard library filesystem APIs (`shutil`, `pathlib`).
6. **History & Undo**: Persistent JSON journaling. Preserves pending records under partial failures so rollbacks can be safely retried without data loss.

---

## CLI Usage

### 1. Preview Before Moving (Dry-Run)
Inspect planned operations without touching any files:
```bash
orge preview ~/Downloads
# or
orge organize ~/Downloads --dry-run
```

### 2. Organize Files
```bash
orge organize ~/Downloads
```
Skip interactive confirmation:
```bash
orge organize ~/Downloads -y
```

### 3. Launch Desktop GUI
```bash
orge gui
```

### 4. Scan Directory
Print categorized file counts and disk usage:
```bash
orge scan ~/Downloads
```

### 5. Rollback / Undo
Reverse the most recent organization operation:
```bash
orge undo
```

### 6. View History
```bash
orge history
```

### 7. Filter by File Age
Only organize files modified more than 14 days ago:
```bash
orge organize ~/Downloads -d 14
```

### 8. JSON Output Mode
For scripting, automation, or integration:
```bash
orge organize ~/Downloads --dry-run --json
orge scan ~/Downloads --json
```

### 9. System Diagnostics
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
