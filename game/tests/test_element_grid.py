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



# ---------------------------------------------------------------------------
# §7.4 test surface (full chart): the canonical 7x7 hexagonal graph
# pinned at the Python mirror level. Per §7.4 of the design document,
# the original Chrono Cross chart has each of the 6 color elements
# strong against exactly 2 and weak against exactly 2; per DEC-006,
# the 7th element is 'neutral' (no special interaction with any of
# the 6 color elements). The full 7x7 chart is the engine's
# reference; a mod that rebalances elements edits one data file
# and the engine does not change (per §7.4 "the chart is data,
# not code").
#
# This is the TWELFTH TDD cycle in the data-layer / combat-engine
# sequence (cycle 12 of the tdd_cron), coming after:
#
#   - cycle 11: test_element_grid_compute_resistance (§7.4 minimal
#     compute_resistance contract — 6 tests, commit 329e509).
#
# The contract being pinned here is the §7.4 full 7x7 chart, the
# canonical Chrono Cross hexagonal graph augmented with the 7th
# 'neutral' element per DEC-006:
#
#   1. The full chart is exposed as a constant on the `element_grid`
#      module so the Python mirror has a single reference. The
#      GDScript `ElementGrid.gd` autoload (a future scaffolding-cron
#      item) will load the same chart from
#      `data/elements/resistances.json` (per the §7.4 GDScript
#      example). The Python constant is the Python mirror's source
#      of truth; a future cycle will author the JSON file to match.
#
#   2. Each of the 6 color elements (white, red, blue, green,
#      yellow, black) has exactly 2 strong (2.0) and 2 weak (0.5)
#      off-diagonal entries, plus self (1.0), the neutral element
#      (1.0), and 1 neutral element-pair — for a total of 7
#      entries per row. This is the §7.4 "hexagonal graph"
#      constraint: each element strong vs 2, weak vs 2.
#
#   3. The neutral element (the 7th) has all 1.0 entries: no
#      special interaction with any of the 6 color elements
#      (per DEC-006 "neutral is 1.0 against everything"). The
#      neutral element is for physical / non-elemental abilities
#      and Chrono Cross specials (Time Egg, etc.).
#
#   4. The mirrored-pairs rule (per DEC-001) holds for every
#      interaction: if A→B = 2.0 (A strong vs B), then B→A = 0.5
#      (B weak vs A), and vice versa. This is the §7.4
#      "symmetric in the right way" contract applied to every
#      strong/weak pair, not just the canonical (white, red) pair
#      pinned in cycle 11.
#
#   5. The chart matches the white.json hint from the data-cron's
#      target queue (per DEC-001 + the white.json values pinned
#      by the data-cron): W→R = 0.5 (white weak vs red) and
#      W→Bk = 2.0 (white strong vs black). The full chart
#      extends this to 2 strong + 2 weak per color element.
#
# This is the §7.4 test surface for the full 7x7 chart. Future
# cycles will pin:
#   - The on-disk data/elements/resistances.json file (the §8.4
#     translator's output, currently a future data-cron item).
#   - The level-based scaling formula (per §7.4, "the exact
#     formula is a design decision logged for §13 review").
#   - The integration with the §7.10 damage step (resistance
#     multiplier applied to base_damage).
# ---------------------------------------------------------------------------

# The 6 color elements (per DEC-001 + DEC-006). The 7th element,
# 'neutral', is excluded from the "2 strong + 2 weak" check
# because the §7.4 spec only requires the hexagonal graph for
# the 6 color elements; neutral is the special-case 1.0 row.
_COLOR_ELEMENTS = ("white", "red", "blue", "green", "yellow", "black")
_ALL_ELEMENTS = _COLOR_ELEMENTS + ("neutral",)


def test_canonical_chart_is_exposed_as_module_constant():
    """Per §7.4, the canonical 7x7 chart must be exposed as a
    module-level constant so the Python mirror has a single
    reference. The GDScript `ElementGrid.gd` autoload will load
    the same chart from `data/elements/resistances.json`; the
    Python constant is the Python mirror's source of truth.

    Pinning this contract here makes the chart discoverable
    for the future S-4 AI-agent integration (§4.4): the agent
    can read the canonical chart and reason about element
    matchups without booting the Godot runtime.
    """
    import element_grid  # type: ignore  # noqa: E402

    assert hasattr(element_grid, "CANONICAL_CHART"), (
        "element_grid module must expose CANONICAL_CHART as a "
        "module-level constant (per §7.4 'the chart is data, "
        "not code')"
    )
    chart = element_grid.CANONICAL_CHART
    # The chart must be a dict keyed by attacker element id.
    assert isinstance(chart, dict), (
        f"CANONICAL_CHART must be a dict, got {type(chart).__name__}"
    )
    # All 7 elements must be present as attackers (per DEC-006).
    for element in _ALL_ELEMENTS:
        assert element in chart, (
            f"CANONICAL_CHART must contain attacker row for "
            f"'{element}' (per DEC-006: 7 elements total)"
        )


