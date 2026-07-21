"""Tests for the determinism layer (§7.2).

Per §7.2 of the design document, the project uses a single Determinism
autoload that owns every PRNG. Direct calls to randi()/randf() are
forbidden. Each subsystem (combat, dialog, treasure, AI) takes a
Determinism instance and calls methods on it, and a `scoped(tag)`
method returns a derived PRNG whose seed is derived from the global
seed plus the tag.

This test file is the FIRST TDD cycle for the determinism layer. It
asserts the contract that a future GDScript `Determinism.gd` autoload
must also satisfy:

  1. The same global seed + same tag produces the same sequence.
  2. Different tags produce independent streams (no cross-contamination).
  3. The same global seed + different tags does not produce the same
     sequence (derived PRNGs must actually derive differently).
  4. Re-seeding clears all derived PRNGs (caller-states are reset).

For the Python tooling layer, we mirror the GDScript contract in a
plain Python module so the agent's test rig (which runs Python) can
exercise the determinism behavior end-to-end without booting the
Godot runtime. The GDScript `Determinism.gd` autoload is a separate
scaffolding item (per the scaffolding_cron queue).

Run:
    python -m pytest tests/test_determinism.py -v
    python -m pytest tests/                   # all tests
"""
import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GAME_DIR / "tools"))

import determinism  # type: ignore  # noqa: E402


def test_module_imports():
    """The determinism module exposes a Determinism class."""
    assert hasattr(determinism, "Determinism")


def test_same_seed_same_tag_same_sequence():
    """Seeding the same value and reading the same tag produces the
    same sequence — this is the core determinism contract."""
    d1 = determinism.Determinism(0)
    d2 = determinism.Determinism(0)
    a = [d1.scoped("combat").randint(0, 999) for _ in range(20)]
    b = [d2.scoped("combat").randint(0, 999) for _ in range(20)]
    assert a == b, "same seed + same tag must produce same sequence"


def test_same_seed_different_tags_independent():
    """Different tags must produce independent streams.

    Per §7.2 "Why derived PRNGs": a damage roll, a dialog pick, and an
    AI decision all consume from the same global seed but different
    derived streams. Tests that want to assert on combat outcomes
    must not be polluted by dialog entropy (or vice versa).
    """
    d1 = determinism.Determinism(0)
    combat_seq = [d1.scoped("combat").randint(0, 999) for _ in range(20)]
    dialog_seq = [d1.scoped("dialog").randint(0, 999) for _ in range(20)]
    assert combat_seq != dialog_seq, (
        "different tags must produce independent streams; "
        f"got identical sequence: {combat_seq}"
    )


def test_reseed_resets_derived_prngs():
    """Re-seeding the Determinism must clear all derived PRNGs so
    a new tag-scoped stream starts from the new seed.

    Per §7.2 determinism contract #1: "seeding twice with the same
    value produces the same sequence." That requires the scoped()
    cache to be cleared on re-seed.
    """
    d = determinism.Determinism(0)
    # consume some entropy from "combat"
    [d.scoped("combat").randint(0, 999) for _ in range(50)]
    # re-seed with the same value
    d.seed_rng(0)
    # the "combat" stream must be fresh — same as a brand-new instance
    fresh = determinism.Determinism(0)
    expected = [fresh.scoped("combat").randint(0, 999) for _ in range(20)]
    actual = [d.scoped("combat").randint(0, 999) for _ in range(20)]
    assert actual == expected, (
        "re-seeding must reset all derived PRNGs; "
        f"expected {expected}, got {actual}"
    )


def test_different_global_seeds_produce_different_sequences():
    """Two Determinism instances with different global seeds must
    produce different sequences for the same tag — otherwise the
    seed is not actually consumed."""
    d1 = determinism.Determinism(0)
    d2 = determinism.Determinism(42)
    a = [d1.scoped("combat").randint(0, 999) for _ in range(20)]
    b = [d2.scoped("combat").randint(0, 999) for _ in range(20)]
    assert a != b, "different global seeds must produce different sequences"
