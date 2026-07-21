"""TechResolver — minimal combat engine entry point (§7.10, §3.5).

Per §7.10 of the design document, the combat engine is split into
`Battle` (orchestrator), `CombatSimulator` (simulation), and
`BattleView` (presentation). The `TechResolver` is the simulation-
side piece that turns a `TechData` plus a combat context into a
concrete `ActionResult` — the resolved list of effects with
magnitudes, status applications, and chance outcomes.

The GDScript `TechResolver.gd` is the engine-side implementation
(a future `scaffolding_cron` item). This Python mirror exists so
the agent's test rig — which runs Python, not the Godot runtime
— can exercise the resolve logic end-to-end. Both implementations
must satisfy the same contract.

The contract pinned by `tests/test_tech_resolver.py` (this cycle):

  1. `TechResolver(determinism)` constructs with a `Determinism`
     instance so the augmentation chain (future cycles) can use
     `d.scoped("combat")` without the resolver importing a
     different PRNG. Per §7.2, the determinism layer is the only
     source of entropy in the project.
  2. `resolve(tech, attacker_attack=...)` returns an `ActionResult`
     with the resolved effects list.
  3. For a basic attack with no augmentations, the resolved
     `effects` list has one entry per input effect with the
     `DAMAGE` kind's magnitude computed as
     `base_damage_multiplier * attacker_attack`. This is the §7.10
     "Base damage × multiplier" formula in its minimal form
     (no element resistance, no row modifier — those compose
     on top in later cycles).
  4. The result's `target_scope` is preserved so the view layer
     can pick the right animation target.
  5. The result is deterministic for a given (tech, attacker,
     determinism_seed) — same inputs produce same outputs.
  6. The result's `applied_augmentations` is empty for a basic
     attack (the resolver does not invent status effects when
     none are configured).
  7. The resolver is decoupled from §7.4 element resistance and
     §7.7 row modifiers in this cycle. Those layers compose on
     top of the resolver's output in future cycles.

This is the §7.10 step 3 entry point. Future cycles will add:
  - Augmentation chain walk (pre/post-damage statuses, multiplier
    bonuses, on-hit chains, MP discounts, self-buffs).
  - Element resistance application via the §7.4 ElementGrid.
  - Row modifiers via the §7.7 Party formation.
  - Status effect application via the §7.5 StatusEffectComponent.
  - Multi-target resolution (ROW, ALL_ENEMIES, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ResolvedEffect:
    """A single concrete effect after resolution.

    Mirrors the §7.3 TechEffect data shape but with a *computed*
    `magnitude` rather than the on-disk base value. The view/
    animation layer reads this list to know what to play.

    The dataclass is intentionally minimal: only the fields the
    PoC needs (kind, magnitude, element, status). Future cycles
    may add `target_id` (which specific combatant the effect hits
    in a multi-target resolve) and `source_id` (who cast the tech)
    when the action lifecycle grows past the basic-attack case.
    """

    kind: str
    magnitude: float
    element: str = ""
    status: str = ""


@dataclass
class ActionResult:
    """The result of resolving one tech against a target.

    Per §7.10, this is what `CombatSimulator.resolve(action)`
    returns. The view/animation layer reads `effects` to know
    what to display, the log layer reads `effects` to record
    the battle, and a future undo/replay layer reads
    `applied_augmentations` to reconstruct the resolve steps.

    `target_scope` is preserved from the input tech so the view
    can pick the right animation target (front row vs all
    enemies vs single ally). Multi-target resolution is a
    future cycle; this version assumes a single resolved effect
    list regardless of scope.
    """

    target_scope: str
    effects: List[ResolvedEffect] = field(default_factory=list)
    applied_augmentations: List[Dict[str, Any]] = field(default_factory=list)


class TechResolver:
    """The §7.10 simulation-side entry point.

    Construction takes a `Determinism` instance (§7.2) so the
    augmentation chain (future cycles) can use
    `d.scoped("combat")` for any chance rolls. The resolver
    itself does not call any PRNG in this cycle — the basic
    attack has no chance rolls. Storing the determinism here is
    the architectural seam: the future augmentation chain will
    have access to it without a refactor.

    The resolver is intentionally a thin function for the basic
    attack case. As the augmentation chain is added in future
    cycles, the resolver grows a `resolve_with_augmentations`
    method (or the same `resolve` method grows internal
    augmentation-walk logic). The dataclass-based return type
    is the contract surface that the view/animation layer
    consumes.
    """

    def __init__(self, determinism) -> None:
        # Stash the determinism instance for future use. The
        # basic attack path does not consume any entropy; this
        # is purely the architectural seam for the augmentation
        # chain (future cycles) and for the §7.10 step 7 battle
        # log entry (a future cycle). Keeping the parameter
        # required means a refactor is not needed when those
        # features land.
        self._determinism = determinism

    def resolve(
        self, tech, attacker_attack: float = 0.0
    ) -> ActionResult:
        """Resolve a single tech against a target.

        For the basic attack case (no augmentations), this walks
        the input `tech.effects` list and produces one
        `ResolvedEffect` per input effect. The DAMAGE kind's
        magnitude is computed as
        `base_damage_multiplier * attacker_attack`. Other kinds
        (HEAL, APPLY_STATUS, REMOVE_STATUS, MODIFY_FIELD) pass
        their on-disk magnitude through unchanged in this cycle
        — the augmentation chain (future) is what modifies them.

        Parameters
        ----------
        tech : TechData
            The tech being executed. The resolver reads `effects`,
            `augmentations`, `target_scope`, and
            `base_damage_multiplier` from the tech.
        attacker_attack : float
            The attacker's current attack stat. The §7.10
            "Base damage × multiplier" formula multiplies this by
            the tech's `base_damage_multiplier` to produce the
            resolved damage magnitude.

        Returns
        -------
        ActionResult
            The resolved effects, target scope, and applied
            augmentations. For a basic attack, the applied
            augmentations list is empty.
        """
        resolved: List[ResolvedEffect] = []
        for eff in tech.effects:
            kind = eff.get("kind", "")
            if kind == "DAMAGE":
                # §7.10 step 3: Base damage × multiplier. The
                # base_damage_multiplier is on the tech (the
                # §3.5 "basic attack line baseline"); the
                # attacker_attack is the runtime stat. Element
                # resistance (§7.4) and row modifier (§7.7)
                # compose on top in later cycles — this cycle
                # pins the formula in its minimal form.
                magnitude = float(
                    tech.base_damage_multiplier * attacker_attack
                )
                resolved.append(
                    ResolvedEffect(
                        kind="DAMAGE",
                        magnitude=magnitude,
                        element=eff.get("element", ""),
                    )
                )
            else:
                # HEAL, APPLY_STATUS, REMOVE_STATUS, MODIFY_FIELD
                # pass through unchanged in this cycle. Future
                # cycles add the augmentation chain and the
                # element/row/status modifiers.
                resolved.append(
                    ResolvedEffect(
                        kind=kind,
                        magnitude=float(eff.get("magnitude", 0.0)),
                        element=eff.get("element", ""),
                        status=eff.get("status", ""),
                    )
                )
        # Basic attack has no augmentations. The augmentation
        # chain walk is a future cycle; for now the result
        # carries an empty list so the view layer has a stable
        # shape to iterate.
        return ActionResult(
            target_scope=tech.target_scope,
            effects=resolved,
            applied_augmentations=list(tech.augmentations),
        )
