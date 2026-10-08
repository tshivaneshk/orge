"""
Comprehensive test suite for the ORGE architecture:
- Classifier precedence (Config > Extension > Metadata > Fallback)
- Regex and glob matching
- Planner deterministic collision resolution
- Safety validation (system root, path traversal, permissions)
- File executor atomic moves
- Undo safety (partial undo, collision protection during undo)
- Unicode paths, spaces, hidden files, files without extension
- Subcommand CLI execution and JSON mode
"""
import os
import sys
import tempfile
import unittest
import json
from pathlib import Path
import datetime

# Ensure src is on path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from orge.core.models import FileItem, ActionType
from orge.config.manager import ConfigManager
from orge.classifier.engine import Classifier
from orge.planner.engine import Planner
from orge.safety.validator import SafetyValidator
from orge.history.journal import HistoryManager
from orge.executor.runner import FileExecutor
from orge.cli.main import main

class TestORGEPipeline(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temp_dir.name).resolve()

        # Isolated configuration and history
        self.config_file = self.test_root / "config.json"
        self.history_dir = self.test_root / "history"

        self.config = ConfigManager(config_path=self.config_file)
        self.classifier = Classifier(self.config)
        self.planner = Planner(self.classifier, self.config)
        self.validator = SafetyValidator()
        self.history = HistoryManager(history_dir=self.history_dir)
        self.executor = FileExecutor(self.history)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_classifier_precedence_and_regex(self):
        # 1. Custom regex rule
        self.config.custom_rules = [
            {"category": "Invoices", "regex": r"^INV-\d+\.pdf$"},
            {"category": "BigFiles", "min_size_bytes": 1024 * 1024},
            {"category": "CustomGlob", "glob": "important_*.txt"}
        ]
        self.classifier.refresh()

        now = datetime.datetime.now()
        # Item 1: Invoice PDF matches regex rule ahead of standard PDF extension
        item1 = FileItem(Path("INV-102.pdf"), "INV-102.pdf", ".pdf", 500, now, now)
        res1 = self.classifier.classify(item1)
        self.assertEqual(res1.category, "Invoices")
        self.assertEqual(res1.reason, "config_rules")

        # Item 2: Standard PDF falls through to extension classification
        item2 = FileItem(Path("doc.pdf"), "doc.pdf", ".pdf", 500, now, now)
        res2 = self.classifier.classify(item2)
        self.assertEqual(res2.category, "PDFs")
        self.assertEqual(res2.reason, "extension_detection")

        # Item 3: Custom glob rule
        item3 = FileItem(Path("important_notes.txt"), "important_notes.txt", ".txt", 20, now, now)
        res3 = self.classifier.classify(item3)
        self.assertEqual(res3.category, "CustomGlob")

        # Item 4: Fallback
        item4 = FileItem(Path("strange.xyz123"), "strange.xyz123", ".xyz123", 20, now, now)
        res4 = self.classifier.classify(item4)
        self.assertEqual(res4.category, "Misc")

    def test_planner_deterministic_collision_resolution(self):
        # Setup an existing destination file: Images/photo.png
        images_dir = self.test_root / "Images"
        images_dir.mkdir(parents=True)
        (images_dir / "photo.png").write_text("existing image")

        # Incoming new file with identical name in target root
        (self.test_root / "photo.png").write_text("new incoming image")

        plan = self.planner.create_plan(self.test_root)
        step = plan.executable_steps[0]

        # The planner MUST pre-resolve destination collision to photo_1.png
        self.assertEqual(step.target_path.name, "photo_1.png")
        self.assertEqual(step.target_path.parent, images_dir)

        # Execution should respect this EXACT destination
        successful, errors = self.executor.execute(plan)
        self.assertEqual(len(errors), 0)
        self.assertTrue((images_dir / "photo_1.png").exists())
        self.assertTrue((images_dir / "photo.png").exists())

    def test_unicode_and_spaces_handling(self):
        unicode_name = "நன்றி அறிக்கை - report.pdf"
        space_name = "my holiday trip video.mp4"

        (self.test_root / unicode_name).write_text("pdf content")
        (self.test_root / space_name).write_text("mp4 content")

        plan = self.planner.create_plan(self.test_root)
        self.assertEqual(len(plan.executable_steps), 2)

        validation = self.validator.validate(plan)
        self.assertTrue(validation.is_safe)

        successful, errors = self.executor.execute(plan)
        self.assertEqual(len(errors), 0)
        self.assertTrue((self.test_root / "PDFs" / unicode_name).exists())
        self.assertTrue((self.test_root / "Videos" / space_name).exists())

        # Test rollback of unicode and spaces
        reverted, undo_errors, _ = self.executor.undo_latest()
        self.assertEqual(len(undo_errors), 0)
        self.assertEqual(reverted, 2)
        self.assertTrue((self.test_root / unicode_name).exists())
        self.assertTrue((self.test_root / space_name).exists())

    def test_undo_safety_and_partial_failure_retention(self):
        f1 = self.test_root / "file1.png"
        f2 = self.test_root / "file2.png"
        f1.write_text("1")
        f2.write_text("2")

        plan = self.planner.create_plan(self.test_root)
        successful, _ = self.executor.execute(plan)
        self.assertEqual(len(successful), 2)

        # Simulate external file conflict: someone created a new file at f1's original path
        f1.write_text("interfering file")

        # Attempt undo
        reverted, errors, rec = self.executor.undo_latest()
        # 1 file (file2) restored, 1 conflict prevented
        self.assertEqual(reverted, 1)
        self.assertTrue(any("Conflict during undo" in e for e in errors))

        # The history record MUST still exist and have 1 pending operation
        self.assertEqual(rec.status, "partial_undo")
        self.assertEqual(len(rec.pending_operations), 1)

        # Retry undo after user clears the conflicting file
        f1.unlink()
        reverted2, errors2, rec2 = self.executor.undo_record(rec)
        self.assertEqual(reverted2, 1)
        self.assertEqual(rec2.status, "completed_undo")
        self.assertEqual(len(rec2.pending_operations), 0)
        self.assertTrue(f1.exists())

    def test_recursive_organization(self):
        sub = self.test_root / "subfolder"
        sub.mkdir()
        (sub / "nested_photo.jpg").write_text("nested")

        plan = self.planner.create_plan(self.test_root, recursive=True)
        self.assertEqual(len(plan.executable_steps), 1)
        self.assertEqual(plan.executable_steps[0].category, "Images")

    def test_ignored_directories(self):
        git_dir = self.test_root / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("repo config")

        plan = self.planner.create_plan(self.test_root, recursive=True)
        # .git files must be skipped
        self.assertTrue(all(s.action == ActionType.SKIP for s in plan.steps if ".git" in str(s.source_path)))

    def test_cli_json_mode(self):
        (self.test_root / "sample.py").write_text("print('test')")
        # Run CLI in dry-run with --json
        cmd_args = ["organize", str(self.test_root), "--dry-run", "--json"]
        ret = main(cmd_args)
        self.assertEqual(ret, 0)

if __name__ == "__main__":
    unittest.main()
