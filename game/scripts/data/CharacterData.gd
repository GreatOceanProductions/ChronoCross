class_name CharacterData
extends RefCounted
## Typed loader for a single `data/characters/<id>.json` file.
##
## Per §7.3 of the design document, every data type in the project
## is a typed data class with a schema-validated JSON loader. This
## is the engine-side implementation of the §15.4 Step 1 data
## layer (CharacterData). The Python mirror in
## `game/tools/character_data.py` is the test-side contract; this
## GDScript class is what the actual Godot runtime uses.
##
## The contract pinned by `tests/test_character_data.py` and
## `tests/test_character_data_godot.gd`:
##   - `CharacterData.from_path(path)` returns a CharacterData or `null` on missing file.
##   - Required schema fields are exposed as typed `@export` properties.
##   - `support_slots` is a list of Dictionaries `{ "support_id": String, "tier": int }`.
##     Per DEC-003a, the on-disk structure is semantic (recruitment/story/final),
##     but the loader flattens to a list of (support_id, tier) for backward compat.
##   - Missing file -> `null` return (loud-fail per §7.3).
##
## Schema reference: `data/schemas/character.schema.json` (draft-07).
## Field whitelist mirrors the schema's `properties` block.

## Closed set of valid elements per §3.4 + DEC-006/008. 7 elements:
## 6 color (white/red/blue/green/black/yellow) + neutral (for physical,
## basic attacks weak/medium/heavy, and Chrono Cross specials).
enum Element { WHITE, RED, BLUE, GREEN, BLACK, YELLOW, NEUTRAL }

## Closed set of valid innate roles per §3.4 element-tier mapping.
## Per DEC-005/005a: playable characters always have NONE; enemies use
## these enums to describe their behavior pattern.
enum InnateRole { STEAL, PERFORMANCE, COMBAT, DARK, HEALER, NONE }

## Lowercase identifier. Matches `^[a-z][a-z0-9_]*$` per schema.
@export var id: StringName = &""

## Display name shown in UI. 1-32 chars per schema.
@export var name: String = ""

## Color element. Lowercase canonical form matching the JSON value.
## 7-element closed set per DEC-006/008.
@export var element: StringName = &""

## Current level. 1..99.
@export var level: int = 1

## True if this is one of the 6 main bases. False for support characters.
@export var is_base: bool = false

## Base stats for the character. Per DEC-004, stats live on the character.
## Runtime scaling (per level) handled by StatResolver autoload.
@export var stats: Dictionary = {}

## Display name of the basic attack line. Per §3.5, matches tier_1_tech.
@export var basic_attack: String = ""

## Display name of the tier 1 tech (the basic attack line's tier-1 form).
@export var tier_1_tech: String = ""

## Display name of the tier 8 ultimate.
@export var tier_8_tech: String = ""

## Innate role. Per DEC-005/005a: "none" for playable characters,
## behavior enum for enemies.
@export var innate: StringName = &"none"

## Flat list of support characters. Per DEC-003a, the on-disk structure
## is semantic (recruitment/story/final scene_progression) but the
## loader flattens to (support_id, max_tier) where max_tier is the
## `final` scene's tier. The semantic structure is exposed on
## `scene_progression` as a separate property.
@export var support_slots: Array[Dictionary] = []

## Rich semantic structure per DEC-003a: each support has 3 scene
## unlocks (recruitment/story/final). List of Dictionaries preserving
## the full structure for consumers that need per-scene tech info.
@export var scene_progression: Array[Dictionary] = []

## Path to the character's field sprite.
@export var sprite: String = ""

## Path to the character's portrait.
@export var portrait: String = ""


## Load a character JSON file from a Godot resource path and return
## a typed CharacterData. Returns `null` if the file does not exist.
##
## The signature returns `RefCounted` (the base class) rather than
## `CharacterData` because Godot 4 GDScript cannot reference its own
## class_name inside a static function signature (GDScript
## resolution-order quirk). The returned value is always a
## CharacterData instance; callers should assign to a typed
## `CharacterData` variable which enforces the upcast automatically.
static func from_path(path: String) -> RefCounted:
	if not FileAccess.file_exists(path):
		push_error("CharacterData: file not found: %s" % path)
		return null
	var f: FileAccess = FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("CharacterData: cannot open: %s (error %d)" % [path, FileAccess.get_open_error()])
		return null
	var raw_text: String = f.get_as_text()
	f.close()
	var parsed: Variant = JSON.parse_string(raw_text)
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("CharacterData: top-level JSON is not an object: %s" % path)
		return null
	return from_dict(parsed)


## Construct a CharacterData from a parsed JSON Dictionary.
##
## This is the §6.4 factory pattern: the only place that touches
## untyped Dictionary values. After `from_dict`, the rest of the
## code works with strongly-typed `@export` properties.
static func from_dict(d: Dictionary) -> RefCounted:
	var c: CharacterData = (load("res://scripts/data/CharacterData.gd") as GDScript).new()
	c.id = StringName(String(d.get("id", "")))
	c.name = String(d.get("name", ""))
	c.element = StringName(String(d.get("element", "")))
	c.level = int(d.get("level", 1))
	c.is_base = bool(d.get("is_base", false))
	c.basic_attack = String(d.get("basic_attack", ""))
	c.tier_1_tech = String(d.get("tier_1_tech", ""))
	c.tier_8_tech = String(d.get("tier_8_tech", ""))
	c.innate = StringName(String(d.get("innate", "none")))
	c.sprite = String(d.get("sprite", ""))
	c.portrait = String(d.get("portrait", ""))
	c.stats = d.get("stats", {})
	var raw_slots = d.get("support_slots", [])
	c.support_slots = _parse_support_slots_flat(raw_slots)
	c.scene_progression = _parse_scene_progression(raw_slots)
	return c


## Flatten semantic scene_progression into (support_id, max_tier) list.
## Per DEC-003a, the on-disk structure is semantic; this preserves the
## pre-DEC-003a test contract that consumers iterate over
## (support_id, tier) pairs.
static func _parse_support_slots_flat(raw: Variant) -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	if typeof(raw) != TYPE_ARRAY:
		return out
	for entry in raw:
		if typeof(entry) != TYPE_DICTIONARY:
			continue
		var entry_dict: Dictionary = entry
		if not entry_dict.has("support_id") or not entry_dict.has("scene_progression"):
			continue
		var sp: Dictionary = entry_dict["scene_progression"]
		var max_tier: int = 0
		for scene in ["recruitment", "story", "final"]:
			if sp.has(scene) and typeof(sp[scene]) == TYPE_DICTIONARY and sp[scene].has("tier"):
				max_tier = max(max_tier, int(sp[scene]["tier"]))
		out.append({
			"support_id": String(entry_dict["support_id"]),
			"tier": max_tier,
		})
	return out


## Preserve the full semantic structure for consumers that need it.
static func _parse_scene_progression(raw: Variant) -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	if typeof(raw) != TYPE_ARRAY:
		return out
	for entry in raw:
		if typeof(entry) != TYPE_DICTIONARY:
			continue
		var entry_dict: Dictionary = entry
		if not entry_dict.has("support_id") or not entry_dict.has("scene_progression"):
			continue
		out.append({
			"support_id": String(entry_dict["support_id"]),
			"scene_progression": entry_dict["scene_progression"],
		})
	return out


## Human-readable string for debug logging. Includes id, element, level.
func _to_string() -> String:
	return "CharacterData(id=%s, element=%s, level=%d)" % [String(id), String(element), level]
