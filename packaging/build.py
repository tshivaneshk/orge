"""
packaging/build.py
Comprehensive cross-platform automated builder & packager for ORGE.

Capabilities:
1. Cleans stale build artifacts (build/, dist/, dist-installer/, *.spec).
2. Builds Python standard sdist (.tar.gz) and wheel (.whl) via `build`.
3. Compiles Windows GUI binary (`ORGE.exe`, windowed/noconsole, PE subsystem 2).
4. Compiles Windows CLI binary (`orge.exe`, console, PE subsystem 3).
5. Assembles complete dist/ORGE package containing both ORGE.exe and orge.exe.
6. Validates binary integrity:
   - ORGE.exe must exist and have PE Subsystem == 2 (Windows GUI, no console)
   - orge.exe must exist and have PE Subsystem == 3 (Windows CUI, console)
7. Generates Portable Zip package (`dist/ORGE-Portable-2.2.0.zip`).
8. Compiles Inno Setup installer (`ORGE-Setup-2.2.0.exe`) if Inno Setup compiler is found.
9. Creates Linux & macOS standalone CLI tarballs if running on those platforms.
"""

import os
import sys
import shutil
import subprocess
import zipfile
import tarfile
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
INSTALLER_DIR = ROOT_DIR / "dist-installer"
VERSION = "2.2.0"

def log(msg: str):
    print(f"\n[ORGE BUILD] {msg}", flush=True)

def clean_artifacts():
    log("Cleaning stale build artifacts...")
    for d in [BUILD_DIR, DIST_DIR, INSTALLER_DIR]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            log(f"  Removed directory: {d}")
    for spec in ROOT_DIR.glob("*.spec"):
        try:
            spec.unlink()
            log(f"  Removed spec: {spec}")
        except Exception:
            pass

def build_python_packages():
    log("Building Python sdist and wheel packages...")
    cmd = [sys.executable, "-m", "build"]
    subprocess.run(cmd, cwd=str(ROOT_DIR), check=True)
    log("Python packages built successfully in dist/")

def build_windows_binaries():
    log("Compiling Windows GUI application (ORGE.exe) with PyInstaller (--onedir --noconsole)...")
    gui_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--onedir", "--noconsole",
        "--name", "ORGE",
        "--paths", "src",
        "src/orge/gui/__main__.py"
    ]
    subprocess.run(gui_cmd, cwd=str(ROOT_DIR), check=True)

    # Ensure dist/ORGE/ORGE.exe has the authentic GUI binary from build/ORGE/ORGE.exe
    src_gui_exe = BUILD_DIR / "ORGE" / "ORGE.exe"
    dst_gui_exe = DIST_DIR / "ORGE" / "ORGE.exe"
    if src_gui_exe.exists():
        shutil.copy2(src_gui_exe, dst_gui_exe)
        log(f"Verified GUI binary: copied {src_gui_exe} -> {dst_gui_exe}")

    log("Compiling Windows standalone CLI application (orge.exe) with PyInstaller (--onefile --console)...")
    cli_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--onefile", "--console",
        "--name", "orge",
        "--paths", "src",
        "src/orge/__main__.py"
    ]
    subprocess.run(cli_cmd, cwd=str(ROOT_DIR), check=True)
    log("Standalone CLI binary built at dist/orge.exe")

    # Also place orge-cli.exe in dist/ORGE/ for the companion directory package
    shutil.copy2(DIST_DIR / "orge.exe", DIST_DIR / "ORGE" / "orge-cli.exe")
    log("Copied companion CLI to dist/ORGE/orge-cli.exe")

