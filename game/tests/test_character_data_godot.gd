bash.exe: warning: could not find /tmp, please create!
extends SceneTree
## Headless GDScript test for CharacterData.gd (§7.3, §15.4 step 1).
##
## Mirrors the contract pinned by tests/test_character_data.py (the
## Python mirror) but executes in the actual Godot 4.3 runtime. This
## is the §13.3 F-1 "architecture-vaporware" guard: the Python
## mirror proves the data shape, this GDScript test proves the
## engine-side implementation can be loaded and used by the Godot
## runtime.
##
## Run (from game/):
##     godot --headless --path . --script res://tests/test_character_data_godot.gd
##
## Exit code 0 = all checks passed; non-zero = at least one failure.
## On failure, the script prints a line starting with "FAIL:".
##
## Note: we use `load(...)` + `call(...)` rather than
## `preload(...)` + typed access because GDScript's static type
## system cannot reference a class by its own class_name from
## inside a test script that also has that name conflict.

var CharacterDataScript: Resource = load("res://scripts/data/CharacterData.gd")

var _failures: int = 0


func _initialize() -> void:
	_run_all_checks()
	if _failures == 0:
		print("PASS: test_character_data_godot (CharacterData.gd) — all checks green")
		quit(0)
	else:
		print("FAIL: test_character_data_godot — %d check(s) failed" % _failures)
		quit(1)


func _check(condition: bool, label: String) -> void:
	if not condition:
		_failures += 1
		printerr("FAIL: test_character_data_godot — %s" % label)


func _run_all_checks() -> void:
	# 1. Module is loadable as a script.
	_check(CharacterDataScript != null, "CharacterData.gd load() returned null")

	# 2. The class can be instantiated.
	var instance: RefCounted = CharacterDataScript.new()
	_check(instance != null, "CharacterData.new() returned null")

	# 3. The class has the locked Phase 3 fields (typed properties exist).
	var props: Array = instance.get_property_list()
	var prop_names: Array[String] = []
	for p in props:
		prop_names.append(String(p.get("name", "")))
	_check("id" in prop_names, "CharacterData missing 'id' property")
	_check("name" in prop_names, "CharacterData missing 'name' property")
	_check("element" in prop_names, "CharacterData missing 'element' property")
	_check("level" in prop_names, "CharacterData missing 'level' property")
	_check("is_base" in prop_names, "CharacterData missing 'is_base' property")
	_check("basic_attack" in prop_names, "CharacterData missing 'basic_attack' property")
	_check("tier_1_tech" in prop_names, "CharacterData missing 'tier_1_tech' property")
	_check("tier_8_tech" in prop_names, "CharacterData missing 'tier_8_tech' property")
	_check("innate" in prop_names, "CharacterData missing 'innate' property")

	# 4. The loader method exists.
	_check(CharacterDataScript.has_method("from_path"),
		"CharacterData missing 'from_path(path)' factory method")

	# 5. Loading a real character file works and surfaces Phase 3 values.
	var serge: RefCounted = CharacterDataScript.call("from_path", "res://data/characters/serge.json")
	_check(serge != null, "from_path(serge.json) returned null")
	if serge != null:
		_check(serge.id == &"serge", "serge.id expected &serge, got %s" % str(serge.id))
		_check(serge.name == "Serge", "serge.name expected 'Serge', got '%s'" % str(serge.name))
		_check(serge.element == &"white", "serge.element expected &white, got %s" % str(serge.element))
		_check(serge.is_base == true, "serge.is_base expected True, got %s" % str(serge.is_base))
		_check(serge.basic_attack == "Dash and Slash",
			"serge.basic_attack expected 'Dash and Slash', got '%s'" % str(serge.basic_attack))
		_check(serge.tier_1_tech == "Dash and Slash",
			"serge.tier_1_tech expected 'Dash and Slash', got '%s'" % str(serge.tier_1_tech))
		_check(serge.tier_8_tech == "Glide Hook",
			"serge.tier_8_tech expected 'Glide Hook', got '%s'" % str(serge.tier_8_tech))
		_check(serge.level == 1, "serge.level expected 1, got %s" % str(serge.level))

	# 6. Kidd loads and exposes the locked 'steal' innate.
	var kidd: RefCounted = CharacterDataScript.call("from_path", "res://data/characters/kidd.json")
	_check(kidd != null, "from_path(kidd.json) returned null")
	if kidd != null:
		_check(kidd.id == &"kidd", "kidd.id expected &kidd, got %s" % str(kidd.id))
		_check(kidd.element == &"red", "kidd.element expected &red, got %s" % str(kidd.element))
		_check(kidd.innate == &"steal", "kidd.innate expected &steal, got %s" % str(kidd.innate))

	# 7. Nikki loads and exposes the combined unit 'korcha_macha'.
	var nikki: RefCounted = CharacterDataScript.call("from_path", "res://data/characters/nikki.json")
	_check(nikki != null, "from_path(nikki.json) returned null")
	if nikki != null:
		_check(nikki.element == &"blue", "nikki.element expected &blue, got %s" % str(nikki.element))
		var support_ids: Array[String] = []
		for slot in nikki.support_slots:
			var slot_dict: Dictionary = slot
			support_ids.append(String(slot_dict.get("support_id", "")))
		_check("korcha_macha" in support_ids,
			"nikki.support_slots missing 'korcha_macha' (combined unit)")

	# 8. Missing file returns null — loud failure per §7.3.
	var missing: RefCounted = CharacterDataScript.call("from_path", "res://data/characters/does_not_exist.json")
	_check(missing == null, "from_path on missing file should return null, got %s" % str(missing))