def test_canonical_chart_every_row_has_seven_entries():
    """Per §7.4 + DEC-006, every element row in the canonical
    7x7 chart has exactly 7 entries: self (1.0), the 5 other
    color elements, and the neutral element. This is the
    "every element has exactly 7 entries" test surface item
    (updated from 6 to 7 per DEC-006's resolution).

    Pinned at the canonical chart level: every row, including
    the neutral row, must have exactly 7 cells. A chart with
    6 or 8 cells per row is malformed.
    """
    import element_grid  # type: ignore  # noqa: E402

    chart = element_grid.CANONICAL_CHART
    for attacker in _ALL_ELEMENTS:
        row = chart[attacker]
        assert len(row) == 7, (
            f"CANONICAL_CHART['{attacker}'] must have exactly 7 "
            f"entries (self + 5 other colors + neutral), got "
            f"{len(row)}"
        )
        # The 7 keys must be exactly the 7 element ids.
        for defender in _ALL_ELEMENTS:
            assert defender in row, (
                f"CANONICAL_CHART['{attacker}'] must contain "
                f"entry for defender '{defender}' (per DEC-006: "
                f"7 elements total)"
            )


def test_canonical_chart_every_color_element_has_two_strong_and_two_weak():
    """Per §7.4, the canonical chart is a hexagonal graph:
    each of the 6 color elements is strong against exactly 2
    other elements and weak against exactly 2. This is the
    "each element is strong against two others and weak
    against two others" §7.4 contract, applied to every
    color element (not just the canonical pair pinned in
    cycle 11).

    The neutral element is excluded from this check because
    the §7.4 spec only requires the hexagonal graph for the
    6 color elements; neutral is the special-case 1.0 row
    (per DEC-006).
    """
    import element_grid  # type: ignore  # noqa: E402

    chart = element_grid.CANONICAL_CHART
    for element in _COLOR_ELEMENTS:
        row = chart[element]
        # Exclude self from the count; self is always 1.0.
        off_diag = {
            defender: value
            for defender, value in row.items()
            if defender != element
        }
        strong_count = sum(
            1 for value in off_diag.values() if value == 2.0
        )
        weak_count = sum(
            1 for value in off_diag.values() if value == 0.5
        )
        assert strong_count == 2, (
            f"CANONICAL_CHART['{element}'] must have exactly 2 "
            f"strong (2.0) entries per §7.4 hexagonal graph, "
            f"got {strong_count}"
        )
        assert weak_count == 2, (
            f"CANONICAL_CHART['{element}'] must have exactly 2 "
            f"weak (0.5) entries per §7.4 hexagonal graph, "
            f"got {weak_count}"
        )


def test_canonical_chart_strong_pairs_have_matching_weak_mirror():
    """Per DEC-001 "mirrored pairs" rule: the strong/weak
    relationship is a *pair*, not a directed edge. If A→B =
    2.0 (A strong vs B), then B→A = 0.5 (B weak vs A), and
    vice versa. This is the §7.4 "symmetric in the right way"
    contract applied to every strong/weak pair in the full
    7x7 chart, not just the (white, red) pair pinned in
    cycle 11.

    Pinned at the canonical chart level: every 2.0 cell has
    a 0.5 mirror at the transposed position, and every 0.5
    cell has a 2.0 mirror.
    """
    import element_grid  # type: ignore  # noqa: E402

    chart = element_grid.CANONICAL_CHART
    for attacker in _ALL_ELEMENTS:
        for defender, value in chart[attacker].items():
            if attacker == defender:
                continue  # self is always 1.0, no mirror check
            if value == 2.0:
                mirror = chart[defender][attacker]
                assert mirror == 0.5, (
                    f"CANONICAL_CHART mirror rule violated: "
                    f"'{attacker}'→'{defender}' = 2.0 (strong) "
                    f"but '{defender}'→'{attacker}' = {mirror} "
                    f"(must be 0.5, per DEC-001 mirrored pairs)"
                )
            elif value == 0.5:
                mirror = chart[defender][attacker]
                assert mirror == 2.0, (
                    f"CANONICAL_CHART mirror rule violated: "
                    f"'{attacker}'→'{defender}' = 0.5 (weak) "
                    f"but '{defender}'→'{attacker}' = {mirror} "
                    f"(must be 2.0, per DEC-001 mirrored pairs)"
                )


