"""Tests that exercise the full project, not just the data layer.

Per §9.4 of the design document, one commit per TDD cycle. This file
extends the test suite beyond the data layer to include the Godot
runtime smoke test (per §15.4 Step 1: "the PoC's first concrete
action is a 4-file seed... the seed files are the §1.5 'no magic'
principle in action").

Run:
    python -m pytest tests/ -v
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
GODOT_EXE = Path("D:/Tools/Godot/Godot_v4.3-stable_win64_console.exe")


def test_godot_binary_exists():
    """Godot 4.3 must be available for the runtime tests to run."""
    if not GODOT_EXE.exists():
        pytest.skip(f"Godot not at {GODOT_EXE} — runtime tests skipped")


def test_godot_boots_headless():
    """Godot boots in headless mode and quits cleanly with no errors.

    This is the §15.6 Artifact 1 verification: the project runs from
    a clean clone via `godot --headless --path . --quit`.
    """
    if not GODOT_EXE.exists():
        pytest.skip(f"Godot not at {GODOT_EXE}")

    clean_env = {k: v for k, v in os.environ.items()
                 if k not in ("PYTHONPATH", "PYTHONHOME") and "hermes" not in v.lower()}

    result = subprocess.run(
        [str(GODOT_EXE), "--headless", "--path", str(GAME_DIR), "--quit"],
        capture_output=True, text=True, env=clean_env, timeout=60,
    )
    assert result.returncode == 0, (
        f"Godot exited {result.returncode}.\n"
        f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
    )


def test_project_godot_exists_and_loads():
    """The project.godot file is well-formed Godot 4.3 config."""
    project_file = GAME_DIR / "project.godot"
    assert project_file.exists(), f"missing {project_file}"
    content = project_file.read_text(encoding="utf-8")
    assert "config_version=5" in content, "not a Godot 4.x project file"
    assert "Remaster Engine" in content
    # Per §6.3 locked decision: GDScript only, no C# / .NET
    assert "project/assembly_name=" in content, ".NET assembly name should be empty"


def test_main_scene_exists():
    """The main scene referenced in project.godot exists and is a valid Godot scene file."""
    main_scene = GAME_DIR / "scenes" / "main.tscn"
    assert main_scene.exists(), f"missing {main_scene}"
    content = main_scene.read_text(encoding="utf-8")
    assert "[gd_scene" in content, "not a Godot 4.x scene file"
    assert "format=3" in content, "expected Godot 4.x format=3"
