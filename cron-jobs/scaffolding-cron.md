# Scaffolding Cron Job

**Job ID:** `scaffolding-cron`
**Schedule:** Every 6 hours
**Purpose:** Author architecture-level files (autoloads, scenes, system glue). One file per run, TDD-style.

---

## ROLE

You are an agent running one cycle of the scaffolding loop. Per §6.3 of the design document, the Godot 4.3 directory structure is `data/`, `scripts/`, `scenes/`, `tests/`, `tools/`. Per §7, the autoloads are: `Determinism.gd`, `PartyManager.gd`, `TechResolver.gd`, `ChapterController.gd`, `SaveSystem.gd`. Your job is to author **one architecture file** per run, with its corresponding test.

## WORKING SET — Read in This Order

1. **State** — `D:\Game Design\Remaster Engine\loop_state.json` (see `scaffolding_cron.target_file`, `scaffolding_cron.last_scaffold_authored`)
2. **Existing scripts** — `D:\Game Design\Remaster Engine\game\scripts\` and `scripts/autoloads\`
3. **Existing scenes** — `D:\Game Design\Remaster Engine\game\scenes\`
4. **Spec** — `D:\Game Design\Remaster Engine\remaster_engine_design_spec.md` §6 (Godot 4 Deep Dive) and §7 (Engine Modifications)
5. **Locked data** — `D:\Game Design\Remaster Engine\loop_state.json.locked_design`

## ERROR-HANDLING EXTENSION

Before authoring new scaffolding:

```
1. Read D:\Game Design\Remaster Engine\game\ISSUES.md
2. If "scaffolding file broken" or "test framework broken" issues exist:
   a. Fix those first
3. Only proceed to new scaffolding after all bugs fixed
```

## PROTOCOL

```
1. Pick the next autoload to author (from the list above) or the next scene
2. If it's a GDScript autoload:
   a. Author scripts/autoloads/{name}.gd with static typing per §6.4
   b. Author a corresponding test in tests/test_{name}.py
   c. If the test requires Godot to run (e.g., scene tests), document the headless invocation
3. If it's a scene:
   a. Author scenes/{name}.tscn (text format)
   b. Author a corresponding test
4. Run tools/run_tests.sh (or godot --headless for scene tests) — must pass
5. Commit
6. Update state and memory
7. Send summary
```

## HARD CONSTRAINTS

- **One file per cycle.** Architecture files are large. Don't try to do two.
- **Static typing required.** Per §6.4 locked decision: `var x: int = 0`, not `var x = 0`.
- **No business logic in autoloads.** Autoloads wire up systems. Business logic goes in scripts/data/ or scripts/combat/.
- **Test every autoload.** A scaffolded autoload without a test is a §13.3 F-1 architecture-vaporware risk.
- **Don't break the data layer.** If your scaffold imports CharacterData, use the same JSON shape as the data files.

## ORDER OF OPERATIONS (Recommended Sequence)

Per §15.4 of the design document, the scaffold order is:

1. `CharacterData.gd` — loads `data/characters/*.json` into typed resources
2. `TechData.gd` — loads `data/elements/*/*.json` into typed resources
3. `PartyManager.gd` — autoload, tracks active roster
4. `Determinism.gd` — autoload, derived PRNGs per tag
5. `TechResolver.gd` — applies a tech in combat
6. `CombatSimulator.gd` — state machine for one combat encounter
7. `ChapterController.gd` — loads and plays a chapter
8. `SaveSystem.gd` — save/load with schema_version
9. Scene files: `character_screen.tscn`, `map.tscn`, `battle.tscn`, `main_menu.tscn`

Don't skip ahead. Each layer depends on the previous.

## WHEN TO BE IDLE

If all 9 architecture files are authored and tested:
- Log idle
- Send: "Scaffolding cycle N — idle, all locked architecture files authored and tested."

## OUTPUTS

- One new GDScript file (or scene) in `D:\Game Design\Remaster Engine\game\`
- One new test file
- One git commit
- Updated state and memory
- Summary message
