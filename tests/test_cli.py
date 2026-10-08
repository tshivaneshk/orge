"""
Test suite covering strict CLI specifications and safety guarantees:
- orge alone without arguments displays help and exits safely (0)
- orge organize requires explicit target
- orge scan, preview, doctor, history, undo commands
"""
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure src is on path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from orge.cli.main import main, create_parser

class TestCLISpec(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temp_dir.name).resolve()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_bare_orge_displays_help_and_does_not_organize(self):
        # Running orge without arguments must NOT organize anything; must print help and return 0
        file_sample = self.test_root / "test.txt"
        file_sample.write_text("loose file", encoding="utf-8")

        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            ret = main([])

        self.assertEqual(ret, 0)
        output = stdout_buf.getvalue()
        self.assertIn("usage: orge", output)
        self.assertIn("Available commands", output)
        # Verify file in test directory was NOT moved
        self.assertTrue(file_sample.exists())

    def test_organize_requires_target_path(self):
        # Running `orge organize` without specifying path should be rejected
        with self.assertRaises(SystemExit) as cm:
            main(["organize"])
        # argparse exits with code 2 on missing required positional argument
        self.assertEqual(cm.exception.code, 2)

    def test_preview_requires_target_path(self):
        with self.assertRaises(SystemExit) as cm:
            main(["preview"])
        self.assertEqual(cm.exception.code, 2)

    def test_scan_requires_target_path(self):
        with self.assertRaises(SystemExit) as cm:
            main(["scan"])
        self.assertEqual(cm.exception.code, 2)

    def test_preview_command_dry_run(self):
        (self.test_root / "photo.png").write_text("image", encoding="utf-8")
        ret = main(["preview", str(self.test_root), "--json"])
        self.assertEqual(ret, 0)
        # File should remain unmoved in test_root
        self.assertTrue((self.test_root / "photo.png").exists())
        self.assertFalse((self.test_root / "Images" / "photo.png").exists())

    def test_organize_with_auto_confirm(self):
        (self.test_root / "song.mp3").write_text("audio data", encoding="utf-8")
        ret = main(["organize", str(self.test_root), "-y", "--json"])
        self.assertEqual(ret, 0)
        # File moved to Audio
        self.assertTrue((self.test_root / "Audio" / "song.mp3").exists())
        self.assertFalse((self.test_root / "song.mp3").exists())

    def test_doctor_command(self):
        ret = main(["doctor", "--json"])
        self.assertEqual(ret, 0)

    def test_history_command(self):
        ret = main(["history", "--json"])
        self.assertEqual(ret, 0)

if __name__ == "__main__":
    unittest.main()
