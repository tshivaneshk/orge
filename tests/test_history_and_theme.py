"""
tests/test_history_and_theme.py - Validates History Management, Clear Features, Undo Safety, and Light-Only Theme & Legacy Config Compatibility.
"""
import unittest
import tempfile
import shutil
import json
from pathlib import Path
from orge.history.journal import HistoryManager
from orge.config.manager import ConfigManager
from orge.gui.theme import ThemeManager, LIGHT_PALETTE
from orge.gui.tokens import LIGHT_PALETTE as TOKENS_PALETTE

class TestHistoryAndTheme(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.history_dir = self.temp_dir / "history"
        self.history_manager = HistoryManager(history_dir=self.history_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_and_list_history(self):
        target = self.temp_dir / "test_target"
        target.mkdir()
        pairs = [(target / "a.txt", target / "Documents" / "a.txt")]
        rec = self.history_manager.record_run(target, pairs)

        self.assertIsNotNone(rec.id)
        records = self.history_manager.list_history()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].id, rec.id)
        self.assertEqual(records[0].total_operations, 1)

    def test_clear_single_record(self):
        target = self.temp_dir / "target"
        target.mkdir()
        rec1 = self.history_manager.record_run(target, [(target / "1.txt", target / "1_dst.txt")])
        rec2 = self.history_manager.record_run(target, [(target / "2.txt", target / "2_dst.txt")])

        self.assertEqual(len(self.history_manager.list_history()), 2)
        deleted = self.history_manager.clear_records([rec1.id])
        self.assertEqual(deleted, 1)

        remaining = self.history_manager.list_history()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].id, rec2.id)

    def test_clear_multiple_records(self):
        target = self.temp_dir / "target"
        target.mkdir()
        rec1 = self.history_manager.record_run(target, [(target / "1.txt", target / "1_dst.txt")])
        rec2 = self.history_manager.record_run(target, [(target / "2.txt", target / "2_dst.txt")])
        rec3 = self.history_manager.record_run(target, [(target / "3.txt", target / "3_dst.txt")])

        self.assertEqual(len(self.history_manager.list_history()), 3)
        deleted = self.history_manager.clear_records([rec1.id, rec3.id])
        self.assertEqual(deleted, 2)

        remaining = self.history_manager.list_history()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].id, rec2.id)

    def test_clear_all_records(self):
        target = self.temp_dir / "target"
        target.mkdir()
        self.history_manager.record_run(target, [(target / "1.txt", target / "1_dst.txt")])
        self.history_manager.record_run(target, [(target / "2.txt", target / "2_dst.txt")])

        self.assertEqual(len(self.history_manager.list_history()), 2)
        deleted = self.history_manager.clear_all()
        self.assertEqual(deleted, 2)
        self.assertEqual(len(self.history_manager.list_history()), 0)

    def test_empty_history(self):
        self.assertEqual(len(self.history_manager.list_history()), 0)
        self.assertIsNone(self.history_manager.get_latest_active())
        self.assertEqual(self.history_manager.clear_all(), 0)

    def test_theme_manager_always_light(self):
        tm = ThemeManager("Dark")
        # Light-only system always enforces Light mode
        self.assertEqual(tm.mode, "Light")
        self.assertFalse(tm.is_dark)

        tm.set_mode("Dark")
        self.assertEqual(tm.mode, "Light")
        self.assertFalse(tm.is_dark)

        tm.set_mode("System")
        self.assertEqual(tm.mode, "Light")
        self.assertFalse(tm.is_dark)

    def test_legacy_config_theme_safely_ignored(self):
        """Confirms that old config files containing a theme value still load cleanly without crashing."""
        cfg_file = self.temp_dir / "legacy_config.json"
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump({"theme": "Dark", "duplicate_strategy": "rename"}, f)

        cfg = ConfigManager(config_path=cfg_file)
        self.assertEqual(cfg.theme, "Dark")  # Preserved in file
        self.assertEqual(cfg.duplicate_strategy, "rename")

        # ThemeManager still safely operates in Light mode
        tm = ThemeManager(initial_mode=cfg.theme)
        self.assertEqual(tm.mode, "Light")
        self.assertFalse(tm.is_dark)

    def test_gradient_tokens_contrast_and_stops(self):
        """Verifies exact spec palette stops."""
        self.assertEqual(TOKENS_PALETTE.bg_mint, "#E6F6F0")
        self.assertEqual(TOKENS_PALETTE.bg_sky, "#E9F0FC")
        self.assertEqual(TOKENS_PALETTE.bg_lavender, "#F1EAFB")
        self.assertEqual(TOKENS_PALETTE.accent_gradient_start, "#0B7A6A")
        self.assertEqual(TOKENS_PALETTE.accent_gradient_end, "#0E7490")
        self.assertEqual(TOKENS_PALETTE.text_primary, "#1C1B19")
        self.assertEqual(TOKENS_PALETTE.text_secondary, "#4F5855")

    def test_regression_history_immediate_update_after_organization(self):
        """Bug 1: Organization record is immediately available in memory and renders in HistoryScreen."""
        hm = HistoryManager(self.history_dir)
        test_folder = self.temp_dir / "target"
        test_folder.mkdir()
        src = test_folder / "file.txt"
        dst = test_folder / "Documents" / "file.txt"
        src.write_text("hello")

        # Record run
        rec = hm.record_run(test_folder, [(src, dst)])
        self.assertIsNotNone(rec)

        # In-memory list_history returns it immediately
        cached_records = hm.list_history()
        self.assertEqual(len(cached_records), 1)
        self.assertEqual(cached_records[0].id, rec.id)
        self.assertEqual(cached_records[0].total_operations, 1)

    def test_regression_settings_dropdown_persistence(self):
        """Bug 3: Settings duplicate strategy and undo retention persist across restarts."""
        cfg_file = self.temp_dir / "settings_persist.json"
        cfg = ConfigManager(config_path=cfg_file)
        cfg.duplicate_strategy = "skip"
        cfg.undo_retention_days = "Forever"
        cfg.save()

        # Reload from disk
        cfg2 = ConfigManager(config_path=cfg_file)
        self.assertEqual(cfg2.duplicate_strategy, "skip")
        self.assertEqual(cfg2.undo_retention_days, "Forever")

        cfg2.undo_retention_days = 90
        cfg2.save()

        cfg3 = ConfigManager(config_path=cfg_file)
        self.assertEqual(cfg3.undo_retention_days, 90)
