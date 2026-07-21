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

- [ ] [P1] DEC-001: Element resistance chart: 6x6 default matrix | Filed: 2026-07-21T09:06:49.991126+00:00
  - Context: The data-cron will need to author the 6x6 element resistance chart next (per spec section 7.4). The spec says it follows the original Chrono Cross chart with a hexagonal strong/weak graph (each element strong vs 2, weak vs 2, neutral vs 2 incl. self). The original chart is not perfectly canonical, and the redesign has a deliberate White-element introduction. Need to lock a default for the chart so the ElementGrid resource can be authored without blocking. Affects data/elements/resistances.json and the ElementGrid autoload.
  - Options: A: Original CC chart (mod) | B: Symmetric placeholder (mirror pairs) - neutral 1.0, strong 0.5, weak 2.0 | C: Identical placeholder (all 1.0) - defensible default for v1
  - Default: B: Symmetric placeholder (mirror pairs) - neutral 1.0, strong 0.5, weak 2.0

- [ ] [P1] DEC-002: Status effect canonical list and IDs | Filed: 2026-07-21T09:06:55.695570+00:00
  - Context: Spec section 7.5 defines the StatusEffect resource (id, display_name, category, max_stacks, duration, tick_phase, can_resist, resist_element, handlers). The tech schema already references status strings (e.g., sleep, poison per tech.schema.json). Before the TDD-cron authors the status effect engine, the canonical set of status IDs needs locking so the schema validator and tech augmentation references all agree.
  - Options: A: 8 canonical statuses (sleep, poison, burn, freeze, confuse, slow, stop, weaken) | B: 12 statuses (8 + paralyze, stone, doom, blind) | C: Defer to status-engine TDD cycle - pick at authoring time
  - Default: A: 8 canonical statuses (sleep, poison, burn, freeze, confuse, slow, stop, weaken)

- [ ] [P1] DEC-003: Norris support tech tier interpretation | Filed: 2026-07-21T09:06:57.003926+00:00
  - Context: The other 4 bases have support_slots with tier 1-6 (e.g., serge.json: leena_poshul@1, riddle@2, starky@3, steena@4, doc@5, angelic_pip@6). The locked level-based progression from spec 3.8 means: avg 1 slot at tier 1 (lvl 1), 2 at tier 1 (lvl 3), 2+1 at tiers 1-2 (lvl 5), 3+1 at tiers 1-2 (lvl 6), 3+2 at tiers 1-2 (lvl 7), 3+2+1 at tiers 1-3 (lvl 8), etc. The support_slots tier field in the JSONs is the cap the support occupies; the unlocked tier is gated by level. Confirm so data-cron does not refactor support_slots.
  - Options: A: Confirm current interpretation - support_slots.tier = cap tier the support occupies, unlocked by level | B: support_slots.tier = exact level requirement for that support | C: Drop tier field - support augments as soon as recruited, level only controls elemental slots
  - Default: A: Confirm current interpretation - support_slots.tier = cap tier the support occupies, unlocked by level

- [ ] [P2] DEC-004: Stats block (HP, MP, Attack, Defense, Speed, Magic) - schema location | Filed: 2026-07-21T09:07:05.517301+00:00
  - Context: CharacterData currently has no stats block - only name, element, level, innate, basic_attack, tier_1_tech, tier_8_tech, support_slots. The TechResolver takes attacker_attack as a runtime parameter (not from character data). Spec 7.10 combat engine needs each character stats. Decision: where do HP, MP, Atk, Def, Spd, Mag live? Affects combat-engine TDD cycle (next after action queue).
  - Options: A: Extend character.schema.json (add hp/mp/atk/def/spd/mag fields, all integers) | B: Separate stat_block.json files (1:1 with characters) referenced by id | C: Compute at runtime from level + element + innate + class (no stored stats)
  - Default: A: Extend character.schema.json (add hp/mp/atk/def/spd/mag fields, all integers)

- [ ] [P2] DEC-005: White element innate role (Serge has innate=none - confirm or assign) | Filed: 2026-07-21T09:07:06.827910+00:00
  - Context: Character schema enum for innate is [steal, performance, combat, dark, healer, none]. Spec 3.4 maps red=steal, blue=performance, green=combat, black=dark, yellow=healer. White is not assigned an innate in the spec - Serge is the player. Existing serge.json has innate=none. Decision: keep white=none as player-anchor default, or assign a 6th innate (e.g., leader, light, summoner)? Affects how augmentation engine treats Serge techs vs all other bases.
  - Options: A: Keep white=none (player-anchor; no special innate treatment) | B: Add leader to enum (e.g., boosts adjacent row stats) | C: Add light to enum (mirrors black dark but for White element)
  - Default: A: Keep white=none (player-anchor; no special innate treatment)

- [ ] [P2] DEC-006: Element file naming and topology (8 elements vs 6 base) | Filed: 2026-07-21T09:07:09.149719+00:00
  - Context: Phase 3 redesign element_catalog has 6 base elements (Red, Blue, Green, White, Black, Yellow) plus Chrono Cross special (Time Egg etc., not in visible portion of loop_state.json). The locked design commits to 6 elements for the redesign. The data/elements/ directory does not exist yet, and data-cron target_queue has red_fireball and white_recoverall as first two element entries. Question: do we need Chrono Cross special element files, or strictly the 6 locked elements?
  - Options: A: 6 base elements only (locked design commitment) | B: 6 base + Chrono Cross special as a 7th element file (optional, can be empty initially) | C: Defer - create the 6 base element files first, add Chrono Cross special when needed
  - Default: A: 6 base elements only (locked design commitment)

- [ ] [P1] DEC-007: Augmentation chain walk order and idempotency | Filed: 2026-07-21T09:11:06.461740+00:00
  - Context: Spec section 7.10 step 2 says 'The simulator walks the tech's augmentations list. Pre-damage augmentations apply (status pre-applications, MP discounts, self-buffs).' The augmentation chain walk is the heart of the section 3.5 augmentation model. Before the TDD-cron authors the augmentation chain test, the chain-walk semantics need locking: (1) Are augmentations applied in array order or by some priority field? (2) Can an augmentation cancel the damage step (e.g., MP-discount that makes the tech fail)? (3) Are pre-damage and post-damage augmentations in the same list with a phase field, or in separate lists? Affects test_tech_resolver_augmentation_chain (the next TDD cycle after ActionQueue) and the TechData/TechAugmentation schema. Blocks the upcoming TDD cycle if not resolved.
  - Options: A: Single list, ordered, with phase field (pre/post) on each augmentation | B: Two separate lists (pre_augmentations, post_augmentations) on the tech | C: Single list ordered; the resolver infers pre vs post from augmentation kind
  - Default: A: Single list, ordered, with phase field (pre/post) on each augmentation

## Resolved Decisions

_(none yet)_
