"""
tests/test_workflow_and_state.py - Tests State Machine, Automatic Review Transition, Single-Pass Scanning, and Stale Result Rejection.
"""
import unittest
import tempfile
import shutil
from pathlib import Path

try:
    from PySide6.QtWidgets import QApplication
    from orge.gui.adapter import EngineAdapter
    from orge.gui.shell import MainWindowShell, AppWorkflowState
    HAS_PYSIDE6 = True
except (ImportError, ModuleNotFoundError):
    HAS_PYSIDE6 = False

from orge.config.manager import ConfigManager
from orge.core.models import OperationPlan, ValidationReport

if HAS_PYSIDE6:
    app = QApplication.instance() or QApplication([])

@unittest.skipUnless(HAS_PYSIDE6, "PySide6 not available on this platform")
class TestWorkflowAndState(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.target_dir = self.temp_dir / "target_folder"
        self.target_dir.mkdir()

        # Create sample files
        for i in range(10):
            (self.target_dir / f"doc_{i}.txt").write_text("sample")
        for i in range(5):
            (self.target_dir / f"img_{i}.png").write_text("sample")

        self.cfg = ConfigManager()
        self.adapter = EngineAdapter(self.cfg)
        self.shell = MainWindowShell(self.adapter)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initial_state_is_home_idle(self):
        self.assertEqual(self.shell.state, AppWorkflowState.HOME_IDLE)
        self.assertEqual(self.shell.stack.currentIndex(), 0)

    def test_fast_folder_inspection_single_pass(self):
        count, cats = self.adapter.inspect_folder_fast(self.target_dir)
        self.assertEqual(count, 15)
        self.assertEqual(cats.get("Documents"), 10)
        self.assertEqual(cats.get("Images"), 5)

    def test_folder_selection_populates_home_state(self):
        count, cats = self.adapter.inspect_folder_fast(self.target_dir)
        self.shell.home_screen.set_folder(self.target_dir, count, cats)

        self.assertEqual(self.shell.home_screen.found_files_count, 15)
        self.assertEqual(self.shell.home_screen.current_folder, self.target_dir)
        self.assertEqual(self.shell.state, AppWorkflowState.HOME_IDLE)

    def test_review_only_opens_after_plan_completion(self):
        count, cats = self.adapter.inspect_folder_fast(self.target_dir)
        self.shell.home_screen.set_folder(self.target_dir, count, cats)

        # Before scan completes, review is NOT active
        self.assertNotEqual(self.shell.stack.currentIndex(), 1)

        # Start scan
        self.shell._on_start_scan()
        self.assertEqual(self.shell.state, AppWorkflowState.HOME_SCANNING)
        self.assertFalse(self.shell.nav_bar.isEnabled())

        # Synchronously produce plan for verification of transition
        plan = self.adapter.planner.create_plan(self.target_dir)
        report = self.adapter.validator.validate(plan)

        # Trigger completion handler with current generation
        gen_id = self.adapter.current_generation
        self.shell._on_scan_completed(plan, report, gen_id)

        # MUST automatically transition to Review screen (index 1)
        self.assertEqual(self.shell.state, AppWorkflowState.REVIEW)
        self.assertEqual(self.shell.stack.currentIndex(), 1)
        self.assertIsNotNone(self.shell.review_screen.current_plan)
        self.assertEqual(len(self.shell.review_screen.current_plan.executable_steps), 15)
        self.assertTrue(self.shell.review_screen.organize_btn.isEnabled())

    def test_stale_generation_result_is_discarded(self):
        count, cats = self.adapter.inspect_folder_fast(self.target_dir)
        self.shell.home_screen.set_folder(self.target_dir, count, cats)

        # Generation 1
        gen1 = self.adapter.next_generation()
        # Generation 2 (user selected another folder or re-triggered)
        gen2 = self.adapter.next_generation()

        # Dummy plan from old generation 1 finishes late
        plan1 = OperationPlan(target_folder=self.target_dir)
        report1 = ValidationReport()
        self.shell._on_scan_completed(plan1, report1, gen1)

        # Shell must ignore gen1 because current_generation is gen2
        self.assertNotEqual(self.shell.state, AppWorkflowState.REVIEW)
        self.assertNotEqual(self.shell.stack.currentIndex(), 1)

    def test_review_search_operates_in_memory_without_filesystem_work(self):
        plan = self.adapter.planner.create_plan(self.target_dir)
        self.shell.review_screen.set_plan(plan)

        # Search filter
        self.shell.review_screen.search_input.setText("img_0")
        self.shell.review_screen._on_search_changed()

        # Root item count should only display matching categories
        count = self.shell.review_screen.tree.topLevelItemCount()
        self.assertEqual(count, 1)  # Only Images

    def test_organization_completion_resets_review_instantly(self):
        """Bug 2: ReviewScreen reset_state releases plan and clears tree with zero redundant work."""
        plan = self.adapter.planner.create_plan(self.target_dir)
        self.shell.review_screen.set_plan(plan)
        self.assertIsNotNone(self.shell.review_screen.current_plan)
        self.assertGreater(self.shell.review_screen.tree.topLevelItemCount(), 0)

        # Trigger reset_state
        self.shell.review_screen.reset_state()
        self.assertIsNone(self.shell.review_screen.current_plan)
        self.assertEqual(self.shell.review_screen.tree.topLevelItemCount(), 0)
        self.assertEqual(self.shell.review_screen.search_input.text(), "")
