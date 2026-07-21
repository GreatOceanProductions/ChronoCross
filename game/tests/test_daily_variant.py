"""Tests for the daily variant ring buffer."""
import os
import shutil
import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GAME_DIR / "tools"))

import daily_variant  # type: ignore


def test_module_imports():
    assert hasattr(daily_variant, "create_variant")
    assert hasattr(daily_variant, "restore_variant")
    assert hasattr(daily_variant, "list_variants")
    assert hasattr(daily_variant, "diff_variants")
    assert daily_variant.RING_SIZE == 4


def test_create_and_list():
    """Create a variant and verify it appears in the list."""
    # Clean up any pre-existing variants
    if daily_variant.DAILY_DIR.exists():
        backup = daily_variant.DAILY_DIR.with_suffix(".bak")
        if backup.exists():
            shutil.rmtree(backup)
        shutil.copytree(daily_variant.DAILY_DIR, backup)
        shutil.rmtree(daily_variant.DAILY_DIR)
    try:
        new = daily_variant.create_variant()
        assert new.exists()
        assert new.name == "variant-03"
        variants = daily_variant.list_variants()
        assert len(variants) >= 1
    finally:
        # Restore
        shutil.rmtree(daily_variant.DAILY_DIR)
        backup = daily_variant.DAILY_DIR.with_suffix(".bak")
        if backup.exists():
            shutil.copytree(backup, daily_variant.DAILY_DIR)
            shutil.rmtree(backup)


def test_create_rotates():
    """Creating a 2nd variant rotates the first to slot 02."""
    if daily_variant.DAILY_DIR.exists():
        backup = daily_variant.DAILY_DIR.with_suffix(".bak")
        if backup.exists():
            shutil.rmtree(backup)
        shutil.copytree(daily_variant.DAILY_DIR, backup)
        shutil.rmtree(daily_variant.DAILY_DIR)
    try:
        first = daily_variant.create_variant()  # variant-03
        second = daily_variant.create_variant()  # variant-03 (new), variant-02 (was 03)
        variants = daily_variant.list_variants()
        slots = [int(v.name.split("-")[1]) for v in variants]
        assert 2 in slots, f"Expected variant-02 in {slots}"
        assert 3 in slots, f"Expected variant-03 in {slots}"
    finally:
        shutil.rmtree(daily_variant.DAILY_DIR)
        backup = daily_variant.DAILY_DIR.with_suffix(".bak")
        if backup.exists():
            shutil.copytree(backup, daily_variant.DAILY_DIR)
            shutil.rmtree(backup)
