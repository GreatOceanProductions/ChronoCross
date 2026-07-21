"""Tests for the ElementGrid (the §7.4 element grid and resistance model).

Per §7.4 of the design document, the combat engine has a single
`ElementGrid` autoload that owns the resistance chart and provides
the `compute_resistance(attacker, defender) -> float` function used
by the damage step in §7.10.

This is the ELEVENTH TDD cycle in the data-layer / combat-engine
sequence (cycle 11 of the tdd_cron, cycle_count 11), coming after:

  - cycle 1-8:  (data layer + tech resolver + action queue + battle
    sim + status resistance — see loop_state.json)
  - cycle 9:    test_party_manager_active_roster (§7.7 PartyManager)
  - cycle 10:   test_battle_sim_status_resistance_immunity
    (§7.5 + §7.10 step 4)

The contract being pinned here is the §7.4 "compute_resistance"
contract, in its simplest form: an ElementGrid constructed with a
known resistance chart returns the correct multiplier for the
canonical strong/weak pairs (per DEC-001 + DEC-006).

The contract (§7.4 + DEC-001 + DEC-006):

  1. `ElementGrid(chart)` constructs with a resistance chart
     keyed by attacker element id (lowercase) to a dict of
     defender element id -> float multiplier. The chart is the
     on-disk data (per §6.5 / §7.4 — "the chart is data, not code,
     so a mod can rebalance elements without touching the engine").

  2. `compute_resistance(attacker, defender)` returns the float
     multiplier for the (attacker, defender) pair. The canonical
     contract per DEC-001:
       - 1.0 = neutral
       - 0.5 = strong defense (attacker weak vs defender)
       - 2.0 = strong offense (attacker strong vs defender)
       - 0.0 = immune (not used in the canonical chart; immunity
         is a per-entity §7.5 field, not a chart entry)
     The default chart per DEC-001 + DEC-006 has the original
     Chrono Cross hexagonal graph: each of the 6 color elements
     is strong against two and weak against two; the 7th element
     (neutral) is 1.0 against everything (no element interaction).

  3. The chart is symmetric in the §7.4 sense: if A is strong
     against B (multiplier 0.5 from A to B's defender perspective,
     2.0 from A's attacker perspective), the relationship is
     mutual — there is no "asymmetric weakness" in the canonical
     chart. This is the §7.4 cross-modifier rule: each element
     is strong against two others and weak against two others,
     and the strong/weak relationship is a *pair*, not a
     directed edge.

  4. Every element has exactly 7 entries in its row (including
     self, which is always 1.0 per the canonical chart). The
     neutral row is all 1.0 (no special interaction). This
     is the §7.4 "6 entries" test surface item, updated to
     7 per DEC-006's resolution.

  5. An unknown attacker or defender element returns 1.0 (the
     safe default) — does not raise. This is the §7.4 "no
     magic" principle: an unknown element is neutral, not an
     error, so a mod that adds a new element without updating
     the chart does not crash combat.

This is the §7.4 test surface in its minimal form. Future cycles
will pin:
  - The full 7x7 chart against the canonical Chrono Cross
    hexagonal graph (white/red/blue/green/yellow/black + neutral).
  - The level-based scaling formula (the "level-vs-element
    scaling" is a §13 design decision logged for review).
  - The integration with the §7.10 damage step (resistance
    multiplier applied to base_damage).

The GDScript `ElementGrid.gd` autoload is the engine-side
implementation (a future `scaffolding_cron` item); this Python
mirror exists so the test rig can exercise the contract without
booting the Godot runtime.

Run:
    python -m pytest tests/test_element_grid.py -v
    python -m pytest tests/                            # all tests
"""
import sys
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GAME_DIR / "tools"))


# ---------------------------------------------------------------------------
# §7.4 test surface (core): the canonical strong/weak pair returns
# the correct multiplier per DEC-001.
# ---------------------------------------------------------------------------


def test_compute_resistance_canonical_strong_offense_returns_2_0():
    """Per §7.4 + DEC-001, a "strong offense" pair (attacker is
    strong against the defender's element) returns the 2.0
    multiplier. This is the half of the §7.4 cross-modifier
    rule: the original Chrono Cross hexagonal graph has each
    element strong against exactly two others.

    The test pins ONE canonical pair (white strong against red,
    per the original CC chart) to keep the cycle's scope tight
    to the §7.4 compute_resistance contract. A future cycle
    will pin the full 7x7 chart.
    """
    import element_grid  # type: ignore  # noqa: E402

    # Minimal 2x2 chart for the pair under test. Per DEC-001,
    # the canonical strong offense is 2.0. Other entries are 1.0
    # (neutral) so this chart is enough to exercise the contract
    # for the (white, red) pair without committing to the full
    # 7x7 hexagonal graph.
    chart = {
        "white": {
            "white": 1.0,
            "red": 2.0,   # white is strong against red
            "blue": 1.0,
            "green": 1.0,
            "yellow": 1.0,
            "black": 1.0,
            "neutral": 1.0,
        },
        "red": {
            "white": 1.0,
            "red": 1.0,
            "blue": 1.0,
            "green": 1.0,
            "yellow": 1.0,
            "black": 1.0,
            "neutral": 1.0,
        },
    }
    grid = element_grid.ElementGrid(chart)
    result = grid.compute_resistance("white", "red")
    assert result == 2.0, (
        "compute_resistance(white, red) must return 2.0 for the "
        "canonical strong-offense pair (per §7.4 + DEC-001)"
    )


