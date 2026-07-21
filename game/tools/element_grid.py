"""ElementGrid — the §7.4 element grid and resistance model.

Per §7.4 of the design document, the combat engine has a single
`ElementGrid` autoload that owns the resistance chart and provides
the `compute_resistance(attacker, defender) -> float` function
used by the damage step in §7.10. The chart is data, not code,
so a mod can rebalance elements without touching the engine.

The GDScript `ElementGrid.gd` autoload is the engine-side
implementation (a future `scaffolding_cron` item); this Python
module exists so the agent's test rig — which runs Python, not
the Godot runtime — can exercise the same resistance contract
end-to-end. Both implementations must satisfy:

  1. The same `compute_resistance(attacker, defender)` interface.
  2. The same canonical multiplier semantics per DEC-001
     (1.0 = neutral, 0.5 = strong defense, 2.0 = strong offense).
  3. The same "unknown element returns 1.0" safety behavior per
     §7.4 "no magic" principle.

The contract pinned by `tests/test_element_grid.py`:

  1. `ElementGrid(chart)` constructs with a resistance chart
     keyed by attacker element id (lowercase) to a dict of
     defender element id -> float multiplier. The chart is
     stashed on the instance as `self.chart` for introspection
     (debug, mod tooling, future S-4 AI-agent integration
     per §4.4).

  2. `compute_resistance(attacker, defender)` returns the float
     multiplier for the (attacker, defender) pair, or 1.0 if
     either side is unknown (per §7.4 "no magic" principle:
     an unknown element is neutral, not an error).

  3. The class is a thin data wrapper. No I/O, no PRNG, no
     implicit state. The chart is the source of truth; the
     function is a pure lookup.

The full 7x7 canonical chart is exposed as the module constant
`CANONICAL_CHART` (per §7.4 + DEC-001 + DEC-006). The GDScript
`ElementGrid.gd` autoload (a future scaffolding-cron item) will
load the same chart from `data/elements/resistances.json`; the
Python constant is the Python mirror's source of truth. A future
data-cron cycle will author `data/elements/resistances.json` to
match this constant (the §8.4 translator's output).

Future cycles will add:
  - On-disk chart loading from `data/elements/resistances.json`.
  - The level-based scaling formula (the "level-vs-element
    scaling" is a §13 design decision logged for review).
  - Schema validation integration with `validate_data.py`.
  - The GDScript `ElementGrid.gd` autoload mirror (a
    `scaffolding_cron` item).
"""
from __future__ import annotations

from typing import Dict, Hashable


# ---------------------------------------------------------------------------
# §7.4 + DEC-001 + DEC-006: the canonical 7x7 element resistance chart.
#
# Per §7.4, the original Chrono Cross element grid is a hexagonal graph:
# each of the 6 color elements is strong against exactly 2 others and weak
# against exactly 2 others. Per DEC-006, the 7th element is 'neutral' (no
# special interaction with any of the 6 color elements; the entire row is
# 1.0, including the neutral self entry).
#
# The 6 color elements form a single strong/weak cycle in the original
# Chrono Cross chart:
#
#   white -> black -> yellow -> green -> blue -> red -> white
#
# In this cycle, each element is STRONG against the 2 elements clockwise
# (next + next-next) and WEAK against the 2 elements counter-clockwise
# (prev + prev-prev). This gives each color element exactly 2 strong
# (2.0) and 2 weak (0.5) off-diagonal entries per the §7.4 "hexagonal
# graph" constraint. The 'neutral' element is the 7th element with all
# 1.0 entries.
#
# The chart is symmetric: if A is strong against B (2.0), then B is weak
# against A (0.5). This is the DEC-001 "mirrored pairs" rule: the
# strong/weak relationship is a *pair*, not a directed edge.
#
# The canonical 7x7 chart is the engine's reference. A mod that wants to
# rebalance elements edits one data file (per §7.4 "the chart is data,
# not code"); the engine does not change.
# ---------------------------------------------------------------------------

