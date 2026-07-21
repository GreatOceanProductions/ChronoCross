"""ActionQueue — speed-based action ordering for combat (§7.10, §6.7).

Per §7.10 of the design document, the combat engine has a per-round
action queue: "the simulator sorts by speed (with the original's
speed-based algorithm) and emits the queue at the start of each
round. The view animates the queue in order."

The §6.7 5-step action lifecycle runs once per actor in the queue.
AI-controlled combatants (enemies, party members in "auto" mode)
pick actions from an `AIStrategy` resource at their turn; the
player-controlled combatants prompt for an action via `BattleView`.

The GDScript `ActionQueue.gd` is the engine-side implementation (a
future `scaffolding_cron` item). This Python mirror exists so the
agent's test rig — which runs Python, not the Godot runtime —
can exercise the speed-sort contract end-to-end. Both
implementations must satisfy the same contract.

The contract pinned by `tests/test_action_queue.py`:

  1. `ActionQueue(roster)` constructs from a list of combatants.
     Each combatant is a duck-typed object with `id` (str) and
     `speed` (number) fields. Dicts and Godot-resource-style
     objects both work — the contract is on the *attribute names*,
     not the type.

  2. `ordered_ids()` returns the list of combatant ids sorted by
     `speed` descending (higher speed acts first — the §7.10
     "speed-based algorithm" matches the original Chrono Cross's
     action order).

  3. Ties on `speed` are broken by *insertion order*: the earlier
     input in the roster list appears earlier in the ordered output.
     This is the §7.10 determinism contract: the same input always
     produces the same queue, regardless of platform or run.

  4. The sort is *stable*: reconstructing the queue (or re-running
     `rebuild()`) on the same input produces identical ordered_ids.
     Python's built-in `sorted()` is stable by default, which is
     why this implementation uses `sorted()` with a tuple key —
     the key controls the sort order, stability comes for free.

  5. An empty roster returns an empty ordered_ids list (not an
     error). A single-element roster returns a single-element list.

  6. The queue is decoupled from `PartyManager` (§7.7) and from
     `StatsComponent` (§6.7) — the bridge layer joins roster ids
     with speed data and feeds the queue. The queue is responsible
     only for ordering, not for stat lookup.
"""
from __future__ import annotations

from typing import Any, Iterable, List


class ActionQueue:
    """The §7.10 speed-sorted action queue.

    The queue is built from a roster of combatants at construction
    time and can be rebuilt with a new roster via `rebuild()`. The
    underlying sorted list is cached on the instance so repeated
    `ordered_ids()` calls are O(1) (returning the cached list).

    The duck-typed combatant contract: anything with `id` and
    `speed` attributes (or dict keys) is accepted. This is what
    lets the queue compose with §7.7 PartyManager results (a list
    of ids bridged with a speed table) and with raw enemy dicts
    (which already have id and speed) in the same `ActionQueue`
    call.
    """

    def __init__(self, roster: Iterable[Any]) -> None:
        # The input roster is the *raw* list (or iterable). We
        # capture it on the instance so `rebuild()` can be called
        # with no argument and re-sort the same data. The actual
        # sorted list is stored separately in `_ordered_ids` so
        # `rebuild()` doesn't mutate the caller's input.
        self._roster: List[Any] = list(roster)
        self._ordered_ids: List[str] = self._sort(self._roster)

    @staticmethod
    def _combatant_id(combatant: Any) -> str:
        """Extract the id from a duck-typed combatant.

        Accepts both dict-style (`combatant["id"]`) and attribute-
        style (`combatant.id`) combatants. The §7.7 PartyManager
        returns a list of strings (ids), so the bridge layer wraps
        each in a dict before passing to the queue; raw enemy
        dicts are accepted directly.
        """
        if isinstance(combatant, dict):
            return str(combatant["id"])
        return str(combatant.id)

    @staticmethod
    def _combatant_speed(combatant: Any) -> float:
        """Extract the speed from a duck-typed combatant.

        Same duck-typed contract as `_combatant_id`: dicts use
        `combatant["speed"]`, attribute-style uses `combatant.speed`.
        Returns a float so the sort key is consistent regardless
        of whether the input is int or float.
        """
        if isinstance(combatant, dict):
            return float(combatant["speed"])
        return float(combatant.speed)

    def _sort(self, roster: List[Any]) -> List[str]:
        """Sort the roster by speed descending, ties by insertion.

        Python's built-in `sorted()` is stable, so the secondary
        "ties by insertion order" rule is achieved by passing a
        tuple key `(-speed, insertion_index)`. Negative speed
        gives descending order; the insertion index keeps the
        stable order on ties.

        Without the explicit insertion index, two combatants
        with the same speed would be ordered by Python's stable
        sort by their *position in the input list* — but only
        because `sorted()` happens to iterate the input in order
        and never re-orders equal keys. The explicit `enumerate`
        makes the contract visible and self-documenting: the
        comment "ties by insertion order" matches the code that
        enforces it.
        """
        # Tag each combatant with its insertion index, then sort.
        indexed = list(enumerate(roster))
        # Key: (-speed, insertion_index). Stable sort + this key
        # gives "speed descending, ties by insertion order".
        indexed.sort(key=lambda pair: (-self._combatant_speed(pair[1]), pair[0]))
        return [self._combatant_id(c) for _, c in indexed]

    def ordered_ids(self) -> List[str]:
        """Return the sorted list of combatant ids.

        This is the §7.10 "queue" — the simulator iterates this
        list and asks the view to animate each actor's turn in
        order. Returns the cached sorted list (O(1)) so callers
        can call repeatedly without re-sorting.
        """
        return list(self._ordered_ids)

    def rebuild(self, roster: Iterable[Any] = None) -> None:
        """Re-sort the queue.

        If `roster` is provided, the new roster replaces the old
        one (useful for mid-battle recruit/release, e.g., the
        §7.6 form-change removes Serge and adds Lynx). If `roster`
        is omitted, the existing roster is re-sorted (useful for
        "speed changed mid-round" scenarios in a future cycle).
        """
        if roster is not None:
            self._roster = list(roster)
        self._ordered_ids = self._sort(self._roster)

    def __len__(self) -> int:
        return len(self._ordered_ids)

    def __repr__(self) -> str:
        return f"ActionQueue(ordered_ids={self._ordered_ids!r})"
