"""
orge.classifier - Triple-Tier Classification Engine
Precedence:
  1. Config Rules (Glob, Regex, Size thresholds)
  2. Extension Classification (O(1) normalized table lookup)
  3. Metadata Detection (MIME-type heuristics)
  4. Misc Fallback
"""
import re
import fnmatch
import mimetypes
from typing import Optional, List, Pattern, Dict, Any
from orge.core.models import FileItem, ClassificationResult
from orge.config.manager import ConfigManager

class CompiledRule:
    """Compiled form of a custom config rule for fast execution."""

    def __init__(self, raw: Dict[str, Any]):
        self.category: str = raw.get("category", "Misc")
        self.raw = raw
        self.regex: Optional[Pattern] = None
        self.glob_pattern: Optional[str] = None
        self.min_size_bytes: Optional[int] = raw.get("min_size_bytes")
        self.max_size_bytes: Optional[int] = raw.get("max_size_bytes")

        if "regex" in raw and raw["regex"]:
            try:
                self.regex = re.compile(raw["regex"], re.IGNORECASE)
            except re.error:
                self.regex = None

        if "glob" in raw and raw["glob"]:
            self.glob_pattern = raw["glob"].lower()
        elif "pattern" in raw and raw["pattern"]:
            # fallback pattern field treated as glob
            self.glob_pattern = raw["pattern"].lower()

    def matches(self, item: FileItem) -> Optional[str]:
        # Check size constraints if defined
        if self.min_size_bytes is not None and item.size_bytes < self.min_size_bytes:
            return None
        if self.max_size_bytes is not None and item.size_bytes > self.max_size_bytes:
            return None

        # Check regex
        if self.regex:
            if self.regex.search(item.filename):
                return f"regex:{self.regex.pattern}"

        # Check glob
        if self.glob_pattern:
            if fnmatch.fnmatch(item.filename.lower(), self.glob_pattern):
                return f"glob:{self.glob_pattern}"

        # Size-only rule match
        if (self.min_size_bytes is not None or self.max_size_bytes is not None) and not self.regex and not self.glob_pattern:
            return f"size_constraint:{item.size_bytes}b"

        return None

class Classifier:
    """Determines file categorization using strict tier precedence."""

    def __init__(self, config: ConfigManager):
        self.config = config
        self._compiled_rules: List[CompiledRule] = []
        self._compile_rules()

    def _compile_rules(self):
        self._compiled_rules = [CompiledRule(r) for r in self.config.custom_rules]

    def refresh(self):
        self._compile_rules()

    def classify(self, item: FileItem) -> ClassificationResult:
        # Tier 1: User Config Rules
        for rule in self._compiled_rules:
            matched_reason = rule.matches(item)
            if matched_reason:
                return ClassificationResult(
                    category=rule.category,
                    reason="config_rules",
                    confidence=1.0,
                    matched_rule=matched_reason,
                )

        # Tier 2: Extension Classification (Fast O(1) table lookup)
        ext = item.extension.lower().lstrip(".")
        if ext and ext in self.config.extension_lookup:
            return ClassificationResult(
                category=self.config.extension_lookup[ext],
                reason="extension_detection",
                confidence=1.0,
                matched_rule=f"ext:{ext}",
            )

        # Tier 3: Metadata / Content Detection (MIME-types)
        mime_type, _ = mimetypes.guess_type(item.filename)
        if mime_type:
            top_type, sub_type = mime_type.split("/", 1) if "/" in mime_type else (mime_type, "")
            if top_type == "image":
                return ClassificationResult(category="Images", reason="metadata_detection", confidence=0.85, matched_rule=f"mime:{mime_type}")
            elif top_type == "video":
                return ClassificationResult(category="Videos", reason="metadata_detection", confidence=0.85, matched_rule=f"mime:{mime_type}")
            elif top_type == "audio":
                return ClassificationResult(category="Audio", reason="metadata_detection", confidence=0.85, matched_rule=f"mime:{mime_type}")
            elif top_type == "text":
                return ClassificationResult(category="Documents", reason="metadata_detection", confidence=0.8, matched_rule=f"mime:{mime_type}")
            elif sub_type in ("pdf", "x-pdf"):
                return ClassificationResult(category="PDFs", reason="metadata_detection", confidence=0.9, matched_rule=f"mime:{mime_type}")
            elif sub_type in ("zip", "x-tar", "gzip", "x-7z-compressed", "x-rar-compressed"):
                return ClassificationResult(category="Compressed", reason="metadata_detection", confidence=0.9, matched_rule=f"mime:{mime_type}")

        # Tier 4: Fallback
        return ClassificationResult(
            category="Misc",
            reason="fallback",
            confidence=0.5,
            matched_rule="default_misc",
        )
