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
3. If target is an element:
   a. Pick from phase_3_redesign.element_catalog.elements.{color}[]
   b. Author game/data/elements/{color}/{name_lowercase}.json
4. If target is a chapter:
   a. Pick from the 10-chapter structure in phase_3_redesign.chapter_structure
   b. Author game/data/chapters/{NN}.json
5. Run tools/validate_data.py — must show "X/X files valid"
6. If validation fails, fix the data file (never the schema), re-run
7. Run tools/validate_data.py for full data dir — confirm no regressions
8. Commit: `git add -A && git commit -m "data: add {type}/{id}\n\n[locked source: which section of the design doc]"`
9. Update loop_state.json: mark target as `data_authored`
10. Append to loop_memory.md
11. Send summary
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
