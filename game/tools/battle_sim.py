"""BattleSimulator — minimal combat orchestrator (§7.10 step 4, §7.2 determinism, §7.5 status engine).

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
resolver for `simulate(action)`, plus a status-application
method that respects the §7.5 resistance and immunity model.

The contract pinned by `tests/test_battle_sim.py` (cycles 44 + 45):

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
  5. `apply_status(target, status_id, chance, attempts)` returns
     a `StatusApplicationResult` describing the outcome of the
     status application. This is the §7.10 step 4 status
     application step in its simplest form (no §7.5
     `StatusEffectComponent` mirroring yet — just the
     resistance/immunity contract).
  6. A target with `status_id` in `target.status_immunities`
     yields 0 stacks regardless of chance or attempts
     (immunity is a hard veto per §7.5).
  7. A target with `status_id` in `target.status_resistances`
     has its effective chance scaled by the multiplier (per
     DEC-001, the canonical "strong defense" is 0.5).
  8. Every chance roll uses the scoped "combat" PRNG from the
     `Determinism` instance, so the result is deterministic for
     a given seed (§7.2 determinism contract).

Future cycles will add:
  - Multi-combatant turn orchestration (ActionQueue → resolve
    per combatant).
  - Element resistance application via the §7.4 ElementGrid.
  - Row modifiers via the §7.7 Party formation.
  - `StatusEffectComponent` mirroring for the full §7.5
    stacking + duration + tick-phase model.
  - Battle log emission for the §7.11 SaveSystem round-trip.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class StatusApplicationResult:
    """The result of one §7.10 step 4 status application.

    `applied` is the number of stacks successfully applied
    across all `attempts` rolls. `immunity_blocked` is True if
    the target had the status in `status_immunities` (in which
    case `applied` is always 0 and no PRNG calls were made).
    `attempts` echoes the input so the caller can compute
    hit rates from a single result object.
    """

    applied: int
    attempts: int
    immunity_blocked: bool = False


class BattleSimulator:
    """The §7.10 simulation-side orchestrator.

    Construction takes a `Determinism` instance (§7.2) and a
    `TechResolver` (§7.10 step 3) so the orchestrator has no
    global state and no implicit PRNG. The Determinism is the
    source of all chance rolls (the resolver and the
    `apply_status` method both consume it through the scoped
    "combat" PRNG). The resolver is the source of truth for
    what a `simulate(action)` call does.

    The simulator is intentionally a thin function in this
    cycle for `simulate(action)` — it does not introduce new
    effects, statuses, or augmentations. The `apply_status`
    method is the §7.10 step 4 entry point for status
    application; it is a thin function in this cycle too, just
    enough to pin the §7.5 resistance/immunity contract.
    """

    def __init__(self, determinism, resolver) -> None:
        # Stash the determinism instance and the resolver. The
        # simulator consumes entropy through `self._determinism
        # .scoped("combat")` in `apply_status` (the only entry
        # point that rolls in this cycle). Storing the
        # determinism here is the architectural seam for future
        # cycles (multi-combatant turn orchestration, battle
        # log emission) that will need scoped PRNG access
        # without a refactor.
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

    def apply_status(
        self,
        target: Any,
        status_id: str,
        chance: float = 1.0,
        attempts: int = 1,
    ) -> StatusApplicationResult:
        """Apply a status effect to a target, respecting §7.5
        resistance and immunity.

        Per §7.10 step 4 + §7.5, status application is a
        per-attempt chance roll. The target's
        `status_immunities` short-circuits to 0 stacks (no
        PRNG call). The target's `status_resistances` scales
        the effective chance by the entry's multiplier
        (per DEC-001 the canonical "strong defense" is 0.5).
        All rolls consume the scoped "combat" PRNG from the
        `Determinism` instance so the result is deterministic
        for a given seed (§7.2).

        Parameters
        ----------
        target : Any
            The target combatant. Must expose
            `status_immunities` (a dict or set) and
            `status_resistances` (a dict mapping status_id to
            a chance multiplier in [0, 1]).
        status_id : str
            The id of the status being applied (e.g. "burn",
            "sleep", "poison"). Must be one of the DEC-002
            canonical 8 ids, but this method does not enforce
            the enum — the schema validator (elsewhere) does.
        chance : float
            The base application chance per attempt, in
            [0, 1]. A chance of 1.0 always succeeds (modulo
            resistance scaling); 0.0 always fails.
        attempts : int
            The number of independent chance rolls to make.
            A value of 0 returns 0 applied stacks without any
            PRNG call.

        Returns
        -------
        StatusApplicationResult
            The number of stacks applied (sum of successes
            across attempts), the attempts echoed back, and
            a boolean `immunity_blocked` flag.
        """
        # §7.5 immunity is a hard veto: no PRNG call, no
        # chance roll, no chance of side effects. The
        # `status_immunities` collection may be a dict or set;
        # both support the `in` operator, so the check is the
        # same.
        if status_id in target.status_immunities:
            return StatusApplicationResult(
                applied=0, attempts=attempts, immunity_blocked=True,
            )

        # No attempts means no rolls and no applied stacks.
        # Early-return before acquiring the PRNG so the
        # determinism state stays clean for the next call.
        if attempts <= 0:
            return StatusApplicationResult(
                applied=0, attempts=attempts, immunity_blocked=False,
            )

        # §7.5 + DEC-001: scale the effective chance by the
        # target's resistance multiplier. Missing entries
        # (no resistance) leave the chance unchanged.
        multiplier = target.status_resistances.get(status_id, 1.0)
        effective_chance = max(0.0, min(1.0, chance * multiplier))

        # Per-attempt chance roll. The §7.2 determinism
        # contract: every PRNG in the project must come from
        # the `Determinism` instance; direct `random` module
        # calls are forbidden. The "combat" tag scopes the
        # roll to the combat subsystem (so a save game's
        # combat log can be replayed independently of the
        # dialog and treasure subsystems' PRNGs).
        combat_rng = self._determinism.scoped("combat")
        applied = 0
        for _ in range(attempts):
            # random() returns a float in [0.0, 1.0). A value
            # strictly less than `effective_chance` is a
            # success. This matches the convention used by
            # the §7.2 determinism layer's other consumers
            # (e.g. the future augmentation-chain roll).
            if combat_rng.random() < effective_chance:
                applied += 1

        return StatusApplicationResult(
            applied=applied, attempts=attempts, immunity_blocked=False,
        )
