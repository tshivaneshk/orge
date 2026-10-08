"""
ORGE Core Data Models and Types
"""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
import datetime

class ActionType(str, Enum):
    MOVE = "MOVE"
    SKIP = "SKIP"

@dataclass
class FileItem:
    path: Path
    filename: str
    extension: str
    size_bytes: int
    created_at: datetime.datetime
    modified_at: datetime.datetime
    is_symlink: bool = False
    is_junction: bool = False
    is_file: bool = True

@dataclass
class ClassificationResult:
    category: str
    reason: str  # "config_rules", "extension_detection", "metadata_detection", "fallback"
    confidence: float = 1.0
    matched_rule: Optional[str] = None

@dataclass
class OperationStep:
    source_path: Path
    target_path: Path
    category: str
    action: ActionType
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": str(self.source_path),
            "target": str(self.target_path),
            "category": self.category,
            "action": self.action.value,
            "reason": self.reason,
            "metadata": self.metadata,
        }

@dataclass
class OperationPlan:
    target_folder: Path
    steps: List[OperationStep] = field(default_factory=list)
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)

    @property
    def executable_steps(self) -> List[OperationStep]:
        return [s for s in self.steps if s.action == ActionType.MOVE]

    @property
    def skipped_steps(self) -> List[OperationStep]:
        return [s for s in self.steps if s.action == ActionType.SKIP]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_folder": str(self.target_folder),
            "created_at": self.created_at.isoformat(),
            "executable_count": len(self.executable_steps),
            "skipped_count": len(self.skipped_steps),
            "steps": [s.to_dict() for s in self.steps],
        }

@dataclass
class ValidationIssue:
    severity: str  # "ERROR", "WARNING"
    source_path: Path
    target_path: Optional[Path]
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "source": str(self.source_path),
            "target": str(self.target_path) if self.target_path else None,
            "message": self.message,
        }

@dataclass
class ValidationReport:
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def is_safe(self) -> bool:
        return not any(i.severity == "ERROR" for i in self.issues)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "issues": [i.to_dict() for i in self.issues],
        }

@dataclass
class HistoryRecord:
    id: str
    timestamp: str
    target_folder: str
    total_operations: int
    pending_operations: List[Dict[str, str]]
    completed_operations: List[Dict[str, str]] = field(default_factory=list)
    status: str = "active"  # "active", "completed_undo", "partial_undo"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "target_folder": self.target_folder,
            "total_operations": self.total_operations,
            "pending_operations": self.pending_operations,
            "completed_operations": self.completed_operations,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryRecord":
        return cls(
            id=data["id"],
            timestamp=data["timestamp"],
            target_folder=data["target_folder"],
            total_operations=data.get("total_operations", len(data.get("pending_operations", []))),
            pending_operations=data.get("pending_operations", data.get("operations", [])),
            completed_operations=data.get("completed_operations", []),
            status=data.get("status", "active"),
        )
