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

This is the §7.4 compute_resistance contract in its minimal
form. Future cycles will add:
  - On-disk chart loading from `data/elements/resistances.json`
    (the §8.4 translator's output).
  - The level-based scaling formula (the "level-vs-element
    scaling" is a §13 design decision logged for review).
  - Schema validation integration with `validate_data.py`.
  - The GDScript `ElementGrid.gd` autoload mirror (a
    `scaffolding_cron` item).
"""
from __future__ import annotations

from typing import Dict, Hashable


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
