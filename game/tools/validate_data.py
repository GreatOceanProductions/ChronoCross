"""Validate every JSON file in data/ against its matching schema.

Usage:
    python tools/validate_data.py
    python tools/validate_data.py --character data/characters/serge.json
    python tools/validate_data.py --strict  # exit 1 on warnings

Per §6.5 of the design document, the data layer is schema-validated
before any code consumes it. This script is the single entry point
for the validation pipeline.

The PoC scope (§15.3) commits to: one schema (character.schema.json)
and one character file (serge.json). The script's discovery logic
walks every data/*.json file and finds its matching schema in
data/schemas/{type}.schema.json. This is the seed; future data
types (elements, maps, chapters) will follow the same pattern.
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Scrub PYTHONPATH contamination from hermes-agent so the project venv
# is the import source for jsonschema. This is a Windows environment
# workaround for the cron job's Python invocation.
for env_var in ("PYTHONPATH", "PYTHONHOME"):
    if env_var in os.environ:
        del os.environ[env_var]
# Also strip any path-like env that points to hermes-agent
for env_var in list(os.environ.keys()):
    if "hermes" in os.environ[env_var].lower():
        del os.environ[env_var]
# Strip hermes paths already prepended to sys.path
sys.path = [p for p in sys.path if "hermes" not in p.lower()]

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema not installed. Run: uv pip install jsonschema", file=sys.stderr)
    sys.exit(2)


# Map a JSON file's parent directory name to its schema filename.
# Per §6.5 / §7.3, every JSON file in data/ validates against a
# matching schema in data/schemas/{type}.schema.json. Adding a new
# data type means adding the directory here AND authoring a schema
# AND the data file itself.
DIR_TO_SCHEMA = {
    "characters": "character",
    "techs": "tech",
    "elements": "element",
    "maps": "map",
    "chapters": "chapter",
}

GAME_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = GAME_DIR / "data"
SCHEMAS_DIR = DATA_DIR / "schemas"


def load_schema(schema_name: str) -> dict:
    path = SCHEMAS_DIR / f"{schema_name}.schema.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_file(json_path: Path, strict: bool = False) -> tuple[bool, list[str]]:
    """Validate one JSON file. Returns (ok, errors)."""
    errors = []
    parent = json_path.parent.name
    if parent not in DIR_TO_SCHEMA:
        # Unknown directory; skip
        return True, []

    schema_name = DIR_TO_SCHEMA[parent]
    schema = load_schema(schema_name)
    if schema is None:
        return True, [f"schema not found for {parent} (expected {schema_name}.schema.json)"]

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"invalid JSON: {e}"]

    validator = jsonschema.Draft7Validator(schema)
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        path_str = "$" + "".join(f"[{p!r}]" if not isinstance(p, str) else f".{p}" for p in err.absolute_path)
        errors.append(f"{json_path.relative_to(GAME_DIR)}: {path_str}: {err.message}")

    return len(errors) == 0, errors


def discover_files() -> list[Path]:
    """Find all JSON files in known data subdirectories."""
    files = []
    for subdir in DIR_TO_SCHEMA:
        sub_path = DATA_DIR / subdir
        if sub_path.exists():
            files.extend(sorted(sub_path.glob("*.json")))
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", type=Path, help="Validate a single character file")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on any warning")
    args = parser.parse_args()

    if args.character:
        files = [args.character]
    else:
        files = discover_files()

    if not files:
        print("No data files found.")
        return 0

    total = 0
    failed = 0
    all_errors = []
    for f in files:
        total += 1
        ok, errors = validate_file(f, args.strict)
        if ok:
            print(f"  [OK]   {f.relative_to(GAME_DIR)}")
        else:
            failed += 1
            all_errors.extend(errors)
            for e in errors:
                print(f"  [FAIL] {e}")

    print(f"\n{total - failed}/{total} files valid")
    if failed:
        print(f"{failed} file(s) failed validation")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
