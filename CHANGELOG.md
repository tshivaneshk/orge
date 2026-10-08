# Changelog

All notable changes to **ORGE** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-10-08

### Added
- Native cross-platform Desktop GUI (`orge gui`) built with Tkinter/ttk sharing the identical core pipeline.
- Standalone standalone application builds powered by PyInstaller (zero Python requirement for end users).
- Windows Inno Setup installer script (`packaging/windows/installer.iss`) creating Start Menu shortcuts and PATH integration.
- Windows portable bundle (`ORGE-Portable-2.1.0.zip`).
- Cross-platform release automation for Linux (`.tar.gz`), macOS (`.tar.gz`), and Windows (`.exe` installer & `.zip`).
- Automated SHA256 checksum generation across all release assets.
- Expanded safety & edge-case test suite (`tests/test_safety.py`).

### Fixed
- Cross-platform path normalization in CI test discovery: resolved symlinked/canonical temporary path comparison failures on macOS (`/private/var/folders` vs `/var/folders`) and Windows 8.3 short paths (`RUNNER~1`).
- Supported Python runtime matrix focused on active modern releases: Python 3.10, 3.11, 3.12, 3.13.

## [2.0.0] - 2026-10-08

### Added
- Complete rewrite and evolution into **ORGE** (Open Resource & Good Organization Engine).
- Standardized `src/orge/` modular layout with discrete pipeline boundaries:
  - `orge.classifier`: Triple-tier classification with regex, glob, fast O(1) extension mapping, and metadata MIME heuristics.
  - `orge.planner`: Deterministic planning resolving collisions before disk execution.
  - `orge.safety`: Multi-stage safety validation protecting system directories, symlinks, Windows junctions, and prevent path traversal.
  - `orge.executor`: Pure Python file operations with zero shell dependencies.
  - `orge.history`: Persistent journaling and partial-undo recovery.
  - `orge.ui`: ANSI table formatting, clean banners, and machine-readable `--json` output.
- Cross-platform path management complying with XDG (Linux) and `%APPDATA%` (Windows).
- Commands: `organize`, `preview`, `scan`, `undo`, `history`, `config`, `doctor`.
- Automated test suite with standard `python -m unittest discover` support.
- Modern `pyproject.toml` packaging.

### Removed
- Legacy prototype Bash scripts (`dirtx.sh`, `setup.sh`).
- Obsolete package namespace and hardcoded scripts.