# The 6 color elements in strong-cycle order (per the original Chrono
# Cross chart). Reading this list left-to-right, each element is STRONG
# against the 2 elements clockwise (the next + next-next element) and
# WEAK against the 2 elements counter-clockwise (the prev + prev-prev
# element). The 'neutral' element is the 7th element (per DEC-006).
_STRONG_CYCLE = ("white", "black", "yellow", "green", "blue", "red")
_ALL_ELEMENTS = _STRONG_CYCLE + ("neutral",)


def _build_canonical_chart() -> Dict[str, Dict[str, float]]:
    """Build the canonical 7x7 resistance chart per §7.4 + DEC-001 + DEC-006.

    The 6 color elements form a strong/weak cycle: each is strong against
    the 2 elements clockwise in `_STRONG_CYCLE` (2.0) and weak against
    the 2 elements counter-clockwise (0.5). The 'neutral' element is the
    special-case 1.0 row (per DEC-006): it has no element interaction
    with any of the 6 color elements.

    The chart is symmetric: if A->B = 2.0 then B->A = 0.5 (and vice
    versa). This is the DEC-001 "mirrored pairs" rule.
    """
    chart: Dict[str, Dict[str, float]] = {}
    for attacker in _ALL_ELEMENTS:
        chart[attacker] = {defender: 1.0 for defender in _ALL_ELEMENTS}
    cycle_len = len(_STRONG_CYCLE)
    for i, attacker in enumerate(_STRONG_CYCLE):
        # Each color element is strong against the 2 elements clockwise
        # (offset +1, +2) and weak against the 2 elements counter-
        # clockwise (offset -1, -2). This gives each color element
        # exactly 2 strong (2.0) and 2 weak (0.5) off-diagonal entries,
        # satisfying the §7.4 "hexagonal graph" constraint.
        for offset in (1, 2):
            strong_target = _STRONG_CYCLE[(i + offset) % cycle_len]
            weak_target = _STRONG_CYCLE[(i - offset) % cycle_len]
            chart[attacker][strong_target] = 2.0
            chart[attacker][weak_target] = 0.5
    return chart


CANONICAL_CHART: Dict[str, Dict[str, float]] = _build_canonical_chart()


class ElementGrid:
    """The §7.4 resistance chart and compute_resistance function.

    Construction takes a resistance chart dict; the chart is
    stashed on the instance for introspection. The
    `compute_resistance` method is a pure lookup with safe
    defaults for unknown elements.

    The class is intentionally a thin data wrapper — no I/O,
    no PRNG, no implicit state. The chart is the source of
    truth and the function is a pure lookup. This is the §7.4
    "the chart is data, not code" principle applied at the
    Python mirror level.
    """

    def __init__(self, chart: Dict[Hashable, Dict[Hashable, float]]) -> None:
        # Stash the chart on the instance for introspection.
        # Per §7.4 "the chart is data, not code", the chart
        # is the source of truth and must be inspectable
        # from the outside (debug, mod tooling, future S-4
        # AI-agent integration per §4.4).
        self.chart: Dict[Hashable, Dict[Hashable, float]] = chart

    def compute_resistance(
        self, attacker: Hashable, defender: Hashable
    ) -> float:
        """Return the damage multiplier for the (attacker, defender) pair.

        Per §7.4 + DEC-001, the canonical semantics are:
          - 1.0 = neutral (default)
          - 0.5 = strong defense (attacker weak vs defender)
          - 2.0 = strong offense (attacker strong vs defender)

        An unknown attacker or defender element returns 1.0
        (the safe default) per the §7.4 "no magic" principle:
        a mod that adds a new element without updating the
        chart does not crash combat. The safe default is
        intentional, not a fallback to error.
        """
        if attacker not in self.chart:
            return 1.0
        if defender not in self.chart[attacker]:
            return 1.0
        return self.chart[attacker][defender]
