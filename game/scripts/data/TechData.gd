class_name TechData
extends RefCounted
## Typed loader for a single `data/techs/<id>.json` file.
##
## Per §7.3 of the design document, every data type in the project
## is a typed data class with a schema-validated JSON loader. This
## is the engine-side implementation of the §15.4 Step 2 data
## layer (TechData). The Python mirror in
## `game/tools/tech_data.py` is the test-side contract; this
## GDScript class is what the actual Godot runtime uses.
##
## The contract pinned by `tests/test_tech_data.py` and
## `tests/test_tech_data_godot.gd`:
##   - `TechData.from_path(path)` returns a TechData or `null` on missing file.
##   - Required schema fields are exposed as typed `@export` properties.
##   - `augmentations` is a list of Dictionaries, one per TechAugmentation
##     (the §7.3 augmentation data model). Empty list (not null) for a
##     basic attack line.
##   - `effects` is a list of Dictionaries, one per TechEffect (the
##     §7.3 effect composition: DAMAGE / HEAL / APPLY_STATUS /
##     REMOVE_STATUS / MODIFY_FIELD).
##   - `base_damage_multiplier` is exposed as a float, default 1.0.
##   - Missing file -> `null` return (loud-fail per §7.3).
##
## Schema reference: `data/schemas/tech.schema.json` (draft-07).
## Field whitelist mirrors the schema's `properties` block.

## Closed set of valid elements per §3.4 + DEC-006/008. 7 elements:
## 6 color (white/red/blue/green/black/yellow) + neutral (for physical,
## basic attacks, and Chrono Cross specials).
enum Element { WHITE, RED, BLUE, GREEN, BLACK, YELLOW, NEUTRAL }

## Closed set of valid target scopes per §7.3 TargetScope enum.
enum TargetScope { SINGLE_ENEMY, ROW, ALL_ENEMIES, ALLY, SELF, ALL_ALLIES, FREE_SLOT }

## Closed set of valid slot kinds per §7.3 slot_kind enum.
enum SlotKind { BASIC_LINE, SUPPORT_FIXED, SUPPORT_PLAYER_CHOICE }

## Closed set of augmentation kinds per §7.3 + DEC-007. Six kinds:
## pre/post-damage status, damage multiplier bonus, on-hit chain,
## MP discount, self buff.
enum AugmentationKind {
	PRE_DAMAGE_STATUS,
	POST_DAMAGE_STATUS,
	DAMAGE_MULTIPLIER_BONUS,
	ON_HIT_CHAIN,
	MP_DISCOUNT,
	SELF_BUFF,
}

## Closed set of effect kinds per §7.3 TechEffect composition.
enum EffectKind { DAMAGE, HEAL, APPLY_STATUS, REMOVE_STATUS, MODIFY_FIELD }

## Closed set of status effects per DEC-002. 8 canonical statuses.
enum StatusId { SLEEP, POISON, BURN, FREEZE, CONFUSE, SLOW, STOP, WEAKEN }

## Closed set of augmentation phases per DEC-007. pre = before the
## damage step, post = after.
enum AugmentationPhase { PRE, POST }

## Lowercase snake_case identifier. Matches `^[a-z][a-z0-9_]*$` per schema.
@export var id: StringName = &""

## Display name shown in UI. 1..48 chars per schema.
@export var display_name: String = ""

## Magic tier slot the tech occupies. 1..8 per §3.4 / §3.8.
@export var tier: int = 1

## Color element. 7-element closed set per DEC-006/008.
@export var element: StringName = &""

## MP cost to execute. 0 for the basic attack line (free); non-zero
## for support techs and tier-8 ultimates.
@export var cost_mp: int = 0

## Multiplier applied to the base damage roll before augmentations
## and the resistance chart. Default 1.0 for an un-augmented basic
## attack.
@export var base_damage_multiplier: float = 1.0

## Whom the tech targets. Closed enum per §7.3.
@export var target_scope: StringName = &""

## How the tech was sourced. BASIC_LINE for a base's locked basic
## attack; SUPPORT_FIXED for a support's locked assignment;
## SUPPORT_PLAYER_CHOICE for the rare open grid slot.
@export var slot_kind: StringName = &""

## List of TechAugmentation entries per §7.3 + DEC-007. Each entry
## is a Dictionary with `kind` (required) and `phase` (required),
## plus optional `chance`, `status`, `value`, `turns`. Empty for the
## basic attack line. Resolver walks the list in array order;
## pre-phase augmentations run before the damage step, post-phase run
## after. Per DEC-007 idempotency rule: each (kind, status, value)
## triple is applied at most once per tech cast.
@export var augmentations: Array = []

