"""Tests for the TechResolver (§7.10 combat engine, §3.5 basic attack line).

Per §7.10 of the design document, the combat engine is split into
`Battle` (orchestrator), `CombatSimulator` (simulation), and
`BattleView` (presentation). The `CombatSimulator.resolve(action)` is
the entry point that turns a chosen `Tech` (a `TechData`) plus a
combat context into an `ActionResult` — the resolved list of effects
with concrete magnitudes, status applications, and chance outcomes.

This is the FIFTH TDD cycle (cycle 39 of the tdd_cron), coming after:
  - cycle 34: test_determinism_prng_seeded (§7.2 derived PRNGs)
  - cycle 35: test_character_data_loads (§7.3 CharacterData)
  - cycle 36: test_tech_data_loads (§7.3 TechData)
  - cycle 37: (prior)
  - cycle 38: test_party_manager_active_roster (§7.7 PartyManager)

The contract being pinned here is the §7.10 "step 3: damage
calculation" of the action lifecycle, in its simplest possible form:
the basic attack line with no augmentations.

The contract (§7.10 step 3 + §3.5 basic attack line + §6.7 ECS):

  1. `TechResolver` is a Python class that resolves a `TechData`
     against a target into an `ActionResult`.
  2. For a basic attack with no augmentations, the resolved result
     has the same effects as the input tech (no augmentation, no
     chain, no status pre/post application).
  3. The resolved result carries a damage magnitude for the canonical
     DAMAGE effect: the magnitude is `base_damage_multiplier *
     attacker_attack` (the §7.10 "Base damage × multiplier" formula
     without element resistance — element resistance is a §7.4 layer
     that the resolver is decoupled from in this cycle).
  4. The resolved result is deterministic for a given input: same
     tech, same attacker, same target → same result. No global
     random calls.
  5. The resolved result exposes a `effects` list of
     `ResolvedEffect` entries (the §7.3 TechEffect concrete
     version) so the view/animation layer can read what to play.
  6. `target_scope` is preserved on the result so the view can pick
     the right animation target (front row vs all enemies vs single
     ally).
  7. The `Determinism` layer (§7.2) is the source of any chance
     rolls. A basic attack has no chance rolls but augmentations
     later will. The resolver takes a `Determinism` instance so the
     augmentation chain can use `d.scoped("combat")` without the
     resolver having to import a different PRNG.
  8. The resolver is decoupled from element resistance (§7.4) and
     row modifiers (§7.7) in this cycle. Those layers compose on
     top of the resolver's output in later cycles.

This is the entry point for the §7.10 combat engine. The GDScript
`TechResolver.gd` will be the engine-side implementation; this
Python mirror lets the test rig exercise the resolve logic without
booting the Godot runtime, just like `character_data.py`,
`tech_data.py`, and `party_manager.py` do.

Run:
    python -m pytest tests/test_tech_resolver.py -v
    python -m pytest tests/                            # all tests
"""
import sys
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GAME_DIR / "tools"))

TECHS_DIR = GAME_DIR / "data" / "techs"


def test_module_imports():
    """The tech_resolver module exposes a TechResolver class and an
    ActionResult / ResolvedEffect shape that the combat engine can
    read."""
    import tech_resolver  # type: ignore  # noqa: E402

    assert hasattr(tech_resolver, "TechResolver"), (
        "tech_resolver module must expose a TechResolver class"
    )


def test_resolver_constructs_with_determinism():
    """The resolver takes a Determinism instance (per §7.2) so the
    augmentation chain (future cycles) can use scoped("combat")
    without the resolver having to import a different PRNG.

    A fresh resolver is empty — it has no global state. The same
    resolver can resolve many actions in sequence.
    """
    import tech_resolver  # type: ignore  # noqa: E402
    import determinism  # type: ignore  # noqa: E402

    d = determinism.Determinism(0)
    resolver = tech_resolver.TechResolver(d)
    assert resolver is not None