def test_canonical_chart_neutral_row_is_all_one():
    """Per DEC-006, the neutral element has no special
    interaction with any of the 6 color elements: the entire
    neutral row is 1.0 (including the neutral self entry).
    Neutral is the 7th element for physical / non-elemental
    abilities and Chrono Cross specials (Time Egg, etc.).

    Pinned here so the engine's "no magic" principle is
    applied to the neutral element specifically: a tech
    with element='neutral' (e.g., a basic attack) does 1.0
    damage to all targets regardless of defender element.
    """
    import element_grid  # type: ignore  # noqa: E402

    chart = element_grid.CANONICAL_CHART
    neutral_row = chart["neutral"]
    for defender, value in neutral_row.items():
        assert value == 1.0, (
            f"CANONICAL_CHART['neutral']['{defender}'] must be "
            f"1.0 (no element interaction per DEC-006), got "
            f"{value}"
        )


def test_canonical_chart_compute_resistance_returns_strong_pair_value():
    """End-to-end check: build an ElementGrid from the
    canonical chart, call compute_resistance for the
    canonical strong/weak pair (white vs red, per the
    white.json hint pinned by the data-cron), and assert
    the right multiplier.

    This pins the §7.4 "compute_resistance" contract
    against the canonical chart, not just an inline 2x2
    fixture. The full chart is the engine's reference; the
    canonical strong/weak pair (W→R = 0.5) is the most
    important test case because it is the only pair the
    data-cron has already pinned on disk (in white.json).
    """
    import element_grid  # type: ignore  # noqa: E402

    grid = element_grid.ElementGrid(element_grid.CANONICAL_CHART)
    # Per the white.json hint + the canonical 2+2 chart:
    # white is weak vs red (W→R = 0.5), white is strong vs
    # black (W→Bk = 2.0). These are the two cells the
    # data-cron has already committed to in white.json.
    assert grid.compute_resistance("white", "red") == 0.5, (
        "compute_resistance(white, red) must return 0.5 "
        "(white weak vs red) per the canonical chart and "
        "the data-cron's white.json hint"
    )
    assert grid.compute_resistance("white", "black") == 2.0, (
        "compute_resistance(white, black) must return 2.0 "
        "(white strong vs black) per the canonical chart "
        "and the data-cron's white.json hint"
    )
    # Mirror check: red's perspective on white.
    assert grid.compute_resistance("red", "white") == 2.0, (
        "compute_resistance(red, white) must return 2.0 "
        "(red strong vs white) per the mirrored-pairs "
        "rule (DEC-001)"
    )
    # Neutral element always returns 1.0 (per DEC-006).
    assert grid.compute_resistance("neutral", "white") == 1.0
    assert grid.compute_resistance("white", "neutral") == 1.0


def test_canonical_chart_is_multiplicatively_inverse_across_diagonal():
    """Per §7.4 + DEC-001, the canonical resistance chart is
    *multiplicatively inverse* across the diagonal: for every
    non-self (A, B) pair, `chart[A][B] * chart[B][A] == 1.0`.
    This is a stronger form of the mirrored-pairs rule
    (DEC-001): if A is strong vs B (2.0), then B is weak vs A
    (0.5), so the product is 2.0 * 0.5 = 1.0. And if A is
    neutral vs B (1.0), then B is neutral vs A (1.0), so the
    product is 1.0 * 1.0 = 1.0.

    The "no magic" principle: any pair that violates this
    property is a chart bug (asymmetric or non-inverse). The
    test walks the full 7x7 chart and asserts the property
    for every non-self cell. Pinned at the Python mirror
    level so a future change that accidentally introduces
    an asymmetric entry (e.g., a typo in the cycle offsets)
    is caught immediately.

    Pairs with test_canonical_chart_strong_pairs_have_matching_weak_mirror
    (which checks the specific 0.5↔2.0 mirror): this test
    checks the general multiplicative inverse property for
    *all* non-self cells, including the 1.0↔1.0 neutral
    cases that the mirrored-pairs test skips.
    """
    import element_grid  # type: ignore  # noqa: E402

    chart = element_grid.CANONICAL_CHART
    elements = list(chart.keys())
    for attacker in elements:
        for defender in elements:
            if attacker == defender:
                continue  # self is always 1.0; 1.0 * 1.0 == 1.0 by definition
            forward = chart[attacker][defender]
            reverse = chart[defender][attacker]
            product = forward * reverse
            assert abs(product - 1.0) < 1e-9, (
                f"CANONICAL_CHART multiplicatively-inverse "
                f"property violated: '{attacker}'→'{defender}' "
                f"= {forward}, '{defender}'→'{attacker}' = "
                f"{reverse}, product = {product} (must be 1.0 "
                f"per §7.4 + DEC-001 mirror rule)"
            )
