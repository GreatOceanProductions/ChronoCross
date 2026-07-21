# Decisions — Implementation Phase

This file is the batched review queue for the Remaster Engine implementation crons.
The crons surface questions here for you to answer. **Default suggested** means the
cron will use that default and continue if you don't answer within 12 hours.

**Format:**
```
- [ ] [PRIORITY] DEC-NNN: short title | Filed: YYYY-MM-DD
  - Context: why this blocks (which cron is waiting)
  - Options: A | B | C  (when applicable)
  - Default: which option the cron will use on timeout
```

**Priority levels:**
- **P0:** Blocks all forward progress. Fix immediately.
- **P1:** Blocks 1-2 work crons. Fix within 24 hours.
- **P2:** Doesn't block current work. Fix within the week.
- **P3:** Cosmetic. Fix when bored.

**When resolved, replace `[ ]` with `[x]` and add:**
- `Resolved: YYYY-MM-DD` and a one-line note

**The crons that read this file:** `decisions-cron` (every 8h), `planner-cron` (every 4h).

---

## Open Decisions

_(none currently)_

## Resolved Decisions

- [x] [P1] DEC-001: Element resistance chart: 6x6 default matrix | Filed: 2026-07-21 | Resolved: 2026-07-21
  - Resolution: Mirrored pairs (option B). Neutral 1.0, strong 0.5, weak 2.0. Affects data/elements/resistances.json and ElementGrid autoload. With DEC-006's resolution, this becomes 7x7 (adding neutral as a 7th element).

- [x] [P1] DEC-002: Status effect canonical list and IDs | Filed: 2026-07-21 | Resolved: 2026-07-21
  - Resolution: 8 canonical statuses (option A): sleep, poison, burn, freeze, confuse, slow, stop, weaken. Used by tech schema, StatusEffect resource, and TechResolver.

- [x] [P1] DEC-003: Norris support tech tier interpretation | Filed: 2026-07-21 | Resolved: 2026-07-21
  - Resolution: Supports have a 3-tech story-driven unlock progression (NOT just level-based). Each support unlocks 3 techs at story scenes: (1) canon recruitment scene → first tech (tier 2 or 3, prioritizing 3 for late recruits, 2 for early); (2) canon storyline scene → second tech (tier 4 for early recruits, 5 for late); (3) canon final tech/equipment scene → third tech (tier 6 for early recruits, 7 for late). This is RICHER than the level-based tier system. The support_slots.tier field needs to be refactored: it should hold an array of 3 entries, each with {scene_id, tech_id, tier}.
  - **Follow-up:** DEC-003a filed (see Open Decisions) to lock the exact support_slots schema.

- [x] [P2] DEC-004: Stats block (HP, MP, Attack, Defense, Speed, Magic) - schema location | Filed: 2026-07-21 | Resolved: 2026-07-21
  - Resolution: Extend character.schema.json (option A). Add hp/mp/atk/def/spd/mag fields, all integers, required at base level. Runtime scaling (per level) handled by StatResolver autoload.

- [x] [P2] DEC-005: White element innate role (Serge has innate=none - confirm or assign) | Filed: 2026-07-21 | Resolved: 2026-07-21
  - Resolution: NO canon character has an innate feature. Innates come from EQUIPMENT, not from elements. Kid's "steal" comes from her tier 1 tech (pilfer), not from her innate. This means the `innate` field on CharacterData may be vestigial. Recommend removing the field from the schema, OR repurposing it to "innate_source: equipment | tech | none" (where it documents where this character gets its innates from).
  - **Follow-up:** DEC-005a filed (see Open Decisions) to choose between vestigial removal or repurposing.

- [x] [P2] DEC-006: Element file naming and topology (8 elements vs 6 base) | Filed: 2026-07-21 | Resolved: 2026-07-21
  - Resolution: 7 elements total. Six base (red, blue, green, yellow, white, black) plus NEUTRAL as the 7th. Neutral is the default for any physical/non-elemental ability and for Chrono Cross specials (Time Egg etc.). Neutral damage is 1.0 flat. The 6x6 resistance matrix from DEC-001 becomes 7x7 with neutral as a 7th row/column.

- [x] [P1] DEC-007: Augmentation chain walk order and idempotency | Filed: 2026-07-21 | Resolved: 2026-07-21
  - Resolution: Single ordered list with phase field (option A). Each augmentation has {kind, phase: pre|post, params}. Resolver walks the list in array order, applying pre-phase augmentations before damage step and post-phase augmentations after. Pre-augmentations can cancel the damage step (return early). Idempotency rule: each (kind, params_hash) augmentation is applied at most once per tech cast.

---

## Open Decisions (Round 2)

- [ ] [P1] DEC-003a: support_slots schema refactor (3-scene unlock) | Filed: 2026-07-21
  - Context: DEC-003's resolution reveals that support_slots cannot be a single {support_id, tier} pair. Each support has 3 unlocks, each tied to a story scene. Need to lock the new schema before any support data files are authored. Affects all 36 supports across 6 bases.
  - Options:
    A: support_slots: [{support_id, unlocks: [{scene_id, tech_id, tier, level_required?}]}] — array of 3 unlocks per support
    B: support_slots: [{support_id, first_unlock: {scene_id, tech_id, tier}, second_unlock: {...}, third_unlock: {...}}] — named slots
    C: support_slots: [{support_id, scene_progression: {recruitment: {tech_id, tier}, story: {tech_id, tier}, final: {tech_id, tier}}}] — semantic slot names
  - Default: C: semantic slot names (recruitment/story/final) — most readable, matches the user's prose

- [ ] [P2] DEC-005a: innate field — remove or repurpose? | Filed: 2026-07-21
  - Context: DEC-005's resolution says no canon character has an innate; innates come from equipment. The current `innate` field on CharacterData is misleading. Need to decide what to do with it.
  - Options:
    A: Remove `innate` field entirely from schema. Document that innates are equipment-driven in a separate EquipmentData resource.
    B: Repurpose `innate` to `innate_source: enum [equipment, tech, none]`. Still on character but describes where innates come from, not what they are.
    C: Keep `innate` as an enum but make it optional and rare. Most characters have `innate=none`. A few outliers have something specific (e.g., Serge = "white_leader" if we want him to be the player anchor).
  - Default: A: remove entirely. EquipmentData is the cleaner abstraction. Updating the schema is mechanical; the data is regenerated.

- [ ] [P1] DEC-008: element_id enum expansion (add "neutral") | Filed: 2026-07-21
  - Context: DEC-006's resolution added a 7th element: neutral. The character.schema.json, tech.schema.json, and element files all reference element IDs as enums. These enums need to be updated to include "neutral". Affects 3+ schema files and 1 element file. Should be a quick patch.
  - Options:
    A: Add "neutral" to all element_id enums. Mechanical change. Run the validator, fix any character JSONs that reference the old 6-element set.
    B: Make element_id a free-form string with validation against a known-elements list. More flexible for future special elements (Time Egg, etc.).
    C: Defer until a neutral-element character/tech is authored. Until then, no schema change needed.
  - Default: A: add "neutral" to enums now. Quick, mechanical, prevents future blockers.
