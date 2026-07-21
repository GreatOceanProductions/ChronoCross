extends SceneTree
## Headless GDScript test for TechData.gd (§7.3, §15.4 step 2).
##
## Mirrors the contract pinned by tests/test_tech_data.py (the
## Python mirror) but executes in the actual Godot 4.3 runtime. This
## is the §13.3 F-1 "architecture-vaporware" guard: the Python
## mirror proves the data shape, this GDScript test proves the
## engine-side implementation can be loaded and used by the Godot
## runtime.
##
## Run (from game/):
##     godot --headless --path . --script res://tests/test_tech_data_godot.gd
##
## Exit code 0 = all checks passed; non-zero = at least one failure.
## On failure, the script prints a line starting with "FAIL:".

var TechDataScript: Resource = load("res://scripts/data/TechData.gd")

var _failures: int = 0


func _initialize() -> void:
	_run_all_checks()
	if _failures == 0:
		print("PASS: test_tech_data_godot (TechData.gd) — all checks green")
		quit(0)
	else:
		print("FAIL: test_tech_data_godot — %d check(s) failed" % _failures)
		quit(1)


func _check(condition: bool, label: String) -> void:
	if not condition:
		_failures += 1
		printerr("FAIL: test_tech_data_godot — %s" % label)


func _run_all_checks() -> void:
	# 1. Module is loadable as a script.
	_check(TechDataScript != null, "TechData.gd load() returned null")

	# 2. The class can be instantiated.
	var instance: RefCounted = TechDataScript.new()
	_check(instance != null, "TechData.new() returned null")

	# 3. The class has the locked §7.3 fields (typed properties exist).
	# NOTE: Godot 4.3 typed-array declarations on class-body variables
	# are not allowed (4.4 feature); we use untyped Array per the same
	# convention as CharacterData.gd.
	var props: Array = instance.get_property_list()
	var prop_names: Array = []
	for p in props:
		prop_names.append(String(p.get("name", "")))
	_check("id" in prop_names, "TechData missing 'id' property")
	_check("display_name" in prop_names, "TechData missing 'display_name' property")
	_check("tier" in prop_names, "TechData missing 'tier' property")
	_check("element" in prop_names, "TechData missing 'element' property")
	_check("cost_mp" in prop_names, "TechData missing 'cost_mp' property")
	_check("base_damage_multiplier" in prop_names, "TechData missing 'base_damage_multiplier' property")
	_check("target_scope" in prop_names, "TechData missing 'target_scope' property")
	_check("slot_kind" in prop_names, "TechData missing 'slot_kind' property")
	_check("augmentations" in prop_names, "TechData missing 'augmentations' property")
	_check("effects" in prop_names, "TechData missing 'effects' property")

	# 4. The loader method exists.
	_check(TechDataScript.has_method("from_path"),
		"TechData missing 'from_path(path)' factory method")
	_check(TechDataScript.has_method("from_dict"),
		"TechData missing 'from_dict(d)' factory method")

	# 5. Loading a real tech file works and surfaces the locked
	# Phase 3 values for Serge's tier-1 basic attack.
	var dash: RefCounted = TechDataScript.call("from_path", "res://data/techs/dash_and_slash.json")
	_check(dash != null, "from_path(dash_and_slash.json) returned null")
	if dash != null:
		_check(dash.id == &"dash_and_slash", "dash.id expected &dash_and_slash, got %s" % str(dash.id))
		_check(dash.display_name == "Dash and Slash",
			"dash.display_name expected 'Dash and Slash', got '%s'" % str(dash.display_name))
		_check(dash.tier == 1, "dash.tier expected 1, got %s" % str(dash.tier))
		_check(dash.element == &"white", "dash.element expected &white, got %s" % str(dash.element))
		_check(dash.target_scope == &"SINGLE_ENEMY",
			"dash.target_scope expected &SINGLE_ENEMY, got %s" % str(dash.target_scope))
		_check(dash.slot_kind == &"BASIC_LINE",
			"dash.slot_kind expected &BASIC_LINE, got %s" % str(dash.slot_kind))
		_check(is_equal_approx(dash.base_damage_multiplier, 1.0),
			"dash.base_damage_multiplier expected 1.0, got %s" % str(dash.base_damage_multiplier))

	# 6. Augmentations is an empty list (not null) for a basic attack
	# line — the combat engine must be able to iterate it without a
	# None check, per §7.3.
	_check(dash.augmentations != null, "dash.augmentations is null (should be empty list)")
	if dash != null and dash.augmentations != null:
		_check(dash.augmentations.size() == 0,
			"dash.augmentations expected empty, got size %d" % dash.augmentations.size())

	# 7. Effects carries the basic-line DAMAGE entry per §7.3.
	_check(dash.effects != null, "dash.effects is null (should be list)")
	if dash != null and dash.effects != null:
		_check(dash.effects.size() == 1,
			"dash.effects expected size 1 (DAMAGE), got %d" % dash.effects.size())
		if dash.effects.size() >= 1:
			var eff: Dictionary = dash.effects[0]
			_check(String(eff.get("kind", "")) == "DAMAGE",
				"dash.effects[0].kind expected 'DAMAGE', got '%s'" % str(eff.get("kind", "")))
			_check(String(eff.get("element", "")) == "white",
				"dash.effects[0].element expected 'white', got '%s'" % str(eff.get("element", "")))

	# 8. Missing file returns null — loud failure per §7.3.
	var missing: RefCounted = TechDataScript.call("from_path", "res://data/techs/does_not_exist.json")
	_check(missing == null, "from_path on missing file should return null, got %s" % str(missing))

	# 9. from_dict factory works directly (used by TechResolver and
	# the battle preload pipeline when techs are inlined as JSON in
	# save files or scene scripts).
	var inlined: RefCounted = TechDataScript.call("from_dict", {
		"id": "test_inline",
		"display_name": "Test Inline",
		"tier": 1,
		"element": "neutral",
		"target_scope": "SELF",
		"slot_kind": "BASIC_LINE",
		"base_damage_multiplier": 1.5,
	})
	_check(inlined != null, "from_dict returned null for inlined dict")
	if inlined != null:
		_check(inlined.id == &"test_inline",
			"inlined.id expected &test_inline, got %s" % str(inlined.id))
		_check(inlined.element == &"neutral",
			"inlined.element expected &neutral, got %s" % str(inlined.element))
		_check(inlined.target_scope == &"SELF",
			"inlined.target_scope expected &SELF, got %s" % str(inlined.target_scope))
		_check(is_equal_approx(inlined.base_damage_multiplier, 1.5),
			"inlined.base_damage_multiplier expected 1.5, got %s" % str(inlined.base_damage_multiplier))
		_check(inlined.cost_mp == 0,
			"inlined.cost_mp expected 0 (default), got %s" % str(inlined.cost_mp))

	# 10. Augmentation normalization: a tech with an augmentation
	# entry should preserve the (kind, phase) pair through from_path.
	# Build an inline-only tech via from_dict (no on-disk file).
	var augd: RefCounted = TechDataScript.call("from_dict", {
		"id": "test_aug",
		"display_name": "Test Aug",
		"tier": 1,
		"element": "white",
		"target_scope": "SINGLE_ENEMY",
		"slot_kind": "BASIC_LINE",
		"base_damage_multiplier": 1.0,
		"augmentations": [
			{"kind": "POST_DAMAGE_STATUS", "phase": "post", "status": "poison", "chance": 0.5, "turns": 3},
		],
	})
	_check(augd != null, "from_dict (with augmentations) returned null")
	if augd != null:
		_check(augd.augmentations.size() == 1,
			"augd.augmentations expected size 1, got %d" % augd.augmentations.size())
		if augd.augmentations.size() >= 1:
			var aug_entry: Dictionary = augd.augmentations[0]
			_check(String(aug_entry.get("kind", "")) == "POST_DAMAGE_STATUS",
				"augd.augmentations[0].kind expected 'POST_DAMAGE_STATUS', got '%s'" % str(aug_entry.get("kind", "")))
			_check(String(aug_entry.get("phase", "")) == "post",
				"augd.augmentations[0].phase expected 'post', got '%s'" % str(aug_entry.get("phase", "")))
			_check(String(aug_entry.get("status", "")) == "poison",
				"augd.augmentations[0].status expected 'poison', got '%s'" % str(aug_entry.get("status", "")))