## List of TechEffect entries per §7.3. Each entry is a Dictionary
## with `kind` (required) plus optional `magnitude`, `status`,
## `element`. The basic attack line has exactly one DAMAGE effect;
## support techs may add heal/status/modify-field effects on top.
@export var effects: Array = []


## Load a tech JSON file from a Godot resource path and return a
## typed TechData. Returns `null` if the file does not exist.
##
## The signature returns `RefCounted` (the base class) rather than
## `TechData` because Godot 4 GDScript cannot reference its own
## class_name inside a static function signature (GDScript
## resolution-order quirk). The returned value is always a
## TechData instance; callers should assign to a typed `TechData`
## variable which enforces the upcast automatically.
static func from_path(path: String) -> RefCounted:
	if not FileAccess.file_exists(path):
		push_error("TechData: file not found: %s" % path)
		return null
	var f: FileAccess = FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("TechData: cannot open: %s (error %d)" % [path, FileAccess.get_open_error()])
		return null
	var raw_text: String = f.get_as_text()
	f.close()
	var parsed: Variant = JSON.parse_string(raw_text)
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("TechData: top-level JSON is not an object: %s" % path)
		return null
	return from_dict(parsed)


## Construct a TechData from a parsed JSON Dictionary.
##
## This is the §6.4 factory pattern: the only place that touches
## untyped Dictionary values. After `from_dict`, the rest of the
## code works with strongly-typed `@export` properties.
static func from_dict(d: Dictionary) -> RefCounted:
	var t: TechData = (load("res://scripts/data/TechData.gd") as GDScript).new()
	t.id = StringName(String(d.get("id", "")))
	t.display_name = String(d.get("display_name", ""))
	t.tier = int(d.get("tier", 1))
	t.element = StringName(String(d.get("element", "")))
	t.cost_mp = int(d.get("cost_mp", 0))
	t.base_damage_multiplier = float(d.get("base_damage_multiplier", 1.0))
	t.target_scope = StringName(String(d.get("target_scope", "")))
	t.slot_kind = StringName(String(d.get("slot_kind", "")))
	t.augmentations = _normalize_augmentations(d.get("augmentations", []))
	t.effects = _normalize_effects(d.get("effects", []))
	return t


## Normalize the augmentations list to plain Dictionaries. The
## schema's `additionalProperties: false` ensures the shape is
## already a Dictionary, but we copy defensively to decouple
## downstream code from the original JSON reference.
static func _normalize_augmentations(raw: Variant) -> Array:
	var out: Array = []
	if typeof(raw) != TYPE_ARRAY:
		return out
	for entry in raw:
		if typeof(entry) != TYPE_DICTIONARY:
			continue
		out.append((entry as Dictionary).duplicate())
	return out


## Normalize the effects list to plain Dictionaries. Same shape
## rationale as `_normalize_augmentations`.
static func _normalize_effects(raw: Variant) -> Array:
	var out: Array = []
	if typeof(raw) != TYPE_ARRAY:
		return out
	for entry in raw:
		if typeof(entry) != TYPE_DICTIONARY:
			continue
		out.append((entry as Dictionary).duplicate())
	return out


## Look up an augmentation's `kind` field, returning it as a String.
## Convenience accessor for the combat engine so it can switch on
## the kind without re-reading the raw Dictionary.
func augmentation_kind(idx: int) -> String:
	if idx < 0 or idx >= augmentations.size():
		return ""
	var entry: Dictionary = augmentations[idx]
	return String(entry.get("kind", ""))


## Look up an augmentation's `phase` field, returning it as a String.
## Convenience accessor for the resolver's pre/post walker.
func augmentation_phase(idx: int) -> String:
	if idx < 0 or idx >= augmentations.size():
		return ""
	var entry: Dictionary = augmentations[idx]
	return String(entry.get("phase", ""))


## Look up an effect's `kind` field, returning it as a String.
## Convenience accessor for the combat engine.
func effect_kind(idx: int) -> String:
	if idx < 0 or idx >= effects.size():
		return ""
	var entry: Dictionary = effects[idx]
	return String(entry.get("kind", ""))


## Human-readable string for debug logging. Includes id, tier, element.
func _to_string() -> String:
	return "TechData(id=%s, tier=%d, element=%s)" % [String(id), tier, String(element)]
