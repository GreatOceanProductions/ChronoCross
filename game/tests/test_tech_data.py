"""Tests for the TechData loader (§7.3, §15.4 Step 2).

Per §7.3 of the design document, every data type in the project is
a typed Resource/data class with a schema-validated JSON loader. The
PoC's second data-layer deliverable (per §15.4 Step 2) is `TechData`
— the class that loads `data/techs/<id>.json` and exposes typed
accessors for the fields that the combat engine, the tech resolver,
and the character screen will read.

This is the third TDD cycle (cycle 37), coming after
`test_character_data_loads` (cycle 35) and
`test_determinism_prng_seeded` (cycle 34). The contract being pinned
here mirrors what the GDScript `TechData.gd` Resource (a future
`scaffolding_cron` item) will need to satisfy — a Python mirror in
`game/tools/` lets the test rig exercise the contract without
booting the Godot runtime.

The contract (§7.3 locked design):
  1. TechData can be constructed from a JSON path.
  2. It loads only valid data (schema-validated).
  3. It exposes typed properties for every required schema field.
  4. It loads the locked base tech for Serge (`dash_and_slash`):
       - tier 1, element white, slot_kind BASIC_LINE,
         target_scope SINGLE_ENEMY, no augmentations.
  5. The id field on disk becomes the `id` property.
  6. `augmentations` is exposed as a list of (kind, params) tuples
     so the augmentation chain can be walked without re-parsing JSON.
  7. Missing file -> loud failure (FileNotFoundError, per §7.3).

Run:
    python -m pytest tests/test_tech_data.py -v
    python -m pytest tests/                     # all tests
"""
import json
import sys
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GAME_DIR / "tools"))

# The fixture: a single locked base tech, authored as a JSON file at
# `data/techs/dash_and_slash.json` and shipped with this test. The
# values mirror what the §3.7 / §12.4 walkthrough commits for
# Serge's tier-1 basic attack. This is the canonical first tech
# because it is the simplest possible Tech shape: a basic attack
# line with no augmentations and no support effects, exactly as the
# §3.5 basic-attack-line model prescribes.
TECHS_DIR = GAME_DIR / "data" / "techs"
SCHEMA_PATH = GAME_DIR / "data" / "schemas" / "tech.schema.json"


def test_module_imports():
    """The tech_data module exposes a TechData class."""
    import tech_data  # type: ignore  # noqa: E402

    assert hasattr(tech_data, "TechData")


def test_load_dash_and_slash_basic_fields():
    """A TechData loaded from dash_and_slash.json exposes the
    locked Phase 3 values for Serge's tier-1 basic attack:
    white element, single-enemy target, basic attack line slot."""
    import tech_data  # type: ignore  # noqa: E402

    td = tech_data.TechData.from_json(TECHS_DIR / "dash_and_slash.json")
    assert td.id == "dash_and_slash"
    assert td.display_name == "Dash and Slash"
    assert td.tier == 1
    assert td.element == "white"
    assert td.target_scope == "SINGLE_ENEMY"
    assert td.slot_kind == "BASIC_LINE"


def test_dash_and_slash_no_augmentations():
    """Serge's tier-1 basic attack is the locked §3.5 starting
    point — no augmentations yet, no support techs layered on.
    The augmentation list must be empty (not None) so the combat
    engine can iterate it without a None check."""
    import tech_data  # type: ignore  # noqa: E402

    td = tech_data.TechData.from_json(TECHS_DIR / "dash_and_slash.json")
    assert isinstance(td.augmentations, list)
    assert len(td.augmentations) == 0


def test_dash_and_slash_damage_multiplier_default():
    """The base_damage_multiplier defaults to 1.0 for a basic
    attack that does not yet have a support augment modifying it.
    Per §7.3, the multiplier field is required and must surface
    as a float, not a string."""
    import tech_data  # type: ignore  # noqa: E402

    td = tech_data.TechData.from_json(TECHS_DIR / "dash_and_slash.json")
    assert isinstance(td.base_damage_multiplier, float)
    assert td.base_damage_multiplier == 1.0


def test_load_serge_tier1_via_base_id():
    """§7.3 names a base's tier-1 tech as a locked reference. The
    test rig can fetch Serge's tier-1 by reading the
    `tier_1_tech` field of his CharacterData and then loading
    the matching TechData. This integration step proves the
    two data layers (characters, techs) compose."""
    import tech_data  # type: ignore  # noqa: E402
    import character_data  # type: ignore  # noqa: E402

    serge = character_data.CharacterData.from_json(
        GAME_DIR / "data" / "characters" / "serge.json"
    )
    assert serge.tier_1_tech == "Dash and Slash"
    td = tech_data.TechData.from_json(TECHS_DIR / f"{serge.tier_1_tech.lower().replace(' ', '_')}.json")
    assert td.id == serge.tier_1_tech.lower().replace(" ", "_")
    assert td.tier == 1
    assert td.element == serge.element


def test_missing_file_raises():
    """Loading a non-existent path raises a clear error rather than
    silently returning a half-constructed object. The §7.3 contract
    is that the loader fails loudly on bad data — same as
    CharacterData.from_json."""
    import tech_data  # type: ignore  # noqa: E402

    with pytest.raises((FileNotFoundError, OSError)):
        tech_data.TechData.from_json(TECHS_DIR / "does_not_exist.json")


def test_schema_validates_dash_and_slash():
    """The tech JSON validates against tech.schema.json. This is
    the §6.5 schema-validated-data-layer contract: every JSON
    file in data/ must pass its schema before any code consumes
    it. The validator (tools/validate_data.py) already handles
    the schema dispatch for data/techs/* once tech.schema.json
    exists and DIR_TO_SCHEMA is updated."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    data = json.loads((TECHS_DIR / "dash_and_slash.json").read_text(encoding="utf-8"))
    # Minimal draft-07 validation: required keys present, types match.
    for required in schema["required"]:
        assert required in data, f"missing required field: {required}"
    for key, prop in schema["properties"].items():
        if key not in data:
            continue
        if "enum" in prop:
            assert data[key] in prop["enum"], (
                f"{key}={data[key]!r} not in enum {prop['enum']}"
            )
        if prop.get("type") == "integer" and not isinstance(data[key], int):
            raise AssertionError(f"{key} should be integer, got {type(data[key]).__name__}")