def test_resolve_basic_attack_returns_damage_effect():
    """The locked §3.5 starting point: Serge's tier-1 basic attack
    `dash_and_slash` resolves to exactly one resolved effect — a
    DAMAGE effect with magnitude = base_damage_multiplier *
    attacker_attack.

    The base_damage_multiplier for dash_and_slash is 1.0 (per
    data/techs/dash_and_slash.json + the schema default). With
    attacker_attack = 10, the resolved magnitude is 10.0. This is
    the §7.10 step 3 "Base damage × multiplier" formula in its
    minimal form.
    """
    import tech_resolver  # type: ignore  # noqa: E402
    import tech_data  # type: ignore  # noqa: E402
    import determinism  # type: ignore  # noqa: E402

    d = determinism.Determinism(0)
    resolver = tech_resolver.TechResolver(d)
    td = tech_data.TechData.from_json(TECHS_DIR / "dash_and_slash.json")
    result = resolver.resolve(td, attacker_attack=10)
    # dash_and_slash has exactly one effect: a DAMAGE entry.
    assert len(result.effects) == 1
    eff = result.effects[0]
    assert eff.kind == "DAMAGE"
    # magnitude = base_damage_multiplier (1.0) * attacker_attack (10) = 10.0
    assert eff.magnitude == pytest.approx(10.0)


def test_resolve_basic_attack_preserves_target_scope():
    """The resolved result carries the tech's `target_scope` so the
    view/animation layer can pick the right target (single enemy
    vs row vs all enemies vs ally). For `dash_and_slash` the scope
    is SINGLE_ENEMY; that must survive the resolve step.
    """
    import tech_resolver  # type: ignore  # noqa: E402
    import tech_data  # type: ignore  # noqa: E402
    import determinism  # type: ignore  # noqa: E402

    d = determinism.Determinism(0)
    resolver = tech_resolver.TechResolver(d)
    td = tech_data.TechData.from_json(TECHS_DIR / "dash_and_slash.json")
    result = resolver.resolve(td, attacker_attack=10)
    assert result.target_scope == "SINGLE_ENEMY"


def test_resolve_is_deterministic_for_same_input():
    """Per §6.7 / §7.2: the resolver is deterministic. Two resolves
    with the same tech, same attacker_attack, and the same
    Determinism seed produce identical results. This is the test
    that fails if a future refactor accidentally introduces a
    non-seeded random call.
    """
    import tech_resolver  # type: ignore  # noqa: E402
    import tech_data  # type: ignore  # noqa: E402
    import determinism  # type: ignore  # noqa: E402

    td = tech_data.TechData.from_json(TECHS_DIR / "dash_and_slash.json")
    r1 = tech_resolver.TechResolver(determinism.Determinism(0)).resolve(
        td, attacker_attack=10
    )
    r2 = tech_resolver.TechResolver(determinism.Determinism(0)).resolve(
        td, attacker_attack=10
    )
    assert len(r1.effects) == len(r2.effects)
    for a, b in zip(r1.effects, r2.effects):
        assert a.kind == b.kind
        assert a.magnitude == pytest.approx(b.magnitude)


def test_resolve_damage_scales_with_attacker_attack():
    """The §7.10 "Base damage × multiplier" formula scales the
    resolved magnitude by attacker_attack. A higher attacker_attack
    produces a strictly higher magnitude. This is the contract a
    future stat-leveling system relies on: bumping Serge's attack
    from 10 to 15 raises the basic-attack damage by 50%.
    """
    import tech_resolver  # type: ignore  # noqa: E402
    import tech_data  # type: ignore  # noqa: E402
    import determinism  # type: ignore  # noqa: E402

    td = tech_data.TechData.from_json(TECHS_DIR / "dash_and_slash.json")
    resolver = tech_resolver.TechResolver(determinism.Determinism(0))
    r_low = resolver.resolve(td, attacker_attack=10)
    r_high = resolver.resolve(td, attacker_attack=15)
    assert r_low.effects[0].magnitude == pytest.approx(10.0)
    assert r_high.effects[0].magnitude == pytest.approx(15.0)
    assert r_high.effects[0].magnitude > r_low.effects[0].magnitude


