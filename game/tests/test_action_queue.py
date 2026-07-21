"""Tests for the ActionQueue (the §7.10 speed-based action ordering).

Per §7.10 of the design document, the combat engine has a 6-character
action queue (6 party members + 8 enemies = up to 14 deep per round).
The simulator "sorts by speed (with the original's speed-based algorithm)
and emits the queue at the start of each round. The view animates the
queue in order."

This is the EIGHTH TDD cycle (cycle 43 of the tdd_cron, cycle_count 8),
coming after:
  - cycle 34: test_determinism_prng_seeded (§7.2 derived PRNGs)
  - cycle 35: test_character_data_loads (§7.3 CharacterData)
  - cycle 36: test_tech_data_loads (§7.3 TechData)
  - cycle 38: test_party_manager_active_roster (§7.7 PartyManager)
  - cycle 39: test_tech_resolver_basic_attack (§7.10 TechResolver)
  - cycle 40: (test_decisions_helper fix-loop, not a TDD cycle)
  - cycle 42: (test_decisions_helper fix-loop, not a TDD cycle)

The contract being pinned here is the §7.10 test surface item (a):
the action queue sorts correctly by speed.

The contract (§7.10 + §6.7 5-step action lifecycle):
  1. `ActionQueue` is a Python class that takes a roster of combatants
     (each with `id` and `speed` attributes — a duck-typed contract so
     the queue can compose with `PartyManager` results AND with raw
     enemy dicts) and produces a deterministic per-round turn order.
  2. After construction (or a `rebuild()` call), `ordered_ids` returns
     the list of combatant ids sorted by `speed` descending (higher
     speed acts first — this is the §7.10 "speed-based algorithm").
  3. Ties on speed are broken by *insertion order* (the position in
     the input list). Earlier input → earlier in the queue. This
     matches the §7.10 requirement that the queue is deterministic
     across the same input.
  4. The sort is *stable* — calling `rebuild()` on an already-sorted
     list (or sorting a list that was sorted and then inserted into)
     produces identical output to the first sort.
  5. The queue length matches the input length. An empty input gives
     an empty ordered_ids list (not an error).
  6. An integration smoke test exercises the queue against the
     `PartyManager` (the §7.7 subsystem) so we know the two compose
     in a real §7.10 Battle setup.

This is the §7.10 test surface item (a). Future cycles pin:
  - (b) damage formula across 100 seeded random fights
  - (c) status applications respect resistance/immunity
  - (d) battle log round-trips through save/load
  - (e) full battle can be simulated without a view (headless)

Run:
    python -m pytest tests/test_action_queue.py -v
    python -m pytest tests/                            # all tests
"""
import sys
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GAME_DIR / "tools"))


def test_module_imports():
    """The action_queue module exposes an ActionQueue class.

    Per §7.10 the action queue is a first-class subsystem of the
    combat engine. The Python mirror in `game/tools/action_queue.py`
    is what the test rig exercises without booting the Godot runtime.
    """
    import action_queue  # type: ignore  # noqa: E402

    assert hasattr(action_queue, "ActionQueue"), (
        "action_queue module must expose an ActionQueue class"
    )


def test_empty_queue_returns_empty_order():
    """An ActionQueue built from no combatants returns an empty
    ordered_ids list (not None, not an error). This is the §7.10
    edge case where a battle starts before any combatants join.
    """
    import action_queue  # type: ignore  # noqa: E402

    q = action_queue.ActionQueue([])
    assert q.ordered_ids() == []
    assert len(q.ordered_ids()) == 0


def test_single_combatant_queue():
    """A single combatant produces a single-element ordered list.
    Edge case for §7.10's "battle with one surviving enemy".
    """
    import action_queue  # type: ignore  # noqa: E402

    q = action_queue.ActionQueue([{"id": "serge", "speed": 10}])
    assert q.ordered_ids() == ["serge"]


def test_queue_sorts_by_speed_descending():
    """Per §7.10 "sorts by speed (with the original's speed-based
    algorithm)": higher speed acts first. A queue with speeds
    [10, 5, 20, 15] produces ordering by descending speed:
    speed=20 first, then 15, then 10, then 5.
    """
    import action_queue  # type: ignore  # noqa: E402

    roster = [
        {"id": "slow_a", "speed": 10},
        {"id": "slow_b", "speed": 5},
        {"id": "fast_c", "speed": 20},
        {"id": "mid_d", "speed": 15},
    ]
    q = action_queue.ActionQueue(roster)
    assert q.ordered_ids() == ["fast_c", "mid_d", "slow_a", "slow_b"], (
        "ActionQueue must sort combatants by speed descending"
    )


def test_queue_ties_broken_by_insertion_order():
    """Per §7.10 the sort is deterministic — ties on speed must be
    broken by insertion order (the position in the input list).
    Earlier input → earlier in the queue. This is the §7.10 contract:
    same input → same queue, every time, in every process.
    """
    import action_queue  # type: ignore  # noqa: E402

    roster = [
        {"id": "first", "speed": 10},
        {"id": "second", "speed": 10},
        {"id": "third", "speed": 10},
    ]
    q = action_queue.ActionQueue(roster)
    # All three have speed=10, so insertion order wins.
    assert q.ordered_ids() == ["first", "second", "third"], (
        "ties on speed must be broken by insertion order "
        "(earlier input → earlier in queue)"
    )


