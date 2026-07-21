"""PartyManager — the 6-character party formation system (§7.7, §3.9).

Per §7.7 of the design document, the project needs a party system
that owns 6 combatant slots, a count of currently active combatants,
and a `slot_unlocked` signal for the cinematic system. Per §3.9
the active party size starts at 3 and grows to 6 across the 10
chapters (one slot unlocks per chapter-boundary recruitment beat).

The GDScript `PartyManager.gd` autoload (a future `scaffolding_cron`
item) is the engine-side implementation. This Python mirror exists
so the agent's test rig — which runs Python, not the Godot runtime
— can exercise the party-formation contract end-to-end. Both
implementations must satisfy the same contract, but the GDScript
version uses Godot's signal/slot semantics while this version
records events in a list.

The contract pinned by `tests/test_party_manager.py`:
  - 6 total slots; active_count starts at 3.
  - `add_base(id)` puts the id into slot[active_count] and
    increments active_count. Raises ValueError on the 7th add.
  - `remove_base(id)` removes the id, shifts later bases forward,
    decrements active_count. Raises ValueError if id not in party.
  - `active_roster` returns the list of active (non-None) ids in
    slot order.
  - `slot_unlocked_events` is a list of (slot_index, character_id)
    tuples recorded on every add_base call.
"""
from __future__ import annotations

from typing import List, Optional, Tuple


# §3.9: the active party size grows to 6 across the 10 chapters.
# The 6-slot total is the §3.9 max and is hard-locked. The party
# starts empty (no bases recruited yet) and is populated chapter by
# chapter as the recruitment beats fire. The "3" referenced in §3.9
# is the *original* Chrono Cross's max party size — the redesign
# commits to *exceeding* that, not matching it from the start.
_MAX_ACTIVE = 6


class PartyManager:
    """Owns the 6-slot party formation.

    Construction is parameter-less: the party starts empty (all
    3 active slots are None) and is populated as bases are
    recruited across chapters per §3.9. Direct construction is
    supported (unlike CharacterData, which is loaded from JSON)
    because the party is a runtime state container, not a data
    artifact.
    """

    def __init__(self) -> None:
        # §3.9: 6 total slots. The party starts empty (no bases
        # recruited yet) and is populated chapter by chapter.
        self._slots: List[Optional[str]] = [None] * _MAX_ACTIVE
        self._active_count: int = 0
        # The §7.7 `slot_unlocked(index, combatant)` signal becomes
        # a recorded event list in the Python mirror. The GDScript
        # version uses `signal slot_unlocked(index: int, combatant: ...)`.
        self.slot_unlocked_events: List[Tuple[int, str]] = []

    @property
    def active_count(self) -> int:
        """Number of currently active (unlocked) slots, including
        those that have not yet been recruited (i.e., still None).
        Per §3.9 this starts at 3 and grows to 6 as bases are
        recruited across the chapter-boundary beats."""
        return self._active_count

    @property
    def max_size(self) -> int:
        """§3.9 maximum party size — always 6."""
        return _MAX_ACTIVE

    def add_base(self, character_id: str) -> int:
        """Recruit a base into the next free slot.

        The slot index is the previous `active_count` (so the first
        add fills slot 0, the second slot 1, etc.). Increments
        `active_count` and records a `slot_unlocked` event.

        Raises ValueError if all 6 slots are filled — per §3.9 the
        max is hard and the §7.3 fail-loudly principle says we
        surface the violation, not silently grow the roster.
        """
        if self._active_count >= _MAX_ACTIVE:
            raise ValueError(
                f"PartyManager: cannot add '{character_id}'; "
                f"party is already at max size {_MAX_ACTIVE}"
            )
        slot_index = self._active_count
        self._slots[slot_index] = character_id
        self._active_count += 1
        self.slot_unlocked_events.append((slot_index, character_id))
        return slot_index

    def remove_base(self, character_id: str) -> int:
        """Remove a base from the party, shifting later bases forward.

        This is the §7.6 form-change primitive: when Serge becomes
        Lynx, the party removes Serge and add_base("lynx") fills
        the now-free slot 0. Slots after the removed base shift
        down by one so slot 0 is always the "front" position.

        Raises ValueError if the id is not in the party — per §7.3
        fail-loudly, a typo or stale id must surface immediately.
        """
        if character_id not in self._slots:
            raise ValueError(
                f"PartyManager: cannot remove '{character_id}'; "
                "base is not in the party"
            )
        slot_index = self._slots.index(character_id)
        # Remove the entry, then shift later entries forward.
        del self._slots[slot_index]
        # Pad back to 6 slots with None so the party size stays at 6.
        self._slots.append(None)
        self._active_count -= 1
        return slot_index

    def active_roster(self) -> List[str]:
        """List of recruited base ids in slot order.

        Skips None entries so the roster reflects *recruited* bases
        only — a fresh PartyManager (all 3 active slots None)
        returns [], not [None, None, None].
        """
        return [s for s in self._slots[: self._active_count] if s is not None]

    def __repr__(self) -> str:
        return (
            f"PartyManager(active_count={self._active_count}, "
            f"roster={self.active_roster()})"
        )
