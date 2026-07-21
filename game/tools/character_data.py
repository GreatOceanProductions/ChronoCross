"""CharacterData — typed loader for `data/characters/<id>.json`.

Per §7.3 of the design document, every data type in the project is
a typed data class with a schema-validated JSON loader. This is the
PoC's first data-layer deliverable (per §15.4 Step 1).

The GDScript `CharacterData.gd` Resource (a future
`scaffolding_cron` item) is the engine-side implementation. This
Python mirror exists so the agent's test rig — which runs Python,
not the Godot runtime — can exercise the data-layer contract. Both
implementations must satisfy the same schema and expose the same
field set, but the GDScript version uses Godot's typed dictionary
semantics while this version uses a regular Python class with
typed properties.

The contract pinned by `tests/test_character_data.py`:
  - `CharacterData.from_json(path)` returns a CharacterData.
  - Required schema fields are exposed as typed attributes.
  - `support_slots` is a list of (support_id, tier) tuples.
  - Missing file → FileNotFoundError (loud failure, per §7.3).

Schema reference: `data/schemas/character.schema.json` (draft-07).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple, Union


# Whitelist of fields the loader is allowed to surface. Mirrors the
# `properties` block of `data/schemas/character.schema.json`. Adding
# a new field here without also adding it to the schema is a
# divergence; the schema is authoritative.
_ALLOWED_FIELDS = (
    "id",
    "name",
    "element",
    "level",
    "is_base",
    "basic_attack",
    "tier_1_tech",
    "tier_8_tech",
    "innate",
    "support_slots",
    "sprite",
    "portrait",
)


class CharacterData:
    """Typed wrapper around a single character JSON file.

    Construction is via `from_json(path)`. Direct construction is
    not supported because the on-disk file is the source of truth
    (per the §6.5 schema-validated data layer rule).
    """

    def __init__(self, raw: dict) -> None:
        # Stash the raw dict for introspection / debugging.
        self._raw = raw
        # Surface the locked Phase 3 fields as typed attributes.
        # Defaults match the schema's `default` and `enum` values.
        self.id: str = raw["id"]
        self.name: str = raw["name"]
        self.element: str = raw["element"]
        self.level: int = int(raw["level"])
        self.is_base: bool = bool(raw.get("is_base", False))
        self.basic_attack: str = raw["basic_attack"]
        self.tier_1_tech: str = raw["tier_1_tech"]
        self.tier_8_tech: str = raw["tier_8_tech"]
        self.innate: str = raw.get("innate", "none")
        self.sprite: str = raw.get("sprite", "")
        self.portrait: str = raw.get("portrait", "")
        # support_slots: list of (support_id, tier) tuples so
        # support_slots: list of (support_id, max_tier) tuples so
        # downstream code (PartyManager, character screen) can iterate
        # without re-parsing JSON. Per DEC-003a, the on-disk structure
        # is semantic (recruitment/story/final), but the test contract
        # pinned by test_character_data.py is a flat list of 2-tuples
        # (one per support). The semantic structure is exposed on
        # `scene_progression` as a separate property.
        raw_slots = raw.get("support_slots", [])
        self.support_slots: List[Tuple[str, int]] = [
            (slot["support_id"], int(slot["scene_progression"]["final"]["tier"]))
            for slot in raw_slots
        ]
        # scene_progression: rich semantic structure per DEC-003a.
        # List of {support_id, recruitment: {...}, story: {...}, final: {...}}
        # for consumers that need the per-scene tech info.
        self.scene_progression: List[dict] = list(raw_slots)

    @classmethod
    def from_json(
        cls, path: Union[str, Path]
    ) -> "CharacterData":
        """Load a character JSON file and return a CharacterData.

        Raises FileNotFoundError if the path does not exist. The
        §7.3 contract is that the loader fails loudly on bad data
        so a typo in a data path surfaces immediately rather than
        silently producing a half-constructed object.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"character data not found: {p}")
        raw = json.loads(p.read_text(encoding="utf-8"))
        return cls(raw)

    def __repr__(self) -> str:
        return f"CharacterData(id={self.id!r}, element={self.element!r}, level={self.level})"