def validate_windows_binaries():
    log("Validating PE Subsystem flags and executable integrity...")
    import pefile

    gui_exe = DIST_DIR / "ORGE" / "ORGE.exe"
    cli_exe = DIST_DIR / "orge.exe"
    cli_comp = DIST_DIR / "ORGE" / "orge-cli.exe"

    if not gui_exe.exists():
        raise RuntimeError(f"Missing GUI binary: {gui_exe}")
    if not cli_exe.exists():
        raise RuntimeError(f"Missing CLI binary: {cli_exe}")
    if not cli_comp.exists():
        raise RuntimeError(f"Missing companion CLI binary: {cli_comp}")

    pe_gui = pefile.PE(str(gui_exe))
    subsys_gui = pe_gui.OPTIONAL_HEADER.Subsystem
    pe_gui.close()

    pe_cli = pefile.PE(str(cli_exe))
    subsys_cli = pe_cli.OPTIONAL_HEADER.Subsystem
    pe_cli.close()

    pe_comp = pefile.PE(str(cli_comp))
    subsys_comp = pe_comp.OPTIONAL_HEADER.Subsystem
    pe_comp.close()

    log(f"  ORGE.exe PE Subsystem: {subsys_gui} (expected 2: IMAGE_SUBSYSTEM_WINDOWS_GUI)")
    log(f"  dist/orge.exe PE Subsystem: {subsys_cli} (expected 3: IMAGE_SUBSYSTEM_WINDOWS_CUI)")
    log(f"  dist/ORGE/orge-cli.exe PE Subsystem: {subsys_comp} (expected 3: IMAGE_SUBSYSTEM_WINDOWS_CUI)")

    if subsys_gui != 2:
        raise RuntimeError(f"Validation FAILED: ORGE.exe must be a GUI application (subsystem 2), got {subsys_gui}")
    if subsys_cli != 3:
        raise RuntimeError(f"Validation FAILED: orge.exe must be a Console application (subsystem 3), got {subsys_cli}")
    if subsys_comp != 3:
        raise RuntimeError(f"Validation FAILED: orge-cli.exe must be a Console application (subsystem 3), got {subsys_comp}")

    log("✓ Validation SUCCESS: ORGE.exe is GUI, orge.exe is CLI.")

def create_portable_zip():
    log(f"Creating Windows Portable Zip: dist/ORGE-Portable-{VERSION}.zip...")
    zip_path = DIST_DIR / f"ORGE-Portable-{VERSION}.zip"
    orge_dir = DIST_DIR / "ORGE"
    root_cli = DIST_DIR / "orge.exe"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(orge_dir):
            for file in files:
                full_path = Path(root) / file
                arcname = full_path.relative_to(orge_dir)
                zf.write(full_path, arcname)
        # Include orge.exe in the portable root
        if root_cli.exists():
            zf.write(root_cli, "orge.exe")

    log(f"✓ Created portable zip: {zip_path} ({zip_path.stat().st_size:,} bytes)")

def compile_inno_installer():
    log("Looking for Inno Setup Compiler (ISCC.exe)...")
    iscc_candidates = [
        shutil.which("iscc"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    iscc_path = None
    for cand in iscc_candidates:
        if cand and Path(cand).exists():
            iscc_path = str(cand)
            break

    if not iscc_path:
        log("Notice: ISCC.exe not found on system. Skipping installer compilation.")
        return None

    log(f"Compiling Inno Setup Script using: {iscc_path}")
    iss_script = ROOT_DIR / "packaging" / "windows" / "installer.iss"
    INSTALLER_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [iscc_path, str(iss_script)]
    subprocess.run(cmd, cwd=str(ROOT_DIR), check=True)

    installer_exe = INSTALLER_DIR / f"ORGE-Setup-{VERSION}.exe"
    if not installer_exe.exists():
        raise RuntimeError(f"Installer was not created at: {installer_exe}")

    log(f"✓ Created installer: {installer_exe} ({installer_exe.stat().st_size:,} bytes)")
    return installer_exe

def main():
    log(f"=== Starting ORGE {VERSION} Unified Local Build Pipeline ===")
    clean_artifacts()
    build_python_packages()

    if sys.platform == "win32":
        build_windows_binaries()
        validate_windows_binaries()
        create_portable_zip()
        compile_inno_installer()
    elif sys.platform.startswith("linux"):
        log("Building standalone Linux CLI...")
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean", "--noconfirm",
            "--onedir", "--name", "orge",
            "--paths", "src",
            "src/orge/__main__.py"
        ]
        subprocess.run(cmd, cwd=str(ROOT_DIR), check=True)
        tar_path = DIST_DIR / f"orge-{VERSION}-linux-x64.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(DIST_DIR / "orge", arcname="orge")
        log(f"✓ Created Linux CLI tarball: {tar_path}")
    elif sys.platform == "darwin":
        log("Building standalone macOS CLI...")
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean", "--noconfirm",
            "--onedir", "--name", "orge",
            "--paths", "src",
            "src/orge/__main__.py"
        ]
        subprocess.run(cmd, cwd=str(ROOT_DIR), check=True)
        tar_path = DIST_DIR / f"orge-{VERSION}-macos.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(DIST_DIR / "orge", arcname="orge")
        log(f"✓ Created macOS CLI tarball: {tar_path}")

    log("=== ORGE Build Pipeline Complete! All local artifacts ready. ===")

if __name__ == "__main__":
    main()
