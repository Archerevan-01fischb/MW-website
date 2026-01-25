#!/usr/bin/env python3
"""
Build script for Midwinter Manual Search standalone app.

Creates a single .exe file that can be distributed on itch.io or anywhere else.
No Python installation required for end users!

Requirements:
    pip install pyinstaller

Usage:
    python build_standalone.py
"""

import subprocess
import sys
import shutil
from pathlib import Path

def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Paths
    main_script = script_dir / "midwinter_search_gui.py"
    database_src = project_root / "database" / "midwinter_unified.db"
    output_dir = project_root / "dist"  # Main project dist folder
    build_dir = script_dir / "build"    # Build artifacts stay local

    # Check requirements
    if not main_script.exists():
        print(f"ERROR: Main script not found: {main_script}")
        sys.exit(1)

    if not database_src.exists():
        print(f"ERROR: Database not found: {database_src}")
        print("Make sure midwinter_unified.db exists in the database folder.")
        sys.exit(1)

    # Check for PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    # Clean previous build artifacts (not output_dir - it has other files)
    if build_dir.exists():
        print("Cleaning previous build artifacts...")
        shutil.rmtree(build_dir)

    # Remove old exe if it exists
    old_exe = output_dir / "MidwinterManualSearch.exe"
    if old_exe.exists():
        old_exe.unlink()

    # Build command
    print("\nBuilding standalone executable...")
    print("This may take a minute...\n")

    # Use absolute path to database for PyInstaller
    db_path_str = str(database_src.absolute())

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                          # Single .exe file
        "--windowed",                         # No console window
        "--name", "MidwinterManualSearch",    # Output name
        "--add-data", f"{db_path_str};database",   # Bundle database with absolute path
        "--distpath", str(output_dir),
        "--workpath", str(build_dir),
        "--specpath", str(build_dir),
        str(main_script)
    ]

    subprocess.run(cmd, check=True, cwd=str(script_dir))

    # Check result
    exe_path = output_dir / "MidwinterManualSearch.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n{'=' * 50}")
        print(f"SUCCESS! Built: {exe_path}")
        print(f"Size: {size_mb:.1f} MB")
        print(f"{'=' * 50}")
        print(f"\nThis .exe can be distributed on itch.io!")
        print("Users just double-click to run - no installation needed.")
    else:
        print("\nERROR: Build failed - exe not created")
        sys.exit(1)


if __name__ == "__main__":
    main()
