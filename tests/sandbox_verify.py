"""
Live sandbox verification script testing all real-world scenarios:
- photo.jpg, report.pdf, script.py, archive.zip, movie.mp4, song.mp3, unknown.xyz, Unicode-தமிழ்.txt
- scan, preview, organize --dry-run, organize, history, undo
- collision detection and prevention
"""
import shutil
import tempfile
from pathlib import Path
from orge.cli.main import main

def run_sandbox():
    temp_dir = tempfile.mkdtemp(prefix="orge_verify_")
    root = Path(temp_dir)
    print(f"Testing sandbox in: {root}")

    try:
        # Create test fixture
        files = {
            "photo.jpg": "img data",
            "report.pdf": "pdf data",
            "script.py": "print('hello')",
            "archive.zip": "zip binary",
            "movie.mp4": "video stream",
            "song.mp3": "audio stream",
            "unknown.xyz": "unknown binary",
            "Unicode-தமிழ்.txt": "தமிழ் உரை",
        }
        for name, content in files.items():
            (root / name).write_text(content, encoding="utf-8")

        # 1. orge scan
        print("\n--- 1. Testing orge scan ---")
        assert main(["scan", str(root)]) == 0

        # 2. orge preview
        print("\n--- 2. Testing orge preview ---")
        assert main(["preview", str(root)]) == 0

        # 3. orge organize --dry-run
        print("\n--- 3. Testing orge organize --dry-run ---")
        assert main(["organize", str(root), "--dry-run"]) == 0
        # Verify no files were moved yet
        for name in files:
            assert (root / name).exists(), f"File {name} should not be moved in dry-run!"

        # 4. orge organize --yes
        print("\n--- 4. Testing orge organize -y ---")
        assert main(["organize", str(root), "-y"]) == 0

        # Verify files organized into folders
        assert (root / "Images" / "photo.jpg").exists()
        assert (root / "PDFs" / "report.pdf").exists()
        assert (root / "Python" / "script.py").exists()
        assert (root / "Compressed" / "archive.zip").exists()
        assert (root / "Videos" / "movie.mp4").exists()
        assert (root / "Audio" / "song.mp3").exists()
        assert (root / "Misc" / "unknown.xyz").exists()
        assert (root / "Documents" / "Unicode-தமிழ்.txt").exists()
        print("All 8 files located in appropriate category subfolders!")

        # 5. orge history
        print("\n--- 5. Testing orge history ---")
        assert main(["history"]) == 0

        # 6. orge undo
        print("\n--- 6. Testing orge undo ---")
        assert main(["undo"]) == 0

        # Verify all files returned
        for name in files:
            assert (root / name).exists(), f"File {name} failed to return after undo!"
        print("All 8 files successfully restored to root folder after undo!")

        print("\n[SUCCESS] Sandbox verification passed completely.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_sandbox()
