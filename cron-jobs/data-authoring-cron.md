bash.exe: warning: could not find /tmp, please create!
bash.exe: warning: could not find /tmp, please create!
bash.exe: warning: could not find /tmp, please create!
# Data Authoring Cron Job

**Job ID:** `data-authoring-cron`
**Schedule:** Every 2 hours
**Purpose:** Author one new data file (character, element, map, chapter) per run, validated against schema.

---

## ROLE

You are an agent running one cycle of the data authoring loop. Per §8.4 of the design document, **one script per character / per tech (extreme granularity)**. Per §8.5, every data file is schema-validated before it enters the codebase. Your job is to author **one data file** per run, validate it, and commit.

## WORKING SET — Read in This Order

1. **State first** — `D:\Game Design\Remaster Engine\loop_state.json` (see `data_cron.target_type`, `data_cron.target_id`, `data_cron.last_data_authored`)
2. **Schemas** — `D:\Game Design\Remaster Engine\game\data\schemas\` (the contract for valid data)
3. **Existing data files** — `D:\Game Design\Remaster Engine\game\data\characters\`, `elements\`, `maps\`, `chapters\`
4. **Element catalog** — `D:\Game Design\Remaster Engine\loop_state.json.phase_3_redesign.element_catalog` (126 elements across 7 groups — this is the source data for element JSON files)
5. **Lock decisions** — `D:\Game Design\Remaster Engine\loop_state.json.locked_design` and `phase_3_redesign.bases` (the locked 6 bases with their tier 1/8 techs)
6. **Spec** — `D:\Game Design\Remaster Engine\remaster_engine_design_spec.md` §3 (Redesign Vision) for the locked 6 bases + 36 supports; §12 (Walkthrough) for chapter structure

## ERROR-HANDLING EXTENSION

Before authoring new data:

```
1. Read D:\Game Design\Remaster Engine\game\ISSUES.md
2. If "data file fails validation" issues exist:
   a. Read the broken file
   b. Identify the schema mismatch
   c. Fix the data (NOT the schema — schema is the contract)
   d. Run tools/validate_data.py to confirm
   e. Commit: "fix: [data file] schema compliance"
   f. Update ISSUES.md
3. Only proceed to new data after all existing files validate
```

## PROTOCOL

```
1. Determine target: from `data_cron.target_id` in state, or pick the next unlocked character/element/map/chapter
2. If target is a character:
   a. Read §3 locked design: which base or support is this?
   b. Get the character's locked techs (tier 1 and tier 8) from phase_3_redesign.bases or phase_3_redesign.locked_techs_per_base
   c. Get support slots if it's a base (from phase_3_redesign.bases[i].supports)
   d. Author game/data/characters/{id}.json matching character.schema.json
3. If target is a spell/tech (the protocol calls these "elements" per the original Chrono Cross vocabulary where individual spells are "elements"; the data layer calls them techs):
   a. Pick from phase_3_redesign.element_catalog.elements.{color}[]
   b. Author game/data/techs/{name_lowercase}.json (per the §6.5 schema/validator; the DIR_TO_SCHEMA map in tools/validate_data.py routes techs to data/techs/, not data/elements/). Each catalog entry is a TechData, not an ElementData. Use cost_mp and base_damage_multiplier as conservative defaults (the locked design does not specify these per-tech numbers; tier 1 damage spells = 3 MP / 1.2x, tier 1 heals = 4 MP, etc.).
   c. The data/elements/ directory is reserved for the 7 element meta-definitions (id/display_name/color_hex/resistances per element.schema.json). Do NOT author spell JSON there — it will fail validation because the schema requires the 7-element enum and the resistance map, not individual spell fields.
4. If target is an element meta-definition (one of the 7 locked color elements):
   a. Author game/data/elements/{id}.json (id ∈ white, red, blue, green, yellow, black, neutral)
   b. Fields per element.schema.json: id, display_name, color_hex, base_damage_type, resistances (mirrored pair chart per DEC-001: 2.0 strong / 0.5 weak / 1.0 neutral; neutral element is all 1.0)
5. If target is a chapter:
   a. Pick from the 10-chapter structure in phase_3_redesign.chapter_structure
   b. Author game/data/chapters/{NN}.json
6. Run tools/validate_data.py — must show "X/X files valid"
7. If validation fails, fix the data file (never the schema), re-run
8. Run tools/validate_data.py for full data dir — confirm no regressions
9. Commit: `git add -A && git commit -m "data: add {type}/{id}\n\n[locked source: which section of the design doc]"`
10. Update loop_state.json: mark target as `data_authored`
11. Append to loop_memory.md
12. Send summary
```

## HARD CONSTRAINTS

- **One file per cycle.** Resist bulk data dumps. Each file is a commit.
- **Data must come from locked design.** Never invent new techs/elements/characters. The `phase_3_redesign` data is the source of truth.
- **Schema is the contract.** If a data file doesn't fit, fix the data, not the schema.
- **Validate before commit.** A commit that breaks the data pipeline is a §13.3 F-2 design-drift failure.
- **No empty placeholder data.** If a field is required, fill it. Use empty strings for `sprite`/`portrait` only when the PoC scope permits.

## WHEN TO BE IDLE

If all 6 bases + 36 supports + 126 elements + 10 chapters are authored and validated:
- Log idle
- Send: "Data authoring cycle N — idle, all locked data authored and validated."

## OUTPUTS

- One new data file in `D:\Game Design\Remaster Engine\game\data\`
- Validation passing for all data
- One git commit
- Updated state and memory
- Summary message
