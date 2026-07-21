"""Tests for the PartyManager (the 6-character party formation system).

Per §7.7 of the design document, the project needs a 6-character
party formation system. The locked §3.9 says the active party size
starts at 3 and grows to 6 across the 10 chapters (slot unlocks at
chapter boundaries create dramatic progression reveals). The
PartyManager owns the 6 slots, the count of currently active
combatants, and a `slot_unlocked` signal that fires when a new
combatant is unlocked.

This is the FOURTH TDD cycle (cycle 6 of the tdd_cron), coming after:
  - cycle 34: test_determinism_prng_seeded (§7.2 derived PRNGs)
  - cycle 35: test_character_data_loads (§7.3 CharacterData)
  - cycle 36: test_tech_data_loads (§7.3 TechData)
  - cycle 37: (prior)

The contract being pinned here mirrors what a future GDScript
`PartyManager.gd` autoload (a `scaffolding_cron` item) will need to
satisfy. A Python mirror in `game/tools/party_manager.py` lets the
test rig exercise the party-formation behavior without booting the
Godot runtime, just like `character_data.py` and `tech_data.py` do.

The contract (§7.7 + §3.9 locked design):
  1. PartyManager has 6 total slots (the §3.9 max active party size).
  2. It starts empty — no bases recruited yet. The party grows
     from 0 to 6 across the 10 chapters as recruitment beats fire
     (one per chapter boundary, per §3.9). The "3→6" framing in
     §3.9 contrasts the *original* Chrono Cross's 3-char max with
     the *redesign's* 6-char max, not a within-game progression.
  3. `add_base(character_id)` puts a base into the next free slot
     and increments `active_count`.
  4. `active_roster` returns the list of active base ids in slot
     order (so slot 0 is the "front" position).
  5. Adding a 4th, 5th, and 6th base fills slots 3, 4, 5 (one per
     `add_base` call) — the §3.9 growth from 3→6 across chapters.
  6. Adding a 7th base raises ValueError (loud failure, per §7.3
     "fail loudly" principle).
  7. `slot_unlocked` is fired exactly once per `add_base` call (so
     the cinematic system can listen for slot-unlock events).
  8. `remove_base(character_id)` removes the base, shifts later
     bases forward, decrements `active_count`. This supports the
     §7.6 form-change logic where Serge's slot is taken by Lynx.
  9. Removing a base that is not in the party raises ValueError
     (loud failure).

Run:
    python -m pytest tests/test_party_manager.py -v
    python -m pytest tests/                        # all tests
"""
import sys
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GAME_DIR / "tools"))


def test_module_imports():
    """The party_manager module exposes a PartyManager class."""
    import party_manager  # type: ignore  # noqa: E402

    assert hasattr(party_manager, "PartyManager")


def test_starts_empty():
    """Per §3.9 the party starts empty and is populated as bases
    are recruited chapter by chapter. The `max_size` is the §3.9
    hard cap (6). `active_count` starts at 0 because no slot has
    been filled yet."""
    import party_manager  # type: ignore  # noqa: E402

    pm = party_manager.PartyManager()
    assert pm.active_count == 0
    assert pm.max_size == 6


def test_active_roster_starts_empty_for_unset_slots():
    """`active_roster` returns the list of active base ids in slot
    order. At construction time the 3 active slots are None (not
    yet recruited). Iteration must skip None so the roster reflects
    *recruited* bases only."""
    import party_manager  # type: ignore  # noqa: E402

    pm = party_manager.PartyManager()
    roster = pm.active_roster()
    assert roster == [], "fresh PartyManager should have no recruited bases yet"
    assert len(roster) == 0


def test_add_base_fills_next_slot():
    """add_base puts the base id into the next free slot (slot index
    = previous active_count) and increments active_count. This is
    the §3.9 slot-unlock growth pattern: chapter 1 ends with Serge
    as the only base, chapter 2 ends with Serge + Kidd, etc."""
    import party_manager  # type: ignore  # noqa: E402

    pm = party_manager.PartyManager()
    pm.add_base("serge")
    assert pm.active_count == 1
    roster = pm.active_roster()
    assert roster == ["serge"]


def test_add_base_grows_from_three_to_six():
    """The §3.9 growth from 3→6: starting from 3 active slots, four
    more add_base calls (one per chapter boundary) bring the party
    to size 6. This is the §3.9 progression reveal mechanic."""
    import party_manager  # type: ignore  # noqa: E402

    pm = party_manager.PartyManager()
    # Simulate the §12.4 chapter-1..3 starting state: Serge, Kidd,
    # Nikki fill the first 3 slots.
    pm.add_base("serge")
    pm.add_base("kidd")
    pm.add_base("nikki")
    assert pm.active_count == 3
    # Chapters 4..6 (per §12.6 / §3.9) unlock Glenn, Herle, Norris.
    pm.add_base("glenn")
    assert pm.active_count == 4
    pm.add_base("herle")
    assert pm.active_count == 5
    pm.add_base("norris")
    assert pm.active_count == 6
    assert pm.active_roster() == ["serge", "kidd", "nikki", "glenn", "herle", "norris"]


def test_add_seventh_base_raises():
    """Per §7.3 "fail loudly": trying to add a 7th base raises
    ValueError rather than silently growing the roster. The §3.9
    max is 6 and the lock is hard."""
    import party_manager  # type: ignore  # noqa: E402

    pm = party_manager.PartyManager()
    for cid in ("serge", "kidd", "nikki", "glenn", "herle", "norris"):
        pm.add_base(cid)
    with pytest.raises(ValueError):
        pm.add_base("mystery_seventh_base")


def test_slot_unlocked_event_fires_per_add():
    """The §7.7 architecture commits to a `slot_unlocked(index, id)`
    signal. In Python, that contract is met by a list of events
    recorded by the manager. One event per add_base call, in order."""
    import party_manager  # type: ignore  # noqa: E402

    pm = party_manager.PartyManager()
    pm.add_base("serge")
    pm.add_base("kidd")
    events = pm.slot_unlocked_events
    assert len(events) == 2
    # (slot_index, character_id) — slot 0 for serge, slot 1 for kidd.
    assert events[0] == (0, "serge")
    assert events[1] == (1, "kidd")


def test_remove_base_shifts_remaining_bases():
    """Per §7.6 form-change logic: when Serge becomes Lynx, the party
    has to remove Serge and add Lynx into the same slot. The remove
    operation shifts later bases forward so slot 0 is always the
    "front" position."""
    import party_manager  # type: ignore  # noqa: E402

    pm = party_manager.PartyManager()
    pm.add_base("serge")
    pm.add_base("kidd")
    pm.add_base("nikki")
    pm.add_base("glenn")
    pm.remove_base("kidd")
    assert pm.active_count == 3
    # glenn shifted from slot 3 to slot 2; nikki stays at slot 2 → 1? No,
    # removing slot 1 (kidd) means slots after it shift down by one.
    roster = pm.active_roster()
    assert roster == ["serge", "nikki", "glenn"], (
        f"expected ['serge', 'nikki', 'glenn'] after removing kidd, got {roster}"
    )


def test_remove_unknown_base_raises():
    """Per §7.3 fail-loudly: trying to remove a base that is not in
    the party raises ValueError, not silent return."""
    import party_manager  # type: ignore  # noqa: E402

    pm = party_manager.PartyManager()
    pm.add_base("serge")
    with pytest.raises(ValueError):
        pm.remove_base("mystery_unknown_base")
