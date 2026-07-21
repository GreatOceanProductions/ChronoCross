"""Smoke test: confirm Godot 4.3 can load the project headless.

Per §15.4 Step 1 of the design document, the PoC's first concrete action
is a 4-file seed that proves the architecture. This test confirms the
Godot runtime can parse the project, load the main scene, and exit
cleanly without errors.

Run:
    tools/test_godot_smoke.sh
"""
import shutil
import subprocess
import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
GODOT_EXE = Path("D:/Tools/Godot/Godot_v4.3-stable_win64_console.exe")

# Scrub hermes-agent contamination from env
import os
clean_env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME") and "hermes" not in v.lower()}


def main() -> int:
    if not GODOT_EXE.exists():
        print(f"SKIP: Godot not found at {GODOT_EXE}")
        return 0  # Skip gracefully; this is OK in CI without Godot installed

    print(f"Running Godot headless smoke test on {GAME_DIR}")
    result = subprocess.run(
        [str(GODOT_EXE), "--headless", "--path", str(GAME_DIR), "--quit"],
        capture_output=True, text=True, env=clean_env, timeout=60,
    )
    if result.returncode != 0:
        print("Godot exited with non-zero status:")
        print(f"  stdout: {result.stdout}")
        print(f"  stderr: {result.stderr}")
        return 1
    print("OK: Godot booted and quit cleanly.")
    if result.stdout.strip():
        print(f"  stdout: {result.stdout.strip()[:500]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