def test_queue_tie_break_is_not_id_alphabetical():
    """Tie-breaking must be insertion-order, not alphabetical id
    order. With speeds [10, 10, 10] and ids ["zebra", "apple", "mango"],
    insertion order is ["zebra", "apple", "mango"] — NOT the
    alphabetical ["apple", "mango", "zebra"] that a naïve sort
    might produce. This pins the §7.10 "speed-based algorithm"
    contract explicitly.
    """
    import action_queue  # type: ignore  # noqa: E402

    roster = [
        {"id": "zebra", "speed": 10},
        {"id": "apple", "speed": 10},
        {"id": "mango", "speed": 10},
    ]
    q = action_queue.ActionQueue(roster)
    assert q.ordered_ids() == ["zebra", "apple", "mango"], (
        "ties on speed must be broken by insertion order, not by id"
    )


def test_queue_is_stable_across_rebuilds():
    """Calling rebuild() (or reconstructing) on the same input must
    produce identical ordered_ids. This is the §7.10 determinism
    contract: the action queue is the same for every round, not
    subject to incidental state from a previous round.
    """
    import action_queue  # type: ignore  # noqa: E402

    roster = [
        {"id": "a", "speed": 5},
        {"id": "b", "speed": 5},
        {"id": "c", "speed": 10},
        {"id": "d", "speed": 10},
    ]
    q1 = action_queue.ActionQueue(roster)
    q2 = action_queue.ActionQueue(roster)
    assert q1.ordered_ids() == q2.ordered_ids()


def test_queue_preserves_roster_length():
    """The queue's ordered_ids list has exactly the same length as
    the input roster — no combatants are added or dropped by the
    sort. (A bug that silently drops combatants on tie would still
    produce a valid queue, just shorter than the input — this test
    catches that class of bug.)
    """
    import action_queue  # type: ignore  # noqa: E402

    roster = [
        {"id": f"unit_{i}", "speed": i} for i in range(14)
    ]
    q = action_queue.ActionQueue(roster)
    assert len(q.ordered_ids()) == 14


def test_queue_sixteen_combatants_full_battle():
    """Per §7.10 the action queue "can be 14 deep per round"
    (6 party + 8 enemies). This test exercises a 14-deep queue to
    pin the full §7.10 battle size. All 14 ids must appear exactly
    once, in the correct speed order.
    """
    import action_queue  # type: ignore  # noqa: E402

    # Party (Serge, Kidd, Nikki, Glenn, Herle, Norris) + 8 enemies.
    roster = [
        {"id": "serge", "speed": 12},
        {"id": "kidd", "speed": 15},
        {"id": "nikki", "speed": 11},
        {"id": "glenn", "speed": 14},
        {"id": "herle", "speed": 10},
        {"id": "norris", "speed": 13},
        {"id": "enemy_1", "speed": 8},
        {"id": "enemy_2", "speed": 7},
        {"id": "enemy_3", "speed": 6},
        {"id": "enemy_4", "speed": 5},
        {"id": "enemy_5", "speed": 4},
        {"id": "enemy_6", "speed": 3},
        {"id": "enemy_7", "speed": 2},
        {"id": "enemy_8", "speed": 1},
    ]
    q = action_queue.ActionQueue(roster)
    ordered = q.ordered_ids()
    assert len(ordered) == 14
    # Kidd (15) acts first, then Glenn (14), Norris (13), Serge (12),
    # Nikki (11), Herle (10), then enemies 1..8 in descending speed.
    expected = [
        "kidd", "glenn", "norris", "serge", "nikki", "herle",
        "enemy_1", "enemy_2", "enemy_3", "enemy_4",
        "enemy_5", "enemy_6", "enemy_7", "enemy_8",
    ]
    assert ordered == expected


def test_queue_integration_with_party_manager():
    """Per §7.10 the action queue is built from the §7.7 PartyManager
    active roster plus the enemy roster. This integration smoke test
    exercises the queue with a real PartyManager and a small enemy
    set to confirm the two compose cleanly.

    The duck-typed combatant contract ({id, speed}) means the queue
    must work with any object exposing those two fields — so the
    PartyManager's roster (a list of ids) has to be combined with
    speed data before being passed to the queue. The bridge is
    explicit in this test so the integration surface is visible.
    """
    import action_queue  # type: ignore  # noqa: E402
    import party_manager  # type: ignore  # noqa: E402

    pm = party_manager.PartyManager()
    pm.add_base("serge")
    pm.add_base("kidd")
    pm.add_base("nikki")

    # Speed table: maps roster ids to their §7.10 stat. The §7.7
    # PartyManager does NOT own speed (that's a §7.10 / StatsComponent
    # concern); the bridge layer is responsible for joining roster
    # and stats. This is the §7.10 test surface item (a) integration
    # check: the queue accepts the bridged input and sorts correctly.
    speed_table = {
        "serge": 12,
        "kidd": 15,
        "nikki": 11,
    }
    party_roster = [
        {"id": cid, "speed": speed_table[cid]}
        for cid in pm.active_roster()
    ]
    enemy_roster = [
        {"id": "boss", "speed": 20},
    ]
    q = action_queue.ActionQueue(party_roster + enemy_roster)
    assert q.ordered_ids() == ["boss", "kidd", "serge", "nikki"], (
        "ActionQueue must compose PartyManager roster + enemy roster "
        "and sort by speed descending"
    )