def test_compute_resistance_canonical_strong_defense_returns_0_5():
    """Per §7.4 + DEC-001, the mirror of the strong-offense pair:
    the *defender* is strong against the *attacker's* element, so
    the multiplier from the attacker's perspective is 0.5 (the
    damage is halved). This is the §7.4 cross-modifier rule: the
    strong/weak relationship is a *pair*, not a directed edge.

    Pairs with the strong-offense test above to pin the §7.4
    "symmetric in the right way" contract: if white→red is 2.0
    (white strong vs red), then red→white is 0.5 (red weak vs
    white). The same relationship expressed from the two
    directions.
    """
    import element_grid  # type: ignore  # noqa: E402

    chart = {
        "white": {
            "white": 1.0,
            "red": 2.0,   # white strong vs red
            "blue": 1.0,
            "green": 1.0,
            "yellow": 1.0,
            "black": 1.0,
            "neutral": 1.0,
        },
        "red": {
            "white": 0.5,  # red weak vs white (mirror of above)
            "red": 1.0,
            "blue": 1.0,
            "green": 1.0,
            "yellow": 1.0,
            "black": 1.0,
            "neutral": 1.0,
        },
    }
    grid = element_grid.ElementGrid(chart)
    result = grid.compute_resistance("red", "white")
    assert result == 0.5, (
        "compute_resistance(red, white) must return 0.5 for the "
        "canonical strong-defense pair (per §7.4 + DEC-001 mirror rule)"
    )


def test_compute_resistance_neutral_pair_returns_1_0():
    """Per §7.4 + DEC-001, a "neutral" pair returns the 1.0
    multiplier. This is the default for (a) the same element
    attacking itself, (b) two elements with no special
    relationship in the hexagonal graph, and (c) any pair
    involving the neutral element (per DEC-006, neutral has
    no element interaction — it is 1.0 against everything).

    The test pins all three cases in one assertion sequence to
    keep the cycle's scope tight: self-vs-self (white→white),
    a non-interacting pair (white→blue), and the neutral element
    attacking a color element (neutral→white).
    """
    import element_grid  # type: ignore  # noqa: E402

    chart = {
        "white": {
            "white": 1.0,
            "red": 2.0,
            "blue": 1.0,
            "green": 1.0,
            "yellow": 1.0,
            "black": 1.0,
            "neutral": 1.0,
        },
        "neutral": {
            "white": 1.0,
            "red": 1.0,
            "blue": 1.0,
            "green": 1.0,
            "yellow": 1.0,
            "black": 1.0,
            "neutral": 1.0,
        },
    }
    grid = element_grid.ElementGrid(chart)
    # Self vs self is always neutral.
    assert grid.compute_resistance("white", "white") == 1.0
    # Two unrelated elements are neutral.
    assert grid.compute_resistance("white", "blue") == 1.0
    # Neutral element has no special interaction (per DEC-006).
    assert grid.compute_resistance("neutral", "white") == 1.0
    assert grid.compute_resistance("white", "neutral") == 1.0


def test_compute_resistance_unknown_attacker_returns_1_0():
    """Per §7.4 "no magic" principle: an unknown element id
    returns 1.0 (the safe default), not an error. This lets a
    mod add a new element without immediately crashing combat
    — the mod author updates the chart as a separate step.

    This pins the §7.4 "the engine does not raise on missing
    chart entries" contract for the attacker side.
    """
    import element_grid  # type: ignore  # noqa: E402

    chart = {
        "white": {
            "white": 1.0,
            "red": 2.0,
            "blue": 1.0,
            "green": 1.0,
            "yellow": 1.0,
            "black": 1.0,
            "neutral": 1.0,
        },
    }
    grid = element_grid.ElementGrid(chart)
    # Unknown attacker (e.g. a mod that added "purple" without
    # updating the chart) is treated as neutral, not an error.
    result = grid.compute_resistance("purple", "white")
    assert result == 1.0, (
        "compute_resistance with an unknown attacker must return "
        "1.0 (the safe default) per §7.4 'no magic' principle"
    )


def test_compute_resistance_unknown_defender_returns_1_0():
    """The mirror of the unknown-attacker test: an unknown
    defender element is treated as neutral, not an error.

    This pins the §7.4 contract for the defender side.
    """
    import element_grid  # type: ignore  # noqa: E402

    chart = {
        "white": {
            "white": 1.0,
            "red": 2.0,
            "blue": 1.0,
            "green": 1.0,
            "yellow": 1.0,
            "black": 1.0,
            "neutral": 1.0,
        },
    }
    grid = element_grid.ElementGrid(chart)
    result = grid.compute_resistance("white", "purple")
    assert result == 1.0, (
        "compute_resistance with an unknown defender must return "
        "1.0 (the safe default) per §7.4 'no magic' principle"
    )


def test_element_grid_exposes_chart_for_introspection():
    """The chart is the §7.4 source of truth and must be
    introspectable for debug, mod tooling, and the future
    AI-agent integration (the agent's S-4 commitment per
    §4.4). The Python mirror exposes the chart via an
    attribute so the test rig can verify the chart shape
    without re-importing the constructor's input.

    A future `scaffolding_cron` item will mirror this as a
    `chart` property on the GDScript `ElementGrid` autoload
    (with `@export var chart: Dictionary`).
    """
    import element_grid  # type: ignore  # noqa: E402

    chart = {
        "white": {
            "white": 1.0,
            "red": 2.0,
            "blue": 1.0,
            "green": 1.0,
            "yellow": 1.0,
            "black": 1.0,
            "neutral": 1.0,
        },
    }
    grid = element_grid.ElementGrid(chart)
    assert hasattr(grid, "chart"), (
        "ElementGrid must expose its resistance chart for "
        "introspection (per §7.4 'the chart is data, not code')"
    )
    # The exposed chart must match the input — no silent
    # normalization that would mask a mod author's typo.
    assert grid.chart == chart
