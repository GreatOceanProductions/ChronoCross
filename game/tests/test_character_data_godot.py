"""Headless Godot test for the GDScript CharacterData class.

This is the scaffolding-cron side of the §15.4 step 1 contract:

  - The TDD-cron authored `tests/test_character_data.py` (Python
    mirror) and `tools/character_data.py` (Python loader) in cycle
    35. The Python mirror proves the *data shape*.
  - The scaffolding-cron authors `scripts/data/CharacterData.gd`
    (the GDScript Resource) and this file (the Godot-runtime proof).
    The GDScript version is what the actual game uses.

This test invokes Godot 4.3 headless with a SceneTree script that
loads CharacterData.gd, instantiates it, loads all 3 existing
character JSON files (serge, kidd, nikki), and asserts the locked
Phase 3 field values match. The script prints "PASS:" or "FAIL:"
plus a count; this test checks the exit code and the stdout prefix.

Per §13.3 F-1 "architecture-vaporware" guard, the Python mirror
alone is not enough — the engine-side implementation must be proven
to load in the actual Godot runtime. This test is that proof.

Run:
    python -m pytest tests/test_character_data_godot.py -v
    python -m pytest tests/                       # all tests
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
GODOT_EXE = Path("D:/Tools/Godot/Godot_v4.3-stable_win64_console.exe")
TEST_SCRIPT = GAME_DIR / "tests" / "test_character_data_godot.gd"
GDSCRIPT_PATH = GAME_DIR / "scripts" / "data" / "CharacterData.gd"


def _clean_env() -> dict:
    """Scrub hermes-agent contamination from the subprocess env so
    Godot's Python detection (if any) doesn't pick up the wrong
    interpreter. Mirrors the pattern in test_godot_runtime.py.
    """
    return {
        k: v for k, v in os.environ.items()
        if k not in ("PYTHONPATH", "PYTHONHOME") and "hermes" not in v.lower()
    }


def _godot_available() -> bool:
    return GODOT_EXE.exists()


@pytest.mark.skipif(not _godot_available(), reason=f"Godot not at {GODOT_EXE}")
def test_character_data_godot_module_imports():
    """The GDScript `CharacterData.gd` file exists where the
    scaffolding-cron is expected to author it (`scripts/data/CharacterData.gd`).
    """
    assert GDSCRIPT_PATH.exists(), (
        f"Missing GDScript source: {GDSCRIPT_PATH}. "
        "The scaffolding-cron should have authored it in this cycle."
    )


@pytest.mark.skipif(not _godot_available(), reason=f"Godot not at {GODOT_EXE}")
def test_godot_boots_and_passes():
    """Run the headless Godot test script and assert it exits 0
    with the expected 'PASS:' marker in stdout.

    This is the §15.6 Artifact 1 verification extended to the data
    layer: Godot can parse the project, load the CharacterData
    class, load the character JSON files, and assert on the loaded
    data — all without a window.
    """
    assert TEST_SCRIPT.exists(), f"Missing test script: {TEST_SCRIPT}"
    assert GDSCRIPT_PATH.exists(), f"Missing GDScript source: {GDSCRIPT_PATH}"

    # On Windows, Godot 4.3 expects native paths in --path.
    result = subprocess.run(
        [str(GODOT_EXE), "--headless", "--path", str(GAME_DIR), "--script", str(TEST_SCRIPT)],
        capture_output=True, text=True, env=_clean_env(), timeout=60,
    )
    stdout = result.stdout or ""
    stderr = result.stderr or ""

    assert result.returncode == 0, (
        f"Godot test exited {result.returncode}.\n"
        f"  stdout: {stdout[:1000]}\n"
        f"  stderr: {stderr[:1000]}"
    )
    assert "PASS: test_character_data_godot" in stdout, (
        f"Expected 'PASS: test_character_data_godot' in stdout, got:\n{stdout[:1000]}"
    )


@pytest.mark.skipif(not _godot_available(), reason=f"Godot not at {GODOT_EXE}")
def test_project_still_boots_after_character_data_added():
    """Adding `scripts/data/CharacterData.gd` must not break the
    project's main scene boot. Per §6.3, new code is layered onto
    the project without disrupting existing scenes.

    This re-runs the basic `godot --headless --quit` smoke test to
    catch the case where a malformed GDScript file (e.g., a parse
    error in CharacterData.gd) breaks the whole project.
    """
    result = subprocess.run(
        [str(GODOT_EXE), "--headless", "--path", str(GAME_DIR), "--quit"],
        capture_output=True, text=True, env=_clean_env(), timeout=60,
    )
    assert result.returncode == 0, (
        f"Godot exited {result.returncode} after CharacterData.gd added.\n"
        f"  stdout: {result.stdout[:500]}\n"
        f"  stderr: {result.stderr[:500]}"
    )
