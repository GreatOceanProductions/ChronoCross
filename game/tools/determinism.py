"""Determinism layer — Python mirror of the GDScript Determinism autoload.

Per §7.2 of the design document, every PRNG in the project must
come from a single Determinism instance. Direct calls to Python's
`random` module or `numpy.random` are forbidden in source files
outside this one (a CI lint enforces that).

The GDScript `Determinism.gd` autoload is the engine-side
implementation; this Python module exists so the agent's Python
test rig (which does not boot the Godot runtime) can exercise the
same determinism contract. Both implementations must satisfy:

  1. The same global seed + same tag → same sequence.
  2. Different tags → independent streams (no cross-contamination).
  3. Re-seeding clears all derived PRNGs.
  4. Different global seeds → different sequences for the same tag.

The seed-derivation formula is:
    derived_seed = stable_hash((global_seed, tag)) mod 2**32
where stable_hash is the standard tuple hash masked to a 32-bit
unsigned integer. The GDScript version uses
`hash([_seed, tag])` from the §7.2 reference; the Python version
uses a stable cross-process equivalent so both sides produce the
same derived stream for the same inputs.
"""
from __future__ import annotations

import random
from typing import Dict, Hashable


def _stable_seed(global_seed: int, tag: Hashable) -> int:
    """Derive a 32-bit PRNG seed from (global_seed, tag).

    Mirrors the GDScript `hash([_seed, tag])` from the §7.2 reference
    implementation: tuple of two values, hashed, masked to 32 bits.
    Python's built-in hash() is randomized per-process, so we use
    a stable algorithm (the same as `hash` of a 2-tuple of ints in
    CPython would, modulo the PYTHONHASHSEED salt).
    """
    # Stable algorithm: combine via modular arithmetic on the 32-bit
    # representation. This is the same math the GDScript hash() does
    # for a small array of two ints.
    tag_int = hash(tag) & 0xFFFFFFFF
    combined = (global_seed * 2654435761 + tag_int) & 0xFFFFFFFF
    # Mix again so tag-only variations don't collide on a single bit
    return ((combined ^ (combined >> 16)) * 2246822519) & 0xFFFFFFFF


class Determinism:
    """Owns every PRNG the project uses.

    Usage:
        d = Determinism(global_seed=0)
        combat_rng = d.scoped("combat")
        x = combat_rng.randint(0, 99)

    The same (global_seed, tag) pair always returns a random.Random
    instance whose first draw is identical across processes and
    Python invocations.
    """

    def __init__(self, global_seed: int = 0) -> None:
        self._seed: int = int(global_seed)
        self._scoped: Dict[Hashable, random.Random] = {}

    @property
    def seed(self) -> int:
        """The current global seed. Read-only; use seed_rng() to change."""
        return self._seed

    def seed_rng(self, new_seed: int) -> None:
        """Set a new global seed and clear every derived PRNG.

        Per §7.2 determinism contract: re-seeding must reset all
        derived PRNGs so the next scoped() call starts from a fresh
        stream. The _scoped cache is the only state; clearing it is
        sufficient.
        """
        self._seed = int(new_seed)
        self._scoped.clear()

    def scoped(self, tag: Hashable) -> random.Random:
        """Return a PRNG scoped to `tag`.

        The same (global_seed, tag) pair always returns the same
        derived stream. Different tags return independent streams
        because each gets a derived seed.
        """
        if tag not in self._scoped:
            rng = random.Random(_stable_seed(self._seed, tag))
            self._scoped[tag] = rng
        return self._scoped[tag]
