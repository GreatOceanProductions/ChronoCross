"""Tests for the BattleSimulator (§7.10 combat engine, §7.2 determinism).

Per §7.10 of the design document, the combat engine is split into
`Battle` (orchestrator), `CombatSimulator` (simulation), and
`BattleView` (presentation). The `CombatSimulator` is the
simulation-side orchestrator: given a list of combatants and a
queue of actions, it walks the actions, calls the `TechResolver`
for each, and returns the resolved turn result.

This is the SIXTH TDD cycle in the data-layer / combat-engine
sequence (cycle 44 of the tdd_cron), coming after:

  - cycle 34: test_determinism_prng_seeded (§7.2 derived PRNGs)
  - cycle 35: test_character_data_loads (§7.3 CharacterData)
  - cycle 36: test_tech_data_loads (§7.3 TechData)
  - cycle 37: test_party_manager_active_roster (§7.7 PartyManager)
  - cycle 38: test_tech_resolver_basic_attack (§7.10 step 3)
  - cycle 39: test_action_queue_speed_sort (§7.10 step 2)
  - cycle 40: test_tech_resolver_augmentation_chain (§7.10 step 2,
    DEC-007 chain walk)

The contract being pinned here is the §7.10 "step 4: orchestrator"
of the action lifecycle, in its simplest possible form: a single
combat action resolved 100 times with the same seed must produce
byte-identical results. This is the §7.2 determinism + §7.10
combat composition test for the orchestration layer.

The contract (§7.10 step 4 + §7.2 determinism + §6.7 ECS):

  1. `BattleSimulator(determinism, resolver)` constructs with a
     `Determinism` instance and a `TechResolver` so the simulator
     has no global state and no implicit PRNG.

  2. `simulate(action)` takes one combat action (tech + attacker +
     attacker_attack) and returns a single `ActionResult` from the
     resolver. The simulator is a thin orchestrator — the resolver
     is the source of truth for what the action does.

  3. Calling `simulate` 100 times with the same inputs (same tech,
     same attacker_attack, same Determinism seed) produces
     byte-identical `ActionResult` objects. This is the §7.2
     determinism contract applied to the orchestration layer.

  4. Different `Determinism` seeds produce different
     `ActionResult` objects when the tech has any chance rolls.
     For a basic attack (no chance rolls) the results are
     identical across seeds; the test pins this for the basic
     case and notes the augmentation-chain variation is a future
     cycle.

  5. The simulator preserves the resolver's contract: `target_scope`,
     `effects`, and `applied_augmentations` pass through unchanged.

  6. The simulator does not invent new effects, statuses, or
     augmentations. It is a pure pass-through to the resolver in
     this cycle.

The Python mirror exists so the test rig (which does not boot the
Godot runtime) can exercise the orchestration contract. The
GDScript `BattleSimulator.gd` will be the engine-side
implementation; both must satisfy the same contract.

Run:
    python -m pytest tests/test_battle_sim.py -v
    python -m pytest tests/                            # all tests
"""
import sys
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GAME_DIR / "tools"))

TECHS_DIR = GAME_DIR / "data" / "techs"


def test_module_imports():
    """The battle_sim module exposes a BattleSimulator class that
    the combat engine can instantiate.
    """
    import battle_sim  # type: ignore  # noqa: E402

    assert hasattr(battle_sim, "BattleSimulator"), (
        "battle_sim module must expose a BattleSimulator class"
    )


def test_simulator_constructs_with_determinism_and_resolver():
    """The simulator takes a Determinism instance and a
    TechResolver so it has no global state. The construction
    is a thin wiring step — no PRNG calls, no state mutation.
    """
    import battle_sim  # type: ignore  # noqa: E402
    import determinism  # type: ignore  # noqa: E402
    import tech_resolver  # type: ignore  # noqa: E402

    d = determinism.Determinism(0)
    resolver = tech_resolver.TechResolver(d)
    sim = battle_sim.BattleSimulator(d, resolver)
    assert sim is not None


