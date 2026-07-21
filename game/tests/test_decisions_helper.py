"""Tests for the decisions queue helper.

Per §9.4 of the design document, one commit per TDD cycle. This is
the test file for the new decisions_helper.py module. Each test is
one TDD cycle.

Run:
    python -m pytest tests/test_decisions_helper.py -v
"""
import os
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add the tools dir to path
GAME_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GAME_DIR / "tools"))

import decisions_helper  # type: ignore


def test_module_imports():
    """decisions_helper imports without crashing."""
    assert hasattr(decisions_helper, "load_queue")
    assert hasattr(decisions_helper, "add")
    assert hasattr(decisions_helper, "apply_timeouts")


def test_load_queue_empty_when_no_file():
    """load_queue returns empty list when DECISIONS.md doesn't exist."""
    # Backup existing file if any
    if decisions_helper.DECISIONS_FILE.exists():
        backup = decisions_helper.DECISIONS_FILE.with_suffix(".md.bak")
        shutil.copy2(decisions_helper.DECISIONS_FILE, backup)
        decisions_helper.DECISIONS_FILE.unlink()
    try:
        items = decisions_helper.load_queue()
        assert items == []
    finally:
        if "backup" in dir() and backup.exists():
            shutil.copy2(backup, decisions_helper.DECISIONS_FILE)
            backup.unlink()


def test_add_creates_decision():
    """add() creates a new decision and returns its id."""
    if decisions_helper.DECISIONS_FILE.exists():
        backup = decisions_helper.DECISIONS_FILE.with_suffix(".md.bak")
        shutil.copy2(decisions_helper.DECISIONS_FILE, backup)
    else:
        backup = None
    try:
        new_id = decisions_helper.add("P2", "Test decision", context="test", options=["A", "B"], default="B")
        assert new_id.startswith("DEC-")
        items = decisions_helper.load_queue()
        assert any(it["id"] == new_id and it["status"] == "open" for it in items)
    finally:
        if backup and backup.exists():
            shutil.copy2(backup, decisions_helper.DECISIONS_FILE)
            backup.unlink()


def test_apply_timeouts_resolves_old_decisions():
    """apply_timeouts auto-resolves decisions older than the threshold."""
    if decisions_helper.DECISIONS_FILE.exists():
        backup = decisions_helper.DECISIONS_FILE.with_suffix(".md.bak")
        shutil.copy2(decisions_helper.DECISIONS_FILE, backup)
    else:
        backup = None
    try:
        # Add a decision
        new_id = decisions_helper.add("P2", "Timeout test", default="B")
        # Manually backdate its filed_ts by writing a hand-crafted file
        # with an old filed timestamp
        old_time = (datetime.now(timezone.utc) - timedelta(hours=13)).isoformat()
        text = decisions_helper.DECISIONS_FILE.read_text(encoding="utf-8")
        # Replace the just-filed timestamp with the old one
        text = text.replace(datetime.now(timezone.utc).isoformat(), old_time)
        decisions_helper.DECISIONS_FILE.write_text(text, encoding="utf-8")
        # Apply timeouts
        timed_out = decisions_helper.apply_timeouts(timeout_hours=12)
        assert new_id in timed_out
        # Verify it's now resolved
        items = decisions_helper.load_queue()
        assert any(it["id"] == new_id and it["status"] == "resolved" for it in items)
    finally:
        if backup and backup.exists():
            shutil.copy2(backup, decisions_helper.DECISIONS_FILE)
            backup.unlink()


def test_resolve_marks_resolved():
    """resolve() marks a decision resolved."""
    if decisions_helper.DECISIONS_FILE.exists():
        backup = decisions_helper.DECISIONS_FILE.with_suffix(".md.bak")
        shutil.copy2(decisions_helper.DECISIONS_FILE, backup)
    else:
        backup = None
    try:
        new_id = decisions_helper.add("P1", "Resolve test")
        success = decisions_helper.resolve(new_id, answer="user picked C")
        assert success
        items = decisions_helper.load_queue()
        assert any(it["id"] == new_id and it["status"] == "resolved" for it in items)
    finally:
        if backup and backup.exists():
            shutil.copy2(backup, decisions_helper.DECISIONS_FILE)
            backup.unlink()


def test_format_summary_returns_string():
    """format_summary returns a non-empty string."""
    summary = decisions_helper.format_summary()
    assert isinstance(summary, str)
    assert len(summary) > 0
