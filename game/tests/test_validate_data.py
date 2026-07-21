"""Tests for the data validation pipeline.

Per §9.4 of the design document, one commit per TDD cycle. This file
is the first TDD cycle: the schema validator accepts serge.json.

Run:
    python -m pytest tests/test_validate_data.py
    python -m pytest tests/                  # all tests

The PoC scope (§15.4 Step 1) commits to this single test for the
data-layer foundation. Future tests will be added as the
character screen, map, combat, and save/load endpoints come online.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
SERGE_JSON = GAME_DIR / "data" / "characters" / "serge.json"
SCHEMA_JSON = GAME_DIR / "data" / "schemas" / "character.schema.json"
VALIDATOR = GAME_DIR / "tools" / "validate_data.py"


def test_serge_json_exists():
    """The first character file exists and is readable."""
    assert SERGE_JSON.exists(), f"missing {SERGE_JSON}"
    data = json.loads(SERGE_JSON.read_text(encoding="utf-8"))
    assert data["id"] == "serge"
    assert data["element"] == "white"
    assert data["is_base"] is True
    assert data["tier_1_tech"] == "Dash and Slash"
    assert data["tier_8_tech"] == "Glide Hook"


def test_character_schema_exists():
    """The character schema exists and is valid JSON Schema draft-07."""
    assert SCHEMA_JSON.exists(), f"missing {SCHEMA_JSON}"
    data = json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))
    assert "$schema" in data
    assert "draft-07" in data["$schema"]
    assert data["title"] == "CharacterData"
    # Required fields per the locked design
    required = set(data["required"])
    assert {"id", "name", "element", "level", "basic_attack", "tier_1_tech", "tier_8_tech"} <= required


def test_serge_validates_against_schema():
    """serge.json validates against character.schema.json with no errors."""
    import jsonschema
    schema = json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))
    data = json.loads(SERGE_JSON.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)
    errors = list(validator.iter_errors(data))
    assert not errors, f"validation errors: {[e.message for e in errors]}"


def test_validator_script_runs_clean():
    """The validate_data.py script runs and returns exit code 0 on serge.json."""
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--character", str(SERGE_JSON)],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, f"validator failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    assert "1/1 files valid" in result.stdout or "1 files valid" in result.stdout


def test_validator_rejects_bad_data():
    """The validator correctly rejects a character file missing required fields."""
    bad_path = GAME_DIR / "data" / "characters" / "_test_bad.json"
    bad_data = {"id": "broken", "name": "Broken"}  # missing required fields
    bad_path.write_text(json.dumps(bad_data), encoding="utf-8")
    try:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), "--character", str(bad_path)],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode != 0, "validator should fail on bad data"
        assert "failed" in result.stdout.lower() or "fail" in result.stdout.lower()
    finally:
        bad_path.unlink(missing_ok=True)
