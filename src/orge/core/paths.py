"""
orge.core.paths - Cross-platform configuration, data, and cache path resolution.
Complies with XDG specifications on Linux/macOS and Known Folders on Windows.
"""
import os
import sys
from pathlib import Path
from typing import Set

def get_config_dir() -> Path:
    """
    Returns the user-level configuration directory:
    - Windows: %APPDATA%/orge
    - Linux / POSIX: $XDG_CONFIG_HOME/orge or ~/.config/orge
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / "AppData" / "Roaming"
        return base / "orge"
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            base = Path(xdg_config)
        else:
            base = Path.home() / ".config"
        return base / "orge"

def get_data_dir() -> Path:
    """
    Returns the user-level data directory (for history journals, audit logs):
    - Windows: %LOCALAPPDATA%/orge
    - Linux / POSIX: $XDG_DATA_HOME/orge or ~/.local/share/orge
    """
    if sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            base = Path(localappdata)
        else:
            base = Path.home() / "AppData" / "Local"
        return base / "orge"
    else:
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            base = Path(xdg_data)
        else:
            base = Path.home() / ".local" / "share"
        return base / "orge"

def get_history_dir() -> Path:
    """Returns directory for history journaling."""
    return get_data_dir() / "history"

def get_default_config_path() -> Path:
    """Returns path to the default config.json file."""
    return get_config_dir() / "config.json"

def get_app_install_dir() -> Path:
    """
    Returns the directory where ORGE binary or package is installed / running from.
    Handles PyInstaller frozen environments (sys._MEIPASS or sys.executable dir)
    as well as source tree root.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # If running from source tree, repository / package root
    return Path(__file__).resolve().parent.parent.parent.parent

def get_runtime_protected_paths() -> Set[Path]:
    """Returns critical paths belonging to ORGE itself (install dir, config dir, data dir)."""
    paths = set()
    try:
        paths.add(get_app_install_dir().resolve())
    except Exception:
        pass
    try:
        paths.add(get_config_dir().resolve())
    except Exception:
        pass
    try:
        paths.add(get_data_dir().resolve())
    except Exception:
        pass
    return paths
