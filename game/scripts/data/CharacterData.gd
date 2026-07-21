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
##   - Missing file -> `null` return (loud-fail per §7.3).
##
## Schema reference: `data/schemas/character.schema.json` (draft-07).
## Field whitelist mirrors the schema's `properties` block.

## Closed set of valid elements per §3.4 + character.schema.json enum.
enum Element { WHITE, RED, BLUE, GREEN, BLACK, YELLOW }

## Closed set of valid innate roles per §3.4 element-tier mapping.
enum InnateRole { STEAL, PERFORMANCE, COMBAT, DARK, HEALER, NONE }

## Lowercase identifier. Matches `^[a-z][a-z0-9_]*$` per schema.
@export var id: StringName = &""

## Display name shown in UI. 1-32 chars per schema.
@export var name: String = ""

## Color element. Lowercase canonical form matching the JSON value.
@export var element: StringName = &""

## Current level. 1..99.
@export var level: int = 1

## True if this is one of the 6 main bases. False for support characters.
@export var is_base: bool = false

## Display name of the basic attack line.
@export var basic_attack: String = ""

## Tier 1 magic slot tech.
@export var tier_1_tech: String = ""

## Tier 8 magic slot tech (the ultimate).
@export var tier_8_tech: String = ""

## Innate role. Default "none" matches schema default.
@export var innate: StringName = &"none"

## List of support characters attached to this base at specific tiers.
## Each entry is a Dictionary `{ "support_id": String, "tier": int }`.
@export var support_slots: Array[Dictionary] = []

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
	c.support_slots = _parse_support_slots(d.get("support_slots", []))
	return c


## Convert the JSON `support_slots` array into a typed `Array[Dictionary]`.
## Returns an empty array if the input is missing or malformed.
static func _parse_support_slots(raw: Variant) -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	if typeof(raw) != TYPE_ARRAY:
		return out
	for entry in raw:
		if typeof(entry) != TYPE_DICTIONARY:
			continue
		var entry_dict: Dictionary = entry
		if not entry_dict.has("support_id") or not entry_dict.has("tier"):
			continue
		out.append({
			"support_id": String(entry_dict["support_id"]),
			"tier": int(entry_dict["tier"]),
		})
	return out


## Human-readable string for debug logging. Includes id, element, level.
func _to_string() -> String:
	return "CharacterData(id=%s, element=%s, level=%d)" % [String(id), String(element), level]
