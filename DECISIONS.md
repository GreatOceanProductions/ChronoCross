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

- [x] [P2] DEC-004: Stats block (HP, MP, Attack, Defense, Speed, Magic) - schema location | Filed: 2026-07-21 | Resolved: 2026-07-21
  - Resolution: Extend character.schema.json (option A). Add hp/mp/atk/def/spd/mag fields, all integers, required at base level. Runtime scaling (per level) handled by StatResolver autoload.

- [x] [P2] DEC-005: White element innate role (Serge has innate=none - confirm or assign) | Filed: 2026-07-21 | Resolved: 2026-07-21
  - Resolution: NO canon character has an innate feature. Innates come from EQUIPMENT, not from elements. Kid's "steal" comes from her tier 1 tech (pilfer), not from her innate. The `innate` field is for ENEMIES (their behavior-driven AI), not for playable characters.

- [x] [P2] DEC-006: Element file naming and topology (8 elements vs 6 base) | Filed: 2026-07-21 | Resolved: 2026-07-21
  - Resolution: 7 elements total. Six base (red, blue, green, yellow, white, black) plus NEUTRAL as the 7th. Neutral is the default for any physical/non-elemental ability, basic attacks (weak/medium/heavy), and Chrono Cross specials (Time Egg etc.). Neutral damage is 1.0 flat. The 6x6 resistance matrix from DEC-001 becomes 7x7 with neutral as a 7th row/column.

- [x] [P1] DEC-007: Augmentation chain walk order and idempotency | Filed: 2026-07-21 | Resolved: 2026-07-21
  - Resolution: Single ordered list with phase field (option A). Each augmentation has {kind, phase: pre|post, params}. Resolver walks the list in array order, applying pre-phase augmentations before damage step and post-phase augmentations after. Pre-augmentations can cancel the damage step (return early). Idempotency rule: each (kind, params_hash) augmentation is applied at most once per tech cast.

- [x] [P1] DEC-003a: support_slots schema refactor (3-scene unlock) | Filed: 2026-07-21 | Resolved: 2026-07-21
  - Resolution: SEMANTIC slot names (option C). Each support has 3 slots named for the story beat that unlocks them: `recruitment` (canon recruitment scene → first tech), `story` (canon storyline scene → second tech), `final` (canon final event, often unlocks final tech or equipment that provides final tech). Schema: `support_slots: [{support_id, scene_progression: {recruitment: {tech_id, tier, level_required?}, story: {...}, final: {...}}}]`. The semantic names also make the story correspondence visually obvious in the data file.

- [x] [P2] DEC-005a: innate field — remove or repurpose? | Filed: 2026-07-21 | Resolved: 2026-07-21
  - Resolution: KEEP the `innate` field. Playable characters: `innate: "none"` (innates come from equipment, per DEC-005). Enemies: `innate` describes their behavior pattern (steal/performance/combat/dark/healer). Same field, different meaning per character type. Future EnemyData schema will formalize this split. For now, character.schema.json `innate` accepts both `"none"` (playable default) and the behavior enums (enemy default).

- [x] [P1] DEC-008: element_id enum expansion (add "neutral") | Filed: 2026-07-21 | Resolved: 2026-07-21
  - Resolution: Add "neutral" to all element_id enums (option A, already applied in previous migration). Neutral is the default for basic attacks (weak/medium/heavy) and physical attacks. 7 elements total in the closed enum: white, red, blue, green, yellow, black, neutral.

---

## Open Decisions (Round 3)

_(none currently — system is unblocked)_
