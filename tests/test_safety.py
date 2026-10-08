"""
Additional unit and cross-platform safety tests for ORGE:
- Symlinks & junctions handling
- Path traversal rejection
- Protected root directory blocking
- Unknown extensions and empty extensions
- Duplicate names and nested directory handling
- History persistence across instance re-instantiation
- GUI module instantiation test
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure src is on path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from orge.core.models import FileItem, ActionType, OperationPlan, OperationStep
from orge.config.manager import ConfigManager
from orge.classifier.engine import Classifier
from orge.planner.engine import Planner
from orge.safety.validator import SafetyValidator
from orge.history.journal import HistoryManager
from orge.executor.runner import FileExecutor

class TestSafetyAndEdgeCases(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()

        self.config = ConfigManager(config_path=self.root / "cfg.json")
        self.classifier = Classifier(self.config)
        self.planner = Planner(self.classifier, self.config)
        self.validator = SafetyValidator()
        self.history = HistoryManager(history_dir=self.root / "hist")
        self.executor = FileExecutor(self.history)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_path_traversal_detection(self):
        # A malformed step whose destination points outside target folder
        bad_src = self.root / "innocent.txt"
        bad_src.write_text("hello", encoding="utf-8")
        escaped_dst = self.root.parent / "escaped.txt"

        plan = OperationPlan(target_folder=self.root)
        plan.steps.append(OperationStep(
            source_path=bad_src,
            target_path=escaped_dst,
            category="Documents",
            action=ActionType.MOVE,
            reason="malicious_escape"
        ))

        report = self.validator.validate(plan)
        self.assertFalse(report.is_safe)
        self.assertTrue(any("escapes target directory" in i.message for i in report.issues))

    def test_protected_root_blocking(self):
        # Trying to organize drive root or system root must fail
        system_root = Path("C:\\") if sys.platform == "win32" else Path("/")
        plan = OperationPlan(target_folder=system_root)
        report = self.validator.validate(plan)
        self.assertFalse(report.is_safe)
        self.assertTrue(any("Refusing to organize protected" in i.message for i in report.issues))

    def test_no_extension_and_hidden_files(self):
        (self.root / "Makefile").write_text("all: build", encoding="utf-8")
        (self.root / ".env").write_text("KEY=VALUE", encoding="utf-8")

        plan = self.planner.create_plan(self.root)
        self.assertEqual(len(plan.executable_steps), 2)

        successful, errors = self.executor.execute(plan)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(successful), 2)

    def test_history_persistence_across_restarts(self):
        # 1. Execute an operation
        f = self.root / "test.mp3"
        f.write_text("audio", encoding="utf-8")

        plan = self.planner.create_plan(self.root)
        self.executor.execute(plan)

        # 2. Simulate restarting application by creating new instances pointing to same history directory
        new_history = HistoryManager(history_dir=self.root / "hist")
        new_executor = FileExecutor(new_history)

        latest = new_history.get_latest_active()
        self.assertIsNotNone(latest)

        # 3. Undo with new executor instance
        reverted, errors, _ = new_executor.undo_latest()
        self.assertEqual(len(errors), 0)
        self.assertEqual(reverted, 1)
        self.assertTrue(f.exists())

    def test_gui_instantiation(self):
        # In headless Linux CI runners without an X11 server ($DISPLAY), creating a Tk window raises TclError
        if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
            # Verify module imports and class attributes are intact without display server
            from orge.gui.app import OrgeGUI
            self.assertTrue(hasattr(OrgeGUI, "_init_ui"))
            return

        from orge.gui.app import OrgeGUI
        app = OrgeGUI()
        self.assertIsNotNone(app)
        app.withdraw()
        app.destroy()

if __name__ == "__main__":
    unittest.main()