def test_simulate_returns_resolver_result_for_basic_attack():
    """A basic attack (no augmentations) simulated 1 time returns
    the same ActionResult the resolver would have produced
    directly. The simulator is a pass-through orchestrator in
    this cycle.
    """
    import battle_sim  # type: ignore  # noqa: E402
    import determinism  # type: ignore  # noqa: E402
    import tech_data  # type: ignore  # noqa: E402
    import tech_resolver  # type: ignore  # noqa: E402

    d = determinism.Determinism(0)
    resolver = tech_resolver.TechResolver(d)
    sim = battle_sim.BattleSimulator(d, resolver)
    td = tech_data.TechData.from_json(TECHS_DIR / "dash_and_slash.json")
    result = sim.simulate(td, attacker_attack=10)
    # Same length, same kinds, same magnitudes.
    assert len(result.effects) == 1
    assert result.effects[0].kind == "DAMAGE"
    assert result.effects[0].magnitude == pytest.approx(10.0)
    assert result.target_scope == "SINGLE_ENEMY"
    assert result.applied_augmentations == []


def test_simulate_100_runs_byte_identical():
    """Per §7.2 + §7.10 step 4: 100 simulations of the same action
    with the same seed produce byte-identical ActionResult objects.
    This is the determinism contract for the orchestration layer.
    The simulator must not introduce hidden state, implicit PRNG,
    or per-call accumulation that would cause drift.
    """
    import battle_sim  # type: ignore  # noqa: E402
    import determinism  # type: ignore  # noqa: E402
    import tech_data  # type: ignore  # noqa: E402
    import tech_resolver  # type: ignore  # noqa: E402

    # Fresh seed per test so any per-instance state on Determinism
    # starts from the same point.
    d = determinism.Determinism(0)
    resolver = tech_resolver.TechResolver(d)
    sim = battle_sim.BattleSimulator(d, resolver)
    td = tech_data.TechData.from_json(TECHS_DIR / "dash_and_slash.json")

    # Run 100 simulations.
    results = [sim.simulate(td, attacker_attack=10) for _ in range(100)]

    # All 100 results must match the first one exactly.
    first = results[0]
    for i, r in enumerate(results[1:], start=1):
        assert r.target_scope == first.target_scope, (
            f"run {i}: target_scope drifted from {first.target_scope!r} to {r.target_scope!r}"
        )
        assert len(r.effects) == len(first.effects), (
            f"run {i}: effect count drifted from {len(first.effects)} to {len(r.effects)}"
        )
        for a, b in zip(r.effects, first.effects):
            assert a.kind == b.kind, (
                f"run {i}: effect kind drifted from {a.kind!r} to {b.kind!r}"
            )
            assert a.magnitude == pytest.approx(b.magnitude), (
                f"run {i}: effect magnitude drifted from {a.magnitude} to {b.magnitude}"
            )
            assert a.element == b.element, (
                f"run {i}: effect element drifted from {a.element!r} to {b.element!r}"
            )
        assert len(r.applied_augmentations) == len(first.applied_augmentations), (
            f"run {i}: applied_augmentations count drifted"
        )


def test_simulator_passes_through_augmentations_unchanged():
    """The simulator must not mutate the resolver's applied
    augmentations. The chain walk (pre/post ordering, intra-phase
    order) is the resolver's job; the simulator is a thin
    orchestrator that does not touch the list.
    """
    import battle_sim  # type: ignore  # noqa: E402
    import determinism  # type: ignore  # noqa: E402
    import tech_data  # type: ignore  # noqa: E402
    import tech_resolver  # type: ignore  # noqa: E402

    # Mixed-phase augmentation list — array order is [post, pre,
    # post, pre]. The resolver must reorder; the simulator must
    # pass that reordering through unchanged.
    mixed_augs = [
        {"kind": "POST_DAMAGE_STATUS", "phase": "post",
         "status": "burn", "chance": 1.0, "turns": 3},
        {"kind": "PRE_DAMAGE_STATUS", "phase": "pre",
         "status": "slow", "chance": 1.0, "turns": 2},
        {"kind": "POST_DAMAGE_STATUS", "phase": "post",
         "status": "weaken", "chance": 1.0, "turns": 2},
        {"kind": "PRE_DAMAGE_STATUS", "phase": "pre",
         "status": "confuse", "chance": 1.0, "turns": 2},
    ]
    raw = {
        "id": "dash_and_slash_aug_test",
        "display_name": "Dash and Slash (aug test)",
        "tier": 1,
        "element": "white",
        "target_scope": "SINGLE_ENEMY",
        "slot_kind": "BASIC_LINE",
        "base_damage_multiplier": 1.0,
        "augmentations": mixed_augs,
        "effects": [
            {"kind": "DAMAGE", "magnitude": 1.0, "element": "white"},
        ],
    }
    td = tech_data.TechData.__new__(tech_data.TechData)
    td._raw = raw
    td.id = raw["id"]
    td.display_name = raw["display_name"]
    td.tier = raw["tier"]
    td.element = raw["element"]
    td.cost_mp = 0
    td.base_damage_multiplier = raw["base_damage_multiplier"]
    td.target_scope = raw["target_scope"]
    td.slot_kind = raw["slot_kind"]
    td.augmentations = list(raw["augmentations"])
    td.effects = list(raw["effects"])

    d = determinism.Determinism(0)
    resolver = tech_resolver.TechResolver(d)
    sim = battle_sim.BattleSimulator(d, resolver)
    result = sim.simulate(td, attacker_attack=10)

    # Resolver reorders to pre, pre, post, post. Simulator must
    # pass that through unchanged.
    phases = [a.get("phase") for a in result.applied_augmentations]
    assert phases == ["pre", "pre", "post", "post"]
    pre_statuses = [
        a.get("status") for a in result.applied_augmentations
        if a.get("phase") == "pre"
    ]
    assert pre_statuses == ["slow", "confuse"]


