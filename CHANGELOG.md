# Changelog

All notable changes to **ORGE** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- GitHub Actions CI workflow supporting Ubuntu, Windows, and macOS matrices.

### Removed
- Legacy prototype Bash scripts (`dirtx.sh`, `setup.sh`).
- Obsolete package namespace and hardcoded scripts.
