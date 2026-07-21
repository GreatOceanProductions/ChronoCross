"""BattleSimulator — minimal combat orchestrator (§7.10 step 4, §7.2 determinism).

Per §7.10 of the design document, the combat engine is split into
`Battle` (orchestrator), `CombatSimulator` (simulation), and
`BattleView` (presentation). This module is the simulation-side
orchestrator: it takes a `Determinism` instance and a
`TechResolver`, and exposes a `simulate(action)` method that
returns the resolved `ActionResult` for one combat action.

The GDScript `BattleSimulator.gd` will be the engine-side
implementation; this Python mirror exists so the agent's test
rig — which runs Python, not the Godot runtime — can exercise
the orchestration contract end-to-end. Both implementations
must satisfy the same contract, but the GDScript version will
own its own state machine, signal emission, and target
selection. The Python version is a thin pass-through to the
resolver.

The contract pinned by `tests/test_battle_sim.py` (this cycle):

  1. `BattleSimulator(determinism, resolver)` constructs with a
     `Determinism` instance and a `TechResolver` so the
     orchestrator has no global state and no implicit PRNG.
  2. `simulate(tech, attacker_attack=...)` calls
     `resolver.resolve(tech, attacker_attack)` and returns
     the `ActionResult` unchanged. The orchestrator does not
     mutate effects, statuses, or augmentations — those are
     the resolver's responsibility.
  3. Calling `simulate` 100 times with the same inputs produces
     byte-identical `ActionResult` objects. This is the §7.2
     determinism contract applied to the orchestration layer.
  4. The orchestrator preserves the resolver's contract:
     `target_scope`, `effects`, and `applied_augmentations`
     pass through unchanged.

Future cycles will add:
  - Multi-combatant turn orchestration (ActionQueue → resolve
    per combatant).
  - Element resistance application via the §7.4 ElementGrid.
  - Row modifiers via the §7.7 Party formation.
  - Status effect application via the §7.5 StatusEffectComponent.
  - Battle log emission for the §7.11 SaveSystem round-trip.
"""
from __future__ import annotations

from typing import Any


class BattleSimulator:
    """The §7.10 simulation-side orchestrator.

    Construction takes a `Determinism` instance (§7.2) and a
    `TechResolver` (§7.10 step 3) so the orchestrator has no
    global state and no implicit PRNG. The Determinism is the
    source of all chance rolls (the resolver and the future
    augmentation chain both consume it through the resolver).
    The resolver is the source of truth for what an action does.

    The simulator is intentionally a thin function in this
    cycle — it does not introduce new effects, statuses, or
    augmentations. As the action lifecycle grows past the
    single-action case (future cycles), the simulator grows
    a `run_turn(combatants, queue)` method or similar.
    """

    def __init__(self, determinism, resolver) -> None:
        # Stash the determinism instance and the resolver. The
        # simulator does not consume any entropy directly in
        # this cycle — the resolver is the only entropy
        # consumer. Storing the determinism here is the
        # architectural seam for future cycles (status-effect
        # application, multi-combatant turn orchestration,
        # battle log emission) that will need scoped PRNG
        # access without a refactor.
        self._determinism = determinism
        self._resolver = resolver

    def simulate(
        self, tech, attacker_attack: float = 0.0
    ) -> Any:
        """Resolve a single combat action and return the result.

        For this cycle, the simulator is a pure pass-through
        to the resolver: it calls
        `resolver.resolve(tech, attacker_attack)` and returns
        the `ActionResult` unchanged. The orchestrator does
        not mutate effects, statuses, or augmentations.

        Parameters
        ----------
        tech : TechData
            The tech being executed. The resolver reads
            `effects`, `augmentations`, `target_scope`, and
            `base_damage_multiplier` from the tech.
        attacker_attack : float
            The attacker's current attack stat. Passed
            through to the resolver.

        Returns
        -------
        ActionResult
            The resolved effects, target scope, and applied
            augmentations. Identical to what the resolver
            would have returned if called directly.
        """
        return self._resolver.resolve(tech, attacker_attack=attacker_attack)