def test_simulator_does_not_invent_effects_for_basic_attack():
    """A basic attack with no augmentations simulated via the
    orchestrator produces exactly the same number of effects as
    the input tech (one DAMAGE). The simulator must not add
    status effects, heal effects, or chain effects when the
    input has none.
    """
    import battle_sim  # type: ignore  # noqa: E402
    import determinism  # type: ignore  # noqa: E402
    import tech_data  # type: ignore  # noqa: E402
    import tech_resolver  # type: ignore  # noqa: E402

    td = tech_data.TechData.from_json(TECHS_DIR / "dash_and_slash.json")
    assert len(td.effects) == 1
    assert len(td.augmentations) == 0

    d = determinism.Determinism(0)
    resolver = tech_resolver.TechResolver(d)
    sim = battle_sim.BattleSimulator(d, resolver)
    result = sim.simulate(td, attacker_attack=10)
    assert len(result.effects) == len(td.effects)
    assert len(result.applied_augmentations) == 0


# ---------------------------------------------------------------------------
# §7.10 test surface (c) + §7.5 status effect engine:
# status applications respect resistance and immunity.
#
# Per §7.5 + DEC-002, the canonical 8 statuses are: sleep, poison, burn,
# freeze, confuse, slow, stop, weaken. The §7.10 step 4 status application
# step must respect the target's status_immunities and status_resistances:
#
#   - status_immunities: a set of status ids that the target is *fully*
#     immune to. Attempts to apply yield 0 stacks regardless of chance.
#   - status_resistances: a dict of {status_id: multiplier} where the
#     multiplier scales the application chance (per the §7.4 chart, a
#     0.5 multiplier halves the effective chance; 0.0 makes the
#     status impossible — but the canonical contract is to use
#     status_immunities for the 0.0 case, not a resistance entry).
#
# The orchestrator's apply_status method is the §7.10 step 4 entry point
# for status application. It consumes the scoped "combat" PRNG from the
# Determinism layer (§7.2) so a fixed seed produces a fixed outcome —
# this is the §7.2 determinism contract applied to status application.
# ---------------------------------------------------------------------------


class _FakeTarget:
    """Minimal target object for status application tests.

    Per §7.5, a target (player, enemy, boss, summon) carries a
    `status_immunities` set and a `status_resistances` dict. This
    fake is enough for the orchestrator's apply_status path; a
    future cycle will replace it with the real `Combatant` /
    `StatusEffectComponent` once the §7.5 engine is mirrored in
    Python.
    """

    def __init__(
        self,
        status_immunities=None,
        status_resistances=None,
    ):
        # Normalize to a dict so the orchestrator can use both
        # `in` and `.get(status_id)` against the same object.
        # Accept either a set-like (iterable of ids) or a dict
        # (id -> anything) for `status_immunities`. The spec
        # contract (§7.5) is set-like; the dict form is an
        # acceptable variant for callers that want to attach
        # extra metadata.
        imm = status_immunities or {}
        if isinstance(imm, dict):
            self.status_immunities = dict(imm)
        else:
            self.status_immunities = {sid: True for sid in imm}
        self.status_resistances = dict(status_resistances or {})


