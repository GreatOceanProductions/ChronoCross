"""TechData — typed loader for `data/techs/<id>.json`.

Per §7.3 of the design document, every data type in the project is
a typed data class with a schema-validated JSON loader. This is the
PoC's second data-layer deliverable (per §15.4 Step 2), following
CharacterData in Step 1.

The GDScript `TechData.gd` Resource (a future `scaffolding_cron`
item) is the engine-side implementation. This Python mirror exists
so the agent's test rig — which runs Python, not the Godot runtime
— can exercise the data-layer contract. Both implementations must
satisfy the same schema and expose the same field set, but the
GDScript version uses Godot's typed dictionary semantics while this
version uses a regular Python class with typed properties.

The contract pinned by `tests/test_tech_data.py`:
  - `TechData.from_json(path)` returns a TechData.
  - Required schema fields are exposed as typed attributes.
  - `augmentations` is a list of (kind, params) dicts so the
    augmentation chain can be walked without re-parsing JSON.
  - `effects` is a list of dicts (the §7.3 TechEffect composition).
  - Missing file -> FileNotFoundError (loud failure, per §7.3).

Schema reference: `data/schemas/tech.schema.json` (draft-07).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union


# Whitelist of fields the loader is allowed to surface. Mirrors the
# `properties` block of `data/schemas/tech.schema.json`. Adding a
# new field here without also adding it to the schema is a
# divergence; the schema is authoritative.
_ALLOWED_FIELDS = (
    "id",
    "display_name",
    "tier",
    "element",
    "cost_mp",
    "base_damage_multiplier",
    "target_scope",
    "slot_kind",
    "augmentations",
    "effects",
)


class TechData:
    """Typed wrapper around a single tech JSON file.

    Construction is via `from_json(path)`. Direct construction is
    not supported because the on-disk file is the source of truth
    (per the §6.5 schema-validated data layer rule).
    """

    def __init__(self, raw: dict) -> None:
        # Stash the raw dict for introspection / debugging.
        self._raw = raw
        # Surface the locked §7.3 fields as typed attributes.
        # Defaults match the schema's `default` values where present.
        self.id: str = raw["id"]
        self.display_name: str = raw["display_name"]
        self.tier: int = int(raw["tier"])
        self.element: str = raw["element"]
        self.cost_mp: int = int(raw.get("cost_mp", 0))
        self.base_damage_multiplier: float = float(
            raw.get("base_damage_multiplier", 1.0)
        )
        self.target_scope: str = raw["target_scope"]
        self.slot_kind: str = raw["slot_kind"]
        # Per §7.3, augmentations is a list of TechAugmentation
        # resources. The Python mirror exposes them as plain dicts
        # (the schema's `additionalProperties: false` ensures shape
        # parity with the GDScript Dictionary approach). The
        # (kind, params) tuple view in the test is just the first
        # element + the remaining dict.
        self.augmentations: List[Dict[str, Any]] = list(
            raw.get("augmentations", [])
        )
        # Per §7.3, effects is a list of TechEffect entries.
        self.effects: List[Dict[str, Any]] = list(raw.get("effects", []))

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "TechData":
        """Load a tech JSON file and return a TechData.

        Raises FileNotFoundError if the path does not exist. The
        §7.3 contract is that the loader fails loudly on bad data
        so a typo in a data path surfaces immediately rather than
        silently producing a half-constructed object.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"tech data not found: {p}")
        raw = json.loads(p.read_text(encoding="utf-8"))
        return cls(raw)

    def __repr__(self) -> str:
        return (
            f"TechData(id={self.id!r}, tier={self.tier}, "
            f"element={self.element!r}, slot_kind={self.slot_kind!r})"
        )
