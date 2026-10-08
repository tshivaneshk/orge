"""
orge.config - Manages configuration, default categories, and user rules.
"""
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
from orge.core.paths import get_default_config_path

DEFAULT_CATEGORIES: Dict[str, List[str]] = {
    "Images": ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "tiff", "ico", "raw", "heic"],
    "Videos": ["mp4", "mkv", "mov", "avi", "flv", "webm", "wmv", "m4v", "3gp"],
    "Audio": ["mp3", "wav", "m4a", "flac", "aac", "ogg", "wma", "opus"],
    "PDFs": ["pdf"],
    "Word": ["doc", "docx", "odt", "rtf"],
    "Excel": ["xls", "xlsx", "csv", "ods", "tsv"],
    "PowerPoint": ["ppt", "pptx", "odp"],
    "Compressed": ["zip", "rar", "7z", "tar", "gz", "bz2", "xz", "tgz"],
    "Installers": ["exe", "msi", "dmg", "deb", "rpm", "appimage", "pkg"],
    "Python": ["py", "pyw", "ipynb"],
    "Java": ["java", "jar", "class"],
    "C": ["c", "h"],
    "C++": ["cpp", "hpp", "cc", "cxx"],
    "C#": ["cs"],
    "Rust": ["rs"],
    "Go": ["go"],
    "Bash": ["sh", "bash", "zsh"],
    "WebApps": ["html", "htm", "css", "js", "ts", "json", "jsx", "tsx", "vue", "svelte", "wasm"],
    "Documents": ["txt", "md", "markdown", "rst", "log"],
    "Misc": ["crdownload", "part", "torrent", "ics", "url"]
}

DEFAULT_IGNORED: List[str] = [
    ".git", ".svn", ".hg", ".orge", ".venv", "venv", "node_modules",
    "__pycache__", ".DS_Store", "Thumbs.db", "desktop.ini",
    "ntuser.dat*", "bootmgr*", "pagefile.sys", "hiberfil.sys", "swapfile.sys"
]

class ConfigManager:
    """Loads, validates, and serves classification settings and rules."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or get_default_config_path()
        self.categories: Dict[str, List[str]] = {k: list(v) for k, v in DEFAULT_CATEGORIES.items()}
        self.custom_rules: List[Dict[str, Any]] = []
        self.ignored_patterns: List[str] = list(DEFAULT_IGNORED)
        self.theme: str = "System"  # "Light", "Dark", "System"
        self.duplicate_strategy: str = "rename"  # "rename", "skip", "overwrite"
        self.confirm_before_organize: bool = True
        self.keep_history: bool = True
        self.undo_retention_days: int = 30

        # Pre-indexed extension lookup table for fast classification
        self.extension_lookup: Dict[str, str] = {}
        self.load()
        self._build_lookup()

    def _build_lookup(self):
        """Builds normalized mapping of extension -> category for O(1) matching."""
        self.extension_lookup = {}
        for category, extensions in self.categories.items():
            for ext in extensions:
                normalized = ext.strip().lower().lstrip(".")
                if normalized:
                    self.extension_lookup[normalized] = category

    def load(self):
        if self.config_path and self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "categories" in data and isinstance(data["categories"], dict):
                        self.categories.update(data["categories"])
                    if "custom_rules" in data and isinstance(data["custom_rules"], list):
                        self.custom_rules = data["custom_rules"]
                    if "ignored_patterns" in data and isinstance(data["ignored_patterns"], list):
                        self.ignored_patterns = data["ignored_patterns"]
                    if "theme" in data and isinstance(data["theme"], str):
                        self.theme = data["theme"]
                    if "duplicate_strategy" in data and isinstance(data["duplicate_strategy"], str):
                        self.duplicate_strategy = data["duplicate_strategy"]
                    if "confirm_before_organize" in data and isinstance(data["confirm_before_organize"], bool):
                        self.confirm_before_organize = data["confirm_before_organize"]
                    if "keep_history" in data and isinstance(data["keep_history"], bool):
                        self.keep_history = data["keep_history"]
                    if "undo_retention_days" in data:
                        self.undo_retention_days = data["undo_retention_days"]
            except Exception:
                pass
        self._build_lookup()

    def save(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "categories": self.categories,
            "custom_rules": self.custom_rules,
            "ignored_patterns": self.ignored_patterns,
            "theme": self.theme,
            "duplicate_strategy": self.duplicate_strategy,
            "confirm_before_organize": self.confirm_before_organize,
            "keep_history": self.keep_history,
            "undo_retention_days": getattr(self, "undo_retention_days", 30),
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_path": str(self.config_path),
            "categories_count": len(self.categories),
            "custom_rules_count": len(self.custom_rules),
            "ignored_patterns": self.ignored_patterns,
            "categories": self.categories,
            "custom_rules": self.custom_rules,
            "theme": self.theme,
            "duplicate_strategy": self.duplicate_strategy,
            "confirm_before_organize": self.confirm_before_organize,
            "keep_history": self.keep_history,
            "undo_retention_days": getattr(self, "undo_retention_days", 30),
        }