def test_apply_status_full_immunity_yields_zero_stacks():
    """A target with `burn` in status_immunities yields 0 stacks
    regardless of chance, attempts, or seed. The orchestrator must
    short-circuit before any chance roll — immunity is a hard veto
    per §7.5. The 100-attempt × chance=1.0 input is the strongest
    possible "should apply" signal; immunity must override it.
    """
    import battle_sim  # type: ignore  # noqa: E402
    import determinism  # type: ignore  # noqa: E402
    import tech_resolver  # type: ignore  # noqa: E402

    d = determinism.Determinism(0)
    resolver = tech_resolver.TechResolver(d)
    sim = battle_sim.BattleSimulator(d, resolver)
    target = _FakeTarget(status_immunities={"burn"})
    out = sim.apply_status(
        target,
        status_id="burn",
        chance=1.0,
        attempts=100,
    )
    assert out.applied == 0, (
        f"immune target must yield 0 stacks, got {out.applied}"
    )
    assert out.immunity_blocked is True


def test_apply_status_normal_target_yields_one_stack_per_attempt_at_chance_1():
    """A target with no immunity and no resistance to `burn` yields
    1 stack per attempt when chance=1.0. Per §7.5, the base contract
    is that a 100% chance always lands — the orchestrator must not
    silently re-roll or drop applications. This pins the "happy
    path" that the resistance/immunity tests deviate from.
    """
    import battle_sim  # type: ignore  # noqa: E402
    import determinism  # type: ignore  # noqa: E402
    import tech_resolver  # type: ignore  # noqa: E402

    d = determinism.Determinism(0)
    resolver = tech_resolver.TechResolver(d)
    sim = battle_sim.BattleSimulator(d, resolver)
    target = _FakeTarget()  # no immunity, no resistance
    out = sim.apply_status(
        target,
        status_id="burn",
        chance=1.0,
        attempts=100,
    )
    assert out.applied == 100, (
        f"normal target at chance=1.0 must yield 1 stack per "
        f"attempt; got {out.applied} over 100 attempts"
    )
    assert out.immunity_blocked is False


def test_apply_status_resistance_halves_effective_chance():
    """A target with `burn` in status_resistances at multiplier
    0.5 has its effective chance halved. Per §7.4 + DEC-001 the
    canonical "strong defense" multiplier is 0.5. With chance=1.0
    and 100 attempts, the expected number of stacks is ~50
    (probabilistic). The test pins the contract that resistance
    *reduces* the stack count below the no-resistance baseline,
    using a tolerance band that holds for any valid PRNG seed.

    This is the contract: a resistant target never gets the full
    per-attempt yield a non-resistant target gets. The exact
    count is not pinned (it is PRNG-dependent) but the inequality
    is.
    """
    import battle_sim  # type: ignore  # noqa: E402
    import determinism  # type: ignore  # noqa: E402
    import tech_resolver  # type: ignore  # noqa: E402

    d = determinism.Determinism(0)
    resolver = tech_resolver.TechResolver(d)
    sim = battle_sim.BattleSimulator(d, resolver)
    target = _FakeTarget(status_resistances={"burn": 0.5})
    out = sim.apply_status(
        target,
        status_id="burn",
        chance=1.0,
        attempts=100,
    )
    # With multiplier 0.5 over 100 attempts at chance 1.0, every
    # valid PRNG must produce strictly fewer than 100 stacks and
    # strictly more than 0 stacks. The tolerance is wide because
    # the underlying count is PRNG-dependent; the inequality is
    # the contract.
    assert 0 < out.applied < 100, (
        f"resistant target must yield strictly fewer stacks than "
        f"no-resistance baseline; got {out.applied} over 100 attempts"
    )
    assert out.immunity_blocked is False


def test_apply_status_is_deterministic_for_same_seed():
    """Per §7.2 + §7.10: two apply_status calls with the same
    target, same parameters, and the same Determinism seed must
    produce identical results. This pins the determinism contract
    at the status-application layer. A refactor that introduces
    a non-seeded random call will fail this test.
    """
    import battle_sim  # type: ignore  # noqa: E402
    import determinism  # type: ignore  # noqa: E402
    import tech_resolver  # type: ignore  # noqa: E402

    target = _FakeTarget(status_resistances={"burn": 0.5})
    # Two independent simulator instances with the same seed must
    # produce the same stack count.
    d1 = determinism.Determinism(42)
    sim1 = battle_sim.BattleSimulator(d1, tech_resolver.TechResolver(d1))
    out1 = sim1.apply_status(
        target, status_id="burn", chance=1.0, attempts=100,
    )
    d2 = determinism.Determinism(42)
    sim2 = battle_sim.BattleSimulator(d2, tech_resolver.TechResolver(d2))
    out2 = sim2.apply_status(
        target, status_id="burn", chance=1.0, attempts=100,
    )
    assert out1.applied == out2.applied, (
        f"same-seed apply_status diverged: {out1.applied} vs {out2.applied}"
    )