def test_resolve_preserves_element_on_damage_effect():
    """The tech's element (white, red, etc.) is part of the damage
    effect so the §7.4 element grid can apply resistance later. The
    resolver passes the element through unchanged. `dash_and_slash`
    is white element per the data file and the schema enum.
    """
    import tech_resolver  # type: ignore  # noqa: E402
    import tech_data  # type: ignore  # noqa: E402
    import determinism  # type: ignore  # noqa: E402

    td = tech_data.TechData.from_json(TECHS_DIR / "dash_and_slash.json")
    resolver = tech_resolver.TechResolver(determinism.Determinism(0))
    result = resolver.resolve(td, attacker_attack=10)
    eff = result.effects[0]
    assert eff.element == "white"


def test_resolve_basic_attack_no_augmentations_no_extra_effects():
    """A basic attack with no augmentations resolves to exactly the
    same number of effects as the input tech (one DAMAGE). The
    resolver must not invent status effects, heal effects, or
    chain effects when the input has none. This is the §3.5
    starting point: the basic attack line is *only* damage, with
    supports (future cycles) layering status/buff features on top.
    """
    import tech_resolver  # type: ignore  # noqa: E402
    import tech_data  # type: ignore  # noqa: E402
    import determinism  # type: ignore  # noqa: E402

    td = tech_data.TechData.from_json(TECHS_DIR / "dash_and_slash.json")
    # dash_and_slash is the §3.5 starting point: 1 effect, 0 augs.
    assert len(td.effects) == 1
    assert len(td.augmentations) == 0

    resolver = tech_resolver.TechResolver(determinism.Determinism(0))
    result = resolver.resolve(td, attacker_attack=10)
    assert len(result.effects) == len(td.effects)
    assert len(result.applied_augmentations) == 0


def test_resolve_augmentation_chain_walks_pre_phase_before_post_phase():
    """Per §7.10 step 2 + DEC-007: the resolver walks the tech's
    augmentations list in *execution order*, not array order. All
    pre-phase augmentations (MP discounts, self-buffs, status
    pre-applications) run BEFORE the damage step; all post-phase
    augmentations (on-hit chains, post-damage status) run AFTER.

    The observable contract for this cycle is that
    `applied_augmentations` reflects execution order: every
    pre-phase entry appears in the result list before any
    post-phase entry, with intra-phase order preserved from
    the input array. This pins the §3.5 augmentation model —
    supports modify the base attack line, not replace it —
    and the DEC-007 idempotency-by-position contract.

    This test will fail against the current implementation,
    which copies `tech.augmentations` verbatim (array order)
    without sorting by phase.
    """
    import tech_resolver  # type: ignore  # noqa: E402
    import tech_data  # type: ignore  # noqa: E402
    import determinism  # type: ignore  # noqa: E402

    # Build a tech with a mixed-phase augmentation list. Array
    # order is [post, pre, post, pre] — the OPPOSITE of the
    # expected execution order. The resolver must reorder
    # so all `pre` entries precede all `post` entries.
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

    resolver = tech_resolver.TechResolver(determinism.Determinism(0))
    result = resolver.resolve(td, attacker_attack=10)

    # The chain walk produces 4 applied augmentations, all of
    # them — the resolver does not drop any.
    assert len(result.applied_augmentations) == 4

    # Execution order: all pre-phase first, then all post-phase.
    # Within each phase, array order is preserved.
    phases = [a.get("phase") for a in result.applied_augmentations]
    assert phases == ["pre", "pre", "post", "post"], (
        f"chain walk order wrong: {phases!r} "
        "(expected ['pre', 'pre', 'post', 'post'])"
    )

    # Within pre-phase: array order is preserved (slow, then confuse).
    pre_statuses = [
        a.get("status") for a in result.applied_augmentations
        if a.get("phase") == "pre"
    ]
    assert pre_statuses == ["slow", "confuse"], (
        f"intra-pre-phase order wrong: {pre_statuses!r}"
    )

    # Within post-phase: array order is preserved (burn, then weaken).
    post_statuses = [
        a.get("status") for a in result.applied_augmentations
        if a.get("phase") == "post"
    ]
    assert post_statuses == ["burn", "weaken"], (
        f"intra-post-phase order wrong: {post_statuses!r}"
    )
