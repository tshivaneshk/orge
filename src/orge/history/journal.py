"""
orge.history - History Journaling & State Persistence
Ensures persistent, atomic audit logs for every operation. Records remain intact
under partial undo failures so users can safely retry.
"""
from pathlib import Path
import json
import uuid
import datetime
from typing import List, Optional, Dict, Any
from orge.core.models import HistoryRecord
from orge.core.paths import get_history_dir

class HistoryManager:
    """Manages creation, loading, update, and removal of history records."""

    def __init__(self, history_dir: Optional[Path] = None):
        self.history_dir = history_dir or get_history_dir()
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self._records_cache: Optional[List[HistoryRecord]] = None

    def record_run(self, target_folder: Path, moved_pairs: List[tuple]) -> HistoryRecord:
        record_id = f"orge_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        record = HistoryRecord(
            id=record_id,
            timestamp=datetime.datetime.now().isoformat(),
            target_folder=str(target_folder.resolve()),
            total_operations=len(moved_pairs),
            pending_operations=[{"source": str(src), "target": str(dst)} for src, dst in moved_pairs],
            completed_operations=[],
            status="active",
        )
        self.save_record(record)
        if self._records_cache is not None:
            self._records_cache.insert(0, record)
        return record

    def save_record(self, record: HistoryRecord):
        file_path = self.history_dir / f"{record.id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(record.to_dict(), f, indent=2)

    def list_history(self, force_reload: bool = False) -> List[HistoryRecord]:
        if self._records_cache is not None and not force_reload:
            return list(self._records_cache)
        records: List[HistoryRecord] = []
        for file in sorted(self.history_dir.glob("*.json"), reverse=True):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    records.append(HistoryRecord.from_dict(data))
            except Exception:
                continue
        self._records_cache = records
        return list(records)

    def get_latest_active(self) -> Optional[HistoryRecord]:
        for rec in self.list_history():
            if rec.status != "completed_undo" and rec.pending_operations:
                return rec
        return None

    def get_by_id(self, record_id: str) -> Optional[HistoryRecord]:
        file_path = self.history_dir / f"{record_id}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return HistoryRecord.from_dict(json.load(f))
            except Exception:
                pass
        return None

    def remove_record(self, record_id: str):
        file_path = self.history_dir / f"{record_id}.json"
        if file_path.exists():
            file_path.unlink()
        if self._records_cache is not None:
            self._records_cache = [r for r in self._records_cache if r.id != record_id]

    def clear_records(self, record_ids: List[str]) -> int:
        """Removes specified history records by ID safely. Returns count of deleted records."""
        deleted = 0
        id_set = set(record_ids)
        for rid in record_ids:
            file_path = self.history_dir / f"{rid}.json"
            if file_path.exists():
                try:
                    file_path.unlink()
                    deleted += 1
                except Exception:
                    pass
        if self._records_cache is not None:
            self._records_cache = [r for r in self._records_cache if r.id not in id_set]
        return deleted

    def clear_all(self) -> int:
        """Removes all history records. Returns count of removed records."""
        deleted = 0
        for file in self.history_dir.glob("*.json"):
            try:
                file.unlink()
                deleted += 1
            except Exception:
                pass
        self._records_cache = []
        return deleted
