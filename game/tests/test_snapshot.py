"""Tests for the 8-state snapshot ring buffer.

Per §9.4 of the design document, one commit per TDD cycle. This is
the test file for snapshot.py. Each test is one TDD cycle.

Note: the snapshot system is exercised in the daily_variant tests
(rotation logic is the same). These tests focus on snapshot-specific
behavior.
"""
import os
import shutil
import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GAME_DIR / "tools"))

import snapshot  # type: ignore


def test_module_imports():
    assert hasattr(snapshot, "create_snapshot")
    assert hasattr(snapshot, "list_states")
    assert hasattr(snapshot, "restore_snapshot")
    assert hasattr(snapshot, "diff_snapshots")
    assert snapshot.RING_SIZE == 8


def test_ring_size_is_8():
    """The ring buffer has exactly 8 states, giving 24 hours of history at 3h cadence."""
    assert snapshot.RING_SIZE == 8


def test_segments_include_data_and_scripts():
    """The snapshot captures the implementation segments."""
    for seg in ("data", "scripts", "scenes", "tests", "tools"):
        assert seg in snapshot.SEGMENTS, f"segment {seg} missing"


def test_snapshots_dir_path():
    """Snapshots dir is game/.snapshots (project-local)."""
    assert snapshot.SNAPSHOTS_DIR.name == ".snapshots"
    assert snapshot.SNAPSHOTS_DIR.parent == snapshot.PROJECT_DIR
