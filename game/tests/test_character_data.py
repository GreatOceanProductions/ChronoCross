"""Tests for the CharacterData loader (§7.3, §15.4 Step 1).

Per §7.3 of the design document, every data type in the project is
a typed Resource/data class with a schema-validated JSON loader. The
PoC's first data layer deliverable is `CharacterData` — the class
that loads `data/characters/<id>.json` and exposes typed accessors
for the fields that other systems (PartyManager, TechResolver,
character screen UI) will read.

This is the second TDD cycle (cycle 35), coming after
`test_determinism_prng_seeded` (cycle 34). The contract being
pinned here mirrors what the GDScript `CharacterData.gd` Resource
will need to satisfy — a Python mirror in `game/tools/` lets the
test rig exercise the contract without booting the Godot runtime.

The contract:
  1. CharacterData can be constructed from a JSON path.
  2. It loads only valid data (schema-validated).
  3. It exposes typed properties for every required schema field.
  4. It loads all 3 existing base files (serge, kidd, nikki).
  5. The id field on disk becomes the `id` property.
  6. Support slots are exposed as a list of (support_id, tier) tuples.

Run:
    python -m pytest tests/test_character_data.py -v
    python -m pytest tests/                     # all tests
"""
import json
import sys
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GAME_DIR / "tools"))

import character_data  # type: ignore  # noqa: E402

CHARACTERS_DIR = GAME_DIR / "data" / "characters"
SCHEMA_PATH = CHARACTERS_DIR.parent / "schemas" / "character.schema.json"


def test_module_imports():
    """The character_data module exposes a CharacterData class."""
    assert hasattr(character_data, "CharacterData")


def test_load_serge_basic_fields():
    """A CharacterData loaded from serge.json exposes the locked
    Phase 3 design values: white element, base character, tier 1
    'Dash and Slash', tier 8 'Glide Hook'."""
    cd = character_data.CharacterData.from_json(CHARACTERS_DIR / "serge.json")
    assert cd.id == "serge"
    assert cd.name == "Serge"
    assert cd.element == "white"
    assert cd.is_base is True
    assert cd.basic_attack == "Dash and Slash"
    assert cd.tier_1_tech == "Dash and Slash"
    assert cd.tier_8_tech == "Glide Hook"
    assert cd.level == 1


def test_load_kidd_innate_field():
    """Kidd has the 'steal' innate per Phase 3 redesign — the
    CharacterData class must surface this typed enum value."""
    cd = character_data.CharacterData.from_json(CHARACTERS_DIR / "kidd.json")
    assert cd.id == "kidd"
    assert cd.element == "red"
    assert cd.innate == "steal"


def test_load_nikki_combined_support_id():
    """Nikki's support list includes the combined unit 'korcha_macha'.
    The CharacterData must expose support_slots as a structured list
    so the PartyManager can map combined units correctly later."""
    cd = character_data.CharacterData.from_json(CHARACTERS_DIR / "nikki.json")
    assert cd.id == "nikki"
    assert cd.element == "blue"
    support_ids = [slot[0] for slot in cd.support_slots]
    assert "korcha_macha" in support_ids


def test_support_slots_is_list_of_tuples():
    """support_slots is exposed as a list of (support_id, tier) pairs
    so downstream code can iterate without re-parsing JSON."""
    cd = character_data.CharacterData.from_json(CHARACTERS_DIR / "serge.json")
    assert isinstance(cd.support_slots, list)
    assert len(cd.support_slots) == 6
    for entry in cd.support_slots:
        assert isinstance(entry, tuple)
        assert len(entry) == 2
        support_id, tier = entry
        assert isinstance(support_id, str)
        assert isinstance(tier, int)
        assert 1 <= tier <= 8


def test_load_all_three_bases():
    """All 3 existing base JSON files (serge, kidd, nikki) load
    without error. This is the integration test for the data layer."""
    for char_id in ("serge", "kidd", "nikki"):
        path = CHARACTERS_DIR / f"{char_id}.json"
        cd = character_data.CharacterData.from_json(path)
        assert cd.id == char_id
        assert cd.is_base is True


def test_missing_file_raises():
    """Loading a non-existent path raises a clear error rather than
    silently returning a half-constructed object. The §7.3 contract
    is that the loader fails loudly on bad data."""
    with pytest.raises((FileNotFoundError, OSError)):
        character_data.CharacterData.from_json(CHARACTERS_DIR / "does_not_exist.json")
