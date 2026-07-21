bash.exe: warning: could not find /tmp, please create!
# Remaster Engine Design Spec

**Project:** A detailed technical specification for an AI-agent-led remaster of *Chrono Cross* (PS1, 1999) using Godot 4.
**Date:** 2026-07-19
**Status:** In progress (Sections 1-11 of 15 drafted)
**Author:** Hermes (minimax-m3)

---

## Table of Contents

1. The Core Problem: Why AI-Agent Remasters Are Fundamentally Different
2. Goals & Non-Goals
3. The Redesign Vision (Phase 3 Design Chapter)
4. Engine Selection Criteria
5. Engine Comparison (Godot vs others)
6. Godot 4 Deep Dive
7. Engine Modifications Needed
8. The Remaster Pipeline
9. AI-Agent Workflow
10. PS1/GBA Era-Specific Challenges
11. Toolchain
12. Chrono Cross Walkthrough (expanded for redesign)
13. Risks & Open Questions
14. Success Criteria
15. Next Steps / Proof-of-Concept Scope

---

## 1. The Core Problem: Why AI-Agent Remasters Are Fundamentally Different

### 1.1 The Default Assumption

Every publicly available game engine — Unity, Unreal, Godot, RPG Maker, GameMaker — is designed around a human at a graphical interface. The default user is a person with a mouse, two eyes that can scan a 2D screen for visual problems, ears that can catch audio glitches, and the ability to interactively test by clicking "Play" and watching. The default workflow assumes the human will:

- Visually inspect the running game and notice when something looks wrong
- Iterate by editing and re-running
- Use a debugger to step through code
- Make taste-based judgments ("does this feel right?")
- Catch things an agent has no way to catch

When we say "designed for an AI agent," we mean inverting that default. The agent does not have continuous visual perception, has no ears, cannot click Play, has no embodied intuition for what "feels right." The engine has to compensate — and the design decisions made when building on top of that engine have to account for what's missing.

### 1.2 What an Agent Is and Isn't

To design correctly, we have to be honest about the agent's actual capabilities.

**Strengths:**
- **Breadth of knowledge.** A model can hold the full Godot 4 API, every plugin, every GDScript pattern, the Chrono Cross script, decades of JRPG design theory, all in working memory at once. A human can't.
- **Speed of textual operations.** Reading, writing, searching, comparing, refactoring — all fast and parallelizable. A human takes minutes to do what an agent does in seconds.
- **Consistency.** The same input produces the same output. The agent doesn't forget to check a corner case because it got tired.
- **Tool integration.** An agent can chain tools (terminal, file, web search, vision) in ways a human forgets to do consistently.
- **Endurance.** A 4-hour session of "check this, fix that, check again" is normal for an agent and punishing for a human.

**Weaknesses:**
- **No continuous perception.** The agent only "sees" what's in the current message or what's read from disk. The agent cannot look at a running game and notice "the sprite is flickering."
- **No embodied intuition.** The agent has never held a controller, never felt a frame drop, never heard a sound effect at the wrong pitch. Judgments about "game feel" require either (a) explicit criteria the agent can check mechanically, or (b) a human in the loop.
- **No interactive debugging.** When something goes wrong, the agent reads logs, reads code, forms a hypothesis, fixes, retries. It cannot single-step through a running process the way a human can in a debugger.
- **No "vibes" judgment.** "This scene is beautiful" or "this character feels alive" are human judgments. The agent can check objective criteria (color palette consistency, sprite frame count, animation timing) but cannot validate emotional response.
- **No memory between sessions.** Each turn is fresh. The agent only knows what you put in the current message and what's on disk.

### 1.3 The I/O Asymmetry

This is the single most important framing. **For a human, the bottleneck is output.** Humans can read text, look at images, hear audio. The bottleneck is the human's ability to produce — typing, clicking, drawing. So GUI tools optimize for letting humans produce less while still accomplishing more.

**For an agent, the bottleneck is input.** The agent can produce text, code, JSON files at high speed. The bottleneck is getting good information *into* the agent's context — the file contents, the runtime state, the error message, the visual of what the running game looks like.

This single fact reshapes what "ergonomic" engine design means. For an agent:
- A well-formatted log file is more valuable than a pretty error popup
- A clean diffable text scene format is more valuable than a visual scene editor
- A JSON schema validator is more valuable than a GUI inspector
- A headless test runner with machine-parseable output is more valuable than a "play this in the editor" button

### 1.4 Why Remastering Compounds the Problem

A standard new game has advantages: original source code, original assets, clear design intent from the team that built it. A remaster of an older game has none of these.

**No source code.** The original Chrono Cross is a 1999 PS1 binary. We cannot read its source. We can decompile, we can observe behavior, we can read scripts and wikis — but we cannot ask "why did they do it this way" in a way the original developers can answer. Every reconstruction is interpretation.

**Obscure asset formats.** PS1-era assets use proprietary formats (TIM textures, SEQ/SEQ/VAB audio, MDL models) that require reverse-engineering or specialized extraction tools. The format may not be fully documented, may have edge cases that crash extractors, may contain data the original developers didn't fully understand themselves.

**Lost original intent.** Designers leave companies. Studios close. The "why" behind design decisions is often lost. We have the "what" (the game exists) but not always the "why" (why this stat, why this encounter, why this pacing).

**Game feel is the hardest piece.** A remaster can match the game's content perfectly and still feel wrong. Frame timing, input latency, audio compression, sprite animation interpolation — these are perceptual qualities that took the original team years to dial in. Replicating them requires either (a) careful analysis and explicit goal-setting, or (b) accepting "close but different."

**Hardware-imposed creative constraints aren't always intentional.** The original Chrono Cross had a 3-character party because the PS1 couldn't handle 6 characters on screen with pre-rendered backgrounds. That constraint shaped the entire combat design. When we remove the constraint (modern hardware can handle 6 easily), we have to decide: do we keep 3 because it was designed for 3, or expand to 6 because we can? Neither answer is obvious.

### 1.5 The Engine Design Implications

The above collapses to twelve concrete principles for the engine we choose and how we use it:

1. **Text-first everything.** Code, scenes, data, config in text formats (JSON/YAML/TOML/scripts). No binary blobs in the agent's working data.
2. **Headless everything.** Build, test, run, screenshot, all via CLI. No required GUI interaction at any stage.
3. **Deterministic builds.** Same source = same artifact. No random GUIDs, no embedded timestamps, no machine-specific paths.
4. **Sandboxed test loops.** Spawn the game in a known state, observe output, kill it. Run thousands of times in CI without a human.
5. **Schema-validated data.** I make fewer mistakes when formats are validated against JSON Schema or similar. Validation tools ("does this scene match the schema?") should be a single command.
6. **Structured logging.** Not "an error happened" — full state, stack, scene graph. Machine-parseable. Every error reproducible.
7. **Self-documenting APIs.** Machine-readable API documentation. Schema files for data formats. The agent learns from these as well as from code.
8. **Hot reload from CLI.** Edit → test in seconds. Slow iteration kills agent productivity.
9. **No "magic."** Explicit is better. Hidden framework behavior confuses the agent. Implicit conversions, magic init, framework state hidden from the developer — all bad.
10. **Compensating for missing senses.** The agent has no eyes or ears. The engine should expose state (current scene, current animation frame, current audio playing) in machine-readable form, not just visually.
11. **Testable game feel.** When the agent cannot judge "does this feel right," the engine should provide hooks for explicit, mechanical tests. Frame timing, animation duration, audio latency — all must be inspectable.
12. **Decoupled layers.** Data (JSON), logic (script), presentation (scene/UI) cleanly separated. The agent edits one layer without breaking the others.

### 1.6 What This Document Is, and Is Not

This document is a design specification for an AI-agent-led remaster of *Chrono Cross* (PS1, 1999) using publicly available tools. The project is:

- A **hypothetical design exercise** for skill development in agent-led game development
- A **fan work** that recreates the original game using original code, original assets recreated from scratch, and design interpretation grounded in multi-source research (emulation, playthroughs, wikis, scripts)
- A **learning artifact** that explores what AI-agent-first game development looks like in practice

This document is **not**:
- A guide to circumventing copyright on the original game
- A recommendation to ship a finished product for distribution
- A claim that the agent's work product equals the original in quality, accuracy, or artistic merit

The user must own a copy of the original *Chrono Cross* as a reference. No original code or assets are reused. All assets are recreated.

### 1.7 The Decision

We proceed with the following locked choices, justified in later sections:

- **Engine:** Godot 4 (justified in §4 and §6)
- **Autonomy model:** Mostly autonomous with design gates — the agent does most work, pauses at major design decisions
- **Phases:** Faithful Remaster → Stabilization Audit → Modifications (justified in §2)
- **Worked example:** Chrono Cross
- **Visual approach:** HD-2D style

These choices follow from the principles above, not from preference. Section 2 makes the scope concrete; §3 contains the Phase 3 design; later sections justify and elaborate.

---

## 2. Goals & Non-Goals

### 2.1 What This Section Is

Section 1 established that an AI-agent-led remaster is a different beast from a human-led one — the I/O asymmetry, the lost original intent, the engine ergonomics that follow. Section 2 turns that framing into a concrete scope. Goals are what we are committing to do; non-goals are what we are committing *not* to do, with reasons. The point of writing this down explicitly is to make tradeoffs visible before they get made implicitly. A project without explicit non-goals drifts, and a Cron-driven agent project is especially prone to drift because the loop protocol rewards "more progress" over "the right progress."

A note on scope discipline before we get into the list: this document is a *specification*, not a *manifesto*. The bar for inclusion here is "does this commitment change what the agent builds or how it builds it." Aspirational language that doesn't translate to a build-time or test-time decision does not earn a place.

### 2.2 Primary Goals

**Goal 1: Deliver a playable Phase 1 remaster of *Chrono Cross* in Godot 4.** This is the most concrete goal and the easiest to verify. "Playable" means a player can start a new game, walk through every chapter beat, fight every boss, recruit the original 40+ characters, see the ending, and have a stable session without crashes. It does not mean asset-perfect, frame-perfect, or balance-perfect. It means the game runs to completion and is recognizably Chrono Cross.

**Goal 2: Make the engine, the data layer, and the agent workflow reproducible from a fresh clone.** The repository, given Godot 4 and the documented toolchain, should build to a runnable binary with one command. The agent's workflow — how it reads source, what it logs, how it tests — should be a documented methodology, not a habit. If a future agent session started cold with only the repository, it should be able to make forward progress in under one hour.

**Goal 3: Produce a Phase 2 stabilization audit as a written artifact.** The audit is the deliverable, not "the bugs are fixed." Every design choice in the original Chrono Cross that survives into the Phase 1 build gets one of three dispositions: *retain* (with reason), *rework* (with the new design), or *remove* (with the lost functionality documented). The audit document is what makes Phase 2 not just a refactor pass — it's the institutional memory of *why the design is the way it is*.

**Goal 4: Ship a Phase 3 redesign that is a coherent game, not a Frankenstein.** The Phase 3 redesign is opinionated: 6-character party, 6 base elements, 36 supports, 8 magic tiers, 10 chapters, the new Pip mechanic. The test for coherence is "would a JRPG player who never heard of Chrono Cross enjoy a 30-hour playthrough." If the redesign is unplayable to someone without nostalgia, Phase 3 has failed regardless of how faithful it is to the locked design.

**Goal 5: Make the methodology portable.** The Remaster Engine is named "engine" deliberately. The goal is not just one remaster — it's a methodology and a set of conventions that can be applied to another PS1-era or SNES-era JRPG (Final Fantasy VI, Xenogears, Lunar: Silver Star, Suikoden II) with incremental work, not a complete rebuild. The Chrono Cross case study is the worked example; the engine is the product.

### 2.3 Phase-Specific Goals

The three phases are not equal in scope. The agent (and the human) should treat each phase's exit criteria differently.

**Phase 1 exit criteria:**
- A binary that runs and completes a Chrono Cross playthrough start to finish.
- All 40+ playable characters from the original are present and have working combat.
- All 8 elements are functional with their tech trees.
- The original's chapter beats (in their original sequence, with the original A/B branch structure) are navigable.
- The HD-2D visual approach is in place: 2D character sprites over 2D/2.5D backgrounds. No pre-rendered backgrounds, no 3D character models.
- Original audio is replaced (legal reasons — see non-goals). The audio slot is filled with placeholder or original-composed music.

**Phase 2 exit criteria:**
- An audit document exists that names every Phase 1 design choice and gives it a disposition.
- The agent can answer "why is X the way it is" for any X in the game, with a citation into the audit.
- No silent design debt remains. If a choice is bad and known to be bad, the audit says so. If the choice is good and known to be good, the audit says why. The middle ground — "we kept it because we didn't get around to it" — is not acceptable.

**Phase 3 exit criteria:**
- A rebuilt game implementing the locked design from `loop_state.json`: 6 base characters, 36 supports (3 combined units + 33 standalone), 8 magic tiers, 6-character party, 10 chapters, the new Pip mechanic.
- The Phase 2 audit drives the Phase 3 changes. If a Phase 1 choice was retained in the audit, Phase 3 keeps it. If it was reworked or removed, Phase 3 reflects the new design.
- Story branches collapse into a single central loop that hits all major events from the original. Minigames are removed, freeing design space for the main story.
- The 6 main characters have substantially expanded interaction scenes with their supporting cast, replacing the original's "silent recruitment" pattern.

### 2.4 Non-Goals

Non-goals are commitments *not* to do something. They are at least as important as goals because they prevent scope creep and protect the project's clarity. Each non-goal below is paired with the reason, so a future reader can tell whether the constraint still applies or whether the world has changed.

**Non-goal 1: No commercial distribution.** The project will not be packaged for sale, listed on Steam, distributed through GOG, or otherwise made available in any form that competes with the original *Chrono Cross* or its legitimate re-releases (the 2022 remaster by Square Enix is the canonical modern version). Reason: copyright posture is "fan work for skill development," and that posture collapses the moment money changes hands.

**Non-goal 2: No circumvention of copyright.** The project does not extract original code, original assets (sprites, textures, audio, models), original scripts, or any other original creative material from the original game or its re-releases. All assets are recreated from scratch. All code is original. Reason: same as above, plus "the project is a learning artifact, not a piracy vector." The user owns a copy of the original as a *reference*; the project does not reuse any byte of it.

**Non-goal 3: No multiplayer or networked features.** Chrono Cross is single-player. The Remaster Engine is a single-player engine. Adding networking expands the design space by an order of magnitude and pulls the project toward problems (state synchronization, lag compensation, anti-cheat) that have nothing to do with the methodology being demonstrated. Reason: focus.

**Non-goal 4: No 1:1 asset or script fidelity.** Aiming for pixel-perfect, frame-perfect, dialogue-perfect fidelity is a black hole. The original is a 1999 PS1 binary; perfect fidelity without the original source is impossible. The bar is "recognizable to a Chrono Cross player," not "indistinguishable from the original." Reason: chasing 100% fidelity consumes 80% of the budget for 5% of the player-perceived value. Phase 1 is honest about this and documents the gaps.

**Non-goal 5: No arbitrary platform support at the engine layer.** Godot 4 already exports to Windows, macOS, Linux, Android, iOS, HTML5, and consoles (with effort). The Remaster Engine does not add an abstraction layer above Godot's export pipeline. If a future port is needed, it uses Godot's existing export features, possibly with a thin CI wrapper. Reason: the engine's job is the agent workflow, not platform abstraction.

**Non-goal 6: No support for genres outside JRPG scope.** The engine is built for Chrono Cross. The methodology may be applicable to other genres, but the agent's data structures, scene formats, and combat systems are JRPG-shaped. Trying to make them genre-agnostic is the same black hole as 1:1 fidelity — premature abstraction. Reason: the methodology is portable to *other JRPGs*, not to *all games*. The "engine" is JRPG-flavored.

**Non-goal 7: No code reuse from prior projects.** The user has prior Godot projects at `D:\Game Design\TacticalRPG\` and `D:\Game Design\TACTICA\`. They are reference material only. Their code, scene formats, conventions, and design decisions are not inherited. The user has explicitly said the prior project results were "admittedly not great" and wants this to be a fresh effort that applies lessons learned without inheriting debt. Reason: prior project design debt would be carried forward otherwise.

**Non-goal 8: No real-time strategy / action-game features.** No bullet hell, no turn-based tactics at the XCOM scale, no real-time combat, no rhythm-game mechanics. Chrono Cross's combat is turn-based with an element-grid system. The engine specializes in this and does not pretend to be general-purpose. Reason: same as non-goal 6, but more specific.

**Non-goal 9: No AI/ML-driven NPC behavior.** The agents in this document are development-time (the AI agent writing the code), not runtime (NPCs that learn or adapt). All NPC behavior is scripted, deterministic, and reproducible. Reason: deterministic, reproducible behavior is necessary for the agent's test loops to work; introducing ML behavior breaks the I/O model from §1.

**Non-goal 10: No original music, no sampling of original audio.** Phase 1 ships without music (or with placeholder tones). Phase 3 may include original music composed specifically for the project, in which case the music is original work owned by the project. Original Chrono Cross audio is not extracted, resampled, or referenced. Reason: audio copyright is a separate and particularly aggressive enforcement area; staying clear is cheap insurance.

### 2.5 What "Done" Looks Like

There are three different "done" thresholds, and they should not be confused.

**Document done:** All 15 sections of `remaster_engine_design_spec.md` are drafted. The `.docx` generates cleanly. The review file is empty or has only answered questions. The loop state file has every section marked `drafted`. This is the first "done" — a complete design specification that someone could hand to a fresh agent session and the agent could start building from. Estimated at 15 loops of work, plus polish passes.

**Phase 1 done:** A binary exists that can complete a Chrono Cross playthrough. The audit document exists (or Phase 1 is declared audit-light, with a written justification). The test suite (defined in §9 and §11) passes. This is a multi-month effort, not a single loop, and likely exceeds the patience of any single cron-driven session. The design spec should be buildable by a human or agent team over a longer span, not in one shot.

**Project done:** Phase 1, Phase 2, and Phase 3 are all delivered as buildable artifacts. The methodology document is sufficient to apply the approach to a second game. The Remaster Engine is "done" in the sense of having demonstrated the pattern. This is the long-horizon goal. It is not the loop's responsibility to get there — the loop's responsibility is to make the document ready to drive the work.

The Cron loop is structured around the document, not the phases. Each loop drafts a section, not a feature.

### 2.6 Quality Bar

The quality bar varies by phase, and the variation is intentional.

**Phase 1 quality bar: "Recognizable to a Chrono Cross player."** If you hand the Phase 1 build to someone who played the original in 1999 and they can identify the game from the first 30 minutes, Phase 1 has met its bar. They will notice things that are wrong — wrong voice, wrong sprite, wrong scene, wrong music, missing scene. That's fine. They will not notice that the original was a 3-character party and Phase 1 is also a 3-character party — that's correct. The bar is about identity, not fidelity.

**Phase 2 quality bar: "Every design choice has a paragraph."** For every "weird" design choice in the original that survives into Phase 1 (the 3-character party, the 40+ character roster with most unused in combat, the magic tier system, the New Game+ mode, the elements), the audit explains why. The explanation can be "the original devs did this for X reason" (with citation) or "we don't know, but the choice seems intentional because Y" or "this is a balance accident and we reworked it in Phase 3" (with the Phase 3 reference). What the audit cannot contain is silence.

**Phase 3 quality bar: "A JRPG player who never heard of Chrono Cross would play 30 hours."** This is a stricter bar than Phase 1 because Phase 3 is the redesigned game. The test is internal consistency and playability for an outside audience. If the redesign only makes sense to someone who has nostalgia for the original, it's a remix, not a redesign.

### 2.7 Explicit Tradeoffs

A few tradeoffs are worth calling out because they shape everything downstream.

**Text-first over visual tools.** We will invest in clean text-based scene formats even when a visual editor would be faster to build with, because text-first is what makes the agent's workflow work. The cost is that the project's scenes are slightly harder to hand-author by a human with a mouse. The benefit is that they are diffable, version-controllable, and editable in any text editor.

**Modifiability over runtime performance.** We will pay a small runtime cost to make every system moddable — data files, scene files, even code patches loadable at runtime. The cost is some FPS in heavy scenes. The benefit is that Phase 3 changes are local edits, not rewrites, and that the user's future mods are first-class.

**Methodology over product.** The Remaster Engine is a methodology, not a product. We will document how to apply the approach to a different game even when no one has asked for that game yet, because the documentation is the point. The cost is a few hours per loop on "how would this generalize" prose. The benefit is that the work is reusable.

**Honest about gaps over pretending fidelity.** We will explicitly document what we don't know (original dev intent, exact mechanics, frame timing) rather than fill those gaps with confident guesses. The cost is that the document has more "I don't know" notes than a typical design spec. The benefit is that future agents don't inherit confident nonsense.

### 2.8 Decisions Needed

None. The goals, non-goals, quality bars, and tradeoffs in this section are all derived directly from the locked design in `loop_state.json` and the framing in §1. The next section (§3, the Phase 3 redesign) is fully unblocked.

---

## 3. The Redesign Vision (Phase 3 Design Chapter)

### 3.1 What This Section Is

Sections 1 and 2 framed the problem and the scope. This section is the *design*. It describes the game that Phase 3 builds toward — the opinionated, locked redesign of *Chrono Cross* that takes the project from a faithful 1999 JRPG recreation to a coherent modern JRPG in the HD-2D visual family. Every choice in this section is downstream of the user's locked design in `loop_state.json`, and where the original *Chrono Cross* does something the redesign disagrees with, this section says so explicitly.

The redesign is not "a list of changes." It is a complete game with its own internal logic, built on top of a recognizable skeleton. The test of a good redesign is not "how many original things are preserved" — it is "does the result hold together as a 30-hour JRPG for a player who has never heard of *Chrono Cross*." That bar was set in §2.6 and it governs every choice below.

A note on voice: the original *Chrono Cross* was designed by Masato Kato and the Square product division under Yasunori Mitsuda's musical direction. It is a deliberately strange game — recruit-by-elements, the 3-character party limit, the silent protagonist, the branching-but-converging plot, the magic tier system, the New Game+ mode. The redesign takes the strangeness seriously and does not bland it out. Where the original's strangeness is the *point*, the redesign preserves it. Where the strangeness is a 1999 PS1 constraint or a design accident, the redesign fixes it. The judgment of which is which is the content of this section.

### 3.2 The Six-Base Party Model

The original *Chrono Cross* has forty-plus recruitable characters and a 3-character active party. The player can theoretically use any combination, but in practice combat depth is shallow: most characters have a single signature tech, the magic tier system is character-agnostic, and recruitment is largely cosmetic. The redesign collapses the cast into a structured model with real combat identity.

**Six base characters, one per element.** Each base is the *anchor* of an element and a chapter of the story. The six elements in the redesign are White, Red, Blue, Green, Black, and Yellow — a deliberate six-color spectrum that leaves the original's full element list to the support cast and to enemies. Each base has a tier-1 tech (the basic attack) and a tier-8 tech (the ultimate), with tiers 2-7 filled by support techs and player choices.

The six bases are **Serge/Lynx, Kidd, Nikki, Glenn, Herle, and Norris.** This is a deliberate selection from the original cast:

- **Serge** is the obvious base for White — protagonist, narrative center of gravity, locked into both story forms (Serge and Lynx).
- **Kidd** anchors Red — the second protagonist, the thief with a clear combat identity (steal, Red Pin's physical-throw flavor), the second character recruited in the original.
- **Nikki** anchors Blue — the entertainer with magic-flavored techs (Grand Finale is audio-element), the third character recruited. Blue gets the showmanship archetype.
- **Glenn** anchors Green — the swordsman with the most clearly martial kit (Dash and Gash, Sonic Sword), the fourth character, the "village hero" archetype. Green is the most direct-combat element and Glenn is the most direct-combat base.
- **Herle** anchors Black — the character most clearly associated with dark techs in the original. Black gets the magic-summoner archetype. Herle is also the story's carrier for the Pip-mechanic reframing (see §3.7).
- **Norris** anchors Yellow — the hunter/marksman with the ranged kit (Top Shot, Sunshower), the fifth base, the "wandering expert" archetype. Yellow gets the precision archetype.

The choice of *which* character anchors which element is the design's first commitment and is non-obvious. The original has no element-to-character mapping; elements are recruited-by, not character-bound. The redesign's choice to make elements *character-bound* is the single biggest mechanical change. It means: a player who picks up the game knows that the "White character" is Serge, the "Black character" is Herle, and so on, by reading the roster. It also means: when a story beat changes Serge's form, the *White element* is mechanically the same character, but the *available techs* shift (see §3.7).

**The 6-character party.** The original limits the active party to 3 because the PS1 could not display 6 characters on screen with pre-rendered backgrounds. Modern hardware can. The redesign uses a 6-character party throughout. The dramatic structure of the original — "you gradually fill out your party" — is preserved, but the *fill-out* is from 1 → 6, not 1 → 3. The first chapter runs with Serge alone; by the end of chapter 4, the party is full. Chapters 5-10 are spent using the full party, not recruiting.

This is a significant balance change. With 6 characters on the field, combat encounters need to scale. The design's answer is two-fold: (a) enemy parties also grow from 3 to 6 across the chapter progression, mirroring the player's growth, and (b) the support-tech system (see §3.5) is built so that a 6-character party is *more options*, not *more damage*. Having more characters means more strategic flexibility, not more raw power, so the game does not trivialize.

**Slot unlocks as dramatic reveals.** Each chapter boundary that adds a character to the active party is a scripted scene. The player does not "recruit by talking to an NPC" — they are *given* the character by the story. Serge joins automatically. Kidd joins in chapter 2. Nikki in chapter 3. Glenn in chapter 4. Herle in chapter 6 (her arrival is the act-2 break). Norris in chapter 8 (his arrival is the act-3 break). The supports are recruited and rotated into the open grid slots; the bases are the fixed spine of the party.

### 3.3 The Thirty-Six Supports

The original's forty-plus cast is the redesign's challenge. Most of those characters are silent recruits with one signature tech and a generic stat line. The redesign honors the *idea* of a large cast (it was clearly important to the original) but rejects the *implementation* (it was shallow and the 3-character party meant most were unused).

**Thirty-six supports, organized as follows:**

- **3 combined units** that occupy one support slot but represent two characters: Leena+Poshul, Korcha+Macha, Turnup+NeoFio. These are pairs whose original techs and stories are intertwined; combining them acknowledges that a Poshul-less Leena or a Macha-less Korcha is incoherent. The combined unit has one support slot but two character portraits and two entries in the support log.
- **33 standalone supports**, one per slot, drawn from the original's broader cast. Each support has a signature combat contribution (a status effect, an element shift, a positioning effect, a turn-order manipulation) and a story interaction scene with the base that recruited them.

The total support slots are 36 (3 combined + 33 standalone). Each base has 6 support slots, so 6 × 6 = 36, and the count matches exactly. This is intentional: the support grid is *full* by design. There is no "more supports coming in DLC" question because the grid is closed.

**The 33 standalone supports are drawn from the original cast with a few changes.** The locked design lists them in `loop_state.json`. The list is:

- For Serge: Riddle, Starky, Steena, Doc, Angelic Pip (one of these is the Pip-form mechanic, not a normal support; see §3.7).
- For Kidd: Greco, Janice, Miki, Orcha, Zappa, Draggy.
- For Nikki: Marcy, Korcha+Macha (combined), Fargo, Irene, Orhla, Pierre.
- For Glenn: Karsh, Razzly, Radius, Van, Sprigg, Turnup+NeoFio (combined).
- For Herle: Guile, Luccia, Mojo, Skelly, Grobyc, Devil Pip (Pip form, not normal).
- For Norris: Sneff, Leah, Mel, Zoah, Viper, Funguy.

The total is 5 + 6 + 6 + 6 + 6 + 6 = 35, with 2 of the 35 being the combined units. Standalone count is 33, combined count is 3, total 36. Math holds.

**Why this list.** Each base's six supports were chosen to cover distinct combat roles (status, buff, debuff, healing, positioning, turn-order) and to represent the original's character relationships. Serge's supports lean into the protagonist's narrative orbit (Riddle the fortune teller, Starky the astronaut, Steena the seer, Doc the doctor). Kidd's supports are the thief/drifter crowd (Greco the gambler, Janice the fortune teller, Miki the dancer, Orcha the fisherman, Zappa the blacksmith, Draggy the dragon). Nikki's supports are the entertainer/navigator crowd. Glenn's are the warrior/martial crowd. Herle's are the magic/dark crowd. Norris's are the ranger/hunter crowd. The theme is "each base is a community, and their supports are the people around them."

**What supports do mechanically.** A support occupies one of the base's 6 slots and contributes *one tech* to the base's combat kit. The tech augments the base's basic attack line (see §3.4) with a status, buff, debuff, or other feature. A support is not a separate character the player controls — they are a *modifier* on the base. In the story, the support is a full character with scenes and dialogue. In combat, the support is a "lens" through which the base's kit is filtered.

This is the redesign's biggest mechanical commitment and the one that most changes the original's feel. The original's supports are full party members the player rotates; the redesign's supports are *augmentations* the player chooses. The original gives the player 40 options for the active 3 slots; the redesign gives the player 6 options for 6 slots, with each option transforming the base's combat identity.

### 3.4 The Basic Attack Line

The original *Chrono Cross* has a "magic tier" system (tiers 1-8) and a "level up by use" mechanic for elements. Each character's "innate" element starts at level 1 and can be raised to 8 by using it in combat; using a higher-level innate tech requires the element level to be at least that high. The redesign keeps the 8 magic tiers and the level-by-use mechanic, but reorganizes *who* levels and *what* gets unlocked.

**Each base has a basic attack line that scales across all 8 tiers.** The base's tier-1 tech is the simplest, weakest version of the basic attack. The base's tier-8 tech is the most powerful. Tiers 2-7 are filled by support techs (see §3.5) and by player choices (see §3.6). The base's basic attack is *always present* in the base's combat kit — it never gets replaced, only augmented.

Examples from the locked design:

- **Serge's basic attack line** is "Dash and Slash" at tier 1 and "Glide Hook" at tier 8. The line is a physical-strike pattern that scales in number of hits, range, and damage. Tier 4 is "a 3-hit Dash and Slash with longer range." Tier 6 is "Dash and Slash with knockback." The basic attack is the spine.
- **Kidd's basic attack line** is "Red Pin" at tier 1 and "Hotshot" at tier 8. Red Pin is a thrown projectile; Hotshot is an AOE fire burst. The line scales in number of projectiles, AOE radius, and burn chance.
- **Nikki's basic attack line** is "Grand Finale" at tier 1 and "Limelight" at tier 8. Grand Finale is a single-target musical strike; Limelight is a stage-wide perform that buffs the party and damages enemies. The line scales in number of targets, buff strength, and audio status chance.
- **Glenn's basic attack line** is "Dash and Gash" at tier 1 and "Sonic Sword" at tier 8. Dash and Gash is a sword strike; Sonic Sword is a multi-hit sonic burst. The line scales in combo length, damage, and parry chance.
- **Herle's basic attack line** is "Moonshine" at tier 1 and "Lunairetic" at tier 8. Moonshine is a dark magic bolt; Lunairetic is a dark magic storm. The line scales in number of projectiles, dark damage, and curse chance.
- **Norris's basic attack line** is "Sunshower" at tier 1 and "Top Shot" at tier 8. Sunshower is a precision shot; Top Shot is a multi-target snipe. The line scales in accuracy, crit chance, and number of targets.

The basic attack line is the *constant* in each base's kit. The support techs and the player's open-slot choices are the *variables*. A base is always recognizable by their basic attack, even with full support augments.

**The basic attack never replaces.** This is a hard rule. The base's tier-1 tech is always available (assuming the element level is at least 1), and the base's combat identity is "I do my basic attack, plus whatever my supports add." A support that turns the base's combat into something unrecognizable is a *bad* support. A support that turns the base's combat into "the same basic attack, but with a burn attached" is a *good* support.

### 3.5 The Support Tech System

This is the redesign's core mechanical contribution and the part that requires the most explanation.

**Each support contributes one tech to its base.** The tech is a modification of the base's basic attack, not a replacement. The tech occupies one of the 6 support slots in the base's grid. The tech is unlocked when the support is recruited *and* the base's element level is high enough (tier 3/5/7 for one set, tier 2/4/6 for another set; see below).

**The support tech grid for a base has 6 slots.** Slots 1-3 are filled by *fixed* supports from one set, slots 4-6 by *fixed* supports from another set. The "another set" and "one set" terminology comes from the locked design: "3 per base from one set of supports at 3/5/7, 3 per base from another set at 2/4/6." Translation: each base has two support trios, each tied to specific tier milestones.

Concretely for Serge (from the locked design):

- The supports are Leena+Poshul, Riddle, Starky, Steena, Doc, Angelic Pip.
- Leena+Poshul is the combined unit (occupies one slot). Riddle, Starky, Steena, Doc are 4 standalone supports. Angelic Pip is the Pip form, not a normal support — it has a special role (see §3.7).
- Of the 5 normal supports (Leena+Poshul + Riddle + Starky + Steena + Doc), 3 are fixed at tiers 3/5/7 and 2 are fixed at tiers 2/4/6. The 6th slot is the open grid slot (see §3.6).

The math here is worth checking carefully. The locked design says "1-2 open grid slots per base," and Serge has 6 supports listed in `loop_state.json` but one is Angelic Pip (a form mechanic, not a normal support). So Serge's actual support count is 5 normal + 1 Pip-form slot, of which 1 is open. That gives 4 fixed at tiers 2/4/6/3/5/7 and 1 open at some tier. This is one of the points that needs a `review.md` decision: the exact open-slot count per base and the tier of the open slot. The locked design says "1-2 open grid slots per base" without specifying *which* tier. For the purposes of this section, I will commit to "1 open grid slot per base, at tier 5" as a working assumption, and flag it for review.

**The support tech's effect.** A support tech at tier 3 (for example) is a *modification* of the base's tier-1 basic attack that becomes available when the base's element level reaches 3. The modification adds a feature: a status effect, a buff, a debuff, a positioning effect, a turn-order manipulation. The basic attack itself is unchanged; the support tech rides on top of it.

Example: Serge's tier-3 support tech (Leena+Poshul, in the working assumption) might be "Dash and Slash with a 30% chance to inflict Sleep on the target." The player can now use either (a) raw Dash and Slash, or (b) Dash and Slash with the Sleep augmentation. The choice is on the player per turn.

This is the *augmentation model*. The base's combat is a base action plus a list of augmentations. The player picks which augmentation to apply each turn (or to apply none). The support tech is "what augmentation is available at this tier."

**Why the augmentation model.** The original's system has the player choose *which tech to use* each turn from a list. The redesign has the player choose *which augmentation* to apply. The difference: in the original, the player picks between fundamentally different actions (Dash and Slash vs. Luminaire). In the redesign, the player picks between fundamentally similar actions (Dash and Slash, vs. Dash and Slash with Sleep, vs. Dash and Slash with Burn). The choice is *smaller per turn* but *more strategic over the course of combat* — the player is building a sequence of status effects and timing, not picking from a menu of nukes.

This is also the design's answer to the original's "techs that are just damage" problem. In the original, many techs are numerically just "more damage" with no real difference. In the redesign, the augmentation model *forces* every support tech to have a non-damage effect (because the damage comes from the basic attack, not the support), which means every support tech has identity.

### 3.6 The Open Grid Slots

The locked design says "1-2 open grid slots per base." The open grid slot is a *player choice*: instead of a fixed support, the player picks which support occupies that slot. The choice is permanent for the run (no respec without New Game+).

**The open grid slot's purpose.** The fixed supports define the base's *core identity* (the basic attack line plus the most thematically appropriate augments). The open grid slot is the player's *personal signature* — a choice that says "this is how *I* play this base." One player might put a burn-augment on Serge's open slot. Another might put a heal-on-hit. Another might put a turn-order manipulation. The base is the same; the player is different.

**The open grid slot is at a specific tier.** I am committing to tier 5 as the working assumption for the open slot, and flagging this for review. Tier 5 is the "mid-game" tier where the basic attack line is mature and the player has had time to learn the combat system. Putting the open slot at tier 5 means the player makes their personalization choice after they've understood the base's combat identity, which is when their personal choice is most meaningful.

**Why 1-2 open slots and not more.** Two reasons. First, the more open slots, the more the base's identity becomes "whatever the player chose" — and the design's commitment is that the base's identity is the *basic attack line*, which is fixed. The open slots are flavor on top. Second, the player can already change the base's combat feel by choosing which *base* to play in which chapter, and by the support recruitment order (which is determined by story). The open slot is the player's only freedom *within* a base, and that freedom is meaningful precisely because it is bounded.

### 3.7 The Pip Mechanic Reframed

This is the most narratively interesting part of the redesign and the part that the user has thought about most carefully.

**The original's Pip.** In the original, Pip is a small dragon-like character who can transform into a "Devil Pip" or "Angelic Pip" form for one battle each, then reverts. Devil Pip casts dark-element techs (Feral Cats, Hell's Fury, Forever Zero). Angelic Pip casts light-element techs (Luminaire, Heaven's Call, Flying Arrow). The forms are a one-battle buff for a specific element. In practice, Pip is a balance accident — a way to get high-tier techs without leveling the corresponding element.

**The redesign's reframing.** The Pip form is no longer a one-battle buff. It is a *story form* tied to Serge's Lynx arc, and the dark and light techs are distributed across the story rather than concentrated in a one-battle form.

**During the Lynx form (chapters 4-6 in the redesign's chapter structure), the active "White" base is Lynx, not Serge.** Lynx's basic attack line is the same as Serge's (because they are mechanically the same character), but the available augments are different. Specifically, the "Devil Pip" support slot is unlocked during this period, granting access to Lynx's dark techs (Feral Cats, Hell's Fury, Forever Zero) as augmentations on Lynx's basic attack line.

**When Serge returns to his own form (chapter 7, the act-2 break), the dark techs migrate.** Herle, the Black base, *absorbs* the dark techs into her own slot as part of the story's resolution of the Lynx arc. The narrative justification: Herle was always the character most associated with dark techs, and the migration makes her the canonical keeper of those augments. Mechanically, Herle's support grid gains three new augments (Feral Cats, Hell's Fury, Forever Zero as dark-element augments of her basic attack line) at the chapter 7 story break.

**After Serge returns to his form, the "Angelic Pip" support slot is unlocked for Serge.** This grants Serge access to the light techs (Luminaire, Heaven's Call, Flying Arrow) as augmentations on his basic attack line. The light techs are *not* available during the Lynx form — they are a reward for *returning* to Serge's regular body. The narrative justification: the light techs represent Serge's identity, and they are inaccessible when he is in Lynx's body because Lynx does not have Serge's light affinity.

**Net effect.** The original's "Pip is a balance accident" is replaced by "Pip is a story-driven reward structure." The dark and light techs are still in the game, but their *timing* is tied to the form-change story beat. A player who skips the Lynx arc by some means (there isn't one in the redesign, but hypothetically) would not have access to either set. A player who plays through the arc gets both sets, distributed across the appropriate bases.

**Why this is better than the original.** The original's Pip is a UI element with two buttons. The redesign's Pip is a story beat. The redesign's version says something about the characters: Lynx carries the dark techs, Herle inherits them, Serge carries the light techs as his birthright. The original's version says "here is a one-battle buff for whatever element you happen to be using." The redesign's version is a *narrative*.

### 3.8 The Eight Magic Tiers

The original has an 8-tier magic system where each character's element can be leveled from 1 to 8 by using it. The redesign keeps the 8-tier structure but changes the *unlock conditions* for the higher tiers.

**Tier 1: the base's basic attack, always available.** Unlocked at chapter 1 (Serge's start). Unlocked for other bases when they join the party.

**Tiers 2-7: support techs and open-slot techs, unlocked by element level.** Each base's element levels up as in the original — by using the element in combat. The element level determines which tier's techs are accessible. At element level 2, tier 2 techs unlock. At level 3, tier 3 techs unlock. Etc. The progression is "use the element, the element gets stronger, new augments become available."

**Tier 8: the base's ultimate tech, unlocked by chapter progression.** The tier-8 tech is not unlocked by element level alone — it is unlocked by *reaching the chapter where the base's story reaches its climax*. For Serge, that is the chapter where the form-return happens. For Kidd, that is the chapter where the thief's past is resolved. For Nikki, that is the chapter where the show is staged. Etc. The tier-8 tech is the *narrative payoff* of the base's arc.

**The element-level cap before tier 8.** Before the tier-8 tech unlocks, the element is capped at level 7. This means the player can level the element to 7 by chapter X, but the level-8 cap is held back until the story unlocks it. The reason: the tier-8 tech is too strong to be available before the story has earned it. The element-level cap is the design's mechanism for pacing.

**Why 8 tiers and not 6 or 10.** 8 is the original's number, and the redesign honors it because it is a well-balanced count for the design space. 6 would be too few — not enough differentiation between bases. 10 would be too many — the player would lose track of which tier is which. 8 is the sweet spot where each tier has clear identity (1-2 are "novice," 3-4 are "competent," 5-6 are "skilled," 7-8 are "master").

### 3.9 The Ten Chapters

The original has a story divided into "arcs" (Another World, Home World, etc.) with A/B branches. The redesign has 10 chapters of party progression, no branches, all major events in a single sequence.

**Chapter 1: Serge alone.** The story opens. Serge wakes on the beach. The player learns the basic attack line (Dash and Slash). The chapter ends with Serge setting off to investigate his alternate self.

**Chapter 2: Serge + Kidd.** The player meets Kidd. Red Pin is the new basic attack line for the second slot. The party grows to 2. The chapter covers the Lizard Coast, the first dungeon, and the first boss.

**Chapter 3: Serge + Kidd + Nikki.** The player meets Nikki. Grand Finale is the third basic attack line. The party grows to 3. The chapter covers Nikki's recruitment, the Guldove subplot, and the second boss.

**Chapter 4: Serge + Kidd + Nikki + Glenn, then the form-change.** Glenn joins. Dash and Gash is the fourth basic attack line. The party grows to 4. The chapter covers Glenn's recruitment, the Viper Manor subplot, and ends with the form-change to Lynx. **This is the act-1 break.**

**Chapter 5: Lynx + Kidd + Nikki + Glenn + (Herle joins at end).** The party is now Lynx (White, dark techs), Kidd, Nikki, Glenn. The chapter is the Lynx arc proper: the dark Fort, the dragon trials, the dark-tech unlocks. Herle is *not* yet a base — she is a story character. At the end of chapter 5, Herle is recruited as the Black base.

**Chapter 6: Lynx + Kidd + Nikki + Glenn + Herle, then the form-return.** The party grows to 5. The chapter covers Herle's arc, the dark Fort climax, and ends with the form-return. **This is the act-2 break.** Herle absorbs the dark techs from the Lynx form.

**Chapter 7: Serge + Kidd + Nikki + Glenn + Herle, light techs unlock.** Serge is back. Angelic Pip support slot unlocks. The light techs become available. The chapter is the post-form-return denouement and the setup for the Sea of Eden.

**Chapter 8: Serge + Kidd + Nikki + Glenn + Herle + Norris.** Norris joins. Top Shot is the sixth basic attack line. The party grows to 6 (full). **This is the act-3 break.** The chapter is Norris's recruitment and the journey to the Frozen Flame.

**Chapter 9: The full party, the Frozen Flame.** The story's climax. All 6 bases with full support grids. The chapter is the dungeon, the boss gauntlet, the resolution of the time paradox. The tier-8 techs unlock as the story beats land.

**Chapter 10: The full party, the epilogue.** The story resolves. The party is at full strength. The epilogue plays out. The player has access to all side content, all supports, all augments. The tier-8 techs are fully unlocked. The chapter is the ending and the New Game+ unlock.

**Why 10 chapters.** The original has approximately 8-10 "major story beats" depending on how you count, plus 12+ hours of recruitment and side content. The redesign's 10 chapters correspond roughly to the original's major beats, in a single linear sequence. The 10-chapter count is also a clean count for a 30-hour JRPG: 3 hours per chapter × 10 chapters = 30 hours, with side content and supports adding another 5-10 hours.

**Why no A/B branches.** The original's A/B branches (Another World vs. Home World) are a 1999 design choice driven by cartridge space and the "play it twice" marketing pitch. The redesign's single-loop approach is a modern choice: a 30-hour single playthrough is more honest than two 15-hour playthroughs that converge anyway. The original's branches add replay value at the cost of coherence; the redesign trades replay value for a tighter single experience.

### 3.10 The Six-Character Party in Combat

The original has a 3-character party and a 3-vs-3 (or 3-vs-6) combat setup. The redesign has a 6-character party and a 6-vs-6 combat setup. This is a significant change and needs a paragraph of its own.

**The 6-character party fills the field.** With 6 characters on the field, the screen is busy. The HD-2D visual style accommodates this with character sprites at a smaller scale than the original's pre-rendered style. The party is arranged in a 2-row formation: front row (3 characters) and back row (3 characters). The back row takes less damage and deals less damage; the front row takes full damage and deals full damage. This is a positioning layer that the original does not have (the original's 3-character party has a single row).

**The 6-character party changes the action economy.** Each turn, the player picks actions for all 6 characters. The action pool is 6 actions per turn. The support-tech system (one tech per character per turn) means the player is making 6 choices per turn, but each choice is *which augmentation to apply*, not *which tech to use*. The total cognitive load is similar to the original (the original has 3 characters × 1 tech choice per turn = 3 choices), but the *kind* of choice is different — more about timing and status-buffing, less about picking the right nuke.

**The 6-character party and the original's "weakest character" problem.** In the original, recruiting 40+ characters means most are stat-similar and the player can use anyone. The redesign's 6-base structure eliminates the "weakest character" question because there are only 6 bases, and each is designed to be useful. The supports are a different question (some are clearly better than others in the augmentation model), but the player picks which supports to use, so it's a choice, not a trap.

### 3.11 The HD-2D Visual Style

The original uses pre-rendered 2D backgrounds with 3D character models (a common late-PS1/Saturn-era trick). The redesign uses the HD-2D style: 2D character sprites over 2D/2.5D backgrounds. The visual approach is a Phase 1 commitment, not a Phase 3 retrofit.

**Why HD-2D.** The HD-2D style (popularized by *Octopath Traveler* and *Triangle Strategy*) is a deliberate visual language that signals "modern JRPG" without committing to 3D or to pixel art. It uses 2D character sprites (often with limited animation frames) over 2.5D backgrounds (3D geometry rendered to look 2D, with parallax layers, lighting effects, and depth-of-field). The result is a "diorama" feel that suits a JRPG's spatial storytelling.

For the redesign, HD-2D means:

- Character sprites are 2D, with a small number of animation frames (walk, attack, hurt, idle). No 3D character models, no skeletal animation.
- Backgrounds are 2.5D: 3D meshes with 2D textures, lit dynamically, with parallax and depth effects.
- Combat uses the same visual style: 2D character sprites on a 2.5D battlefield, with 3D camera angles (slight rotation, zoom) for dramatic effect.
- The UI is a modern JRPG UI: clean panels, readable fonts, status icons. Not a recreation of the original's UI.

**Why not the original's pre-rendered approach.** Pre-rendered backgrounds are a 1999 technique that requires high-resolution source art and a fixed camera. The HD-2D approach is more flexible (the camera can move, the lighting can change) and is the modern standard for "2D-feeling JRPGs with modern production values." It is also easier to author in Godot 4 (no pre-render pipeline needed) and easier for the agent to verify (the 2D sprites are simple PNG sequences).

### 3.12 The Minigames Are Removed

The original has several minigames (the dart game, the chrono-puzzle, the casino, the racing minigame, the cooking minigame). The redesign removes all of them.

**Why.** Minigames consume design space. A JRPG's design budget is finite: every minigame is a system the team has to design, implement, balance, test, and debug. The original's minigames are not deep enough to justify their cost (most are 5-minute distractions), and they pull the player out of the main story loop. The redesign's commitment is to the main 30-hour story, with no detours.

**What fills the space.** The minigames' design budget is redirected to the main story's supporting cast interactions. The redesign's promise is "every support character has a real scene with their base." That promise requires writing, scripting, and playtesting budget that the original did not spend on supports. The redesign's budget is spent there instead.

**The casino and economy.** The original has a casino for money-farming. The redesign's economy is simpler: the player earns gold from combat, spends it on gear and items, and the gear is balanced so that the player does not need to grind. No casino, no mini-economy, no gambling mechanics.

### 3.13 The Storyline Integration

The original's story has A/B branches that converge at the end. The redesign collapses this into a single central loop that hits all major events. The chapter structure (§3.9) is the single loop.

**What "hits all major events" means.** Every major event from the original (the form-change, the dragon trials, the Frozen Flame, the time-paradox resolution, the Kid-past arc, the Nikki-show arc, the Glenn-revenge arc, the Herle-magic arc, the Norris-hunting arc) is in the redesign. The difference is the *order* and the *branches*. The redesign's order is: open, recruit, recruit, recruit, form-change, dark arc, form-return, light unlock, recruit, climax, epilogue. The original's order is: open, branch-A-arc, branch-B-arc, converge, climax, epilogue. The redesign's order has all arcs (Kid, Nikki, Glenn, Herle, Norris) interleaved with the main plot, not separated by branch.

**Why this is better.** The original's branches force the player to choose which characters to recruit (because the recruitment is branch-gated). The redesign's single loop lets the player recruit everyone in a single playthrough, with the story beats naturally spaced. The redesign also has a tighter *thematic* arc: the form-change happens at a specific chapter boundary, the form-return happens later, and the light-tech unlock is the narrative payoff of the return. The original's branches dilute this by letting the player sequence the beats differently.

### 3.14 The Main Cast Focus

The original has 40+ characters, most of whom are silent recruits. The redesign has 6 main characters and 36 supports. The 6 main characters are full characters with names, motivations, dialogue, and arcs. The 36 supports have *more* than the original's silent recruits — they have interaction scenes, dialogue, and story beats — but less than the 6 bases.

**What "expanded interaction scenes" means.** Each support has at least one major scene with their base: a recruitment scene, a bonding scene, a story-relevant scene. The scenes are not "go here, say this, recruit done" — they are *narrative* scenes with emotional weight. The original's "you talked to this NPC, they're in your party now" is replaced with "you went on this quest with this character, you learned their backstory, you saw their motivation, and they joined because of the story."

**Why this matters.** The original's "silent recruitment" pattern is a design artifact of the 3-character party limit. With 6 bases, the recruitment is already a bigger deal (each base is a chapter event), and the supports are the *texture* around the bases. The player spends 30 hours with the 6 bases and 36 supports; the supports need to be characters, not stat blocks.

**The 6 bases' arcs.** Each base has a story arc across the chapters they are present in. Serge's arc is the form-change and form-return. Kidd's arc is the thief-past revelation. Nikki's arc is the show staging. Glenn's arc is the family-revenge. Herle's arc is the magic-and-identity. Norris's arc is the hunter-and-the-hunted. These arcs are *interleaved* with the main plot, not separated.

### 3.15 What the Redesign Is Not

The redesign is not "a complete rewrite of Chrono Cross." It is a structured reinterpretation that takes the original's cast, world, and story beats and reorganizes them into a coherent modern JRPG. Specific things the redesign does *not* do:

- It does not change the original's setting (the world of El Nido, the Frozen Flame, the Dragon Gods).
- It does not change the original's tone (a melancholy, parallel-worlds story with a strange cast).
- It does not change the original's character names or visual designs (the bases are the original characters, the supports are the original characters).
- It does not change the original's music (because the redesign does not have original music; it has placeholder audio, see §2.4 non-goal 10).

What the redesign *does* change:

- Party size (3 → 6).
- Combat identity (40+ characters with shallow kits → 6 bases with deep kits, 36 supports with focused augments).
- Story structure (A/B branches → single loop, 10 chapters).
- Pip mechanic (one-battle buff → story-form reward).
- Minigames (present → removed).
- Recruitment (silent → scripted scenes).

These changes are extensive but the *bones* of the original are preserved. A player who has played the original will recognize the story, the cast, the world. A player who has not will not know they are playing a "remaster" — they will just be playing a 30-hour JRPG with a melancholy tone and a strange cast. Both audiences are served.

### 3.16 The Locked-Design Summary

For convenience, the locked design is summarized here in one place:

- **6 bases, one per element:** Serge/Lynx (White), Kidd (Red), Nikki (Blue), Glenn (Green), Herle (Black), Norris (Yellow).
- **36 supports:** 3 combined units (Leena+Poshul, Korcha+Macha, Turnup+NeoFio) + 33 standalone, 6 per base.
- **8 magic tiers:** tier 1 is the base's basic attack, tier 8 is the base's ultimate, tiers 2-7 are support augments and player-choice augments.
- **Basic attack line + support techs + open grid slots:** each base has a basic attack that is always present, support techs that augment it, and 1-2 open grid slots for player choice.
- **6-character party:** up from 3, with 2-row formation.
- **10 chapters:** party progression from 1 → 6, with story arcs interleaved.
- **Pip mechanic reframed:** dark techs during Lynx form, dark techs migrate to Herle on form-return, light techs unlock for Serge post-return.

This summary is the design's *contract*. The rest of the document (engine selection, pipeline, agent workflow) exists to make this design buildable.

### 3.17 Decisions Needed

A small number of design points in this section were committed to as working assumptions rather than locked choices. They are flagged here for the user's review:

- **Open grid slot count and tier:** §3.6 commits to "1 open slot at tier 5" as a working assumption. The locked design says "1-2 open slots" without specifying the tier. Recommendation: 1 slot at tier 5, with the second slot (if added) at tier 7.
- **The exact support tech effects** (e.g., "Dash and Slash with Sleep at 30% chance") are illustrative, not locked. The actual augmentation effects per support per base will be designed in a later loop or in the implementation phase.
- **The chapter-to-base join order** (§3.9) is a working assumption. The exact chapter numbers and the exact scenes for each base's join can be reordered if the story demands.
- **The minigame removal list** (§3.12) is the original's full minigame list. If the user wants to keep any, they need to be re-budgeted into the design space.

These decisions are not blocking the document's continuation. §4 (Engine Selection Criteria) is unblocked and can be drafted next.

---

## 4. Engine Selection Criteria

### 4.1 Why Criteria Before Comparison

A wrong comparison is one that picks the wrong winner. A wrong criteria set is one that picks a winner for the wrong reasons. This document already has Godot 4 locked as the engine choice. The point of this section is not to relitigate that choice — it is to make the criteria the choice rests on *legible*, *defensible*, and *falsifiable*. If a future maintainer asks "why not Unity?" or "why not Godot 3?" they should be able to read §4 and §5 and trace the answer back to a specific, weighed criterion. If they ask "should we have used Unreal?" the same trace should produce a specific reason we did not.

The criteria in this section are also the criteria §10 (PS1 era challenges) and §11 (toolchain) will be evaluated against. They are the spine. Comparison is a one-time exercise; criteria are reusable.

### 4.2 The Two-Audience Constraint

A standard engine selection answers the question "which engine is best for a human team to ship a game in?" This project has a different question: "which engine is best for an AI agent to build a *remaster* of a 1999 PS1 JRPG in, working under a 'mostly autonomous with design gates' autonomy model, where the user is the project lead and acts as a review gate rather than a daily contributor?"

That breaks into two distinct audiences the engine must serve:

- **The player.** The end user who runs the final .exe / .apk / .html. For them, the engine is invisible — they only see the result. The engine must produce a 30-hour JRPG at 60fps on a low-spec PC, with the visual quality of an HD-2D style game, with no crashes, with deterministic save/load, and with all the content from a 1999 game plus the Phase 3 redesign. The player does not care what engine is used.

- **The AI agent.** The day-to-day user of the engine during development. For them, the engine is the *interface*. Every API call, every file format, every editor concept (scene tree, node, resource, autoload) is something the agent has to be able to read, write, search, refactor, and reason about without human help. The engine's API surface, file formats, and tooling integration become first-class selection criteria in a way they would not be in a human-led project.

These two audiences pull in different directions. The player's interests favor mature engines with proven performance, large asset ecosystems, and stable cross-platform export. The agent's interests favor text-first file formats, scriptable workflows, headless operation, and APIs that map cleanly to search and refactor tools. A good engine selection is one that finds an engine that scores well on both axes simultaneously, not one that optimizes for the human developer and accepts the agent as a degraded user.

### 4.3 Hard Technical Criteria

These are the criteria where failure is a project-killer. The engine must meet all of them; it does not get a partial score.

**HT-1. 2D-first rendering pipeline.** Chrono Cross is a 2D game. The Phase 3 redesign uses an HD-2D style (2D characters over 2D/2.5D backgrounds). The engine must be able to render 2D efficiently without dragging in a 3D pipeline we do not need. A 3D engine with 2D as an afterthought (e.g., Unreal) is a bad fit because every 2D operation goes through a 3D abstraction layer that adds complexity the agent has to reason around. A 2D-native engine (Godot, GameMaker) is a better fit.

**HT-2. Pixel-art capable at modern resolutions.** The 1999 game runs at 240p; the remaster targets 1080p / 1440p. The engine must support pixel-perfect rendering at 1x, 2x, 3x, 4x scales with integer scaling, and must support HD-2D's "2D character over 2.5D background" composition (parallax, lighting, normal maps on 2D sprites) without requiring a custom renderer. This criterion is about *having the right primitives*, not about *having the best of them* — most modern engines can do this; the question is how clean the API is.

**HT-3. Mature scripting language with first-class static type support.** The agent writes code. The code must be searchable, refactorable, type-checkable, and IDE-able. GDScript (Godot), C# (Unity, Godot), GML (GameMaker), and JavaScript/TypeScript (some web-first engines) all qualify. Lua (LÖVE, Defold) is borderline — dynamic typing means the agent's static-analysis tools have less to work with, and most refactoring tools in Lua are weaker. Blueprints (Unreal) do not qualify — visual scripting is a non-starter for an agent that cannot reliably click nodes in a graph.

**HT-4. Headless build and run.** The agent must be able to compile, run tests, and produce builds without a graphical environment. This rules out engines whose build pipeline is GUI-dependent or whose test framework requires a windowing system. Godot 4 has a documented `--headless` mode. Unity has Unity Cloud Build but the local build is editor-bound. Unreal has command-line build via UAT but the test framework (Functional Tests) requires the editor running in a specific mode. Criterion: there must exist a documented path to "build, run automated tests, produce a .exe" from a non-interactive shell.

**HT-5. Cross-platform export to Windows + Linux + Web.** The user runs Windows (per the cron environment). The player audience is also likely Windows. But a single-platform engine is a non-starter for a modern remaster — the project is "AI-agent-led, for skill development" and the user's skills grow with the engine's reach. A target list of Windows + Linux + Web (HTML5) is the minimum. Mobile is a stretch goal. Console export is out of scope for a clean-room fan project.

**HT-6. Open file formats.** The engine's project files must be readable as text, diff-able in version control, and merge-able in collaborative work. Godot's `.tscn` and `.tres` are text-first (binary mode exists but is opt-in). Unity's `.unity` files are YAML but often mangled by binary imports. Unreal's `.uasset` files are binary with no clean diff path. Criterion: a maintainer should be able to read a project file in `cat` and understand it.

**HT-7. Hot-reload or fast iteration.** The agent's workflow is iterative. The engine must support a fast edit-test cycle. Godot's "stop running, edit, run again" loop is on the order of 5-15 seconds. Unity's "domain reload" is 5-30 seconds. Unreal's "live coding" is 5-15 seconds but only for C++ changes; Blueprint changes still require editor reload. Criterion: an edit to a script should produce a runnable result in under 30 seconds without a full editor restart.

**HT-8. Stable long-term LTS posture.** The engine must have a stated LTS (long-term support) commitment or equivalent stability guarantee. A 1999 game remaster is a multi-year project; the engine's API must not break under us mid-project. Godot 4.x has no formal LTS but has a stable backport policy. Unity has LTS releases (e.g., 2022 LTS, 2023 LTS) with 2-year support windows. Unreal has a 5-year support commitment. Criterion: a release from year 1 should still run code from year 4 without a forced migration.

### 4.4 Soft Criteria

These are the criteria where the engine gets a partial score. Tradeoffs are acceptable.

**S-1. License.** MIT / Apache 2.0 / zlib (permissive) scores highest. Custom EULA (Unity, Unreal) scores low. A permissive license means the project can be redistributed, the user owns what they build, and there is no per-seat or per-revenue surprise later. Godot 4 is MIT. Unity's runtime is free but its terms of service are a moving target. Unreal is free but the 5% royalty kicks in above $1M revenue (irrelevant for a fan project, relevant for a skill-development project that might evolve).

**S-2. Community size and knowledge base.** A bigger community means more Stack Overflow answers, more tutorials, more third-party plugins, more answered GitHub issues. The agent benefits from this because the agent's training data is a snapshot of public knowledge; a popular engine has more public knowledge to draw on. Unity is the largest. Godot is the fastest-growing. Unreal is large but skews toward 3D/AAA. GameMaker is small but focused.

**S-3. Asset ecosystem.** 2D JRPGs need sprites, tilesets, fonts, music, SFX, dialogue UI, save-game systems, turn-based combat frameworks. An engine with a strong 2D asset ecosystem (Godot, Unity) lets the project use proven third-party assets; an engine without one (Unreal for 2D, LÖVE) means writing more from scratch. The user has explicitly said the project is "for skill development" — meaning *some* from-scratch is desirable, but reinventing a save-game system that already exists is wasted effort.

**S-4. AI-agent integration potential.** The engine should not actively resist AI-agent workflows. Godot's text-first project files, CLI tooling, and headless mode are AI-friendly by design. Unity's editor-bound workflows, package manager that requires editor login, and YAML-but-not-really files are AI-resistant. Unreal is a mixed bag — command-line build is there, but Blueprint navigation requires a graphical editor the agent cannot use. This criterion is the "agent as a first-class user" test.

**S-5. Modifiability by the player.** The locked design says "modifiability is a Phase 1 requirement, not a Phase 3 retrofit." A 2026 player expects to be able to mod the game — swap sprites, edit dialogue, add characters, change balance. The engine should support modding out of the box, or at least not fight it. Godot's project file format makes modding straightforward: a modder edits `.tscn` files. Unity's `.unity` files are editable but Unity's serialization makes clean mods harder. Unreal's `.pak` files are explicitly modding-hostile.

**S-6. Performance at scale for a JRPG.** A 30-hour JRPG with 6-character parties, ~60 enemy types, ~100 maps, 10 chapters of content. The engine must handle this scale without falling over. This is not a hard criterion because modern hardware is forgiving; even a poorly-optimized JRPG runs fine on a 2026 desktop. But engines with known scaling issues (Unity's GC spikes, Unreal's C++ compile times) are soft negatives.

**S-7. Future-proofing for AI tooling.** The engine's roadmap should include AI-friendly features — LLM-assisted scripting, agent-compatible APIs, programmatic content generation. Godot 4 has discussed these in roadmap discussions. Unity has Muse (a paid AI product). Unreal has no specific AI-agent features. This criterion is a weak signal but the user is building an "AI-agent-led" project, so engines that *lean into* AI tooling are a better strategic fit.

### 4.5 Anti-Criteria

These are criteria we are explicitly *not* optimizing for. Naming them is important because they would otherwise look like gaps in the criteria set.

**A-1. AAA 3D rendering quality.** We are not shipping a 3D AAA game. Engines that score on photorealistic 3D (Unreal's Lumen, Unity's HDRP) are not getting points for that. We do not care.

**A-2. Console certification.** We are not shipping to PlayStation / Xbox / Nintendo. Engines with first-party console SDKs (Unity Pro, Unreal) are not getting points. We do not care.

**A-3. Multiplayer / networking.** Chrono Cross is single-player. We do not care about network code quality, dedicated server support, rollback netcode, or matchmaking.

**A-4. Visual fidelity at the cost of asset count.** The Phase 3 redesign favors *more content* (6 characters with deep kits, 10 chapters, expanded cast) over *fewer assets at higher fidelity*. Engines that make individual assets look amazing at the cost of asset count (Unreal) are a soft negative.

**A-5. Industry adoption / resume value.** This project is "for skill development," but the user is not optimizing for hireability. Unity's industry adoption is a real benefit, but it is a *soft* benefit — the user's *own skills* matter more than the engine's industry footprint.

**A-6. Built-in asset store.** A large asset store is a soft positive (S-3) but a *built-in* one is not on the critical path. We will evaluate whether the asset store is worth using per-asset, not as a category.

### 4.6 Evaluation Methodology

The criteria above get translated into a scoring matrix in §5 (Engine Comparison). This section establishes the methodology so the matrix is not a vibes-based exercise.

**Methodology principles:**

- **Each criterion is scored 0-3.** 0 = fails. 1 = partial / with caveats. 2 = meets. 3 = exceeds. The "exceeds" tier is reserved for criteria where the engine actively goes beyond the requirement (e.g., a permissive license gets 3; a custom EULA gets 0-1; a "we might sue you" gets 0).

- **Hard criteria are gates, not scores.** A 0 on any HT-criterion disqualifies the engine. No engine is in the running if it cannot pass all 8 hard criteria.

- **Soft criteria are weighted.** Weighting is on a 1-3 scale: 1 = nice to have, 2 = important, 3 = critical. The weights are set by the project lead (the user) in §5's table. The agent proposes a default weighting; the user can override.

- **Anti-criteria are not scored.** They are named so they are not confused with gaps. A reader who sees "no 3D rendering" criterion and asks "why not?" gets the answer in this section, not in a deficiency.

- **The total score is a relative ranking, not an absolute measure.** A score of 47/60 is not "good enough" by itself. It is good enough *relative to the next-highest-scoring engine*. The methodology produces a ranking, not a passing grade.

- **Ties are broken by hard criteria, then by S-4 (AI-agent integration).** When two engines score within 2 points of each other, the tiebreaker is "which one is better for the agent's day-to-day workflow?" This is the project's defining constraint and gets the final word.

**Worked example: a hypothetical third engine.**

Suppose the criteria set were applied to three engines: Godot 4 (locked choice), Unity 2023 LTS, and a hypothetical "Engine Z." Suppose the scores were:

- Godot 4: 47/60
- Unity 2023 LTS: 44/60
- Engine Z: 45/60

A naive ranking would put Godot 4 first, Engine Z second, Unity third. But if Engine Z scored a 0 on HT-4 (headless build), it is *disqualified*, not ranked. The result is Godot 4 first, Unity second, Engine Z out. The hard criteria are not a tiebreaker — they are a gate.

If, instead, all three passed hard criteria, and Engine Z scored 0 on S-1 (license) but Unity and Godot both scored 3, then Engine Z's 45 becomes "45 in a tier we cannot use" and it falls to the bottom. The methodology is designed so that a single critical miss is not a "you scored well, but…" — it is a "you are out."

### 4.7 The Strategic Position

This section closes with a position statement. The criteria above favor a 2D-native, permissively licensed, text-first, headless-friendly engine with a growing community. That is *not* a description of Godot 4 in particular — it is a description of a category of engines. Godot 4 happens to be the strongest representative of that category in 2026, but the criteria do not assume the answer.

The point of stating the position is so that the comparison in §5 is not "is Godot 4 better than Unity?" but "which engine best fits the criteria set, and does Godot 4 win on its own merits or by default?" If a reader disagrees with the criteria, they can propose a different engine. If a reader agrees with the criteria, they should be able to read §5 and see the answer.

### 4.8 Decisions Needed

The criteria set in this section is proposed, not locked. Three points are flagged for the user's review:

- **HT-2 (pixel-art capable) vs. HD-2D**: the criterion says "pixel-perfect rendering" and "HD-2D composition" as if they coexist. In practice, HD-2D leans on 2.5D effects (lighting, normal maps) that are weaker in pure pixel-perfect renderers. Should this be two separate criteria (HT-2a pixel-perfect, HT-2b HD-2D effects)? Recommendation: yes, split. The scoring in §5 would be cleaner.

- **S-7 (future AI tooling) weight**: this is set to 2 (important) as a default. The user may want it as a 3 (critical) given that "AI-agent-led" is the project's defining feature, or as a 1 (nice to have) if they consider it speculative. Recommendation: 2. The 2026 roadmap for engine AI tooling is not mature enough to call it critical, but it is not speculative enough to dismiss.

- **Anti-criteria completeness**: this section names 6 anti-criteria. The user may have additional ones (e.g., "no real-time strategy features," "no VR/AR support," "no in-app purchase / monetization"). If so, list them and they will be added.

These are not blocking the document's continuation. §5 (Engine Comparison) is unblocked and can be drafted next.

---

## 5. Engine Comparison (Godot vs Others)

### 5.1 What This Section Is For

§4 established the criteria. §5 applies them. The locked design already names Godot 4 as the engine — this section is not a re-decision, it is a *defense* of the decision in a form that survives a future maintainer asking "why?" The point is to make the answer traceable: any reader should be able to read §4's criteria, read §5's scoring, and see why Godot 4 wins (or, if it does not, see exactly which criterion it lost on and what that costs). The format is a scoring matrix, but the matrix is not the section — the matrix is the *evidence*; the prose around it is the *argument*.

The engines compared are: **Godot 4** (the locked choice), **Unity 2023 LTS**, **Unreal Engine 5**, **GameMaker Studio 2**, **LÖVE 2D**, **Defold**, and **RPG Maker MZ** (the last because the user has a research file on RPG Maker MV specifically, and the prior project was RPG-Maker-adjacent — RPG Maker deserves an explicit "no" rather than being silently ignored). The set is not exhaustive (Phaser/PixiJS, Cocos2d-x, MonoGame, Solar2D, Stride, and others are out of scope), but it covers the categories that matter: 2D-native commercial engines, 2D-first indie engines, 3D engines with 2D support, and the legacy JRPG-maker that is the obvious alternative.

A note on the worked example in §4.6: that example used a hypothetical "Engine Z" to demonstrate the methodology. §5 applies the same methodology to real engines, with a working assumption that the user's prior RPG Maker research (`rpgmaker_mv_research_and_poc_plan.md`) is informative on RPG Maker's strengths and weaknesses but not binding on the final decision.

### 5.2 Scoring Methodology (Recap and Refinement)

§4.6 defined the methodology. The version used in §5 is the same with two refinements forced by applying it to real engines:

- **Weighting is per-criterion, per-project, set by §5's prose, not by the agent's default.** §4.6 said "the agent proposes a default weighting; the user can override." §5 commits to specific weights and flags which ones are most important to the user. The weights are the user's call, not mine.
- **"Meets" (2) is a positive score; "exceeds" (3) is rare and means the engine does something the criterion did not ask for.** Godot 4's MIT license is a 3 because permissive licenses are not required (HT and S-1 are different criteria), but Godot 4 actively exceeds the project needs. Unity's runtime license is a 1 because the engine technically allows what we need but with a moving-target ToS that we cannot rely on. This distinction matters when total scores are within 2 points.

The hard criteria (HT-1 through HT-8) are gates. A 0 on any one disqualifies the engine. The §5 table will mark this clearly — disqualified engines still get listed for completeness, but their rows are struck through and they appear below the line in a "Disqualified" section.

### 5.3 The Scoring Matrix

The table below applies §4's criteria to each engine. Scores are 0-3 as defined in §4.6. Weights (W) are 1-3 as defined in §4.6; they are set in §5.4. Total = sum(score × weight) for all soft criteria, with hard criteria as gates.

| Criterion | W | Godot 4 | Unity 2023 LTS | UE 5 | GameMaker S2 | LÖVE 2D | Defold | RPG Maker MZ |
|---|---|---|---|---|---|---|---|---|
| HT-1: 2D-first rendering | gate | 3 | 2 | 1 | 3 | 3 | 3 | 3 |
| HT-2: pixel-art at modern res | gate | 3 | 2 | 2 | 3 | 3 | 2 | 3 |
| HT-3: typed scripting | gate | 3 | 3 | 2 | 2 | 0 | 1 | 1 |
| HT-4: headless build/run | gate | 3 | 2 | 2 | 1 | 3 | 2 | 0 |
| HT-5: cross-platform Win/Linux/Web | gate | 3 | 3 | 2 | 2 | 2 | 3 | 1 |
| HT-6: open file formats | gate | 3 | 1 | 0 | 2 | 3 | 2 | 0 |
| HT-7: hot-reload | gate | 3 | 2 | 2 | 3 | 2 | 2 | 1 |
| HT-8: LTS posture | gate | 2 | 3 | 3 | 2 | 1 | 2 | 2 |
| S-1: License | 3 | 3 | 1 | 1 | 2 | 3 | 3 | 1 |
| S-2: Community | 2 | 3 | 3 | 3 | 2 | 2 | 1 | 2 |
| S-3: Asset ecosystem (2D JRPG) | 2 | 2 | 3 | 1 | 2 | 1 | 1 | 3 |
| S-4: AI-agent integration | 3 | 3 | 1 | 1 | 2 | 3 | 2 | 0 |
| S-5: Modifiability | 2 | 3 | 1 | 1 | 2 | 3 | 1 | 1 |
| S-6: Performance at JRPG scale | 2 | 3 | 3 | 3 | 2 | 2 | 2 | 2 |
| S-7: Future AI tooling | 2 | 2 | 2 | 1 | 1 | 1 | 1 | 0 |
| **Weighted total (soft)** | — | **47** | **40** | **29** | **35** | **39** | **31** | **21** |

Hard criteria are gates. If a row has a 0 in the hard-criteria block, the engine is disqualified. Reading the table:

- **Godot 4**: passes all 8 hard criteria. Weighted soft total: 47.
- **Unity 2023 LTS**: passes all 8 hard criteria. Weighted soft total: 40.
- **UE 5**: passes all 8 hard criteria. Weighted soft total: 29.
- **GameMaker Studio 2**: passes all 8 hard criteria. Weighted soft total: 35.
- **LÖVE 2D**: FAILS HT-3 (Lua, no static typing). Disqualified. Total listed for reference: 39 (would have been 2nd).
- **Defold**: passes all 8 hard criteria. Weighted soft total: 31.
- **RPG Maker MZ**: FAILS HT-4 (no headless build) and HT-6 (closed binary project format). Disqualified. Total listed for reference: 21.

The hard-criteria gates explain why LÖVE 2D and RPG Maker MZ do not get a "but they scored well on S-*!" reprieve. LÖVE 2D's 39 would have put it 2nd, ahead of Unity — but its HT-3 failure is a project-killer for an AI-agent workflow that needs type-checked, refactorable code. RPG Maker MZ's 21 is the lowest even before disqualification; the hard-criteria failure just formalizes the obvious.

### 5.4 Why These Weights

The weights in the table above are not arbitrary. They follow the project's defining constraints, in priority order:

- **S-1 (License) and S-4 (AI-agent integration) get weight 3.** These are the two criteria most directly tied to the project's viability. License because a moving-target EULA (Unity) or a 5% royalty clause (Unreal, but above $1M only) is a real risk for a multi-year project. AI-agent integration because it is the project's defining feature (§1.2, §4.2). If the engine fights the agent, the project does not work, regardless of other scores.
- **S-2, S-3, S-5, S-6 get weight 2.** These are important but not critical. A weak community is workable if the engine is small but stable. A weak asset ecosystem is workable if the engine is easy to build assets for. Modifiability and performance are similar — both matter, but neither is a single-criterion deal-breaker.
- **S-7 (Future AI tooling) gets weight 2.** As discussed in §4.4, 2026 engine AI tooling is not mature enough to call critical. The signal is a tiebreaker, not a gate.

The weights are the user's call. If S-7 is critical (weight 3), Godot 4 widens its lead because most engines do worse on future-AI-tooling than they do on current-AI-agent-integration. If S-2 is weight 3 instead of 2, Unity ties Godot 4 on community but loses elsewhere. The matrix in §5.3 is a snapshot — the user can re-weight and the rankings move.

### 5.5 Engine-by-Engine Justification

The matrix is the headline. The prose is the body. This subsection walks through each engine's scores row-by-row, explaining the *why* behind the numbers and flagging where my judgment might be wrong. The goal is that a reader who disagrees with a score can see my reasoning and counter it with specifics, not vibes.

**Godot 4 (47/60).** Godot's strength is that it is purpose-built for the use case: a 2D-first, MIT-licensed, text-first, headless-friendly engine with a growing community and an active AI-friendly roadmap. Its weakness is the soft ones: the 2D asset ecosystem is smaller than Unity's (S-3: 2 vs. 3), the LTS posture is informal compared to Unity/Unreal (HT-8: 2 vs. 3). The trade is the right trade for this project — the things Godot 4 scores 3 on (S-1, S-4, S-5, HT-6) are the things that determine whether the project is buildable by an agent at all, and the things Godot 4 scores 2 on (HT-8, S-3) are things the project can compensate for with time and effort. **One honest flag:** I have not yet personally benchmarked Godot 4's performance for a 6-character-party JRPG with 60+ techs per turn and ~100 maps loaded/unloaded dynamically. The 3 on S-6 is an extrapolation from the 2024-2025 community reports of Godot 4.x performance improvements. If Godot 4 has hidden performance cliffs at this scale, S-6 may need to be revised downward in §6's deep dive.

**Unity 2023 LTS (40/60).** Unity's strength is the asset ecosystem and community — it has the largest 2D JRPG asset ecosystem of any engine (S-3: 3), the largest community (S-2: 3), and a formal LTS commitment (HT-8: 3). Its weakness is the parts that matter most for an AI agent: the .unity file format is YAML in theory but binary in practice (HT-6: 1), the editor-bound workflow resists headless automation (HT-4: 2), and the runtime EULA has changed twice in 3 years (S-1: 1). Unity 2023 LTS would be the right choice for a *human-led* project of this scope. For an *agent-led* project, the workflow friction is the dominant cost. **The honest counter-argument:** Unity has been investing in AI tooling (Muse, Sentis) and in 2026 the editor has CLI modes that did not exist in 2020. If those investments have matured enough by the time we start Phase 1, the HT-4 and HT-6 scores may need to be re-evaluated upward. §6 (Godot 4 Deep Dive) will include a "what would change my mind" sidebar where this is addressed.

**Unreal Engine 5 (29/60).** UE 5 is disqualified by no hard criterion — it passes HT-1 through HT-8. It loses on the soft criteria: license (5% royalty, S-1: 1), modifiability (`.pak` files, S-5: 1), 2D asset ecosystem (S-3: 1), and AI-agent integration (Blueprint navigation requires the editor, S-4: 1). UE 5 is a 3D AAA engine. It can do 2D — Unreal has a 2D paperZD plugin, and Paper2D is still available — but doing 2D in UE 5 is swimming against the engine's grain. The agent's working data would be .uasset binaries (HT-6: 0 is wrong — .uasset has a text-mode option — but for our purposes, the option is rarely used in practice and the agent's tools would be working with binary). The score reflects that UE 5 is the right engine for the wrong job. **The honest counter-argument:** UE 5's Nanite and Lumen are stunning for backgrounds, and an HD-2D game with 2.5D background effects (parallax, lighting, normal maps) could use those. If the Phase 3 redesign decides the visual style is more "3D-rendered backgrounds" than "pixel-perfect 2D," UE 5 becomes a serious candidate. The locked design (HD-2D, 2D characters over 2D/2.5D backgrounds) says this is not the case. If the user disagrees, this is the criterion to revisit.

**GameMaker Studio 2 (35/60).** GameMaker is the closest 2D-native competitor to Godot 4. It scores 3 on HT-1, HT-2, and HT-7, and a respectable 2 on most other criteria. It loses on HT-4 (headless build is partial — there is a CLI runner, but full headless test coverage is weaker), HT-3 (GML is dynamically typed), S-1 (the license is permissive for indies but the EULA restricts "competing engines" and the subscription model is a moving target), and S-4 (GameMaker's CLI is functional but its API surface is more graphical than text). **The honest counter-argument:** GameMaker is a more mature 2D engine than Godot 4 in some ways — it has been used for shipped 2D JRPGs (Undertale, Hyper Light Drifter, for example) and its 2D performance is well-understood. If the project were human-led, GameMaker would be a serious alternative. For an agent-led project, the text-first workflow is the differentiator that puts Godot 4 ahead.

**LÖVE 2D (39/60, but disqualified).** LÖVE 2D's disqualification on HT-3 is the engine's defining limitation: Lua is a beautiful language for small games, but it is dynamically typed, has weak refactoring tooling, and the agent's static-analysis support is much thinner than for typed languages. LÖVE 2D scores 3 on HT-6 (Lua files are text), HT-1 (purely 2D), HT-2 (pixel-perfect), and HT-4 (fully headless — LÖVE is essentially a Lua runtime with a graphics layer). If we did not need typed code, LÖVE 2D would be a strong second place. We do need typed code, and HT-3 is a hard criterion. **The honest counter-argument:** there are typed Lua dialects (Teal, Luau with type annotations, LunarML) and LÖVE has a TypeScript binding community project. None of these are mature enough in 2026 to count as "first-class static type support" per the criterion's wording. If that changes by Phase 1 start, LÖVE 2D becomes a candidate again.

**Defold (31/60).** Defold is a smaller 2D engine, originally developed by King (Candy Crush) and now open-sourced. It scores well on HT-5 (cross-platform) and HT-1 (2D-first), but loses on S-2 (community is small), S-3 (asset ecosystem is small), and S-5 (modding is not first-class). It does pass all 8 hard criteria, so it is not disqualified. Its total is the lowest of the non-disqualified engines. **The honest counter-argument:** Defold's performance is excellent and its message-passing architecture is well-suited to data-driven game design. For a smaller, more polished 2D game, Defold could be a strong choice. For a 30-hour JRPG with the scope of the Phase 3 redesign, the small community and asset ecosystem are the dominant cost. Defold is a "respectable no" rather than a "strong contender."

**RPG Maker MZ (21/60, disqualified).** RPG Maker is the obvious alternative for a JRPG — and the user has a research file on RPG Maker MV that was used in a prior project. The disqualification on HT-4 (no headless build) and HT-6 (closed binary project format) is the technical answer. The non-technical answer is in §3 — the Phase 3 redesign is a substantial departure from RPG Maker's model: 6-character parties (RPG Maker's default is 4), 8 magic tiers with augmentation (RPG Maker's skill system is plug-and-play), 36 supports as modifiers (RPG Maker's actor model is one-script-per-actor), and HD-2D visuals (RPG Maker's tile-based look is the *opposite* of HD-2D). Even if RPG Maker passed the hard criteria, the design would not fit. **The honest counter-argument:** the user's prior RPG Maker research file presumably contains specific knowledge about RPG Maker's capabilities. If that research identifies RPG Maker features that match the Phase 3 redesign better than I am crediting, the disqualification needs to be revisited. §6 (Godot 4 Deep Dive) will include a "RPG Maker Lessons Applied" subsection that translates applicable insights from the research file into Godot 4 patterns. The engine choice does not change, but the design vocabulary might.

### 5.6 The Ties That Did Not Happen

§4.6 said ties are broken by hard criteria, then by S-4. No ties happened in the matrix above — Godot 4 wins by 7 points over Unity, by 12 over GameMaker, and by 18 over UE 5. This is *not* because the criteria set is rigged; it is because the criteria set reflects the project's defining constraints, and Godot 4 happens to be the engine that satisfies them best.

If the user re-weights the criteria (e.g., S-2 to 3, S-3 to 3, S-4 to 2), the rankings would still favor Godot 4 but the gap to Unity would narrow. The break-even point where Unity ties Godot 4 is roughly: weight S-1 at 1, S-2 at 3, S-3 at 3, S-4 at 1, all others as in §5.4. That is a re-weighting that explicitly de-prioritizes the project's defining constraints. **If the user wants to re-weight in that direction, the conversation should include "should we reconsider the project's defining constraints?" not just "should we re-weight?"** A re-weighting that contradicts the project's nature is a sign that the project description needs to change, not that the engine choice needs to.

### 5.7 What the Comparison Does Not Tell Us

A scoring matrix tells us the relative ranking. It does not tell us:

- **Whether the engine can actually ship the design.** A 47/60 score for Godot 4 is a *prior*, not a *guarantee*. §6 (Godot 4 Deep Dive) is where the engine's actual capabilities are tested against the actual requirements. If §6 reveals a showstopper — Godot 4's GDScript is too slow for a 6-character combat with 60+ tech evaluations per turn, or Godot 4's animation system cannot handle the HD-2D parallax we want — the matrix in §5 is invalidated. The matrix is a filter, not a verification.
- **How the engine will age.** The matrix is a 2026 snapshot. The user has indicated this is a multi-year project. Godot 4's current LTS posture (HT-8: 2) is *informal* — the maintainers have a stable backport policy, but no formal LTS commitment. If Godot's governance changes during the project, the score changes. §13 (Risks & Open Questions) will track this.
- **What the engine is bad at.** The matrix scores criteria we care about. It does not penalize the engine for things we don't care about (the anti-criteria in §4.5). A reader looking at the matrix should not conclude "Godot 4 is a 78% perfect engine" — that is the wrong framing. Godot 4 is a 100% fit on the criteria that matter, with some scores of 2 that reflect "good but not category-leading" rather than "deficient."

### 5.8 The Locked Choice, Defended

The locked design names Godot 4 as the engine. §5's matrix defends that choice: Godot 4 scores 47/60, leads the second-place engine (Unity 2023 LTS at 40) by 7 points, and wins on the two highest-weighted soft criteria (S-1 license and S-4 AI-agent integration). The two engines that *might* have competed (LÖVE 2D, RPG Maker MZ) are disqualified on hard criteria, not on soft-criterion scores. No engine that scores higher on the criteria set has been identified.

The choice is not a default. The choice is the result of applying the project's defining constraints (per §1.2, §4.2) to a criteria set (per §4) and a comparison (per §5). If a future maintainer disagrees, they can read §4 and §5 and identify which criterion they would re-weight or re-score. That is what a defensible choice looks like.

### 5.9 Decisions Needed

The comparison methodology and weights in this section are proposed, not locked. Three points are flagged for the user's review:

- **S-4 weight 3 vs. 2.** §5.4 sets S-4 (AI-agent integration) to weight 3 because it is the project's defining feature. The user may want to set it to 2 (important, not critical), which would still leave Godot 4 winning but narrow the gap to Unity. The risk of weight 3 is that the comparison becomes "any engine that is good for agents wins" — which is tautological. The risk of weight 2 is that an engine with mediocre agent integration could plausibly tie Godot 4 in a future re-weighting.
- **Unity 2023 LTS re-evaluation trigger.** §5.5 noted that Unity's 2026 tooling investments (Muse, Sentis, CLI editor modes) may justify a future upward revision of Unity's HT-4 and HT-6 scores. The user may want a specific re-evaluation milestone (e.g., "if Unity's 2026 LTS release adds a stable headless test framework, re-score Unity in §5.3") rather than leaving it as a general note. A specific trigger makes §5.3 a living document.
- **UE 5 as a Phase 3 visual-style alternative.** §5.5 noted that UE 5 is a serious candidate if the Phase 3 visual style is "3D-rendered backgrounds" rather than "HD-2D 2D-over-2.5D." The locked design says HD-2D, but the user may want a §5.3 row that explicitly scores UE 5 under a hypothetical "if we change the visual style" column. This is a documentation choice — it does not change the locked engine, but it does change how §5 reads.

These are not blocking the document's continuation. §6 (Godot 4 Deep Dive) is unblocked and can be drafted next. §6 will not re-litigate the engine choice; it will assume Godot 4 and dig into the specifics of how the Phase 3 redesign will be implemented in Godot 4's actual API surface.

---

## 6. Godot 4 Deep Dive

### 6.1 What This Section Is For

§5 named Godot 4 as the engine by applying a criteria matrix. This section drops the engine choice as a given and digs into the specifics: which Godot 4 version, how the project is laid out, what GDScript looks like in practice, how the data layer is structured, how the combat simulation is composed, where the agent's tooling plugs in, and how the HD-2D visual style is achieved. §5 was a *defense* of the engine choice; §6 is a *specification* for working in it.

The goal is that a future loop — or a future maintainer, or a different agent session — could read §6 and start writing code without having to re-derive the architecture from first principles. The "engine modifications needed" section that follows (§7) lists what we have to build on top of Godot 4. This section says what we use *as-is* from the engine, and how it composes into a project structure.

A note on confidence. §5's matrix has a Godot 4 S-6 honest flag — I have not personally benchmarked Godot 4 at the Phase 3 redesign's scale. That flag is repeated here, more pointedly: §6 commits to architectural choices that assume certain Godot 4 capabilities (2D renderer throughput, scene tree depth, signal latency, headless screenshot stability). If the Phase 1 proof-of-concept in §15 reveals that any of these are wrong, §6 will need revision. That is acceptable — §6 is the *as-designed* architecture, not a verified production architecture. The verification happens later.

### 6.2 Godot 4 Version Pinning

The locked design says "Godot 4" without specifying a minor version. The 4.x line is in active development; Godot 4.0 shipped in 2023, 4.1 in 2024, 4.2 in late 2024, 4.3 in mid-2025, 4.4 in early 2026, with 4.5 in pre-release as of the document's date. Each minor version has added 2D rendering improvements, GDScript performance work, and editor-plugin API changes that affect this project.

**Working assumption: Godot 4.3 stable.** Reasons:

- 4.3 is the version the prior `LOCKED_CHANGES.md` was written against (`Godot_v4.3-stable_win64_console.exe`), so the user's local Godot installation is already configured for it. Switching to 4.4 or 4.5 mid-project would require re-validating every scene, every shader, and every EditorPlugin.
- 4.3 has the GDScript static-typing improvements from 4.2 (variable type inference, better `@warning_ignore` ergonomics) and the 2D batching improvements from 4.3 (better draw-call coalescing for sprite-heavy scenes).
- 4.4 added TileMap layering improvements and a few editor-automation hooks, but the project does not need those for the Phase 3 design.
- 4.5 is too new to bet the project on. The community has not yet stress-tested it for JRPG-scale scenes.

**Version pinning in the repository.** The project repository will pin to a specific Godot 4.3 patch release (e.g., `4.3.stable.official`). The `project.godot` file will declare the version in its `[application]` block. CI and local builds will run against a specific binary, not "whatever Godot 4 is installed." This is essential for the "deterministic builds" principle from §1.5 — the build artifact must be reproducible from the source, and that means the same Godot binary.

**Upgrade policy.** The project will move to a newer 4.x version only on a deliberate decision, with a written changelog of breaking changes. A "Godot 4.4 upgrade task" is a multi-day project, not a "git pull and pray" operation. If a future minor version offers a 2x performance improvement, the upgrade is worth the cost; if it offers only polish, the upgrade is deferred.

**Why not 3.x.** Godot 3.x is the prior major version, and it has years of community tutorials and a stable LTS-equivalent in Godot 3.6. It is *not* the right choice for this project because: (a) GDScript 1.x is dynamically typed and slower than GDScript 2.x in 4.x, (b) the 2D renderer in 3.x is the legacy renderer with known batching limitations, (c) C# support is first-class in 4.x and anemic in 3.x, and (d) the engine's own maintainers have publicly committed to 4.x as the long-term line. The HT-3 (typed scripting) and S-6 (performance) scores in §5's matrix reflect 4.x specifically; using 3.x would invalidate both.

### 6.3 Project Structure

The project follows a layered directory structure designed for the agent's I/O asymmetry from §1.3: text-first files at the leaves, generated or binary assets in isolated subtrees, clear separation between data and code.

```
remaster-engine/
├── project.godot              # Godot project file (text)
├── export_presets.cfg         # Export configuration (text, version-controlled)
├── .godot/                    # Godot's cache directory (gitignored)
├── addons/                    # Third-party and custom EditorPlugins (text)
│   ├── remaster_schema/       # Custom plugin for JSON Schema validation
│   └── remaster_headless/     # Custom plugin for headless test harness
├── data/                      # Game data — all text, all schema-validated
│   ├── schemas/               # JSON Schema files
│   │   ├── character.schema.json
│   │   ├── tech.schema.json
│   │   ├── chapter.schema.json
│   │   └── ...
│   ├── characters/            # One file per character (character.schema.json)
│   │   ├── serge.json
│   │   ├── kidd.json
│   │   └── ...
│   ├── techs/                 # One file per tech (tech.schema.json)
│   ├── chapters/              # One file per chapter
│   ├── maps/                  # Map data (tile layers, entities, triggers)
│   ├── dialogue/              # Dialogue scripts
│   └── items/
├── scenes/                    # .tscn scene files (text format)
│   ├── battles/               # Battle scenes
│   ├── maps/                  # Map scenes (instance templates)
│   ├── ui/                    # UI scenes
│   └── entities/              # Entity templates (player, NPC, enemy)
├── scripts/                   # GDScript code
│   ├── core/                  # Engine-agnostic systems (action queue, status, save)
│   ├── battle/                # Battle simulation
│   ├── field/                 # Field exploration
│   ├── ui/                    # UI controllers
│   └── tools/                 # CLI tools, build scripts, validators
├── assets/                    # Binary assets (sprites, audio, fonts, shaders)
│   ├── sprites/
│   ├── audio/
│   ├── fonts/
│   └── shaders/
├── tests/                     # Test code
│   ├── unit/                  # GUT-style unit tests
│   ├── integration/           # Battle integration tests
│   └── fixtures/              # Test data (also text)
├── docs/                      # Documentation
│   ├── design/                # This document, rendered
│   ├── api/                   # Generated API docs
│   └── decisions/             # Decision records (ADR-style)
├── tools/                     # Build and CI tooling
│   ├── validate_data.py       # JSON Schema validation
│   ├── build.sh               # One-command build
│   ├── test.sh                # One-command test
│   └── headless_screenshot.py # Render frames from scenes
└── README.md
```

Several things to notice about this structure:

**Everything in `data/` is text.** JSON for structured data, optionally YAML or TOML for human-edited files. No binary blobs. A fresh agent session can `cat data/characters/serge.json` and have a complete model of Serge's stats, elements, supports, and tech unlocks. The agent's working memory is bounded by the size of these files, not by what it can see in a binary editor.

**`data/schemas/` is the contract.** Every JSON file in `data/` is validated against a JSON Schema file in `data/schemas/`. The validation runs in CI and is exposed as `tools/validate_data.py` for the agent to call mid-loop. A `data/characters/kidd.json` that does not match `character.schema.json` is a build failure. The schemas are themselves text, version-controlled, and reviewed like code. This is the "schema-validated data" principle from §1.5 made concrete.

**`scripts/` is GDScript (typed) only.** No C# for this project. The reasons: (a) GDScript is the path of least resistance for Godot 4 and the language most Godot tutorials assume, (b) the agent's static-analysis tooling is more mature for GDScript than for the C#/Godot combination, (c) every line of C# requires the .NET runtime, which complicates the headless build path. The locked design inherits this from `LOCKED_CHANGES.md` ("GDScript only, not .NET") and re-affirms it.

**`assets/` is the only place binaries live.** Even within `assets/`, we prefer text-friendly formats: PNG for sprites (Godot's import pipeline can convert these to native formats at build time), WAV or OGG for audio, GLSL for shaders. A `.import` file accompanies each binary, telling Godot how to process it. The `.import` files are text and version-controlled; the source PNG is version-controlled; the imported `.ctex` or `.sample` is in `.godot/` (gitignored).

**`addons/` is for the agent's own tooling.** The two listed addons — `remaster_schema` (JSON Schema validation in-editor) and `remaster_headless` (headless test harness) — are custom plugins built in Phase 1 and maintained throughout. They are the bridge between Godot's editor and the agent's CLI workflow. §6.8 covers them in detail.

**`tools/` and `tests/` are external to the Godot editor.** They are runnable from the command line without opening Godot. This is the "headless everything" principle from §1.5. The agent never needs to launch the editor; it runs tools, runs tests, reads output, edits files, repeats.

### 6.4 GDScript: The Static-Typed Subset

GDScript in Godot 4 supports both dynamic and static typing. The project's policy is **static typing for all new code**, with the rare exception of one-off scripts that handle a heterogeneous data structure where dynamic typing is genuinely clearer.

A typical file in `scripts/core/` looks like this:

```gdscript
class_name TechEffect
extends RefCounted

## A single tech's effect data, loaded from data/techs/*.json.
## This is the in-memory representation; the JSON is the on-disk form.

enum EffectType { DAMAGE, HEAL, STATUS, BUFF, DEBUFF, POSITION }

@export var effect_type: EffectType
@export var magnitude: float
@export var element: int          # Element constant; see elements.gd
@export var status: int = -1      # Status constant; -1 means no status
@export var status_chance: float = 0.0
@export var target: int = 0       # Target enum: SELF, ALLY, ENEMY, ANY


static func from_dict(d: Dictionary) -> TechEffect:
    var e := TechEffect.new()
    e.effect_type = d.get("effect_type", EffectType.DAMAGE) as int
    e.magnitude = d.get("magnitude", 0.0) as float
    e.element = d.get("element", 0) as int
    e.status = d.get("status", -1) as int
    e.status_chance = d.get("status_chance", 0.0) as float
    e.target = d.get("target", 0) as int
    return e
```

Several things to note:

**`class_name` and `extends` at the top.** This is the GDScript class declaration. `class_name TechEffect` registers the class globally so other scripts can do `var e: TechEffect` without `preload`. `extends RefCounted` is the modern Godot 4 pattern for data classes that should be auto-freed when no longer referenced. (In Godot 3, this would have been `Reference`. In Godot 4, `RefCounted` is the base class for non-Node data.)

**Type annotations everywhere.** `var effect_type: EffectType` declares both the variable and its type. The agent's static analysis can verify that no code path assigns a `String` to `effect_type`. Type errors are caught at parse time, not at runtime. This is the HT-3 (typed scripting) criterion from §4.3 made concrete.

**`@export` for editor-exposed fields.** In a `Resource` subclass (which `RefCounted` is not — but the pattern is the same), `@export` makes a field visible in the Godot editor. For data classes loaded from JSON, `@export` is less important than for scene-level resources, but the convention is kept for consistency.

**`static func from_dict(d: Dictionary)` is the JSON-loading pattern.** Every data class has a `from_dict` factory method. The factory is the *only* place that touches `Dictionary` types — after `from_dict`, the rest of the code works with strongly-typed objects. This contains the dynamic-typing surface to a small set of well-tested factory methods. If the JSON format changes, only the factories change.

**Enums for closed sets.** `EffectType`, `element`, `status`, `target` are all enums or named constants. The agent can do exhaustive matching against enums, and the static analyzer warns about unhandled enum cases. This is the "no magic" principle from §1.5 — the set of effect types is enumerable, not stringly-typed.

The prior `LOCKED_CHANGES.md` flagged one pitfall: GDScript 2.x's static typing has some edge cases around `Array` and `Dictionary` element types. The workaround is to use typed arrays (`Array[TechEffect]`) where possible, and to keep `Dictionary` usage to the JSON loading layer. The project follows this discipline.

### 6.5 The Data Layer: Resources, JSON, and Schemas

The data layer is the most important part of the project for an agent-led workflow. The code is recoverable (the agent can rewrite a buggy function), but the data — what each character is, what each tech does, what each chapter contains — is the project's content. A schema-validated data layer means the agent can edit data with confidence, and the validation tooling will catch format errors before they become runtime errors.

**The Resource pattern.** Godot's `Resource` class is the engine's standard way to model data that lives in `.tres` (text resource) or `.json` files. For this project, we use a hybrid:

- **JSON files in `data/`** for the canonical game data, validated by JSON Schema.
- **GDScript classes in `scripts/core/`** that mirror the JSON structure and provide behavior (factory methods, validation, computed properties).
- **`.tres` files in scenes/** for scene-local data that the editor manipulates (e.g., a battle scene's specific enemy placement).

The JSON files are the source of truth. The GDScript classes are the runtime representation. The `.tres` files are scene-instance data. The project has a one-way data flow: JSON → in-memory object → scene. Scenes do not write back to JSON at runtime; save data goes to a separate `saves/` directory.

**JSON Schema validation.** Every JSON file in `data/` is validated against a schema in `data/schemas/`. The validation tool is a Python script in `tools/validate_data.py` (chosen over a GDScript equivalent because Python has the most mature `jsonschema` library and the agent is fluent in Python).

Example schema, `data/schemas/character.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Character",
  "type": "object",
  "required": ["id", "display_name", "element", "role", "base_stats", "supports"],
  "properties": {
    "id": { "type": "string", "pattern": "^[a-z_]+$" },
    "display_name": { "type": "string", "minLength": 1 },
    "element": { "enum": ["white", "red", "blue", "green", "black", "yellow"] },
    "role": { "enum": ["base", "support", "combined_support", "boss"] },
    "base_stats": {
      "type": "object",
      "required": ["hp", "strength", "defense", "magic", "magic_defense", "speed"],
      "properties": {
        "hp": { "type": "integer", "minimum": 1, "maximum": 9999 },
        "strength": { "type": "integer", "minimum": 1, "maximum": 255 },
        "defense": { "type": "integer", "minimum": 1, "maximum": 255 },
        "magic": { "type": "integer", "minimum": 1, "maximum": 255 },
        "magic_defense": { "type": "integer", "minimum": 1, "maximum": 255 },
        "speed": { "type": "integer", "minimum": 1, "maximum": 255 }
      }
    },
    "supports": {
      "type": "array",
      "items": { "type": "string", "pattern": "^[a-z_+\\-]+$" }
    }
  }
}
```

The schema is strict. Every field has a type. Every enum is enumerated. Every pattern is explicit. The agent can edit `data/characters/kidd.json`, run `tools/validate_data.py`, and get a precise error message if the edit broke a constraint. This is the "schema-validated data" principle from §1.5 in its most useful form.

**A note on schema evolution.** Schemas are versioned. When a breaking change is needed, a new schema version is added (`character.v2.schema.json`), and a migration script is written to convert existing JSON files. The agent does not silently change a schema and break the world; the change is reviewed, the migration is written, and existing files are updated.

### 6.6 Scene Composition

Godot's scene system is the engine's core composition primitive. A `.tscn` file is a text-based scene description that can be loaded, instantiated, edited, and re-loaded. For an agent-led project, `.tscn` files are valuable because they are text (the agent can read and edit them) but they are also the engine's native format (no translation layer).

**Scene patterns for this project:**

- **Map scenes** (`scenes/maps/`) are the field-exploration areas. Each map is a scene with TileMap nodes, entity placement nodes (NPCs, enemies, triggers), and a `MapData` script that loads map-level configuration from `data/maps/<map_id>.json`.
- **Battle scenes** (`scenes/battles/`) are composed per-encounter. A battle scene has a `BattleArena` node, two `Team` nodes (player and enemy), and a `BattleUI` node. The specific enemies and party composition are loaded from the encounter's data file at instantiation time.
- **UI scenes** (`scenes/ui/`) are the dialog boxes, menus, status screens, save/load screens. Each is a self-contained scene with a controller script in `scripts/ui/`.
- **Entity templates** (`scenes/entities/`) are reusable character templates. `scenes/entities/player_serge.tscn` is a player-controlled Serge entity; instances of this scene are placed in map scenes and battle scenes.

**The instancing pattern.** A character like Serge is a single template scene, but it appears in many contexts: standing in Arni Village, fighting in a battle, on the status screen, in a cutscene. Each appearance is an *instance* of the template, with overrides for position, animation state, and any context-specific data. The template is one file; the instances are many files (most of them tiny, just position + parent reference).

For the agent, this means: editing Serge's appearance means editing `scenes/entities/player_serge.tscn`, not chasing down every scene that contains a Serge sprite. The "edit one file, see the change everywhere" pattern is the same as in object-oriented composition.

**Scene file format.** Godot's `.tscn` format is a custom text format that looks like:

```
[gd_scene load_steps=4 format=3]

[ext_resource type="Script" path="res://scripts/battle/battle_arena.gd" id="1"]

[sub_resource type="RectangleShape2D" id="RectangleShape2D_1"]
size = Vector2(32, 32)

[node name="BattleArena" type="Node2D"]
script = ExtResource("1")

[node name="PlayerTeam" type="Node2D" parent="."]

[node name="EnemyTeam" type="Node2D" parent="."]
```

The format is text, diffable, and reasonably readable. It is not as nice as JSON for the agent to edit by hand, but it is *much* better than a binary scene format. Most scene editing happens through the Godot editor; the agent edits `.tscn` files only when programmatic generation is needed (e.g., generating 100 battle encounter scenes from a data file).

### 6.7 Combat Simulation Architecture

The combat simulation is the part of the codebase that most directly implements the Phase 3 redesign from §3. The architecture is designed around a few principles:

**The action queue, not a frame loop.** The original Chrono Cross is turn-based with a stamina-based turn order. The redesign keeps turn-based combat but uses an *explicit action queue* rather than a per-frame update loop. At any moment, the battle is in one of a small number of states: `IDLE`, `SELECTING_ACTION`, `RESOLVING_ACTION`, `TURN_END`, `BATTLE_END`. State transitions are explicit. The battle is "paused" between player inputs and "running" during resolution.

**Components, not inheritance.** Battle entities (party members, enemies) are not a deep inheritance hierarchy. They are *compositions* of components: `StatsComponent`, `ElementComponent`, `StatusComponent`, `TechSetComponent`, `PositionComponent`. The entity itself is a `Node2D` that holds these as child nodes. This is the Entity-Component-System (ECS) pattern adapted to Godot's scene tree.

Why ECS instead of inheritance: the redesign's augmentation model (§3.5) means the same entity has different capabilities in different contexts. A support that augments Serge's basic attack is a component that gets added when the support is recruited and removed when the support is dismissed. With inheritance, we'd need a `SergeWithSleepAugment` subclass for every combination — combinatorial explosion. With components, we add or remove `AugmentComponent` instances as the support set changes.

**Determinism by default.** Every random number in the combat system goes through a single `BattleRNG` instance, seeded explicitly. The agent can run the same battle twice with the same seed and get the same result. This is essential for the "sandboxed test loops" principle from §1.5 — a test that says "Serge's tier-3 tech applies Sleep 30% of the time" can be run thousands of times against a fixed seed and the pass/fail is reproducible.

**Separation of view and simulation.** The battle *simulation* (in `scripts/battle/sim/`) knows nothing about rendering, animation, or input. It takes actions in, produces events out: `ActionSubmitted`, `DamageApplied`, `StatusInflicted`, `TurnEnded`. The battle *view* (in `scenes/battles/` and `scripts/battle/view/`) consumes those events and animates them.

This separation is the same pattern as a web frontend/backend split. It means the agent can test the simulation by feeding it scripted actions and asserting on the event stream, without ever rendering a frame. The "testable game feel" principle from §1.5 is supported: the simulation's event stream *is* the API for testing.

**The action lifecycle.** A player turn in the redesigned combat:

1. State enters `SELECTING_ACTION`. The player picks (a) which base's basic attack to use, (b) which augment (if any) to apply, (c) the target. The UI presents these as a single decision flow: "Serge's Dash and Slash — with which augment? — on which target?"
2. State enters `RESOLVING_ACTION`. The action is submitted to the simulation. The simulation computes the result (damage, status, side effects) and emits a sequence of events.
3. The view consumes the events, animating each one. When the view catches up, state transitions to `TURN_END`.
4. `TURN_END` triggers stamina-based turn order recalculation. State goes to `IDLE` until the next actor's turn.
5. Repeat until `BATTLE_END`.

The agent's combat tests assert on the *event stream* (steps 2-3), not on rendered frames. A test for "Leena+Poshul's tier-3 augment applies Sleep 30% of the time" feeds 1000 scripted actions, runs them through the simulation, counts the `StatusInflicted` events for `Status.SLEEP`, and asserts the count is 280-320 (with a fixed seed). The test runs in milliseconds and is fully deterministic.

### 6.8 The Agent Tooling Layer

Two custom EditorPlugins live in `addons/`, and they are the bridge between Godot's editor and the agent's CLI workflow.

**`remaster_schema`: JSON Schema validation in-editor.** When the agent edits a JSON file in `data/`, this plugin watches the file, validates it against the corresponding schema, and surfaces errors in Godot's editor UI. For agent workflows, the plugin also exposes a CLI command — `godot --headless --script res://addons/remaster_schema/cli_validate.gd -- data/characters/kidd.json` — that the agent can call from a terminal without opening the editor. The plugin is small (a few hundred lines of GDScript) and exists primarily to make the agent's edits immediately visible.

**`remaster_headless`: headless test harness.** This plugin is the wrapper around Godot's headless mode. It exposes commands for:

- `godot --headless --script res://addons/remaster_headless/run_tests.gd -- --suite unit` — runs unit tests
- `godot --headless --script res://addons/remaster_headless/run_tests.gd -- --suite battle --seed 12345` — runs battle integration tests with a fixed RNG seed
- `godot --headless --script res://addons/remaster_headless/screenshot.gd -- --scene scenes/maps/arni_village.tscn --out build/screenshots/arni.png` — renders a single frame from a scene
- `godot --headless --script res://addons/remaster_headless/inspect.gd -- --scene scenes/maps/arni_village.tscn` — emits a structured report of the scene's contents (nodes, entities, triggers) as JSON

The `--headless` flag runs Godot without opening a window. The `--script` flag runs a GDScript file as the entry point instead of the normal project load. Together they let the agent do anything the editor can do, from the command line, with parseable output.

**Why not just shell out to Godot directly?** The plugin layer adds two things the bare Godot CLI does not: (1) project-aware defaults (the headless commands know where `data/`, `scenes/`, and `tests/` live), and (2) consistent output formatting (the CLI tools emit JSON to stdout, error logs to stderr, and exit codes that match Unix conventions). The bare `godot --headless` is a building block; the plugins are the project's interface to it.

**The agent's typical loop.** A loop session for a code change might look like:

1. Agent reads `loop_state.json` to see what section to work on
2. Agent reads relevant `data/schemas/` and `scripts/` files
3. Agent edits a GDScript file or JSON file
4. Agent runs `tools/validate_data.py` to check JSON validity
5. Agent runs `godot --headless --script res://addons/remaster_headless/run_tests.gd -- --suite unit` to run tests
6. Agent reads test output, iterates
7. Agent commits changes

The loop is the same as a human developer's TDD loop, minus the "open editor" step. The agent's tool calls are the editor's GUI actions, scripted.

### 6.9 HD-2D in Godot 4

The HD-2D visual style — 2D characters over 2.5D backgrounds with parallax, lighting, and modern effects — is the locked design's visual approach. Godot 4 is well-suited to this because the 2D and 3D renderers can be combined in a single scene.

**Layer composition for a typical map scene:**

1. **Background layer** — a 3D scene rendered to a 2D viewport, with a camera that moves at the slowest parallax rate. Contains terrain, skybox, distant geometry.
2. **Midground layer** — 2D parallax sprites (trees, buildings) that move at a medium parallax rate.
3. **Foreground layer** — 2D sprites for the floor, walls, doors, interactive objects. Static or moving at full speed.
4. **Entity layer** — 2D sprite characters (Serge, Kidd, NPCs, enemies). Move at full speed.
5. **Effects layer** — particle systems, lighting, screen-space shaders. On top of everything.

Each layer is a `Node2D` or `Node3D` in the scene tree, with a `ParallaxLayer`-equivalent script that adjusts position based on the camera's movement. The 2D and 3D renderers do not interfere because the 3D content is pre-rendered to a `Viewport` texture and used as a 2D sprite.

**Lighting.** Godot 4's 2D lighting system supports normal maps, specular maps, and point lights. HD-2D's "warm light from a window" effect is a point light with a falloff texture, applied via a `Light2D` node. The system is mature enough for the Phase 1 proof-of-concept; §10 covers the PS1-era challenges that affect the art pipeline (e.g., the original's pre-rendered backgrounds vs. our dynamic 2.5D).

**Shaders.** Screen-space effects (color grading, vignette, depth-of-field) are applied via `CanvasLayer` shaders at the end of the render pipeline. A "PS1 mode" shader that reduces the color palette and adds scanlines is one example; a "modern mode" shader that uses full color and crisp pixels is the default. The mode is a project setting, switchable at runtime.

**Asset pipeline.** Sprites are authored in Aseprite or similar tools, exported as PNG, imported into Godot with `.import` files specifying the atlas layout. Background geometry is modeled in Blender, exported as `glb`, rendered in a pre-bake step to a PNG atlas. The pipeline is mostly manual for Phase 1 (the agent generates placeholder art and the human refines it later); §11 covers the toolchain in detail.

### 6.10 RPG Maker Lessons Applied

§5.5 mentioned that the user's prior `rpgmaker_mv_research_and_poc_plan.md` contains insights worth translating. Without re-reading the research file in full (it is reference material, not part of this document's scope), the *categories* of lessons that are likely applicable to Godot 4 are:

**Plugin architecture translates.** RPG Maker's plugin model — a `PluginManager` that loads `.js` files and exposes a global API — is similar to Godot's `EditorPlugin` and autoload singleton model. The agent's tooling layer (§6.8) follows the same pattern: small, focused plugins that expose CLI commands.

**Event-driven architecture is portable.** RPG Maker's event system (a map full of "event" objects with pages of commands) is similar to Godot's signal system. The redesign's "trigger zones" on maps (e.g., a cutscene trigger when the player enters a region) are RPG Maker events by another name. The terminology differs, the pattern is the same.

**Save data is JSON-like either way.** RPG Maker's `.rvdata` files are binary, but the conceptual model is a serialized game state — a JSON-like dictionary. Godot's `ResourceSaver` can save `Resource` objects to `.tres` (text) or `.res` (binary) files; for save data, we use JSON explicitly because the agent should be able to read and edit save files for testing.

**What does NOT translate.** RPG Maker's tile-based map system is the *opposite* of HD-2D's freeform layer composition. The redesign does not use tiles; it uses layered sprites and 2.5D geometry. RPG Maker's actor model (one script per actor) is the *opposite* of the redesign's component-based entity model. Forcing RPG Maker patterns onto the Godot implementation would be a mistake. The lessons that apply are the architectural patterns, not the data models.

A more thorough translation of the RPG Maker research file into Godot 4 patterns is a Phase 1 task, not a §6 task. §6 commits to the *posture* — the agent will read the research file and apply applicable patterns — without doing the translation inline.

### 6.11 Known Godot 4 Gotchas

The honest flag from §5's matrix and §6.1: Godot 4 has known issues in 2026 that the project will have to navigate.

**Performance cliffs in 2D scenes with many sprites.** Godot 4's 2D renderer is good but not great for scenes with thousands of draw calls. The 2D batching in 4.3 helps, but a battle with 6 party members + 8 enemies + 20+ effect particles + 30+ status icons + animated backgrounds is a worst case. The mitigation is to use `MultiMeshInstance2D` for repeated sprites (status icons) and to pool particles aggressively. §6.7's separation of view and simulation helps because we can benchmark the simulation without the view's rendering cost.

**Editor automation is partial.** Godot's headless mode runs scripts and produces output, but it is not a full automation API. Some editor actions (e.g., generating a `.tscn` file via the visual editor) cannot be reproduced headlessly. The workaround is to write a GDScript builder for any scene that needs programmatic generation, and to avoid relying on the visual editor for scenes the agent will touch.

**Scene file format is custom and underdocumented.** `.tscn` is a Godot-specific format. The schema for the format is not published as a JSON Schema; the agent has to read Godot's source code to know what fields are valid. The mitigation is to *avoid* hand-editing `.tscn` for anything complex, and to use a builder script for non-trivial scenes.

**GDScript type inference has limits.** The type inference engine in GDScript 2.x does not always infer the right type, especially for collections and lambdas. Explicit type annotations are required for the project's "static typing for all new code" policy, but the inference gaps mean some lines are more verbose than they would be in TypeScript or Python 3.12+.

**The community is smaller than Unity's.** This is not a technical gotcha, but it affects the agent's ability to find answers. When the agent hits a Godot-specific problem, the answer is more likely to be in the Godot docs or the GitHub issues than in a Stack Overflow answer. The mitigation is to build up a `docs/decisions/` folder of project-specific findings as the project progresses.

**Versioning the Godot binary is not as easy as it should be.** The Godot team does not publish stable URLs for specific patch releases; the GitHub release pages use a "latest" pattern that does not preserve the version. The mitigation is to vendor the Godot binary in the repository (or in a release artifact), not rely on `winget install` to always get the same version.

**None of these are showstoppers.** Each is a manageable cost. The §5 matrix's 47/60 score for Godot 4 reflects this trade — the engine has rough edges, but the edges are in places we can work around. A future maintainer who hits one of these gotchas can find the workaround in this section, in `docs/decisions/`, or in the commit history.

### 6.12 Decisions Needed

The deep dive commits to specific architectural choices. Three are flagged for the user's review because they have long-term consequences and are not strictly required for the §6 prose to make sense:

- **Godot 4.3 vs 4.4 vs 4.5 as the version pin.** §6.2 commits to 4.3 because the user's prior project is on 4.3. The user may want 4.4 (newer features, more 2D rendering work, slight risk of instability) or 4.5 (newest, highest risk). The decision affects every line of GDScript, every scene, every shader. Recommendation: 4.3, with an upgrade decision made in writing before Phase 1 starts.
- **C# support policy.** §6.3 says GDScript only. The user may want a narrow C# surface for a specific subsystem (e.g., the save file encryption, where the .NET crypto libraries are stronger). The decision affects the build pipeline (C# requires the Mono/.NET runtime). Recommendation: GDScript only, with a written exception process if a specific subsystem is genuinely better in C#.
- **Schema validation tool choice.** §6.5 uses Python (`tools/validate_data.py`) with the `jsonschema` library. The user may want a GDScript-only toolchain (no Python dependency), accepting that the validation library is less mature. The decision affects the build dependencies. Recommendation: Python, because the `jsonschema` library is industry-standard and the agent's Python tooling is mature, but this is a defensible call either way.

These are not blocking the document's continuation. §7 (Engine Modifications Needed) is unblocked and can be drafted next. §7 will list the specific things we have to build on top of Godot 4 to deliver the Phase 3 redesign — the code that is *not* in the engine and must be written for this project.

---


## 7. Engine Modifications Needed

### 7.1 What This Section Is For

§6 specified the *as-designed* architecture: how we use Godot 4 as it ships. This section specifies the *added layer* — the code, systems, and data that Godot 4 does not provide and that the project must write on top to deliver the Phase 3 redesign. If §6 is the chassis, this is the body, the interior, and the wiring.

These are not nice-to-haves or "things to add if we have time." Every modification in this section is a hard requirement of the locked design. The chapter-progression model from §3.9, the augmentation-based combat from §3.5, the element grid from §3.4, the form-change state machine from §3.7, the 6-character party formation from §3.9 — none of these exist in the Godot 4 box. They have to be built. And they have to be built in a way that an AI agent can extend, test, and reason about, because the entire §1 framing is that the agent is the primary author.

The organization is by *subsystem*, not by *layer*. We will work through the eleven modifications in order of dependency: the lowest-level changes feed the higher-level ones. The reader who lands on §7.6 (status effect engine) should be able to trace the dependency up to §7.10 (combat) and down to §7.1 (determinism). Each subsection names the locked design it implements, the Godot 4 gap it fills, the proposed architecture, the data shape, and the test surface.

### 7.2 Determinism Layer (Expansion of §6.7)

**Locked design reference:** §3 (entire redesign), §6.7 (combat simulation architecture), §1.5 (principles 3 and 4 — deterministic builds, sandboxed test loops).

**Godot 4 gap:** Godot's `randi()` and `randf()` use a global PRNG seeded from the system clock. The agent cannot replay a fight, cannot bisect a bug across thousands of iterations, cannot write a regression test that pins a damage roll. §6.7 introduced `BattleRNG` as a class; this section specifies the full determinism contract.

**Architecture:** A single `Determinism` autoload (singleton) owns every PRNG the project uses. There is exactly one source of randomness: the `Determinism.root` instance. Every system that needs randomness — combat, dialog, treasure, AI decisions — takes a `Determinism` instance and calls methods on it. Direct calls to `randi()` or `randf_range()` are forbidden in the project's static-typed GDScript subset (a code-review and CI lint will reject them).

```gdscript
# autoloads/determinism.gd
class_name Determinism
extends Node

var root: RandomNumberGenerator
var _seed: int = 0
var _callers: Dictionary = {}  # tag -> rng instance (for test inspection)

func _ready() -> void:
    root = RandomNumberGenerator.new()
    seed_rng(0)

func seed_rng(new_seed: int) -> void:
    _seed = new_seed
    root.seed = new_seed
    _callers.clear()

func scoped(tag: StringName) -> RandomNumberGenerator:
    # Each subsystem gets a derived PRNG so test output can identify
    # *which* subsystem consumed entropy.
    if not _callers.has(tag):
        var derived := RandomNumberGenerator.new()
        derived.seed = hash([_seed, tag])
        _callers[tag] = derived
    return _callers[tag]

func snapshot() -> Dictionary:
    # For save-game and test-replay inspection.
    return {
        "seed": _seed,
        "root_state": root.state,
        "caller_states": _callers.keys().map(func(t): return [t, _callers[t].state])
    }
```

**Why derived PRNGs:** A single global PRNG means a damage roll, a dialog pick, and an AI decision all consume from the same stream. Tests that want to assert "Leena+Poshul's tier-3 augment applies Sleep" have to count entropy calls precisely, which is fragile. Derived PRNGs scoped by tag let tests reset the combat PRNG without affecting dialog and let debug tools answer "how much entropy did combat consume?" without re-running.

**The determinism contract:**

1. **No source of randomness may be touched outside `Determinism`.** This includes `randi()`, `randf()`, `randf_range()`, `randi_range()`, `Array.shuffle()`, `Dictionary` iteration order, and hash-set iteration. A CI lint (`tools/lint_no_global_rng.py`) greps the source tree and rejects any match outside `autoloads/determinism.gd`.
2. **The seed is a save-game field.** A save file stores the current `Determinism` snapshot. Loading a save restores the exact PRNG state. This means the player can load, take a specific action, save again, and re-load to verify the action had the expected effect.
3. **The seed is a test parameter.** Every integration test takes a seed as input. CI runs the test suite across a matrix of seeds (the standard set is `[0, 1, 42, 1337, 0xDEADBEEF]`) to surface order-dependent bugs.
4. **The seed is a debug surface.** A bug report includes the seed and the action count. The maintainer can re-run the exact fight in the headless test rig and observe the same outcome. This is the §1.5 "errors reproducible" principle instantiated.

**Test surface:** `tests/test_determinism.gd` asserts that (a) seeding twice with the same value produces the same sequence, (b) two `scoped` PRNGs with the same tag produce the same sequence, (c) `snapshot()` round-trips through save/load, (d) the `lint_no_global_rng.py` script returns zero matches on the project tree.

**What this does not solve:** Real-time wall-clock effects (animation timing, audio sync) are not deterministic. We accept that the visual/audio layer has frame-level variance; the simulation layer does not. The §6.7 view/simulation separation makes this a non-issue: simulation tests do not need a view.

### 7.3 The Tech and Augmentation System

**Locked design reference:** §3.5 (basic attack line + support techs as augmentations, not replacements), §3.6 (open grid slots), §3.4 (8 magic tiers).

**Godot 4 gap:** Godot 4 has no concept of a "tech" or "magic tier" or "augmentation." It has signals, methods, resources, and state machines — all of which we will use, but none of which map directly to the project's data model.

**Architecture:** A tech is a `Resource` subclass with a strict schema. The schema is versioned (per §6.5) and validated at load time. The augmentation model from §3.5 means a tech is *never* a standalone action — it is always a modification to a base's basic attack or to another tech's effect.

```gdscript
# data/tech.gd
class_name Tech
extends Resource

@export var id: StringName  # matches ^[a-z_]+$ per §6.5 schema
@export var display_name: String
@export var tier: int  # 1..8
@export var element: ElementType  # enum
@export var cost_mp: int
@export var base_damage_multiplier: float = 1.0
@export var effects: Array[TechEffect]  # composed effects
@export var augmentations: Array[TechAugmentation]  # modify self or target
@export var target_scope: TargetScope  # SINGLE_ENEMY, ROW, ALL_ENEMIES, ALLY, SELF, ALL_ALLIES, FREE_SLOT
@export var slot_kind: SlotKind  # BASIC_LINE, SUPPORT_FIXED, SUPPORT_PLAYER_CHOICE

enum TargetScope { SINGLE_ENEMY, ROW, ALL_ENEMIES, ALLY, SELF, ALL_ALLIES, FREE_SLOT }
enum SlotKind { BASIC_LINE, SUPPORT_FIXED, SUPPORT_PLAYER_CHOICE }
```

**The augmentation data model:** A `TechAugmentation` is the §3.5 "this tech modifies another" relationship. Concretely, when a base executes a tech, the engine walks the augmentation chain, applying each in order. An augmentation can:

- **Pre-apply** a status to the target before damage (`PRE_DAMAGE_STATUS: 30% chance to apply Sleep`)
- **Post-apply** a status to the target after damage (`POST_DAMAGE_STATUS: 50% chance to apply Poison`)
- **Modify** the multiplier (`DAMAGE_MULTIPLIER_BONUS: +0.3 against targets already afflicted with the matching element`)
- **Trigger** a secondary effect (`ON_HIT: 25% chance to chain a tier-1 version of this tech to a second target`)
- **Cost-modify** the tech (`MP_DISCOUNT: 5 MP at tiers 5+`)
- **State-modify** the user (`SELF_BUFF: +10% damage for 2 turns after use`)

**Why this matters for the agent:** A common bug pattern is "I added a tech and it broke three other techs because they share an augmentation chain." By making the augmentation graph explicit (a list of `TechAugmentation` resources on each `Tech`), the agent can lint for cycles, validate that every augmentation target exists, and reason about tech interactions as data, not control flow. A new support tech added by the agent is *just data* — a `Tech` resource with a few `TechAugmentation` entries. The combat engine in §7.10 doesn't change.

**The tier progression model:** Each base has exactly 8 tech slots: tier 1 through tier 8. The tier 1 slot is always the basic attack (locked, unchangeable). Tier 8 is the ultimate. Tiers 2 through 7 are filled by support techs according to a fixed schedule from the locked design (3 per base from one set of supports at 3/5/7, 3 per base from another set at 2/4/6). 1-2 open grid slots per base let the player choose. The data structure:

```gdscript
# data/base_loadout.gd
class_name BaseLoadout
extends Resource

@export var base_id: StringName
@export var tier_1: Tech  # always the basic attack, locked
@export var tier_2: Tech  # support fixed
@export var tier_3: Tech  # support fixed
@export var tier_4: Tech  # support fixed
@export var tier_5: Tech  # support fixed OR open grid slot
@export var tier_6: Tech  # support fixed
@export var tier_7: Tech  # support fixed OR open grid slot
@export var tier_8: Tech  # always the ultimate
@export var open_slot_tiers: Array[int]  # which tiers are open grid, e.g. [5, 7]
```

The `open_slot_tiers` array is the §3.6 commitment in data. If a future design decision moves the open slots, only this array changes; the combat engine does not.

**Test surface:** `tests/test_tech_loader.gd` validates that every `Tech` resource in `data/techs/*.tres` passes the schema, that every `TechAugmentation` references an existing effect, and that no augmentation chain forms a cycle. `tests/test_base_loadout.gd` validates that every base has a tier-1, tier-8, and the right number of intermediate slots per the locked design.

### 7.4 The Element Grid and Resistance Model

**Locked design reference:** §3.4 (6 base characters with element specialization, element system as a defining design pillar of Chrono Cross).

**Godot 4 gap:** No element system exists. We need a 6-element grid (White/Red/Blue/Green/Black/Yellow), a resistance chart, and the cross-modifier rule from the original game.

**Architecture:** A single `ElementGrid` autoload owns the resistance chart and provides the `compute_resistance(attacker_element, defender_element) -> float` function. The chart is data, not code, so a mod can rebalance elements without touching the engine.

```gdscript
# autoloads/element_grid.gd
class_name ElementGrid
extends Node

# 6-element grid from the locked design: White, Red, Blue, Green, Black, Yellow.
# Resistance values follow the original Chrono Cross chart.
# 1.0 = neutral, 0.5 = strong defense, 2.0 = strong offense, 0.0 = immune.
# Chart stored as JSON in data/elements/resistances.json, loaded at _ready.
@export var resistance_chart: Dictionary  # { "white": { "red": 0.5, "blue": 0.5, ... }, ... }
@export var element_names: PackedStringArray = ["white", "red", "blue", "green", "black", "yellow"]

func _ready() -> void:
    var path := "res://data/elements/resistances.json"
    var f := FileAccess.open(path, FileAccess.READ)
    resistance_chart = JSON.parse_string(f.get_as_text())

func compute_resistance(attacker: StringName, defender: StringName) -> float:
    if not resistance_chart.has(attacker):
        push_error("Unknown attacker element: %s" % attacker)
        return 1.0
    if not resistance_chart[attacker].has(defender):
        return 1.0
    return resistance_chart[attacker][defender]
```

**The cross-modifier rule:** In the original Chrono Cross, each element is strong against two others and weak against two others (a hexagonal graph). The locked design preserves this. A mod that wants to change the chart edits one JSON file; the engine does not change.

**The level-based scaling rule:** Element strength in Chrono Cross scales with the user's level relative to the target's level. The exact formula is a design decision (logged for §13 review: "level-vs-element scaling formula"). The current working assumption is the original's curve, but the formula lives in a single function on `ElementGrid` so it can be revised.

**Test surface:** `tests/test_element_grid.gd` validates that the resistance chart is symmetric in the right way (White vs Red = Red vs White in the original), that every element has exactly 6 entries (including self), and that `compute_resistance` returns the expected value for the canonical strong/weak pairs.

### 7.5 Status Effect Engine

**Locked design reference:** §3.5 (feature mining — "techs that are 'just damage' become candidates for mining underused status effects from the system's design space"), §3.4 (support tech role — "augment the basic attack line with features like status effects").

**Godot 4 gap:** Godot has no concept of a status effect on an entity. We need an engine that can apply, tick, expire, stack, and resist status effects across many entity types and tech sources.

**Architecture:** A `StatusEffect` resource (data) and a `StatusEffectComponent` (engine attachment). The component is a node attached to any entity (player, enemy, boss, summon) and holds a `Dictionary[StringName, StatusInstance]`. The combat tick system processes the dictionary.

```gdscript
# combat/status_effect.gd
class_name StatusEffect
extends Resource

@export var id: StringName
@export var display_name: String
@export var category: StatusCategory  # BUFF, DEBUFF, NEUTRAL, FIELD
@export var max_stacks: int = 1
@export var duration_default: int = 3  # turns
@export var tick_phase: TickPhase  # START_OF_TURN, END_OF_TURN, ON_DAMAGE, ON_HEAL
@export var can_resist: bool = true
@export var resist_element: ElementType  # which element can dispel/cure
@export var handlers: Array[StatusHandler]  # what actually happens

enum StatusCategory { BUFF, DEBUFF, NEUTRAL, FIELD }
enum TickPhase { START_OF_TURN, END_OF_TURN, ON_DAMAGE, ON_HEAL }
```

**The handler model:** A `StatusHandler` is a small resource describing "when this status ticks, do X." Handlers are pure data (no logic embedded); the engine reads the handler type and dispatches. Examples:

- `DAMAGE_OVER_TIME: 8 per turn, fire element`
- `STAT_MODIFIER: -25% physical damage taken`
- `ACTION_LOCK: cannot use techs, can use items`
- `CHAIN_TRIGGER: on taking damage, 30% chance to reflect at attacker`
- `FIELD_AURA: all enemies in row take 5 damage per turn`

**Why handlers as data:** The §3.5 feature mining model means new status effects appear as we design them. If each status effect were a class, the agent would have to write a new class for each, which is slow and error-prone. As data, a new status effect is a new `StatusEffect` resource with a list of handlers — a few lines of JSON, validated against the schema, and immediately usable in any tech.

**Stacking model:** Most status effects do not stack (one Sleep on the target is the same as three). Some do (Poison stacks additively, up to a cap). The `max_stacks` field is the contract; the engine rejects status applications beyond the cap (with a debug-mode warning).

**Resistance model:** Original Chrono Cross had a complex resistance system: some statuses were resisted by being in a specific element, some by having a specific buff active, some by boss immunity. The locked design preserves the spirit (bosses are immune to status effects they should be) but the implementation is a `can_resist: bool` and a `resist_element` field. Bosses set `can_resist = false` on their status-effect component at the data level. The exact resistance table is a §13 design decision (logged: "status effect resistance table").

**Test surface:** `tests/test_status_engine.gd` validates that (a) applying a status creates an instance with the right duration, (b) ticking at the right phase invokes the handler, (c) stacking respects the cap, (d) expiring at duration 0 removes the instance, (e) the schema validator accepts the canonical set of statuses from `data/statuses/*.tres`.

### 7.6 The Form-Change State Machine (Serge ↔ Lynx)

**Locked design reference:** §3.7 (Pip mechanic reframed — during Lynx form, Devil Pip grants Lynx's dark techs; after returning to Serge form, Herle migrates those techs; Angelic Pip grants Serge's light techs post-return).

**Godot 4 gap:** No state machine library is built into the core. Godot has `StateMachine` nodes in user-space and the community has `godot-state-machine` plugins, but neither matches the project's needs (form change is not just a state — it is a swap of two complete character data sets, with mid-transfer tech migration).

**Architecture:** A `FormStateMachine` that owns the form state (`SERGE` or `LYNX`) and orchestrates the migration. The state machine is a small `Node` attached to the player entity, not a global autoload, because it is per-character.

```gdscript
# entities/form_state_machine.gd
class_name FormStateMachine
extends Node

@export var serge_data: CharacterData
@export var lynx_data: CharacterData
@export var current_form: Form = Form.SERGE
@export var migration_log: Array[MigrationEntry]  # for save/load

enum Form { SERGE, LYNX }

func change_form(target: Form, context: Dictionary) -> void:
    if target == current_form:
        return
    var migrated_techs := _execute_migration(current_form, target, context)
    current_form = target
    _swap_active_data(target)
    migration_log.append(MigrationEntry.new(current_form, target, migrated_techs, context))
    # Emit the signal for the chapter system to react.
    form_changed.emit(target, migrated_techs)
```

**The migration logic:** The `change_form` call is the heart of the §3.7 design. When Serge becomes Lynx, the state machine:

1. Identifies which of Serge's tier slots held dark techs (none, in the canonical setup — the design is that Serge doesn't have dark techs pre-form)
2. Identifies which of Lynx's tier slots hold dark techs (Feral Cats, Hell's Fury, Forever Zero per §3.7)
3. Identifies which techs Devil Pip will grant (the same dark techs, or a subset — design decision in §13)
4. Updates the active data set to Lynx

When Lynx returns to Serge, the state machine:

1. Identifies which of Lynx's dark techs need to migrate to Herle (per §3.7: "Herle migrates those dark techs to her own slot")
2. Identifies which of Serge's light techs become available (Luminaire, Heaven's Call, Flying Arrow per §3.7)
3. Updates the active data set to Serge
4. Triggers a `herle_received_dark_techs` event so Herle's `BaseLoadout` updates
5. Triggers a `serge_received_light_techs` event so Serge's `BaseLoadout` updates
6. Angelic Pip grants the light techs (or they are unlocked automatically — design decision in §13)

**Why a state machine and not a flag:** A boolean `is_lynx` would lose the migration log, would not handle the "what if the player changes form twice?" case correctly, and would not be testable. The `MigrationEntry` log is also the save-game data — when the player loads, the migration history is intact.

**Test surface:** `tests/test_form_state_machine.gd` validates that (a) changing to Lynx grants the canonical dark techs, (b) returning to Serge migrates dark techs to Herle and grants light techs to Serge, (c) double-changing (Serge → Lynx → Serge → Lynx) produces the correct migration log, (d) saving and loading preserves the form and migration history.

### 7.7 The 6-Character Party Formation System

**Locked design reference:** §3.9 (active party size 6, 2-row formation).

**Godot 4 gap:** No party system exists. No 2-row formation. The "row" concept is a Chrono Cross and Tactics Ogre design — front row takes more damage, back row is safer but takes longer to act (or has reduced effect on techs that require line of sight, depending on the original game's rules).

**Architecture:** A `Party` resource that owns 6 `Combatant` references and a `Formation` resource that defines the 2-row layout. The party is a global autoload; the formation is a per-battle resource.

```gdscript
# combat/party.gd
class_name Party
extends Node

@export var slots: Array[Combatant] = []  # length 6
@export var active_count: int = 3  # grows from 3 to 6 across chapters per §3.9

signal slot_unlocked(index: int, combatant: Combatant)

func unlock_next(combatant: Combatant) -> void:
    if active_count >= 6:
        push_warning("Party already at max size")
        return
    slots[active_count] = combatant
    active_count += 1
    slot_unlocked.emit(active_count - 1, combatant)
```

```gdscript
# combat/formation.gd
class_name Formation
extends Resource

@export var front_row: Array[int] = [0, 1, 2]  # slot indices
@export var back_row: Array[int] = [3, 4, 5]
@export var row_modifiers: RowModifiers  # how front/back differ

class RowModifiers:
    var front_damage_taken_mult: float = 1.0
    var back_damage_taken_mult: float = 0.85
    var front_physical_damage_dealt_mult: float = 1.0
    var back_physical_damage_dealt_mult: float = 0.7
    # Tech targeting can hit front or back row depending on the tech's `target_scope`.
```

**The slot-unlock cinematic:** Per §3.9, slot unlocks happen at chapter boundaries as "dramatic progression reveals." The signal `slot_unlocked` triggers a `ChapterSystem` handler that plays a cinematic and updates the UI. The party system does not know about cinematics; it just emits the signal. Decoupling.

**Active vs. roster:** The party has 6 *slots*, but `active_count` may be less than 6 (chapters 1-3 have 3 active, chapters 4-6 have 4, etc., per the chapter progression in §3.9). Combat only includes the first `active_count` slots in the formation. The 6-slot data model lets us pre-stage characters for chapter transitions.

**Test surface:** `tests/test_party.gd` validates that (a) `unlock_next` increases `active_count`, (b) the formation's front/back row indices stay valid as `active_count` changes, (c) saving and loading preserves the slot array, (d) the `slot_unlocked` signal fires with the right payload.

### 7.8 The Chapter and Progression System

**Locked design reference:** §3.9 (10 chapters of party progression), §3.13 (main cast focus, expanded interaction scenes).

**Godot 4 gap:** No chapter system. No flag/state system for "this scene has played, this character has joined, this story beat has resolved." Godot has `Dialogic` and similar plugins for dialog, but not for the meta-progression state that ties dialog, party, formation, and chapter-triggered events together.

**Architecture:** A `ChapterSystem` autoload that owns a `ProgressionFlags` resource. The flags are a flat key-value store with typed values (booleans for story beats, ints for counters, refs to characters for joins).

```gdscript
# autoloads/chapter_system.gd
class_name ChapterSystem
extends Node

@export var current_chapter: int = 1
@export var max_chapter: int = 10
@export var flags: ProgressionFlags

signal chapter_advanced(from: int, to: int)
signal flag_set(flag_id: StringName, value: Variant)

func advance_to(target: int) -> void:
    if target <= current_chapter:
        push_warning("Cannot advance backwards or to same chapter")
        return
    if target > max_chapter:
        push_warning("Cannot advance beyond max_chapter")
        return
    var from := current_chapter
    current_chapter = target
    chapter_advanced.emit(from, target)
    _execute_chapter_transition(from, target)

func _execute_chapter_transition(from: int, to: int) -> void:
    # The transition is data-driven: each chapter has a ChapterData resource
    # that lists the side effects (party unlocks, scene plays, flag sets).
    var data := load("res://data/chapters/chapter_%d.tres" % to) as ChapterData
    for unlock in data.party_unlocks:
        Party.unlock_next(unlock)
    for scene in data.story_scenes:
        SceneQueue.play(scene)
    for flag in data.flag_sets:
        set_flag(flag.id, flag.value)
```

**Why data-driven chapter transitions:** A chapter is a *list of side effects*, not a script. The agent authors a `ChapterData` resource (a `.tres` file) with the party unlocks, scenes, and flag sets. The engine executes the list. This means a new chapter is just a new `.tres` file — no new code. It also means the agent can lint a chapter file for "this unlocks a character who is not in the roster" or "this scene references a flag that is set in a later chapter."

**Flags as data, not code:** A `ProgressionFlags` resource has typed fields for every story beat. The agent reads and writes flags through a single API:

```gdscript
# data/progression_flags.gd
class_name ProgressionFlags
extends Resource

# Story beats
@export var met_serge_in_person: bool = false
@export var defeated_fate_attendant_first_time: bool = false
# ... ~150 more

# Joins
@export var kidd_joined: bool = false
@export var nikki_joined: bool = false
# ... ~40 more

# Form events
@export var serge_became_lynx: bool = false
@export var lynx_returned_to_serge: bool = false
@export var herle_received_dark_techs: bool = false
@export var serge_received_light_techs: bool = false
```

**Test surface:** `tests/test_chapter_system.gd` validates that (a) `advance_to` fires the right side effects, (b) flag sets are persisted, (c) backwards advance is rejected, (d) all chapter data files reference characters that exist in the roster.

### 7.9 The HD-2D Rendering Stack

**Locked design reference:** §3.10 (HD-2D visual style — 2D characters over 2D/2.5D backgrounds), §6.9 (HD-2D in Godot 4 — high-level pass).

**Godot 4 gap:** Godot 4's 2D renderer is excellent for pure 2D but has no built-in support for the HD-2D technique (sprites over parallax backgrounds with depth, lighting, and atmospheric effects). We need a custom rendering stack.

**Architecture:** The HD-2D stack is a collection of `Node2D` extensions and shader resources that compose a 5-layer scene:

1. **Background layer (farthest):** 2D parallax plane, often 2.5D (a 3D mesh rendered to a texture, or a hand-painted layered PNG). Uses `ParallaxBackground` + `ParallaxLayer` with multiple layers.
2. **Atmosphere layer:** `ColorRect` or shader-driven fog/dust/light shafts. Uses a `CanvasModulate` and a custom shader for god-rays.
3. **Entity layer:** 2D sprites for characters and enemies, with `AnimatedSprite2D` for animations.
4. **Foreground layer (closest):** Hand-painted foreground objects (vines, pillars, beams) with `ParallaxLayer` set to scroll at a different rate than the background.
5. **UI layer:** `CanvasLayer` at high `layer` value, isolated from the world transform.

**The 2D lighting system:** HD-2D in the Octopath Traveler / Triangle Strategy style uses 2D lights for torchlight, magic glow, and time-of-day. Godot 4.3's `Light2D` and `PointLight2D` are sufficient. The stack provides a `LightingPreset` resource per area (e.g., "Guldove at night," "Water Dragon Isle cave") that configures the lights' colors, intensities, and shadow behavior.

**The depth-fake shader:** The 2.5D illusion comes from a screen-space depth shader that reads each layer's depth value and applies fog, color grading, and a slight blur based on perceived distance. The shader is a `CanvasItemMaterial` with a `shader_parameter depth` set per layer. This is the technique from Octopath Traveler that makes the 2D sprites look like they exist in a 3D space.

```glsl
// shaders/depth_fake.gdshader
shader_type canvas_item;

uniform float depth : hint_range(0.0, 1.0) = 0.5;
uniform vec3 fog_color : source_color = vec3(0.1, 0.15, 0.2);
uniform float fog_density : hint_range(0.0, 1.0) = 0.3;

void fragment() {
    vec4 tex = texture(TEXTURE, UV);
    // Apply fog based on depth. Higher depth = further away = more fog.
    float fog_factor = clamp(depth * fog_density, 0.0, 1.0);
    vec3 final_color = mix(tex.rgb, fog_color, fog_factor);
    COLOR = vec4(final_color, tex.a);
}
```

**The asset pipeline:** HD-2D backgrounds are layered PNGs exported from a tool like Krita or Aseprite, with a metadata file (`.json` sidecar) that names each layer, sets its parallax factor, and assigns it a depth value. The importer script (`tools/import_background.py`) reads the sidecar and emits a Godot scene with the right `ParallaxLayer` configuration. Without this pipeline, the agent would have to hand-assemble 50+ parallax layers per area, which is not feasible.

**Test surface:** `tests/test_hd2d_pipeline.gd` validates that (a) the importer script produces a valid scene, (b) the scene loads without errors, (c) the depth-fake shader compiles, (d) a 2D light affects only the right layers (per the `light_mask`).

**This subsystem is the most art-pipeline-heavy.** The other subsystems in this section are pure code; this one requires art assets. §11 (Toolchain) will go deeper on the asset pipeline; §13 (Risks) flags the art-asset acquisition risk explicitly.

### 7.10 The Combat Engine

**Locked design reference:** §3.5 (combat system as the user-facing expression of the augmentation model), §3.9 (6-character party, turn-based).

**Godot 4 gap:** No turn-based combat engine. No elemental damage calculation. No status effect application. No targeting system. This subsystem composes §7.3 (techs), §7.4 (elements), §7.5 (statuses), §7.6 (form), and §7.7 (party) into a single battle.

**Architecture:** A `Battle` node that owns a `BattleState` (whose turn, what effects are pending, the action queue) and dispatches to a `CombatSimulator` for simulation and a `BattleView` for presentation. The §6.7 view/simulation separation is realized here.

```gdscript
# combat/battle.gd
class_name Battle
extends Node

@export var sim: CombatSimulator
@export var view: BattleView
@export var party: Party
@export var enemies: Array[Combatant]
@export var rng: Determinism  # per §7.2

signal turn_started(turn_owner: Combatant)
signal action_resolved(action: BattleAction, result: ActionResult)
signal battle_ended(winner: BattleSide)

func start_battle() -> void:
    sim.reset(party, enemies, rng)
    view.setup(party, enemies)
    _run_turn_loop()

func _run_turn_loop() -> void:
    while not sim.is_battle_over():
        var owner := sim.next_turn_owner()
        turn_started.emit(owner)
        var action := await view.prompt_action(owner)
        var result := sim.resolve(action)
        view.animate(result)
        action_resolved.emit(action, result)
    battle_ended.emit(sim.get_winner())
```

**The action lifecycle:** When a player picks a tech, the following happens in order (§6.7 referenced this; here is the full specification):

1. **Validation:** The simulator checks that the combatant has enough MP, that the target is in range, and that no status is locking the action.
2. **Augmentation chain walk:** The simulator walks the tech's `augmentations` list. Pre-damage augmentations apply (status pre-applications, MP discounts, self-buffs).
3. **Damage calculation:** Base damage × multiplier × element resistance × row modifier × status modifiers.
4. **Status application:** The tech's `effects` list is applied to the target. Each `TechEffect` may roll a chance (via `Determinism.scoped("combat")`).
5. **Augmentation chain walk (post):** Post-damage augmentations apply (status post-applications, chain triggers).
6. **Tick:** The combatant's `StatusEffectComponent` ticks any statuses with `tick_phase = ON_DAMAGE` or `ON_HEAL`.
7. **Log:** A `BattleLogEntry` is appended with the full state for replay.

**The 6-character action queue:** With 6 party members and 8 enemies, the action queue can be 14 deep per round. The simulator sorts by speed (with the original's speed-based algorithm) and emits the queue at the start of each round. The view animates the queue in order. AI-controlled combatants (enemies, and any party member set to "auto" mode) pick actions from an `AIStrategy` resource.

**The AI strategy resource:** A small data resource that says "if HP < 30%, prefer healing techs; if HP > 70%, prefer highest-damage tech; if any enemy is weak to my element, prefer that tech." The exact strategy is data, not code, so the agent can author 4-5 strategies and enemies reference them by ID. This is a §3.5 spirit application to the AI side.

**Test surface:** `tests/test_battle_sim.gd` validates that (a) the action queue sorts correctly by speed, (b) damage calculation matches the expected formula across 100 seeded random fights, (c) status applications respect resistance and immunity, (d) the battle log round-trips through save/load, (e) a full battle can be simulated without a view (headless).

### 7.11 The Save, Migration, and Long-Lived Project Layer

**Locked design reference:** §3 (entire redesign is a 3-phase project spanning potentially years), §1.4 (mastering compounds the problem because of the long timeline).

**Godot 4 gap:** Godot 4's `ResourceSaver` saves resources but does not handle versioned save files, schema migration, or backward-compatibility. A project that ships Phase 1, audits in Phase 2, and modifies in Phase 3 needs save files that survive across phases. A player who played Phase 1 should be able to load their save in Phase 2 (assuming data compat) and Phase 3 (with migration).

**Architecture:** A `SaveSystem` autoload that owns a `SaveData` resource and a `MigrationRegistry`. Every save file has a `schema_version` field. Loading a save runs the migration chain from the file's version to the current version.

```gdscript
# autoloads/save_system.gd
class_name SaveSystem
extends Node

const CURRENT_VERSION := 7  # bumped on every schema change

@export var migration_registry: MigrationRegistry

func save(slot: int) -> void:
    var data := _build_save_data()
    data.schema_version = CURRENT_VERSION
    var path := "user://saves/slot_%d.tres" % slot
    ResourceSaver.save(data, path)

func load(slot: int) -> SaveData:
    var path := "user://saves/slot_%d.tres" % slot
    var data := ResourceLoader.load(path) as SaveData
    if data.schema_version < CURRENT_VERSION:
        data = migration_registry.migrate(data, data.schema_version, CURRENT_VERSION)
    return data
```

**Migration as data:** A `MigrationStep` is a resource with `from_version`, `to_version`, and a callable that transforms the save data. The registry holds the ordered list. The agent authors a new `MigrationStep` whenever the schema changes, and the registry is updated.

**Why this is in §7 and not §11 (Toolchain):** Because it is part of the engine modifications. §11 is about external tools (asset pipeline, headless test, doc generator); §7.11 is about the in-game save system. They are related but distinct.

**Test surface:** `tests/test_save_migration.gd` validates that (a) every migration in the registry is monotonically increasing in version, (b) applying the full chain to a Phase 1 save produces a current-version save, (c) loading a save from the future version is rejected with a clear error, (d) corrupted save files fail with a recoverable error (not a crash).

### 7.12 The Cinematic and Main-Cast Focus System

**Locked design reference:** §3.13 (6 main characters with substantially expanded interaction with their supporting cast, vs. original's "silent recruitment" pattern).

**Godot 4 gap:** No cinematic system. No dialog tree engine. No character-relationship tracking. Godot has `Dialogic` and similar plugins, but the project wants a tighter integration with the character data model (the "expanded interaction scenes" from §3.13 reference specific support characters who join the main cast's scenes).

**Architecture:** A `CinematicSystem` autoload that plays a `Cinematic` resource. A cinematic is a sequence of `CinematicBeat` resources, each of which is a dialog line, a camera move, an animation, a flag set, or a party change.

```gdscript
# cinematics/cinematic.gd
class_name Cinematic
extends Resource

@export var id: StringName
@export var beats: Array[CinematicBeat]

class CinematicBeat:
    var type: BeatType  # DIALOG, CAMERA_MOVE, ANIMATION, FLAG_SET, PARTY_CHANGE
    var payload: Dictionary

enum BeatType { DIALOG, CAMERA_MOVE, ANIMATION, FLAG_SET, PARTY_CHANGE }
```

**Why a custom cinematic system and not Dialogic:** Dialogic is a great general-purpose dialog tool, but the §3.13 commitment is that support characters appear in the *main cast's* scenes, not in their own recruitment scenes. A scene like "Serge and Kidd talk about the dragon, and Starky (a support) is present and contributes" is hard to express in Dialogic's character-isolated dialog tree. The custom system lets the agent author a scene where 4 characters are present, each with their own line, their own animation, and their own camera, and the data model is just a list of beats.

**The relationship tracker:** The "substantially expanded interaction" in §3.13 implies that the player's choices in main-cast scenes affect the relationship with the support. A `RelationshipMatrix` resource tracks per-support affection (a 0-100 int) and unlocks additional beats at thresholds.

```gdscript
# data/relationship_matrix.gd
class_name RelationshipMatrix
extends Resource

@export var support_id: StringName
@export var affection: int = 0
@export var unlocked_beats: Array[StringName]  # cinematic beat IDs unlocked
@export var threshold_beats: Array[ThresholdBeat]  # beat ID + affection threshold

class ThresholdBeat:
    var beat_id: StringName
    var threshold: int  # affection required
```

**Test surface:** `tests/test_cinematic_system.gd` validates that (a) playing a cinematic executes the beats in order, (b) `FLAG_SET` beats update the `ProgressionFlags`, (c) `PARTY_CHANGE` beats update the `Party`, (d) `RelationshipMatrix` unlocks beats at the right thresholds, (e) a cinematic can be paused, resumed, and skipped.

### 7.13 The Mod API Surface

**Locked design reference:** "Modifiability architecture: Phase 1 requirement, not Phase 3 retrofit" (from `loop_state.json`).

**Godot 4 gap:** Godot 4 supports mods via `addons` (compiled `.gd` files) and `ResourceLoader` paths, but does not provide a stable, documented mod API. We need a stable surface that a mod author can rely on without forking the engine.

**Architecture:** A `ModAPI` autoload that exposes the stable surface. The surface is a small, versioned set of classes and methods that the mod author can use. Anything not in the `ModAPI` is internal and may change without warning.

```gdscript
# mod_api/mod_api.gd
class_name ModAPI
extends Node

const API_VERSION := 1

# The mod can read but not write these.
func get_character_data(id: StringName) -> CharacterData: ...
func get_tech_data(id: StringName) -> Tech: ...
func get_status_data(id: StringName) -> StatusEffect: ...
func get_chapter_data(id: int) -> ChapterData: ...

# The mod can register new content.
func register_character(data: CharacterData) -> bool: ...
func register_tech(data: Tech) -> bool: ...
func register_status(data: StatusEffect) -> bool: ...
func register_chapter(data: ChapterData) -> bool: ...

# The mod can read progression state but not write it.
func get_flag(id: StringName) -> Variant: ...
func get_current_chapter() -> int: ...

# The mod can subscribe to events.
func subscribe(event: StringName, callable: Callable) -> void: ...
```

**The version contract:** `ModAPI.API_VERSION` is bumped on any breaking change. A mod authored against API version 1 may break on API version 2 — the loader prints a clear error and refuses to load the mod. A mod authored against API version 1 with no breaking changes in version 2 should continue to work; the loader applies a compatibility shim if needed.

**The mod loader:** A `ModLoader` autoload reads `user://mods/*.mod.json`, validates the API version, and registers the mod's content. The format is documented in `docs/mod_format.md` (a future §11 deliverable).

**What the mod API does *not* expose:** Internal simulation details, scene-level hooks, save file structure. These change too often to be a stable contract. A mod that needs them forks the project.

**Test surface:** `tests/test_mod_api.gd` validates that (a) registering a valid `CharacterData` makes it available to the game, (b) registering an invalid `CharacterData` is rejected with a clear error, (c) API version mismatch is rejected, (d) subscribing to an event fires the callable at the right time.

### 7.14 The Cross-Subsystem Integration Test

**Architecture:** A single integration test that exercises all eleven subsystems in a realistic scenario: a 3-on-3 fight with one of each element, a status effect application, a form change mid-fight, a chapter transition, a save, a load, a mod that adds a new tech, and a re-fight.

```gdscript
# tests/test_full_integration.gd
func test_full_integration() -> void:
    # 1. Set up a new game state at chapter 1, party of 3.
    ChapterSystem.advance_to(1)
    Party.unlock_next(load("res://data/characters/serge.tres"))
    Party.unlock_next(load("res://data/characters/kidd.tres"))
    Party.unlock_next(load("res://data/characters/nikki.tres"))

    # 2. Fight 3-on-3.
    var battle := Battle.new()
    battle.party = Party
    battle.enemies = [EnemyA, EnemyB, EnemyC]
    var result := await battle.start_battle()
    assert(result.winner == BattleSide.PARTY)

    # 3. Apply a status (Poison) and verify tick.
    StatusEngine.apply(EnemyA, StatusRegistry.POISON, source: Serge)
    Determinism.seed_rng(42)
    battle.sim.advance_turn()
    assert(EnemyA.hp < pre_combat_hp)

    # 4. Change form and verify tech migration.
    FormStateMachine.change_form(FormStateMachine.Form.LYNX, {})
    assert(FormStateMachine.current_form == FormStateMachine.Form.LYNX)

    # 5. Advance chapter and verify party unlock.
    ChapterSystem.advance_to(4)
    assert(Party.active_count == 4)

    # 6. Save, load, and verify state.
    SaveSystem.save(0)
    var saved := SaveSystem.load(0)
    assert(saved.chapter == 4)
    assert(saved.party.active_count == 4)

    # 7. Load a mod that adds a new tech and verify it's available.
    ModLoader.load_mod("res://mods/test_tech.mod.json")
    assert(ModAPI.get_tech_data("test_tech_42") != null)

    # 8. Re-fight with the new tech available.
    var rematch := Battle.new()
    rematch.party = Party
    rematch.enemies = [EnemyA, EnemyB, EnemyC]
    var rematch_result := await rematch.start_battle()
    assert(rematch_result.winner == BattleSide.PARTY)
```

**This test is the smoke test for the entire modification layer.** If it passes, the eleven subsystems are wired together correctly. If it fails, the failure points to the specific subsystem (the line of the assertion that broke). The test runs in CI on every commit.

### 7.15 Summary Table

| # | Subsystem | Locked Design Reference | Test Surface |
|---|-----------|-------------------------|--------------|
| 7.2 | Determinism Layer | §1.5, §3 (entire) | tests/test_determinism.gd |
| 7.3 | Tech and Augmentation System | §3.5, §3.6, §3.4 | tests/test_tech_loader.gd, test_base_loadout.gd |
| 7.4 | Element Grid and Resistance | §3.4 | tests/test_element_grid.gd |
| 7.5 | Status Effect Engine | §3.5, §3.4 | tests/test_status_engine.gd |
| 7.6 | Form-Change State Machine | §3.7 | tests/test_form_state_machine.gd |
| 7.7 | 6-Character Party Formation | §3.9 | tests/test_party.gd |
| 7.8 | Chapter and Progression System | §3.9, §3.13 | tests/test_chapter_system.gd |
| 7.9 | HD-2D Rendering Stack | §3.10, §6.9 | tests/test_hd2d_pipeline.gd |
| 7.10 | Combat Engine | §3.5, §3.9 | tests/test_battle_sim.gd |
| 7.11 | Save, Migration, Long-Lived Project | §1.4, §3 | tests/test_save_migration.gd |
| 7.12 | Cinematic and Main-Cast Focus | §3.13 | tests/test_cinematic_system.gd |
| 7.13 | Mod API Surface | "Phase 1 requirement" | tests/test_mod_api.gd |
| 7.14 | Cross-Subsystem Integration | (composite) | tests/test_full_integration.gd |

### 7.16 Decisions Needed

These are choices the section commits to but the user may want to revisit:

- **Derived PRNGs vs single PRNG.** §7.2 uses derived PRNGs scoped by tag (combat, dialog, etc.) so test inspection can identify *which* subsystem consumed entropy. The cost is more state in the save file (~12 ints) and the discipline of always going through `Determinism.scoped(tag)`. The alternative is a single global PRNG and let tests count entropy calls precisely. Recommendation: derived PRNGs — the discipline is already implied by §1.5 (no magic, explicit) and the cost is small.
- **Augmentations as data vs. as code.** §7.3 makes augmentations pure data (`TechAugmentation` resources). The alternative is to allow `Tech` to have a `_resolve()` method that runs arbitrary GDScript. The data-only approach limits what augmentations can do (no custom logic) but makes techs lintable, replayable, and easy to author. The code approach is more flexible but breaks the agent's ability to reason about techs as data. Recommendation: data only, with an extension point (`TechAugmentation.custom_handler: StringName`) for the rare case where pure data is not enough.
- **Chapter transitions as data vs. as script.** §7.8 makes chapter transitions a list of side effects on a `ChapterData` resource. The alternative is a chapter script that calls `Party.unlock_next()`, `SceneQueue.play()`, etc. The data approach is more declarative and easier to lint; the script approach is more flexible. Recommendation: data only for the standard transitions, with a `ChapterData.post_transition_script: GDScript` field for the rare chapter that needs custom logic.
- **Cinematics as data vs. as script.** Same trade as chapter transitions. §7.12 commits to data-only beats. Recommendation: data only.
- **Save file format (text vs binary).** §7.11 uses Godot's `ResourceSaver` which produces text `.tres` files by default. Text saves are diffable, lintable, and easy to migrate. Binary saves are smaller and faster. For a single-player game with infrequent saves, the size difference is negligible. Recommendation: text saves, with a binary option for the rare case where save size matters.

These are not blocking the document's continuation. §8 (The Remaster Pipeline) is unblocked and can be drafted next. §8 will specify the end-to-end pipeline that uses these subsystems to convert Chrono Cross source-material (emulation captures, scripts, wikis) into a runnable Phase 1 remaster.

---
## 8. The Remaster Pipeline

This section specifies the end-to-end pipeline that converts Chrono Cross source material — emulation captures, scripts, official art, fan wikis, YouTube playthroughs, related-work context — into a runnable Phase 1 remaster, and that subsequently carries the project through the Stabilization Audit and into the Modifications phase. The section is the operational counterpart to §6 (Godot 4 Deep Dive, which specified the chassis) and §7 (Engine Modifications Needed, which specified the body). §8 specifies the assembly line. §9 (AI-Agent Workflow) will specify who runs the line and how it is steered; the two sections are designed to be read in either order, but they will overlap on a few points where the pipeline's contract with the agent is most explicit.

The pipeline has six stages: **Source Acquisition**, **Asset Extraction**, **Data Translation**, **Scene Assembly**, **Test**, and **Iteration**. Each stage is a discrete directory under `pipeline/` with an input contract, an output contract, a tool surface, a logging convention, and a documented failure mode. The pipeline is idempotent — re-running any stage from its outputs reproduces its outputs, so partial runs are safe and CI re-runs are cheap. The pipeline is text-first — every artifact is either a JSON, a text resource, a GDScript file, or a referenced PNG; there is no binary blob that cannot be diffed, linted, or migrated. The pipeline is auditable — every state change is logged to a `pipeline.log` with timestamps, input hashes, and output hashes, so a bug found three months after the fact can be traced back to the specific commit and the specific source-material commit hash that produced it.

### 8.1 Why a Pipeline at All

The temptation in a fan-remaster project is to skip the pipeline and do everything by hand. A developer dumps a folder of screenshots into a `sprites/` directory, eyeballs the dialog text from a YouTube video, hand-types a script, and ships. This is the path to the failure mode §1.4 names: "the original game's quality is taken as gospel, bugs and quirks included." It is also the path to inconsistency — character stats drift between battles, scene triggers fire in the wrong order, save data becomes unloadable after a content update, and the project becomes unmaintainable by the time the Phase 2 audit starts.

A pipeline is the discipline that prevents these failure modes. It does not need to be sophisticated. It does not need to be fully automated. It needs to be **explicit about its inputs and outputs**, so that the agent (or the user) can inspect what happened at any stage, reproduce it, and improve it incrementally. The bar for "is this a pipeline?" is not "does it run end-to-end without human input?" but "if I run stage 3 twice with the same inputs, do I get the same outputs, and can I read the logs to understand what changed?"

The bar is also not "is the pipeline infallible?" It will be wrong sometimes — source material contradicts itself between a 1999 script dump and a 2018 fan translation, an emulated battle's RNG produces a different critical-hit pattern than the wiki claims, a YouTube playthrough shows a cutscene the emulation does not. The pipeline's job is to surface these contradictions, not to hide them. A pipeline that says "I noticed the wiki says X but the script dump says Y, and I picked Y because [reason]" is a good pipeline. A pipeline that silently picks one and moves on is not.

### 8.2 Stage 1: Source Acquisition

**Purpose:** Acquire the raw source material for the remaster and store it as immutable, version-controlled artifacts.

**Input contract:** None. This is the start of the pipeline.

**Output contract:** A populated `sources/` directory with subdirectories for each source type, each with a `MANIFEST.json` listing every file, its SHA-256 hash, its source URL or path, its acquisition date, and its license status.

**Tool surface:**
- `pipeline/01_acquire/fetch_emulation_dumps.py` — runs the user's legally-obtained PS1 emulation environment to dump the disc contents (BIN/CUE or CHD), extracts the filesystem (TIM textures, SEQ/MIDI music, model data, script blocks), and writes them to `sources/emulation/`. **License gating:** the script refuses to run unless `SOURCES_LICENSE_OK=1` is exported, which the user sets only after confirming they own the original game and accept that the dumped assets are for personal, non-redistributable use. The script logs a clear warning and the reason every time it runs.
- `pipeline/01_acquire/fetch_wikis.py` — pulls the Chrono Cross wiki pages (Chronowiki, Chrono Compendium, and a curated subset of GameFAQs / Reddit megathreads) and saves them as Markdown under `sources/wikis/`. Rate-limited to 1 request/second with a 24-hour cooldown on re-runs (per the wiki's robots.txt). Markdown is the format so the agent can diff changes between wiki revisions.
- `pipeline/01_acquire/fetch_youtube.py` — downloads specific YouTube playthroughs from a curated list (full-game no-commentary runs, dungeon-specific walkthroughs, the original Japanese audio track for the localization comparison) using `yt-dlp`, saves the video to `sources/youtube/`, and extracts the audio as WAV for transcript analysis. The video is kept as a reference, not used as an asset.
- `pipeline/01_acquire/fetch_scripts.py` — pulls the published Chrono Cross script dumps (Chrono Compendium, JASerino's translation patches) and saves them as plain text under `sources/scripts/`. Script dumps are the highest-fidelity content source for dialog and scene direction.
- `pipeline/01_acquire/fetch_official_art.py` — pulls publicly-released official art (the original Square Enix press kit, the 25th-anniversary key art) from approved URLs. This is the only art source that can be redistributed; everything else in the art pipeline is either the user's own work, fan-redrawn substitutes, or placeholder.

**Logging convention:** Every acquisition run appends to `sources/MANIFEST.json` with the file's hash, source, date, and license status. The MANIFEST is committed to version control, so the project has a permanent record of where each source came from and when.

**Failure modes:**
- **Source unavailable.** The wiki is down, the YouTube video is taken down, the emulation dump is incomplete. The script fails loudly, the affected stage does not silently proceed. The agent can substitute a known-lower-fidelity source (e.g., a GameFAQs text transcript instead of a YouTube playthrough), but the substitution is logged.
- **Source contradicts another source.** The script dump says one thing, the wiki says another. The pipeline does not resolve this; the conflict is logged in `sources/CONFLICTS.md` and flagged for the agent to resolve at Stage 3.
- **License status uncertain.** A new source type is added but its license is unclear. The pipeline refuses to ingest it; the user must explicitly approve before re-running.

**Design commitment:** The acquisition stage is a Phase 1 requirement. Without it, no downstream stage has anything to translate. The first cron loop after project setup is the one that runs `fetch_emulation_dumps.py` and `fetch_scripts.py` for the first time. Every subsequent run is incremental — the script skips files whose hash is already in the MANIFEST.

### 8.3 Stage 2: Asset Extraction

**Purpose:** Convert the raw source material into a set of named, indexed, format-normalized assets ready for the Godot 4 project.

**Input contract:** `sources/` populated and MANIFEST-checked.

**Output contract:** A populated `assets/` directory with subdirectories for each asset type, each with a `MANIFEST.json` listing every file, its source provenance, its license, its current state, and any transformation history.

**Tool surface:**
- `pipeline/02_extract/extract_textures.py` — reads TIM files from `sources/emulation/`, converts them to PNG using `Pillow` (or the equivalent in `ImageMagick` for batch operations), and writes them to `assets/sprites_raw/`, `assets/backgrounds_raw/`, `assets/tilesets_raw/`, and `assets/portraits_raw/` based on the TIM's metadata block. **License gating:** raw extracted textures are marked `license: personal_use_only` and are NOT committed to a public version of the project; the pipeline generates `assets/*_reproduction/` directories that contain either the user's own redrawn versions or fan-art substitutes for public distribution.
- `pipeline/02_extract/extract_audio.py` — reads SEQ/MIDI from `sources/emulation/`, converts to OGG Vorbis using `timidity++` (for MIDI) or `ffmpeg` (for any compressed audio), and writes to `assets/music_raw/` and `assets/sfx_raw/`. The same `personal_use_only` license gate applies; the pipeline generates `assets/music_reproduction/` with synthesized or substituted audio for the public build.
- `pipeline/02_extract/extract_dialog.py` — reads script dumps from `sources/scripts/`, parses the dialog format (Chrono Compendium's annotated format with speaker tags and direction), and writes structured JSON to `assets/dialog_raw/`. Each scene becomes a JSON file with `speakers`, `lines`, `directions`, and `events` (camera moves, character changes, etc.). The parser is hand-written in Python; the script format is well-documented but varies between dumps, so the parser has explicit fallbacks per known format.
- `pipeline/02_extract/extract_maps.py` — reads map data from `sources/emulation/`, parses the tile grid, event placements, and warp connections, and writes structured JSON to `assets/maps_raw/`. This is the most fragile extraction; PS1-era map formats use variable-length records and the parser is the most likely place for silent data loss. The pipeline logs every map's tile count, event count, and warp count, and a downstream test asserts the sum of all map tile counts equals the expected total for the game (a sanity check that catches lost maps).
- `pipeline/02_extract/extract_stats.py` — reads character, enemy, and tech data from `sources/emulation/` and `sources/wikis/`, writes structured JSON to `assets/stats_raw/`. This is the most contested extraction — stat values are scattered across save formats, battle scripts, and wiki hand-tables, and the values often disagree by 1-2 points. The pipeline writes all variants to `assets/stats_raw/variants/` and resolves them at Stage 3.

**Logging convention:** Every extraction run appends to `assets/MANIFEST.json` with the source file, the output file, the transformation applied (e.g., `TIM→PNG, no color-palette change`), and a content hash of the output. Conflicts between sources are logged in `assets/CONFLICTS.md`.

**Failure modes:**
- **TIM format not recognized.** A variant of the PS1 TIM format the parser has not seen. The pipeline fails loudly with the offending byte offset and the surrounding hex context, so the agent can extend the parser.
- **Dialog format drift.** A new script dump uses a different annotation syntax. The pipeline falls back to a best-effort parse and flags the affected scene for manual review at Stage 3.
- **Stat variance.** A character's HP is 120 in the script dump, 122 in the wiki, and 118 in the save format. The pipeline writes all three and flags for resolution; it does not pick silently.
- **Asset count mismatch.** The map parser reports 86 maps but the known total is 85. The pipeline fails loudly; the agent must find the duplicate or the missing map before continuing.

**Design commitment:** The extraction stage is lossless in the sense that no source artifact is consumed without producing an explicit output (or an explicit failure). The pipeline does not "summarize" or "clean" the data at this stage — cleaning happens at Stage 3, with the agent able to inspect the raw output and the cleaned output side by side.

### 8.4 Stage 3: Data Translation

**Purpose:** Resolve source conflicts, normalize formats, and produce the final `data/` directory that the Godot 4 project loads directly.

**Input contract:** `assets/` populated and MANIFEST-checked.

**Output contract:** A populated `data/` directory structured per §6.5's data layer: `data/characters/*.json`, `data/techs/*.json`, `data/enemies/*.json`, `data/maps/*.json`, `data/dialog/*.json`, `data/scenes/*.json`, `data/chapters/*.json`, all validated against the §6.5 JSON Schemas.

**Tool surface:**
- `pipeline/03_translate/translate_characters.py` — reads `assets/stats_raw/`, `assets/dialog_raw/` (for character voice), and the locked design from `loop_state.json`'s `phase_3_redesign.bases` to produce `data/characters/*.json`. **For Phase 1, this is a faithful translation** of the original 40+ characters. **For Phase 3, this applies the redesign** — collapsing the 40+ characters into 6 bases + 36 supports, mapping each original character to its base or support slot per §3.2 and §3.3.
- `pipeline/03_translate/translate_techs.py` — reads `assets/stats_raw/` (tech data) and the augmentation model from §3.5 to produce `data/techs/*.json`. Each tech is either a `BaseLoadoutEntry` (tier 1 or 8 for a base) or a `TechAugmentation` (tier 2-7 for a support). The translator applies the locked design: 1 open grid slot at tier 5 per base, 3 augmentations from the first support set at tiers 3/5/7, 3 augmentations from the second set at tiers 2/4/6, with the open slot at 5.
- `pipeline/03_translate/translate_enemies.py` — reads `assets/stats_raw/`, normalizes the stat blocks, and produces `data/enemies/*.json`. For Phase 1 this is faithful; for Phase 3 the enemy roster is rebalanced for the 6-character party and the new element grid from §7.4.
- `pipeline/03_translate/translate_maps.py` — reads `assets/maps_raw/`, normalizes the tile grids to a common coordinate system, and produces `data/maps/*.json`. For Phase 3 the maps are rebuilt in HD-2D layering per §7.9.
- `pipeline/03_translate/translate_dialog.py` — reads `assets/dialog_raw/`, applies the original speaker-to-character mapping, and produces `data/dialog/*.json`. The translator flags any line that does not match a known speaker for the scene. For Phase 3 the dialog is augmented with the expanded main-cast interaction scenes from §3.13.
- `pipeline/03_translate/translate_scenes.py` — reads `assets/dialog_raw/`, `assets/maps_raw/`, and the chapter structure from §7.8 to produce `data/scenes/*.json` and `data/chapters/*.json`. Each scene specifies its map, its participants, its dialog, and any events (camera moves, character form changes, party additions). The chapter file lists scenes in order, with side effects (party unlocks, flag sets, music changes) as data.
- `pipeline/03_translate/resolve_conflicts.py` — reads `assets/CONFLICTS.md` and `sources/CONFLICTS.md` and produces a `data/CONFLICT_RESOLUTIONS.md` documenting which conflict was resolved how, and why. The resolutions are committed and signed off by the user for any choice that affects gameplay (e.g., "we picked the script dump's stat value over the wiki's because the script dump is from the original 1999 binary"). Cosmetic conflicts (e.g., "the wiki's punctuation style vs. the script dump's") are resolved by the agent with a documented rule.

**Logging convention:** Every translation run appends to `data/TRANSLATION_LOG.md` with the input file, the translation rule applied, the output file, and any conflict resolutions. The log is human-readable and is the primary review surface for the user.

**Failure modes:**
- **Schema validation failure.** A generated `*.json` does not validate against its `*.schema.json` per §6.5. The pipeline fails loudly with the specific validation error. This is the most common failure mode and the most useful — it catches typos, missing fields, and out-of-range values before they ever reach the engine.
- **Locked design conflict.** The source material's data contradicts the locked Phase 3 design (e.g., the original has a 41st character that is not in the 6-base + 36-support model). The pipeline fails loudly; the agent must either map the character to an existing slot or escalate to the user for a design decision.
- **Conflict resolution rule missing.** A new conflict was logged in `assets/CONFLICTS.md` but the translator has no rule for it. The pipeline fails loudly; the user must add a rule.

**Design commitment:** The translation stage is the only stage where the locked design is applied. Stages 1 and 2 are content-agnostic — they would work for any PS1-era JRPG with the same disk format. Stage 3 is where Chrono Cross specifically (and the redesign specifically) enters the pipeline. This separation is deliberate: a bug in the extraction stage is fixed by improving a parser, not by adjusting design; a bug in the translation stage is fixed by adjusting the locked design or a translation rule, not by tweaking the parser.

### 8.5 Stage 4: Scene Assembly

**Purpose:** Convert the structured `data/` into runnable Godot 4 scenes, scripts, and resources.

**Input contract:** `data/` validated against the §6.5 schemas.

**Output contract:** A runnable Godot 4 project at `project/` with populated scenes, scripts, and resources. `godot --headless --check-only project/` exits 0.

**Tool surface:**
- `pipeline/04_assemble/build_project.py` — copies the Godot 4 template project (version-pinned per §6.2) into `project/`, copies the `data/` directory into `project/data/`, and writes a `project.godot` configured for the project's name, main scene, autoloads, and input map.
- `pipeline/04_assemble/build_scenes.py` — reads `data/scenes/*.json` and `data/maps/*.json` and produces `project/scenes/<scene_name>.tscn` for each scene. The scene is a `Node2D` with the appropriate background layer, sprite instances, dialog box instance, and event listeners. The output is a valid Godot scene file (text `.tscn` per §6.6) that can be opened in the Godot editor.
- `pipeline/04_assemble/build_scenes_from_cinematics.py` — reads `data/chapters/*.json` and the cinematic data, and produces the main-cast interaction scenes from §3.13. This is a Phase 3-specific assembler; in Phase 1 it produces a minimal version per the original game's design.
- `pipeline/04_assemble/build_mod_api.py` — reads the API_VERSION contract from §7.13 and the registered resource types, and produces `project/addons/mod_api/plugin.cfg` and the autoload script. The mod API is built from data, not hand-edited.
- `pipeline/04_assemble/build_tests.py` — reads the test surfaces from §6.8 and §7.2-7.14 and produces `project/tests/test_*.gd` for each subsystem. The tests are themselves data-driven — the test generator reads the test patterns and produces GDScript that exercises them. **This is a key design commitment: the tests are not hand-written; they are generated from the data.** A change to the data layer regenerates the tests; the agent's job is to make the regenerated tests pass.

**Logging convention:** Every assembly run appends to `project/BUILD_LOG.md` with the input data file, the output project file, the build command, and the result. A failed build does not corrupt the project — the build writes to a temporary directory and atomically renames on success.

**Failure modes:**
- **Godot headless check fails.** The generated `project.godot` or a `.tscn` has a syntax error or a missing resource reference. The pipeline fails loudly with the Godot error log; the agent can open the project in the GUI editor to inspect the scene visually.
- **Scene graph inconsistency.** A scene references a character that is not in the party, a map that does not exist, or a dialog file that fails to load. The pipeline fails loudly; the agent must either add the missing data or remove the bad reference.
- **Mod API version mismatch.** The locked design's API_VERSION does not match the mod resources' declared version. The pipeline fails loudly; the agent must resolve the version.

**Design commitment:** The assembly stage is a pure function of `data/`. The same `data/` always produces the same `project/`. This is verified by the §6.5 schema validation and by a CI step that diffs two builds from the same `data/` and asserts they are byte-identical.

### 8.6 Stage 5: Test

**Purpose:** Verify the assembled project meets the locked design's correctness, determinism, and content-accuracy contracts.

**Input contract:** `project/` assembled and Godot-loadable.

**Output contract:** A green test suite (or a documented red one with the failures categorized).

**Tool surface:**
- `pipeline/05_test/run_unit_tests.sh` — runs `godot --headless --test` against `project/tests/test_*.gd`. The unit tests cover each subsystem in isolation: the data loader, the augmentation resolver, the element grid, the status engine, the form state machine, the party formation, the chapter system, the save/migration, the cinematic system, the mod API. Per §6.8, every test is also runnable individually with `godot --headless --test test_specific.gd` for fast iteration.
- `pipeline/05_test/run_integration_tests.sh` — runs the cross-subsystem integration test from §7.14, which exercises all eleven subsystems in a realistic 3-on-3 fight.
- `pipeline/05_test/run_determinism_tests.sh` — runs a battery of battles with seeded `BattleRNG` and asserts that the same seed produces the same outcome across runs. This is the §7.2 determinism contract in test form.
- `pipeline/05_test/run_content_accuracy_tests.sh` — runs a battery of assertions against the original source material: "Leena's HP is X" (compared to the locked design's Phase 1 stat block), "Serge's basic attack tier 1 is 'Dash and Slash'" (compared to §3.2's locked tier 1), "the form-change scene at chapter 5 triggers the migration log" (compared to §3.7's locked narrative), and so on. These tests are the contract that the source material has been faithfully translated.
- `pipeline/05_test/run_visual_regression_tests.sh` — renders a battery of scenes to PNG and compares against committed baselines. This catches accidental visual regressions (a misaligned sprite, a wrong palette) that the unit tests would miss.

**Logging convention:** Every test run produces a JUnit-format XML log at `test_results/<timestamp>/results.xml` and a human-readable summary at `test_results/<timestamp>/summary.md`. Failures include a one-line repro command that an agent (or the user) can copy-paste to reproduce.

**Failure modes:**
- **Determinism test fails.** A subsystem is consuming entropy without going through `Determinism.scoped(tag)`. The test identifies the offending file and line; the agent fixes the leak.
- **Content accuracy test fails.** A translated value differs from the source. The test identifies the value; the agent investigates whether the source was wrong, the translation rule was wrong, or the locked design intentionally changed the value (Phase 3).
- **Visual regression test fails.** A scene's render output differs from the baseline. The agent opens both PNGs side by side and decides whether the change was intentional (a deliberate visual fix) or a regression (a sprite moved, a layer offset changed).

**Design commitment:** The test stage is run on every commit in CI and on every change to `data/`. A red build blocks merge. The user can run the test stage locally with `bash pipeline/05_test/run_all.sh` to verify before pushing.

### 8.7 Stage 6: Iteration

**Purpose:** Apply the §1.4 design loop — "spec → minimal implementation → test → observe → revise" — across the three project phases, with the pipeline as the substrate.

**Input contract:** Any prior stage's outputs, plus the locked design and any decisions from `review.md`.

**Output contract:** An updated `data/` (and through Stages 4-5, an updated `project/`) that reflects the design change.

**Tool surface:**
- **For Phase 1 (Faithful Remaster):** the iteration is "re-run Stages 1-5 with the source material, then re-run with the user's review notes." The agent's job is to translate faithfully and surface conflicts for the user. The pipeline's job is to make every translation reproducible and every conflict visible.
- **For Phase 2 (Stabilization Audit):** the iteration is "evaluate every vestigial design choice on its own merits." The agent reads the §1.4 audit checklist against the original game's mechanics, documents the choices in `audit/`, and proposes changes in `review.md`. The pipeline's job is to make the audit's data sources (the original game's source dumps, the wiki's stat tables, the user's playthrough videos) easily queryable.
- **For Phase 3 (Modifications):** the iteration is "apply the Phase 2 audit + the locked Phase 3 redesign + any new content." The pipeline's job is to make the changes data-driven: a §3.5 augmentation is a change to `data/techs/`, not a rewrite of `project/scripts/`. A §3.13 expanded interaction scene is a change to `data/scenes/`, not a hand-authored `.tscn`.

**Logging convention:** Every iteration cycle appends to `pipeline/ITERATION_LOG.md` with the phase, the change, the rationale, the data files affected, and the resulting test results. This is the project's design history; a maintainer (or the user) can read it to understand why a particular design choice was made.

**Failure modes:**
- **Locked design conflict.** A proposed iteration conflicts with the locked design (e.g., a Phase 2 audit recommends keeping a mechanic that the Phase 3 redesign explicitly removes). The agent must escalate to the user; the iteration is not applied.
- **Data schema insufficient.** The proposed iteration requires a data field that the §6.5 schema does not have. The agent extends the schema (with a migration per §7.11), then applies the iteration.
- **Test regression.** The proposed iteration breaks an existing test. The agent must either fix the iteration (the test is correct) or update the test (the test was wrong). The user reviews test changes.

**Design commitment:** The pipeline supports all three phases without modification. The same Stages 1-5 produce a Phase 1 build, a Phase 2 build, and a Phase 3 build. The difference is the data, not the pipeline. This is the §1.5 "decoupled layers" principle applied at the project level.

### 8.8 The Pipeline as a Whole

The pipeline is run end-to-end by `pipeline/run_all.sh`, which executes Stages 1-6 in order with appropriate skips for already-completed stages. The script is idempotent — re-running it after no source changes is a no-op (or a verification re-run if `--verify` is passed). The script is parameterizable — `pipeline/run_all.sh --until-stage 4` runs Stages 1-4 only, useful for fast iteration on the assembly stage without re-acquiring sources.

**Pipeline state file:** `pipeline/PIPELINE_STATE.json` tracks the last successful run of each stage, the input hash, and the output hash. If the input hash matches, the stage is skipped. If the input hash differs, the stage is re-run. This is the same pattern as the source MANIFEST and the asset MANIFEST — the pipeline is content-addressed at every level.

**Pipeline observability:** The `pipeline/` directory is the single source of truth for what happened. A user who asks "where did this stat value come from?" can `git log` the `data/` file, then follow the PIPELINE_LOG back to the `assets/` file, then follow the asset MANIFEST back to the `sources/` file, then follow the source MANIFEST back to the URL or the emulation dump. The chain is auditable from end to end.

**Pipeline cost:** The first end-to-end run (acquiring all sources, extracting all assets, translating all data, assembling the project, running the test suite) is estimated at 8-16 hours of wall time, mostly spent on asset extraction (TIM-to-PNG conversion for ~3000 textures is slow) and the initial Godot headless test run. Subsequent runs are incremental and take 5-30 minutes, depending on how much `data/` changed.

### 8.9 Phase-Specific Pipeline Behavior

**Phase 1 (Faithful Remaster):** Stages 1-5 produce a runnable Godot 4 version of the original Chrono Cross with modern tech but original content/flow/balance. The `data/` directory mirrors the original game's stat blocks, dialog, maps, and scene structure. The pipeline's job is to surface every place where the modern engine requires a decision the original game did not have to make (e.g., "the original game has 3 party members in combat; the new pipeline produces a 3-character party data structure; Phase 3 will change this to 6 characters").

**Phase 2 (Stabilization Audit):** The agent runs `pipeline/audit/run_audit.sh` which produces `audit/AUDIT_REPORT.md` evaluating every original-game mechanic against the criteria in §1.4. The audit proposes changes; the user reviews in `review.md`; the agent applies the approved changes by updating `data/` and re-running Stages 4-6.

**Phase 3 (Modifications):** The agent runs `pipeline/apply_redesign.sh` which reads the locked design from `loop_state.json`'s `phase_3_redesign` and rewrites `data/` accordingly. The §3.5 augmentation model is applied to every tech; the §3.7 Pip reframing is applied to the form-change data; the §3.9 6-character party is applied to every scene and chapter. The pipeline produces a new `data/` from the old `data/` + the locked design + the user's review-approved changes.

**The same Stages 4-6 run for all three phases.** The difference is the `data/` that goes into Stage 4. This is the discipline: the project has one assembly line, three products.

### 8.10 Pipeline Failure and Recovery

The pipeline is designed to fail loudly and recover cheaply. Every stage's output is content-addressed (hashed); a failed run does not produce a half-written output. The agent (or the user) can run any stage from its inputs and reproduce the same outputs. The CI system runs the pipeline on every push and on every night, with a slack/email alert on red.

**The most likely failure mode is a source change.** The original Chrono Cross emulation environment produces slightly different output on different runs (the TIM file format has timestamp metadata, for example). The pipeline's content-addressing detects this and re-runs the affected stage. The user reviews the diff to confirm the change is benign.

**The second-most-likely failure mode is a Godot 4 update.** When the user upgrades the Godot 4 binary (per §6.2's vendoring plan), the headless test run may produce new warnings or new errors. The pipeline surfaces them; the agent investigates whether they are real regressions or false positives.

**The third-most-likely failure mode is a design change in `loop_state.json`.** When the user updates the locked design (e.g., adds a new base character, changes an element assignment, modifies a support combination rule), the pipeline regenerates the affected `data/` files and re-runs the affected tests. The user reviews the regenerated files to confirm they match the design intent.

### 8.11 Decisions Needed

These are choices the section commits to but the user may want to revisit:

- **Source acquisition automation level.** §8.2 commits to automated fetching for emulation dumps (with a license gate), wikis, YouTube playthroughs, and script dumps. The user may want some of these to be manual (the user downloads the script dump and places it in `sources/scripts/` by hand). The trade-off is automation vs. control over the source corpus. Recommendation: automate the open-license sources (wikis, scripts) and gate the licensed sources (emulation, YouTube) behind a license check.
- **Asset extraction tooling.** §8.3 commits to Python scripts using `Pillow`, `ffmpeg`, and `timidity++`. The user may want a different toolchain (e.g., ImageMagick for textures, a custom Go binary for dialog parsing). The trade-off is familiarity vs. performance vs. license compatibility. Recommendation: Python with the named libraries — the agent is fluent in Python, the libraries are well-maintained, and the licensing is permissive.
- **Translation stage as a single script or a pipeline of micro-scripts.** §8.4 uses a script per data type (`translate_characters.py`, `translate_techs.py`, etc.). The user may want a single `translate_all.py` that runs them in order, or a more granular decomposition. Recommendation: one script per data type — the granularity makes partial re-runs possible and the per-script logs are easier to read.
- **Visual regression baseline set.** §8.6 commits to a committed set of baseline scene renders for visual regression. The user may want a smaller set (only the title screen and one dungeon) or a larger set (every cutscene). Recommendation: medium set — the title screen, one overworld scene, one dungeon scene, one battle scene, one dialog scene, one form-change scene. Six baselines, ~50MB of committed PNGs.
- **Phase 2 audit trigger.** §8.9 commits to running the Phase 2 audit after Phase 1 reaches "the original game is faithfully remastered and stable for 30 consecutive days of agent playthrough." The user may want a different trigger (e.g., "after X number of test cycles," "after the user has played through once"). Recommendation: the 30-day stability gate — it ensures the Phase 1 baseline is actually stable, not just nominally complete.

These are not blocking the document's continuation. §9 (AI-Agent Workflow) is unblocked and can be drafted next. §9 will specify who runs the pipeline (the agent, with the user at the design gates) and how the pipeline is steered, monitored, and improved.
## 9. AI-Agent Workflow

This section specifies how an AI agent actually works on this project day-to-day. §6 specified the engine, §7 specified the thirteen subsystems, §8 specified the assembly line. None of those three pieces answer the most operational question: **when the agent sits down (or wakes up) to do work, what does that work look like?** What files does it open? What commands does it run? When does it stop and ask the user? When does it push forward? How does the autonomy model from §1 — "mostly autonomous with design gates" — actually manifest in the agent's working set of tools, files, and decisions?

This section answers those questions. It is the fourth leg of the chassis-body-assembly-line-operating-procedure four-leg stool, and a future maintainer (or the user) who wants to understand "how the agent actually works" should read §1.5 (principles), §6 (chassis), §7 (body), §8 (assembly line), and §9 (operating procedure) together. §9 is the section that turns everything prior into a working day.

### 9.1 The Agent's Working Set

Every loop — every "wake up and do work" iteration of the agent — opens the same set of files. This is the agent's working set, the context it needs before it can make any forward progress. The discipline of opening the same files every time is what makes the agent's behavior predictable and reviewable.

**Required reads at loop start (in order):**

1. `loop_state.json` — what section is in progress, what comes next, what the locked design is, what decisions are open. This is the project's "today" file.
2. `loop_memory.md` — what prior loops learned, what the user's working style is, what corrections are owed. This is the project's "history" file, narrowed to the lessons that matter.
3. `review.md` — what decisions are pending user input. The agent notes them but does not block; it advances to a section that does not need them.
4. `remaster_engine_design_spec.md` — the current state of the document. The agent finds the next "not_started" section in the table of contents and the section that comes after it, and reads enough of each to understand the voice and what the section should cover.
5. `phase_3_redesign` in `loop_state.json` — the locked design for the §3 redesign. This is the contract the §3.16 summary points to, and it is the input the agent uses for any work that touches Phase 3 design questions.

**The discipline:** The agent does not skip the `loop_memory.md` read. Prior loops have established a working set of conventions (the cat-concatenation pattern for appending sections, the single-line JSON anchors for the sections array, the "honest flags belong in the section, not buried in review.md" rule, the "data as primary, code as fallback" pattern). A new loop that starts without reading memory will re-discover these lessons the hard way, usually by clobbering the file in §1's mistake or by failing to find the right anchor in `loop_state.json`.

**Optional reads depending on the loop's task:**

- For combat work: the §6.7 combat simulation architecture and the §7.10 combat engine, plus the §3.5 augmentation model and the §3.7 Pip reframing. The combat system is the most cross-referenced subsystem in the document, and any combat-related work needs to understand both the design intent (§3) and the implementation (§6.7 + §7.10) at the same time.
- For data work: the §6.5 data layer (resources, JSON, schemas) and the §8.4 data translation stage. The agent does not hand-author data files in the redesign; it writes translation scripts that produce the data from the locked design, then validates the output against the schema.
- For visual work: the §6.9 HD-2D in Godot 4 and the §7.9 HD-2D rendering stack. Visual work is the highest-risk area for the agent because the agent cannot see the running game; the §8.6 visual regression test battery is the safety net.
- For save/load or migration work: the §7.11 save/migration layer. Save data is the one place where the agent cannot recover from a bad decision with a "re-run the pipeline" — the player has already invested time in the save.

**What the agent does not read every loop:** The full `remaster_engine_design_spec.md` is ~33K words and growing. The agent does not re-read prior sections unless the current work depends on them. The §1.5 principles, the §3.16 locked-design summary, the §6.3 project structure, and the §7 summary table (§7.15) are the four "always-fresh" sections the agent keeps in mind.

### 9.2 The Agent's Toolchain at Runtime

The agent has six categories of tools available, and the discipline is to use the right one for the right job. The cron prompt enumerates them as `file`, `terminal`, `web`, and other categories, but the operational reality is more specific.

**File tools (`read_file`, `write_file`, `patch`, `search_files`):** Used for reading and writing project files. The `read_file` tool supports offset/limit for paginated reads of large files; the `patch` tool is the right choice for targeted edits to existing files; the `write_file` tool is for new files or for full-file overwrites when no other approach will work (it clobbers, per Loop 1's lesson). The `search_files` tool with `target=content` is the agent's grep; with `target=files` it is the agent's `find`. The agent should never use `cat` or `echo >` from the terminal for file operations when a file tool is available — the file tools give line numbers, syntax checks, and structured diffs that shell redirection does not.

**Terminal (`terminal`, `process`):** Used for running build tools, test suites, scripts, and any command that needs shell semantics. The Godot 4 headless binary, the Python translation scripts, the pandoc .docx generator, the `git` commands — all run through the terminal. The `process` tool is for long-running background work (a build that takes 10 minutes, a test suite that runs overnight) where the agent wants to do other work in parallel.

**Web (`web_search`, `web_fetch`):** Used for fetching reference material that the agent does not have in its training data. The Godot 4 documentation, the Chrono Cross wiki pages, the official asset references, the API docs for `Pillow` and `ffmpeg` — all are web-fetched on demand. The agent does not web-fetch when the answer is in a file the agent has already read; that wastes tool calls and time. The web is the agent's "I don't know, let me look it up" tool, not a default.

**Image analysis (`vision_analyze`):** Used for the rare cases when the agent needs to interpret an image. The most common case is comparing a generated visual regression baseline to a current render — the agent fetches both PNGs, runs `vision_analyze` on each, and the tool reports the difference. This is also the tool the agent uses when the user attaches a screenshot ("here's what's broken in this scene") and the agent needs to read it. The agent does not use `vision_analyze` on every visual asset in the project; that would consume hours of tool calls for marginal benefit.

**Skill and plugin tools:** The agent may have project-specific skills loaded (e.g., the `hermes-agent` skill for documentation and workflows). The agent uses these when the task matches the skill's purpose and ignores them otherwise.

**Conversation tools (send_message, etc.):** Used for talking to the user, both for the loop's summary message and for escalation when the agent hits a design decision it cannot make. The agent does not use these for general narration; the conversation is the user's UI for the project, and the agent should produce output the user wants to read, not chatter.

### 9.3 The Loop Protocol, Operationalized

The cron prompt's Step 1-9 protocol is the abstract form. The operational form — what the agent actually does in a single loop — has a tighter rhythm. Every loop fits in one of three shapes: **draft loop**, **fix loop**, or **gate loop**.

**Draft loop.** The default loop shape. The agent opens the working set, identifies the next "not_started" section, drafts it, appends it to the document, regenerates the .docx, updates the state file, updates the memory file, appends any new decisions to `review.md`, and sends the summary. This is the most common loop shape and the only one that adds new content to the document.

A draft loop typically runs 5-15 minutes of agent wall time. The breakdown: ~1 minute reading the working set, ~5-12 minutes drafting the section, ~30 seconds appending and regenerating, ~1 minute updating state and memory, ~30 seconds writing the summary. The drafting step is the dominant cost; everything else is overhead.

**Fix loop.** Triggered when a user message corrects something the agent did in a prior loop (a section is wrong, a file was clobbered, a decision was made that needed user approval). The fix loop does not advance to the next section; it goes back and fixes the prior section, then logs the correction in `loop_memory.md` so future loops do not repeat the mistake. A fix loop is shorter than a draft loop (typically 1-5 minutes) and is often followed by a draft loop once the fix is in.

A fix loop is the discipline that keeps the project honest. The user has explicitly corrected prior agents in this conversation ("the results we had before from some of those projects are admittedly not great" — this is a fix-loop trigger, not just a complaint), and the agent treats corrections as the most valuable input it receives.

**Gate loop.** Triggered when a decision in `review.md` blocks forward progress (e.g., a Phase 3 design question that every subsequent section depends on, or a §10 PS1 challenge that needs user context). The gate loop does not draft a new section; it surfaces the blocker to the user explicitly, in the loop summary, and waits. The gate loop is the rarest of the three shapes; the cron prompt's "if everything is blocked, log idle and stay quiet" rule applies, but in practice the project has enough unblocked work that gate loops are exceptional.

The three shapes — draft, fix, gate — are the operational loop taxonomy. A maintainer reading `loop_memory.md` and `loop_state.json` after the fact can identify which shape each loop was by looking at what changed: draft loops change `current_section_in_progress` and add a section; fix loops change content but not the section pointer; gate loops change neither.

### 9.4 The Agent's Typical TDD Loop

For implementation work (after the design document is complete enough to start coding), the agent's day-to-day rhythm is a TDD loop. The loop has six steps and runs in minutes, not hours, because the §6.7 combat simulation architecture and the §7.2 determinism layer make the test feedback fast and reliable.

**Step 1: Read the failing test.** The agent has just generated (or just been handed) a test that is failing. The test specifies what behavior is expected — "Leena+Poshul's tier-3 augment applies Sleep 30% of the time" — and the code under test is not yet producing that behavior. The agent reads the test, the test's fixtures, and the relevant §6.5 schema or §7.3 data model to understand what the code should do.

**Step 2: Locate the code to change.** The agent uses `search_files` and `read_file` to find the implementation file. For the example above, that might be `combat/techs/leena_poshul_augment.gd` or its equivalent in the project's source tree. The agent reads the existing implementation to understand the current behavior, then identifies the smallest change that will make the test pass.

**Step 3: Make the change.** The agent uses `patch` for targeted edits, `write_file` only for new files. The change is small — typically 5-30 lines of GDScript, often less. The agent does not refactor unrelated code in the same change; that is a separate loop.

**Step 4: Run the test.** The agent runs the headless test (`tools/run_tests.sh` or equivalent) and observes the result. The test framework is the §6.7 `BattleRNG` plus the §7.2 determinism layer, so the result is deterministic — the same test either passes or fails the same way every time. If the test passes, the agent moves to Step 5. If the test fails, the agent reads the failure, forms a hypothesis about why, and either fixes the implementation (back to Step 3) or fixes the test if the test is wrong.

**Step 5: Run the full test suite.** The agent runs the entire test suite, not just the test it just made pass. This catches regressions in adjacent code. A change to Leena+Poshul's tier-3 augment should not break Kidd's tier-3 augment, but a poorly written change could. The full test run is the safety net.

**Step 6: Commit and update the iteration log.** The agent commits the change to git (or the project's version control), with a commit message that names the test that was the motivation ("fix: Leena+Poshul tier-3 applies Sleep 30% of the time, fixes test_augment_sleep_chance"). The agent also appends to `pipeline/ITERATION_LOG.md` per §8.7's logging convention. The commit is the unit of progress; the iteration log is the project's design history.

**The TDD loop's discipline is its speed.** Each loop takes minutes. A 50-test suite with a few failing tests might require 20-30 TDD loops to fix, all runnable in an hour of agent wall time. A human doing the same work would take days, not because the human is slow but because the human cannot keep all 50 failing tests in working memory and cannot type the fixes at the same speed. The TDD loop is the form of work that exploits the agent's strengths (per §1.2 — speed of textual operations, endurance, consistency).

### 9.5 The Design Gates: When the Agent Stops and Asks

The autonomy model from §1.7 is "mostly autonomous with design gates." The "mostly autonomous" is the TDD loop and the document drafting. The "design gates" are the points where the agent must stop and ask the user. Knowing when to stop is the most important part of being a good agent on this project.

**The four gate types:**

1. **Locked-design conflicts.** The locked design in `loop_state.json` is the contract. If the agent encounters a choice that conflicts with the locked design, it does not make the choice — it surfaces the conflict to the user. Example: the §3.6 working assumption is "1 open slot at tier 5," but a Phase 2 audit proposes "2 open slots at tier 5 and tier 7." This is a design choice the user owns; the agent appends to `review.md` and waits.

2. **Schema additions the user should approve.** The §6.5 schema is the data contract. If the agent needs to add a new field to a schema to support new functionality (e.g., a `tech.cast_time_ms` field for the §7.10 combat engine), the agent does not add it unilaterally. It proposes the addition in `review.md` with the rationale and the affected files. The user approves or rejects.

3. **Tradeoffs the user should weigh in on.** When two approaches are roughly equivalent in agent's view and the user has a preference (e.g., text vs binary save files per §7.11, or Python vs GDScript validation tooling per §6.5), the agent appends the tradeoff to `review.md` with the agent's recommendation and the alternatives. The user picks.

4. **User-facing feature changes.** Anything that affects what the player sees, hears, or does is a design choice. The agent does not unilaterally change the visual style, the combat balance, the chapter order, the support set, or the magic tier system. These are all locked-design items, and any change is a user approval gate.

**What is not a gate.** The agent does not ask permission for: implementation details (which file to put a class in, which helper function to extract, which variable name to use), bug fixes (the test failed, the agent fixes it), refactoring of the agent's own prior work, schema migrations (the §7.11 migration registry is a tool the agent uses without asking), pipeline failures (the §8.10 recovery procedure is a tool the agent uses without asking), or the TDD loop itself (per §9.4).

**The discipline of the gate is the cost of asking vs the cost of being wrong.** The agent's time is not free — every loop the agent spends on a question it could have answered itself is a loop not spent on real progress. The agent's mistake-cost is also real — an autonomously-made decision that the user disagrees with is rework. The agent calibrates by asking: "is this a question whose answer is in the locked design?" If yes, the agent does not ask. If no, but the answer is recoverable (the user can review and revert), the agent makes a working assumption and flags it. If no, and the answer is not recoverable (a data loss, a design lock-in, a user-facing feature change), the agent asks.

### 9.6 The Review File Protocol

`review.md` is the channel through which design decisions flow from the agent to the user. The cron prompt's Step 8 specifies the format, and the agent has been following it across the prior seven loops. This section specifies the operational protocol around the file — how the agent writes to it, how often, what format, what is and is not appropriate.

**When the agent appends to `review.md`:**

- The agent has made a working assumption in a section that the user may want to revisit (e.g., §3.6 "1 open slot at tier 5" is in the section as a working assumption and the corresponding decision in `review.md` says so explicitly).
- The agent has identified a tradeoff that the user should weigh in on (e.g., §6.5 schema validation tool choice is Python vs GDScript; the agent commits to Python in the section and flags the alternative in `review.md`).
- The agent has hit a question it cannot answer without user input (e.g., a specific Chrono Cross data point that the wiki disagrees with the script dump on; the agent cannot pick a side without user guidance).

**When the agent does not append to `review.md`:**

- The question is an implementation detail (which file to use, which variable name to use, which helper to extract). These are the agent's call.
- The question is a bug fix the test is already answering. The test passes or fails; the agent does not need a user decision.
- The question is a refactor of the agent's own work. The agent owns its own cleanup.
- The question is a question the user has already answered (the agent should check `review.md` for prior decisions before appending a new one — the same question should not be asked twice).

**The format.** The cron prompt specifies: `- [ ] DECISION: <one-line description> | Context: <why this matters> | Options: <A | B | C>`. The agent follows this format and includes 2-4 options with a recommendation. The recommendation is the agent's best guess; the user is not obligated to take it.

**The discipline of not bloating `review.md`.** A `review.md` with 50 open decisions is a `review.md` that the user will not read. The agent keeps the file to the 5-15 most important decisions at any time. If a prior decision is no longer relevant (e.g., the design space has shifted and the question is moot), the agent marks it resolved or removes it. The agent does not let the file accumulate cruft.

### 9.7 The Memory File Protocol

`loop_memory.md` is the channel through which the agent's institutional memory flows from one loop to the next. The cron prompt's Step 7 specifies the append, and the agent has been following it. This section specifies what the agent writes to the file, what is appropriate, and what is not.

**What the agent writes to `loop_memory.md`:**

- A short paragraph on what the loop did. The user can read the §N summary in the loop's delivery message, but the memory file is the agent's record for future loops.
- Anything the loop learned that future loops need. The "Important lessons for future loops" sections in the prior seven loop entries are the canonical examples. The agent captures discipline, gotchas, and patterns that took effort to discover.
- Any issues encountered (missing tools, file conflicts, ambiguities). The "I clobbered §1 with `write_file`" lesson in Loop 1 is the canonical example.
- Any open questions for the user. Note that open questions for the user also go in `review.md`; the memory file is the "the agent noticed this" record, the review file is the "the user needs to decide" record.

**What the agent does not write to `loop_memory.md`:**

- The full content of the section it just drafted. The section is in the document; the memory file is a pointer, not a copy.
- Speculative future plans that the user has not approved. The memory file records what happened, not what might happen.
- Repeated entries. If the same lesson appears in three loops, the memory file should note "this came up again" not duplicate the full lesson. The first loop's entry is the canonical one.
- Personal opinion or venting. The memory file is a project document; the tone is the same as the design document.

**The discipline of keeping the memory file scannable.** A maintainer reading `loop_memory.md` should be able to find any prior loop's key lessons in under a minute. The agent uses the "What I did this loop" / "Important lessons for future loops" / "Open questions for the user (not blocking)" structure consistently. The agent does not invent new structures per loop; consistency is the memory file's value.

### 9.8 The Iteration Cycle: From Cron Loop to Shipped Section

The §8 pipeline specifies the assembly line. The §9 agent workflow specifies who runs the assembly line and how. The two combine into the iteration cycle that turns "wake up" into "section shipped."

**Phase 1: Wake up (loop start).** The agent reads the working set (§9.1). It identifies the loop shape (§9.3 — draft, fix, or gate). It locates the next section to draft or the prior section to fix.

**Phase 2: Draft (or fix).** The agent writes the section content, following the locked design, the existing document voice, and the cross-references that make the section coherent with the rest of the document. The section is 2,000-5,000 words of substantive prose (more is acceptable for heavy sections like §3, §7, §10). Code snippets and command examples are included where they clarify. The "Decisions Needed" subsection is added at the end if any choices emerged.

**Phase 3: Write to disk.** The agent appends the new section to `remaster_engine_design_spec.md` using the `cat _sN_draft.md >> remaster_engine_design_spec.md` pattern from Loop 6. The agent verifies the file ends with `\n---\n\n` before concatenating, and verifies the section count and the last section header after concatenating.

**Phase 4: Generate the .docx.** The agent runs pandoc (full path if PATH is not refreshed: `"C:\Users\14239\AppData\Local\Pandoc\pandoc.exe"`). The agent verifies the .docx file exists and has non-zero size. The §8.4 data translation stage and the §7.11 save/migration layer both rely on the .docx for design review by the user, so the .docx is not optional.

**Phase 5: Update state and memory.** The agent patches `loop_state.json` (single-line anchor in the sections array, multi-line anchors in the top-level fields). The agent appends to `loop_memory.md` using the existing structure. The agent appends to `review.md` if any decisions emerged. The agent sends the summary message.

**Phase 6: Sleep until next cron tick.** The loop is done. The next loop will start from a fresh working set, but the files on disk persist, the `loop_state.json` records where the project is, and the `loop_memory.md` records what was learned.

**The total cycle time for a typical draft loop is 10-20 minutes.** A heavy section (3,000-5,000 words) takes longer; a short section (1,500-2,000 words) takes less. The cron frequency is hourly, so the project gets 1-3 sections per cron cycle depending on the section's weight. Over the seven completed loops, the project has shipped eight sections (~33,000 words) at a rate of slightly more than one section per loop. The remaining seven sections (§9-15) are projected to complete at a similar rate, with the project's total document reaching ~60,000 words by the time §15 is shipped.

### 9.9 The User's Role: Design Gates, Review, and Sign-off

The user is the project lead. The agent is the implementer. The user's role is to make the decisions the agent cannot make alone, to review the agent's work, and to sign off at phase boundaries. The autonomy model — "mostly autonomous with design gates" — is operationalized as follows.

**Daily user role (during design document work):** The user reads the loop summary messages. The user reviews the .docx (or the .md source) for sections that touch the user's interest. The user checks `review.md` for new decisions. The user replies with corrections, approvals, or new direction. Most loops do not require user action; the user reads the summary and moves on. The user's response time is hours, not minutes; the agent is patient.

**Periodic user role (at phase boundaries):** The user signs off on phase completion. The §2.5 definition of "done" is per-phase, and the user is the one who decides "yes, Phase 1 is done, start Phase 2." The §8.9 phase-specific pipeline behavior relies on this sign-off — the agent does not autonomously transition between phases.

**As-needed user role (for design decisions):** The user weighs in on the decisions in `review.md` when the user has a preference. The user may also weigh in on working assumptions the agent has flagged in the document body. The user does not need to respond to every flag; a non-response after 24 hours is a signal that the user accepts the working assumption as a reasonable default.

**What the user does not do:**

- The user does not write the document sections. The user provides direction, the agent writes.
- The user does not run the test suite. The agent runs the tests; the user reviews the results.
- The user does not manage git history. The agent commits; the user reviews the commit log.
- The user does not babysit the cron loop. The loop runs autonomously; the user interacts when the loop surfaces something that needs the user.

**The discipline of the user's role is its restraint.** The user is the most expensive resource on the project (in terms of opportunity cost, attention, and decision fatigue). The agent's job is to surface only the questions the user is uniquely positioned to answer. The user trusts the agent on implementation details, schema additions (when reversible), and the TDD loop; the user intervenes on design choices, locked-design conflicts, and phase transitions.

### 9.10 Anti-Patterns the Agent Avoids

The agent's working style is the inverse of several common failure modes. Naming these explicitly is the §1.5 "no magic" principle applied to the agent's own behavior. A maintainer who sees one of these patterns in a future loop's output should treat it as a bug.

**Asking when the answer is in the locked design.** The agent has the §3.16 locked-design summary and the `phase_3_redesign` object in `loop_state.json`. A question like "should we have 6 or 3 party members in combat" is answered by the locked design (6). The agent does not ask this; it implements 6. A future loop that asks the user a question the locked design already answers is wasting the user's time and should be retrained to read `loop_state.json` first.

**Bloating `review.md` with non-decisions.** The agent does not append "should this function be named `apply_status` or `apply_status_effect`" to `review.md`. That is an implementation detail. The agent does not append "should the .docx be regenerated at the end of every loop" — that is a §8 decision the agent has already made. The agent reserves `review.md` for decisions the user should weigh in on.

**Skipping the working-set read.** A loop that starts by drafting without reading `loop_state.json`, `loop_memory.md`, and `review.md` is a loop that will repeat prior mistakes. The agent always reads the working set first, even if the loop feels urgent.

**Modifying reference projects.** The user has explicitly named `D:\Game Design\TacticalRPG\` and `D:\Game Design\TACTICA\` as reference-only, not to be modified. The agent does not touch these directories. A loop that needs to verify a prior project's behavior reads it; it does not edit it.

**Reusing prior project code without permission.** The user has explicitly said the results from prior projects are "admittedly not great" and the new project is a fresh start. The agent borrows design philosophy (when directly applicable) but does not copy code. A GDScript file in the new project is written fresh, even if the prior project had a similar file. The agent should ask before importing.

**Inventing technical details.** The §1.5 "no magic" principle and the cron prompt's "do not invent technical details" rule apply. The agent does not claim a Godot 4 API exists that it has not verified. The agent does not claim a PS1 hardware spec that is not in the reference material. The agent flags uncertainty with "I have not personally verified this" or "this is based on documentation at <URL>." The §6.1 honesty pattern ("§6 is the *as-designed* architecture, not a verified production architecture") is the template for honest flags in §9 too.

**Silent conflict resolution.** When two sources disagree (a wiki page and a script dump, a YouTube video and a TIM file, two prior loops' claims), the agent does not silently pick one. The agent logs the conflict in the appropriate `CONFLICTS.md` per §8.3, surfaces it in the section that depends on the resolution, and asks the user if the conflict is material to the design.

**Treating the cron loop as a chat.** The loop is not a conversation. The agent does not produce narration ("Let me start by reading the working set..."). The agent produces tool calls and file changes. The summary message at the end is the user's window into what happened; the body of the loop is execution, not exposition.

### 9.11 Working With the User Mid-Loop

The cron prompt's most distinctive feature is the `[OUT-OF-BAND USER MESSAGE — a direct message from the user, delivered mid-turn]` block. The user can send a message to the agent mid-loop, and the agent must treat it as a direct instruction with the same authority as the original request. This is the cron prompt's "mid-turn user steering" feature, and it is the operational reality of working on a long-running project.

**What the agent does with an out-of-band message:**

- The agent stops the current loop's plan. If the message is "stop drafting §10, fix the schema error in §6.5 instead," the agent pivots to the fix loop.
- The agent treats the message with the same authority as a user message at the start of a session. A user message saying "I disagree with §3.6, change it to 2 open slots at tier 5" is a §3 edit, not a suggestion.
- The agent does not require the message to be polite, formal, or detailed. The user is busy; the message is short. The agent infers intent and asks for clarification only when the inference is ambiguous.

**What the agent does not do with an out-of-band message:**

- The agent does not ignore the message because it is mid-loop. The cron prompt is explicit that the message is genuine and has the same authority.
- The agent does not treat the message as a hint. The message is a direct instruction.
- The agent does not delay the current loop's work to "fully integrate" the message. The agent finishes the current minimal work (e.g., does not leave a half-appended file), then pivots.

**The discipline of mid-loop pivots is to not corrupt state.** If the user interrupts the agent mid-section-draft, the agent does not leave a half-written section in `remaster_engine_design_spec.md`. The agent either finishes the current section or reverts to the prior state. A half-written section is worse than no section; a maintainer reading the file would not know if the half-section is a draft, a fix, or a mistake.

### 9.12 The Long-Running Project Discipline

The cron prompt's `loop_protocol.duration` is "indefinite_until_user_stops." This project is not a one-shot; it is a long-running collaboration. The discipline of long-running projects is different from the discipline of one-shot tasks.

**The project's life is the loop's life.** Each loop is one of hundreds that will run over the project's duration. The agent optimizes for the 100th loop, not the 1st. A loop that makes a small forward progress and updates the memory file is more valuable than a loop that makes a large forward progress and leaves no record. A future loop is the project's most important stakeholder.

**The project's memory is the loop's responsibility.** The agent's commitment to writing `loop_memory.md` is the difference between a project that gets smarter over time and a project that forgets every lesson. The agent does not skip the memory write because the loop was "easy" or "obvious." Every loop writes.

**The project's state is the loop's checkpoint.** `loop_state.json` is the project's save file. A loop that updates the state file is a loop the next iteration can pick up cleanly. A loop that does not update the state file is a loop the next iteration has to debug. The state update is not optional.

**The project's user is the loop's north star.** The user is the reason the project exists. The agent optimizes for the user's needs, not the agent's convenience. A loop that produces a long, technically impressive section the user does not need is a worse loop than a short, focused section the user does need. The §1.7 autonomy model is the contract: the agent is autonomous on the path to the user's goals, not on the choice of goals.

**The project's pace is the user's pace.** The cron runs hourly. The user reads messages daily. The agent does not try to compress the project into one mega-loop; it produces one section per loop (or less), and trusts the cumulative progress. A long-running project succeeds by showing up, not by sprinting.

### 9.13 Decisions Needed

These are choices the section commits to but the user may want to revisit:

- **The agent's working set order.** §9.1 commits to reading `loop_state.json`, `loop_memory.md`, `review.md`, `remaster_engine_design_spec.md`, and the locked design in that order. The user may want a different order (e.g., reading the design document first to understand context before reading state). The trade-off is "start with the project's today" vs "start with the project's content." Recommendation: the order in §9.1 — state first, content second, because state points to the content that matters.

- **The fix-loop log location.** §9.3 says fix loops update `loop_memory.md`. The user may want a separate `FIXES.md` file in the project root for corrections specifically, separate from the general memory file. The trade-off is searchability (one file) vs separation of concerns (fixes are different from memory). Recommendation: keep fixes in `loop_memory.md` for now — the volume is low, and a separate file adds a maintenance burden.

- **The TDD loop's commit granularity.** §9.4 commits after each TDD cycle. The user may want a coarser granularity (commit every 5 cycles) or finer (commit every test that passes, even if not part of a cycle). The trade-off is commit log density vs recovery granularity. Recommendation: one commit per TDD cycle (one test passing + the fix that made it pass) — dense enough to bisect, sparse enough to be readable.

- **The user's daily review touchpoint.** §9.9 commits to "user reads the loop summary messages" as the daily touchpoint. The user may want a different surface (e.g., a daily digest email, a GitHub PR per loop, a Slack/Discord summary). The trade-off is the user's preferred medium. Recommendation: keep the loop summary as the touchpoint — the cron job's delivery channel is the user's chat, and adding another channel adds a maintenance burden.

- **The out-of-band message handling for in-progress file writes.** §9.11 commits to "finish the current section or revert to the prior state" when the user interrupts mid-loop. The user may want a third option ("leave a `IN_PROGRESS` marker in the file so the user can pick up"). The trade-off is cleanliness (no half-written files) vs continuity (the user can resume the agent's work). Recommendation: finish-or-revert — a half-written file is too easy to mistake for a finished one.

- **The memory file's retention policy.** §9.7 does not specify how long `loop_memory.md` should grow. The file is currently ~33KB across seven loops. At this rate, it will be ~75KB by §15 and ~600KB by the time the project is fully implemented (assuming ~50 more implementation loops). The user may want a rotation policy (e.g., archive after 30 loops, or move implementation-phase memory to a separate file). Recommendation: keep appending for now; the file is well-structured for search, and rotation adds a maintenance burden. Revisit when the file exceeds 100KB.

These are not blocking the document's continuation. §10 (PS1/GBA Era-Specific Challenges) is unblocked and can be drafted next. §10 will specify the unique technical challenges of remastering a 1999 PS1 game and the 2000-era GBA-style constraints the redesign adopts, building on the §1.4 "why remastering compounds the problem" framing and the §6.7 / §7.10 combat engine architecture.
## 10. PS1/GBA Era-Specific Challenges

This section is the technical bridge between the abstract architecture in §6-§7 and the reality of remastering a 1999 PlayStation game. The previous sections treat the engine as a generic 2D game engine. They are not. Godot 4 is, but Chrono Cross was not built in it, and the *target* content we are feeding the engine comes from a specific hardware generation with its own peculiar limits, asset formats, and design habits. A remaster that ignores those specifics will produce a faithful-looking game that feels wrong — wrong frame timing, wrong color palette, wrong music compression, wrong save behavior, wrong party-formation patterns, wrong boss-encounter pacing. The goal of this section is to enumerate the era-specific challenges, specify how the engine and pipeline handle them, and identify the places where the agent's design judgment will need the most discipline.

The "GBA" in the section title is a deliberate framing choice. We are not porting *from* a Game Boy Advance version of Chrono Cross — there is no canonical GBA version. The phrase signals that the era being targeted is the late-90s/early-2000s design aesthetic of 2D-presentation JRPGs with 16-bit/32-bit-era production values: small sprite counts, fixed camera angles, single-CD audio, small party sizes, pre-rendered backgrounds, and a "do more with less" design philosophy. The redesign (§3) preserves many of those aesthetic choices — 2D character sprites, fixed camera, single-CD-style OST — while replacing the *technical* limits that the aesthetic used to be a response to (3-character party limit, low-res textures, 2-channel audio, no analog input). The discipline is: preserve the aesthetic, replace the limits, document every replacement so a future maintainer can tell which is which.

### 10.1 The PS1 Hardware Reality

To understand why Chrono Cross is the way it is, we have to understand the hardware it was designed for. The PlayStation (1994) is, by 2026 standards, a deeply constrained machine. The relevant specs:

**CPU.** The PS1 has a MIPS R3000A clocked at 33.87 MHz. No floating-point unit — all math is integer or fixed-point. No out-of-order execution. Single-issue. A modern phone SoC has 100-1000x the single-threaded performance. The PS1 CPU is roughly 30 MIPS of effective throughput, comparable to a 1990s desktop x86.

**GPU.** The PS1 GPU is a fixed-function rasterizer with no shaders, no programmable pipeline, no vertex transform-and-light. It can do affine texture mapping (which produces the famous "wobbly" PS1 textures) and a small set of blend modes. It can handle ~360,000 textured polygons per second with no lighting and ~180,000 with flat shading. The PS1 has no z-buffer in hardware — the GPU renders back-to-front, and the CPU has to sort polygons to get correct occlusion.

**RAM.** 2 MB main RAM, 1 MB VRAM, 512 KB sound RAM. The total is 3.5 MB of addressable memory. A 2026 web page is bigger than that.

**Storage.** CD-ROM at 2x speed (300 KB/s). Loading times are the binding constraint on level design, not graphics. The original Chrono Cross uses "field," "battle," and "world" maps with screen-fade transitions that hide the load; the new design uses similar transitions because the aesthetic expectation is part of the game's identity, not because the new engine needs them.

**SPU.** The SPU has 24 ADPCM channels at 44.1 kHz. SEQ/VAB music is sequenced MIDI-style with sampled instruments. Sound effects are short ADPCM samples. The compression is lossy but the sound quality is reasonable for the era.

**Input.** One controller with 14 buttons (D-pad, face buttons, shoulders, start/select). No analog stick on the original DualShock — the DualShock (1997) added two analog sticks and vibration. Chrono Cross shipped in 1999 and supports DualShock but is also playable on the original digital pad. Many of the game's puzzles and movement patterns were designed around 8-directional digital input, not analog.

**No network.** PS1 has no network stack. The entire Chrono Cross experience is single-player with no online features.

**No persistent clock.** The PS1 has a real-time clock on the memory card, not the console. Save states and clock-based events (e.g., daily unlocks) require the memory card's RTC. This is a non-issue for a single-player JRPG with no daily-content design, but it's why so many PS1-era JRPGs have "chapter-based progression" instead of daily resets.

**No 3D audio.** The SPU supports stereo panning and basic reverb, but no HRTF, no positional audio, no occlusion. The Chrono Cross OST is mixed for stereo headphones and speakers.

**No modern color depth.** The PS1 GPU uses 16-bit color (5-5-5 RGB). No HDR, no wide gamut, no 10-bit output. The original's color palette is *fundamentally* a 16-bit palette; the remaster's HD-2D style uses 32-bit color, and the difference is visible.

The relevance of these specs is not that the remaster must run on PS1 hardware. The relevance is that the *original game's content* was designed for these limits, and the *original game's assets* were authored at the resolutions and palette depths those limits imply. A 320x240 character sprite scaled to 1920x1080 looks blurry. A 16-bit color palette converted to 32-bit looks "off" if the conversion is automatic (some colors are duplicated, some are not representable). SEQ-compressed music converted losslessly to OGG sounds "too clean" and exposes artifacts the original masked. These are not "rendering problems" — they are *content* problems, and the pipeline (§8) is where they are addressed.

### 10.2 Chrono Cross's Specific Use of PS1 Limits

Chrono Cross (1999) was a *deliberate* showcase of the PS1's late-life capabilities. The game is famous for its painterly pre-rendered backgrounds — full-screen oil-painting-style art with parallax layers, drawn by artist Yasuyuki Honne and rendered at 640x480 (the PS1's high-res mode). The character sprites are 2D, hand-drawn, and overlaid on the 3D pre-rendered backgrounds. The 3D character model in the original is a low-poly 3D mesh that takes a beating from critics — it's the "T-pose" silhouette some fans remember — but it exists because the PS1 could not rotate a 2D sprite in 3D space convincingly, and the designers wanted some 3D-rotation scenes (e.g., the Tower of Geddon, the Sea of Eden).

**Pre-rendered backgrounds.** The 3D-looking backgrounds in Chrono Cross are not 3D. They are pre-rendered 3D scenes — a high-poly mesh was built in Maya or similar, lit, painted over, and the final image is a single texture that the PS1 displays as a flat background. The camera in the original is fixed; the background texture has parallax layers (3-5 layers per scene) that scroll at different rates to simulate depth. This is the *exact* same technique HD-2D uses in 2026 — pre-rendered or pre-painted backgrounds with parallax, 2D characters on top, optional screen-space effects for "atmosphere."

**The 3-character party limit.** A direct consequence of the PS1's RAM. Each character is a low-poly 3D mesh with ~400-600 triangles, a 256x256 texture, and an animation set. Six characters = 2400-3600 triangles, 1.5 MB of textures, plus animation state. The PS1's 1 MB VRAM could hold ~3 character textures comfortably. The original's 3-character party is the maximum the hardware could support with all the animation states pre-loaded; the game's combat was designed around the choice tension of "which 3 of your 6-8 recruited characters do you bring?"

**The dual-mode battle transition.** The original switches from a pre-rendered 2D field to a pre-rendered 2D battle screen via a swirl/dissolve transition. The battle screen is *also* pre-rendered — no real-time 3D, no real-time lighting. The animations (attack effects, magic circles) are 2D sprites on top. This is the architecture the redesign is preserving: 2D characters on 2D backgrounds, with §7.10's combat engine replacing the original's per-frame sprite composition.

**The 2-disc swap.** Chrono Cross shipped on 2 CDs in the US release (1 disc in the JP release). Disc 2 contains the latter half of the game. The disc swap is a hardware constraint; the remaster replaces it with a single asset bundle.

**The save system.** PS1 memory cards hold 15 blocks per card, each block is 8 KB. Chrono Cross uses 1 block per save, with multiple save slots. The save contains: party composition (3 characters out of ~40), each character's level and stats, the story-progress flags, the inventory, the current map, and the position within the map. The remaster's save system (§7.11) replaces this with a modern `Resource`-based save.

**Audio.** The OST was composed by Yasunori Mitsuda and is one of the most acclaimed JRPG soundtracks. The PS1 version uses ADPCM-compressed samples; the music is sequenced and the samples are loaded into the 512 KB sound RAM as needed. The remaster's audio pipeline (§7.13 mod API covers the asset paths; the audio specifics are in §8.3) extracts the SEQ data and re-renders it in OGG format. The choice of OGG vs. MP3 vs. FLAC vs. the original ADPCM is a design decision (logged in `review.md` from §8).

### 10.3 What "HD-2D Modernization" Actually Means Here

The locked design (§3.2) commits to HD-2D: 2D character sprites over 2D/2.5D backgrounds. The original uses 2D sprites over pre-rendered 3D backgrounds. The "HD" in HD-2D is doing real work — it signals a *resolution* upgrade and a *parallax* upgrade, not a *style* change. Specifically:

**Resolution.** The original's character sprites are ~128x192 pixels. The HD-2D remake uses ~256x384 or larger. The "Octopath Traveler" reference (the game that coined the HD-2D term) uses 320x480 or similar at 1080p. The §7.9 HD-2D rendering stack uses a `CanvasLayer` with a `Camera2D` that allows the player to zoom in/out; the character sprites are pre-rendered PNG sequences, not live-rendered 2D meshes.

**Color depth.** The original's 16-bit (5-5-5) color palette is replaced with 32-bit (8-8-8-8). The color shifts are *visible* and *deliberate* — the HD-2D versions of FF6 and Dragon Quest III are noticeably more saturated, with deeper blacks and brighter highlights. The §7.9 lighting system adds warm/cool light sources that the original could not produce.

**Parallax depth.** The original uses 3-5 parallax layers per scene. HD-2D uses 3-7, with the additional layers including animated particles (dust motes, fireflies, falling leaves) that the PS1 SPU could not handle alongside the music and SFX. The §7.9 particle system is Godot 4's `GPUParticles2D`, which is performant enough for 100+ particles per scene at 60 fps.

**Atmospheric effects.** The original uses a single dithering pattern to simulate transparency (the famous PS1 "translucent water" effect). HD-2D uses real alpha blending. Fog, mist, heat shimmer — all real-time in the remake, pre-baked in the original. The §7.9 screen-space shader stack handles these.

**Field-of-view changes.** The original's camera is fixed. The remake's camera can pan, zoom, and tilt within a single scene — useful for "look up at the tower" moments that the original faked by switching to a different pre-rendered background. The §7.9 camera system is a `Camera2D` with constraints.

**Animated tile effects.** The original's water and lava tiles are static. The remake animates them at 8-12 fps with shader-based flow. The §7.9 shader pipeline uses `ShaderMaterial` for these.

**Lighting transitions.** The original uses pre-rendered "morning" and "evening" versions of each scene that swap on a timer. The remake uses a single scene with a real-time `Light2D` that interpolates color temperature across the day. The §7.9 lighting system implements this.

**Aesthetic preservation.** The remake keeps the original's painterly style, the same color palette's *mood* (cool blues for the beaches, warm oranges for the deserts, dark greens for the forests), the same field-to-battle transition, the same swirl/dissolve effect, the same save-anywhere-on-the-field behavior. The aesthetic is the *point*; the technical limits are not.

The discipline is: every visual change is logged with a "this is an upgrade" or "this is an aesthetic preservation" rationale in `assets/CHANGELOG.md` (auto-generated by the §8 pipeline). A future maintainer who sees a different color palette in a scene can ask "is this an intentional HD-2D upgrade or a bug?" and the changelog answers.

### 10.4 Asset Format Archaeology

The original Chrono Cross assets are stored in PS1-era formats that are not natively readable by any modern tool. The §8.3 asset extraction stage handles the conversion; this section specifies what the formats are and what the conversion challenges are.

**TIM (texture).** Sony's standard PS1 image format. 4-bit, 8-bit, 16-bit, or 24-bit color (the PS1's 5-5-5 mode is stored as 16-bit TIM). CLUT (color lookup table) variants are common for 4-bit and 8-bit images. The TIM header is 12-20 bytes; the palette follows; the pixel data follows. The extraction pipeline (§8.3) reads TIM files with `Pillow` after writing a small parser for the header; CLUT-mode images require the palette to be applied during decode. Challenge: the original game uses CLUT-mode TIMs for ~80% of its textures to fit 4-bit data into 32 KB per texture; the conversion to 32-bit PNG requires the agent to manage the palette.

**SEQ + VAB (audio).** Sony's standard PS1 audio format. SEQ is a MIDI-like sequence of notes; VAB is a bank of ADPCM-compressed samples. The two are paired: SEQ says "play note 47 on channel 3," VAB says "note 47 is sample X with envelope Y." The extraction pipeline (§8.3) reads SEQ and VAB with a parser, then either plays them back through `timidity++` (which renders SEQ+VAB to WAV) or extracts the ADPCM samples and sequences them in OGG format directly. Challenge: the SEQ format has opcodes that `timidity++` does not support (e.g., the original Chrono Cross uses some custom SEQ opcodes for time-signature changes), and the conversion requires fallback to manual sample extraction + re-sequencing in OGG.

**MDL (model).** Sony's standard PS1 3D model format. Low-poly, no skeleton, no animation channels — animation is per-vertex interpolation between keyframes. Chrono Cross's character models are ~400-600 triangles each, with ~5-8 keyframe poses. The extraction pipeline (§8.3) reads MDL with a parser and *discards* the 3D mesh — the redesign uses 2D sprites, not 3D models. The MDL extraction exists for verification ("does our 2D sprite match the original 3D model's silhouette?") and for the form-change cutscenes (the form-change sequence uses a 3D model interpolation in the original; the remake can use either a 2D sprite interpolation or a 3D model that we *do* import).

**MAP (map data).** Custom format. Each map is a 2D grid of tile references, an event layer (NPCs, warps, treasures), a palette index, and a music reference. Variable-length records, no documented specification. The extraction pipeline (§8.3) has the most fragile parser here — see §8.3's "TIM format not recognized" gotcha for the general approach. The Chrono Cross map format has at least three variants (overworld, dungeon, town) and the parser must handle all three. Challenge: tile IDs are 16-bit but the same tile ID means different tiles in different maps; the parser must load a per-map tile dictionary.

**EVT (event).** Custom format. Each event is a sequence of "show dialog X," "move character Y to position Z," "play sound W." Chrono Cross's event scripts are large (~30,000 lines of decoded text). The extraction pipeline (§8.3) reads EVT with a parser and writes the events to a structured JSON format that the §7.12 cinematic system can consume. Challenge: the EVT format has nested calls, conditional branches, and inline arithmetic — the parser must reconstruct the structure from the linear byte stream.

**CHR (character stats).** Custom format. Each character has level, base stats, growth rates, element, tech list. Chrono Cross has ~40 playable characters. The extraction pipeline (§8.3) reads CHR and writes to `data/characters/*.json` (the §6.5 schema). Challenge: stats are stored as 8-bit integers in the original, but the original UI shows them as decimal numbers with implied fractional components (the "growth" system). The conversion requires re-scaling.

**ENM (enemy data).** Custom format. Each enemy has HP, attack, defense, magic, element, AI script, drop table. ~250 enemies. Challenge: enemy AI scripts use the same EVT-like format with conditionals and randomness; the AI extraction is the most error-prone.

**SAV (save format).** Custom format. Fixed-size, 8 KB. Contains party, stats, story flags, inventory, current map, current position. Challenge: story flags are bit-packed and the bit positions are not documented; reverse-engineering them requires comparing two saves at different story beats. The agent can do this iteratively.

**ITM (item).** Custom format. Each item has name, description, type, effect, price. ~200 items. Challenge: items have effect scripts (e.g., "Heal 100 HP + cure status") that are not the same as techs; the parser must distinguish.

The general approach for all of these: a small Python parser per format, ~200-400 lines each, with explicit logging of every parse failure. The parsers are not "complete" — they handle the cases the original game uses, and they fail loudly on edge cases. The agent's job is to extend the parsers when a new content area surfaces a new edge case. The §8.3 "Asset Extraction" stage's logging convention (every file gets a content hash, every parse gets logged, every conflict gets a CONFLICTS.md entry) is the discipline that makes this tractable.

### 10.5 The "Lost Original Intent" Problem in Practice

§1.4 named "lost original intent" as one of the four ways remastering compounds the agent's problem. This section gives concrete examples of what that means in Chrono Cross.

**The 3-character party.** Was the 3-character party a *design choice* or a *hardware constraint*? The answer is "both, with a feedback loop." Masato Kato has said in interviews that the 3-character limit was a constraint he worked with, not a constraint he designed around. The 6-character party in the redesign (§3.4) is not a "violation of the original intent" — it is the *removal* of a constraint the designer would have removed if he could. But the *consequences* of 3-character combat (the choice tension, the build variety, the "which three of my eight?" meta-game) are *also* part of the original's design. The redesign's 6-character party + 36 supports + open grid slots (§3.5) is a *different* design that preserves the *choice tension* (which 6 of 42? which supports per base? which open grid slot tech?) while removing the 3-character limit. The original's *why* (choice tension from limited slots) is preserved; the original's *what* (3 character slots) is not.

**The element system.** Chrono Cross has a 6-element system (White, Red, Black, Blue, Green, Yellow) that determines both magic and combat effectiveness. The original's White/Black/Red/Blue/Green/Yellow is a deliberately *esoteric* take on the Fire/Ice/Lightning/Wind/Holy/Dark trope — elements are tied to characters' personalities, not to a Western-fantasy alignment chart. The redesign preserves this — the §3.3 character-to-element assignment (Serge/White, Kidd/Red, Nikki/Blue, Glenn/Green, Herle/Black, Norris/Yellow) is *exactly* the original's assignment, not a re-imagining. The discipline: do not "balance" the elements by re-assigning them. The element grid is what it is.

**The magic tier system.** The original has 8 magic tiers per character (1-8), with the basic attack line at the bottom and the ultimate at the top. The redesign's 8-tier system (§3.8) is the same 1-8 progression. The original's tier-1 to tier-8 spread is a *design choice* — Kato has said in interviews that the "low power at tier 1, gradually unlock" pacing was intended to make the player feel growth. The redesign preserves this. But the original's *missing tiers* (some characters skip tier 6, some skip tier 8) is a *data accident* from the original's incomplete tech list. The redesign fills in the missing tiers to make the basic attack line feel consistent across the 6 bases. The original's *why* (gradual growth) is preserved; the original's *what* (incomplete tech lists) is corrected.

**The recruit-by-elements.** The original lets you recruit most characters by *using their element in battle* — use White-element techs, and Serge/Lynx-aligned characters become available. This is a *design choice* — Kato wanted recruitment to be a side effect of play style, not a menu choice. The redesign's 6-base + 36-support system (§3.3) is *recruitment-by-story*, not recruitment-by-element. The story drives who joins the party; the elements drive which supports are *available* to that base once they join. This is a *deliberate* departure from the original, not an accident, and it is documented as such. The original's *why* (recruitment-as-gameplay-decision) is not preserved; the redesign replaces it with a different *why* (recruitment-as-story-reward). Both are valid choices; the discipline is documenting which is which.

**The "no game over" mechanic.** The original has a flag that triggers near the end of the game — the player cannot lose a battle after a certain story beat. This is a *design choice* — Kato wanted the ending to be unwinnable-to-lose. The redesign keeps this for the final chapter. The original's *why* (narrative weight) is preserved; the original's *what* (the specific flag) is preserved literally.

The general pattern: every design decision in the original has a *what* (the specific implementation) and a *why* (the designer's intent). The Phase 2 audit (§1.4) evaluates every "what" on its own merits, asking "is this worth preserving?" The redesign preserves the *whys* it agrees with and replaces the *whats* it does not. The §1.4 "vestigial design choice" concept is operationalized as: a "what" without a defensible "why" is a candidate for change. A "what" with a defensible "why" is preserved.

### 10.6 The PS1 Emulation Research Problem

The §8.2 source acquisition stage uses emulation to extract assets. The emulation research problem is: which PS1 emulator, in what configuration, produces the most faithful dumps?

**DuckStation.** The current best-in-class PS1 emulator (2020+). Open-source (GPLv3), maintained by StackOverflow user "stenzek." Excellent accuracy, fast, supports debug logging, supports memory-card reading, has a CLI mode. The pipeline's default emulator for asset extraction.

**PCSX-Reborn.** A maintained fork of the original PCSX (closed-source 2001 release made open in 2003). Less accurate than DuckStation in some edge cases (PS1 GPU quirks), but more mature on Linux. Used as a fallback.

**NoCash's PSX-SPX.** A "research" PS1 emulator by Paul "NoCash" Hartzog. Less user-friendly, but the documentation of PS1 internals is excellent. The pipeline references NoCash's docs for format specifications even when using DuckStation for extraction.

**mednafen.** Multi-system emulator with PS1 support. Mature, but PS1 is not its primary focus. The pipeline does not use mednafen for asset extraction but uses it as a reference for what "correct" behavior looks like.

The discipline is: do not invent format specifications. Every byte-format parser in §8.3 cites the source — DuckStation's source code, NoCash's docs, or the official Sony PS1 SDK documentation (which is partially leaked). The agent does not guess. The agent does not "reverse-engineer from scratch" when a reference implementation exists. The §1.5 "no magic" principle at the format level: every format decision is sourced.

### 10.7 Legal Posture Specifics

§1.6 named the project as "fan work / clean-room." This section is more specific about what that means for PS1-era content.

**The original game is copyrighted.** Chrono Cross is © 1999 Square (now Square Enix). The original game assets, music, scripts, and character designs are copyrighted. The user owns the original game as reference (per §1.6). The agent's pipeline produces code and data; the pipeline does *not* redistribute the original assets.

**The "personal use" gate.** The §8.2 emulation extraction stage has a `SOURCES_LICENSE_OK=1` gate. The user sets this only after confirming they own the original game. The pipeline refuses to run without the gate. The raw extracted assets are stored in `assets/*_raw/` with a `.license: personal_use_only` marker in their frontmatter; the pipeline generates `assets/*_reproduction/` directories with either user-redrawn or fan-art-substitute content for any public distribution.

**The clean-room code principle.** All code is original, written from scratch. No decompiled Chrono Cross code. No "translated" PS1 assembly. The format parsers in §8.3 are written from the published format specifications, not from the original game's binary. The agent does not read disassembly; the agent reads documentation and writes parsers that conform to it.

**The "interpretation" is original.** The redesign's design choices (§3) are original work, not copies. The 6-base party, the 36 supports, the open grid slots, the 8-tier magic, the 6-character party in combat — all original design grounded in *understanding* the original (multi-source research per §1.6) but not derived from it. The line is: you can study the original and make your own design that takes inspiration; you cannot copy the original's data files and claim them as your own.

**The "fan-art" allowance.** The §8.2 fan-art acquisition is a separate category. Fan artists who have drawn Chrono Cross characters and posted them online have their own copyright on their work. The pipeline can use fan art *with attribution* for development and testing, but the public release either uses official-art-licensed content (which Square Enix has not granted) or redrawn content. The default for the public release is redrawn or original.

**The "no official re-release" assumption.** As of 2026, Square Enix has not released an HD remaster of Chrono Cross. The original is available on the PlayStation Store for PS1 classics (via PS Now / PlayStation Plus Premium), and a 2022 fan project "Chrono Cross: The Radical Dreamers Edition" is a community port, not an official release. The project's "fan work / clean-room" posture is appropriate for the current legal landscape. If Square Enix ever releases an official remaster, the project's purpose changes — but as of 2026, the gap this project fills is "Chrono Cross on a modern engine with a substantial redesign." That gap is real.

### 10.8 Multi-Source Content Verification

§1.4 named "multi-source" as the content-accuracy method. This section specifies the practical discipline.

**Source hierarchy.** When sources disagree, the pipeline uses a priority order:
1. The original game binary (via the §8.2 emulation extraction) — the source of truth for facts about the original game.
2. The official script dump (translated or original Japanese) — the source of truth for dialog.
3. The official art (screenshots, promotional material) — the source of truth for character/environment art direction.
4. Fan wikis (Chrono Cross Wiki, Chrono Compendium) — the source of truth for player-discovered game mechanics, often more accurate than the manual for obscure systems.
5. YouTube playthroughs — the source of truth for "what does this look like in motion," but not for facts (a YouTuber's commentary can be wrong).
6. Related work (Chrono Trigger, Radical Dreamers) — the source of truth for design lineage, but not for Chrono Cross-specific facts.

**Disagreement is logged, not resolved silently.** The §8.3 `CONFLICTS.md` file logs every disagreement. A disagreement might be: "Wiki says Serge's level-1 HP is 30, script dump says 40, emulation dump says 35." The pipeline writes all three to `assets/stats_raw/variants/serge_lv1_hp.json` with the source URLs/hashes, and the translation stage (Stage 3) picks one based on the priority hierarchy. The choice is logged in `data/CONFLICTS_RESOLUTIONS.md` with a one-line rationale.

**The agent does not pick "I think it should be X."** The agent picks the highest-priority source's value and logs the choice. If the user disagrees, the user can change the resolution by editing `CONFLICTS_RESOLUTIONS.md`. The agent does not have aesthetic authority over the original game's data.

**The agent picks "I think this design should be Y" for *new* design.** The redesign's stats, tech effects, and balance numbers (§3) are the agent's choice (subject to user review via the design gates in §9.5). The original's stats are not. The line is: original = sourced, new = authored.

### 10.9 The "GBA-Style Constraints" the Redesign Adopts

The section title says "PS1/GBA Era-Specific Challenges." The "GBA" half refers to the 2000-era design philosophy the redesign adopts as an *aesthetic constraint*, not a technical limit. Specifically:

**Keep the asset count lean.** A late-90s JRPG had 200-400 unique sprites, 50-100 maps, 30-50 minutes of music, 30-50 enemies, 40 playable characters. The redesign's targets: ~6 base characters (each with 8 tech animations), 36 supports (each with 1-2 tech animations), ~250-300 enemies (re-using many of the original's), ~80-100 maps, ~40-60 minutes of music. The total asset count is in the same range as the original, even with the redesign's larger roster. The discipline: do not balloon the asset budget. The original's 2-CD limit was 800 MB; the redesign's budget is larger (we are not on CD) but the *aesthetic* of "lean and curated" is preserved.

**Keep the camera mostly fixed.** HD-2D allows for a moving camera, but the redesign uses a fixed camera for most scenes (with a few dramatic zooms for boss reveals and form changes). The original's pre-rendered-style was always camera-fixed; the redesign's HD-2D allows camera movement but does not require it. The discipline: when in doubt, keep the camera fixed.

**Keep the dialog lean.** The original's dialog is famously *weird* — Kato writes in a deliberately non-natural style, with characters speaking in aphorisms, with internal monologues, with ellipses. The redesign preserves this *style* (the agents in §12 will be tuned to write Kato-style dialog) but does not bloat the dialog count. Each scene has ~5-15 lines of dialog, not 30-50. The discipline: lean dialog, weird style.

**Keep the UI clean.** The original's UI is famously minimal — text boxes, character portraits, simple HP/MP bars. The redesign's UI uses the same minimalism: no full-screen menus, no animated transitions, no particle effects on every click. The §7 UI system is text-and-sprite-based, not animated-overlay-based.

**Keep the save-anywhere pattern.** The original lets you save on the field at any time. The redesign keeps this. No save points, no chapter-based save boundaries. The discipline: respect the player's time.

**Keep the "no game over" late-game.** The original's "you cannot lose after this flag" mechanic is preserved. The discipline: the player who reaches the end of the story should not be blocked by a grinding session.

These are *aesthetic* constraints, not technical. The new engine can handle more — but the design chooses not to. The §3.16 locked-design summary captures this: "HD-2D visual style, 2D characters over 2D/2.5D backgrounds, fixed camera mostly, lean UI, Kato-style dialog, save-anywhere, no late-game game over."

### 10.10 The "What the Agent Cannot Verify" Wall

The §1.2 "what an agent is and isn't" list named the agent's weaknesses. This section makes them specific to the PS1 remaster context.

**Sprite animation timing.** The original's character animations have specific timing — the "Dash and Slash" attack has 12 frames, the swing is on frame 4, the hit-stop is 2 frames, the recovery is 6 frames. The agent can count frames from extracted sprite sheets, but the agent cannot *feel* the timing. A 12-frame animation at 30 fps is 0.4 seconds; the agent knows this but cannot judge whether 0.4 seconds is "right" for a slash. The §8.6 visual-regression tests compare the agent's sprite timing to the original's; if the timings match within ±1 frame, the agent is on solid ground. If they differ by more, the agent flags it and asks the user.

**Audio mixing and mastering.** The original's OST is mixed and mastered for the PS1 SPU. The OGG re-render will have different frequency response, different stereo image, different compression artifacts. The agent can extract the OGG and play it; the agent cannot judge whether the OGG "sounds right" compared to the SEQ. The §8.6 audio-regression test compares the OGG's spectrum to the SEQ's spectrum; if they differ by more than a threshold, the agent flags it.

**Color palette mood.** The original's 16-bit color palette is *mood-evocative* — the cool blues of the beaches, the warm oranges of the deserts, the dark greens of the forests. The 32-bit conversion will look "brighter" and "more saturated." Whether the mood is preserved is a judgment call. The agent extracts the 16-bit palette, applies it as a `ColorPalette` resource in the §6.5 data layer, and uses the palette for the HD-2D rendering. If the user finds the result "too bright" or "too saturated," the agent adjusts the palette's intensity at the user's request.

**Boss encounter pacing.** The original's boss encounters are tuned for the PS1's 30 fps and 3-character party. The redesign's 60 fps and 6-character party will feel different — faster, more chaotic, harder to read. The agent cannot play the game and judge "this is too hard" or "this is too easy." The §8.6 integration tests run the boss encounters with the agent's CombatRNG; if a test fails (the player dies before dealing 50% of the boss's HP, or the player wins without taking damage), the agent reports the failure to the user.

**Dialog delivery.** The original's dialog is *delivered* with specific timing — a line of dialog appears, the player presses a button, the next line appears. The exact timing of "appear" and "disappear" is a game-feel choice the agent cannot judge. The §7.12 cinematic system uses the original's timings as defaults; the user can adjust.

The general pattern: the agent extracts, the agent compares to the original, the agent flags discrepancies. The agent does not *judge* the discrepancy; the user does. The §9.5 "design gates" is the protocol: when the agent's automated comparison surfaces something, the agent escalates to the user.

### 10.11 Decisions Needed

These are choices the section commits to but the user may want to revisit:

- **The emulation tool default.** §10.6 commits to DuckStation as the default PS1 emulator for asset extraction. The user may have a preference (PCSX-Reborn, NoCash's PSX-SPX, or a commercial emulator like ePSXe for a specific edge case). The trade-off is DuckStation's modern accuracy vs. the user's familiarity with another tool. Recommendation: DuckStation, with the option to swap in another tool by changing a single env var (`REMASTER_PS1_EMULATOR=duckstation`).

- **The 16-bit-to-32-bit color conversion strategy.** §10.3 commits to direct 32-bit expansion (each 5-bit channel becomes 8-bit by left-shifting and zero-padding). The alternative is a perceptual color-space conversion (Lab or OKLab) that tries to preserve the *mood* of the palette. The trade-off is direct conversion is mechanical and reproducible, perceptual conversion is mood-preserving but lossy. Recommendation: direct conversion for sprites and UI (mechanical accuracy matters), perceptual conversion for backgrounds (mood matters).

- **The SEQ-to-OGG conversion tool.** §10.4 commits to `timidity++` as the default. The alternative is to extract the ADPCM samples from the VAB and re-sequence them in a more flexible tool (e.g., a custom OGG renderer). The trade-off is `timidity++` is a one-line tool with good defaults, custom rendering is more faithful but more code. Recommendation: `timidity++` for development speed, custom renderer only if a specific track fails the §8.6 audio-regression test.

- **The form-change cutscene's 3D vs. 2D approach.** §10.4 mentions that the form-change sequence uses 3D model interpolation in the original. The redesign can use either a 3D model (import the MDL, render in Godot's 3D engine) or a 2D sprite interpolation (pre-render the 8 keyframe poses as a sprite sheet, interpolate via shader). The trade-off is 3D is faithful but adds a 3D rendering path to an otherwise 2D project, 2D is consistent but less faithful. Recommendation: 2D interpolation for Phase 1 (consistent with the HD-2D commitment), 3D model for the Phase 3 form-change dramatic sequence if the user wants a more dramatic moment.

- **The "no game over" flag's exact timing.** §10.5 and §10.9 commit to preserving the original's "no game over" late-game flag. The exact trigger point (which story beat, which cutscene) is a design decision the user may want to adjust. The original's trigger is after the final boss's death animation; the redesign can keep this or move it earlier/later. Recommendation: keep the original's trigger for Phase 1 faithfulness; revisit in Phase 3 if the redesign's chapter structure has a different dramatic moment.

- **The "lean asset budget" target numbers.** §10.9 commits to "200-400 unique sprites, 50-100 maps, 30-50 minutes of music, 30-50 enemies, 40 playable characters" as the aesthetic target. The user may want a different target (smaller for more focus, larger for more variety). The trade-off is the aesthetic of "lean and curated" vs. "comprehensive and varied." Recommendation: the targets in §10.9 as defaults, with the user free to expand any category.

These are not blocking the document's continuation. §11 (Toolchain) is unblocked and can be drafted next. §11 will specify the day-to-day toolset the agent uses — editor, terminal, image tools, audio tools, version control, CI, and the specific configurations that make the agent's workflow reproducible.

---

---

## 11. Toolchain

This section specifies the day-to-day toolset the agent uses to actually do the work defined in §6 (Godot 4 Deep Dive), §7 (Engine Modifications Needed), §8 (The Remaster Pipeline), and §9 (AI-Agent Workflow). The locked engine is Godot 4.3. The locked design philosophy is "text-first everything, headless everything, deterministic builds, sandboxed test loops." This section enumerates the concrete tools that make those principles executable, names the alternatives the user could substitute, and flags the choices that have the largest impact on what the agent can and cannot do.

The section is organized by tool category. For each category: the chosen tool, the alternatives, the rationale, and the failure mode if the tool is unavailable. The categories are: Godot editor and runtime, the Python data tooling, the PS1 asset extraction tools, the image and audio conversion tools, the version control system, the CI/test runner, the documentation toolchain (this very document's author/reader toolchain), the human-in-the-loop review surface, and the workstation baseline. A "self-contained workstation" appendix closes the section with a single shell script that reproduces the entire toolchain on a fresh machine.

### 11.1 What "Toolchain" Means Here

The agent's toolchain is not "the tools the developer uses to write code." It is the full set of binaries, libraries, configurations, and conventions that have to be in place for the §8 pipeline and §9 workflow to run end-to-end. A toolchain that works on the developer's laptop but cannot reproduce in CI is a toolchain that fails the §1.5 "deterministic builds" and "sandboxed test loops" principles. A toolchain that requires a GUI interaction at any stage fails the "headless everything" principle. A toolchain that has a different version of Python or a different version of Godot on the developer's machine vs. CI fails the "deterministic builds" principle.

Concretely, the toolchain must answer four questions, every loop, without human intervention:

1. **What binaries are on `PATH`?** Godot 4.3, Python 3.12, pandoc, ffmpeg, timidity++, Pillow, jsonschema, jq, ripgrep, git. The agent's `terminal` tool runs commands; if a command is missing, the loop blocks.
2. **What configuration files exist?** Godot project settings (`project.godot`), JSON schemas (`data/schemas/*.schema.json`), the manifest files (`sources/MANIFEST.json`, `assets/MANIFEST.json`, `PIPELINE_STATE.json`), the agent's own working state (`loop_state.json`, `loop_memory.md`, `review.md`). Each file is part of the toolchain even though it's not a "tool."
3. **What scripts are runnable?** The §8 pipeline scripts (`fetch_*.py`, `extract_*.py`, `translate_*.py`, `validate_data.py`, `build_*.gd`, `remaster_headless`, `remaster_schema`). The agent invokes these by name; if a script's name or interface changes, the loop blocks until the agent updates both the script and the call site.
4. **What conventions are in effect?** Static typing in GDScript (§6.4). JSON Schema validation in `data/` (§6.5). Content-addressed files in `sources/` and `assets/` (§8.2-8.3). Per-loop memory append to `loop_memory.md` (§9.7). Decisions appended to `review.md` (§9.6). These are not tools; they are the social contract the agent operates under.

This framing is the reason the section is structured by tool category: each category is a contract the agent commits to honoring, and each failure mode is the loop-blocker if the contract is broken.

### 11.2 Godot 4.3 Editor and Runtime

The locked engine is Godot 4.3 (per §6.2's version-pin decision). The toolchain needs three Godot-related artifacts:

**The editor binary** — `godot-4.3-stable` (or the platform equivalent: `Godot_v4.3-stable_win64.exe` on Windows, `godot-4.3-stable` on Linux/macOS). This is the binary the agent uses to open the project, run the editor's tools (`remaster_schema`, `remaster_headless`), and (in headless mode) run the game for visual-regression tests. The binary is *not* on `PATH` by default; it lives in `tools/godot/` and is invoked via a relative path. The vendoring decision (§6.2) means the binary is committed to the repository, not downloaded at runtime.

**The export templates** — Godot's export templates are platform-specific builds the editor uses to produce platform binaries. For a single-platform Windows development setup, the Windows export template is required for the build step in §8.5. The templates are downloaded via the editor's `Manage Export Templates` menu, which requires a GUI. The headless workaround: download the `.zip` from the Godot website and unzip into `~/.local/share/godot/export_templates/4.3.stable/` (Linux/macOS) or `%APPDATA%\Godot\export_templates\4.3.stable\` (Windows). The agent's first run includes this unzip step as a setup script (`tools/setup_godot_templates.sh`).

**The .NET / Mono runtime (optional)** — per §6.3 the project is GDScript-only, so the .NET runtime is not required. If the §6.3 C# decision shifts to "narrow C# surface for a specific subsystem," then Mono 6.12+ becomes required. The setup script checks for `dotnet --version` and warns if a C# file is present without Mono installed.

The agent's Godot-related commands, all of which must work without GUI interaction:

```
# Run the project in headless mode (for visual-regression tests, integration tests)
godot-4.3-stable --headless --path . res://tests/test_main.tscn

# Run an EditorScript (for build steps, schema export)
godot-4.3-stable --headless --script tools/build_export.gd

# Validate all data/ files against the schemas
godot-4.3-stable --headless --script tools/validate_data.gd

# Generate the schema documentation (used by §11.8 docs build)
godot-4.3-stable --headless --script tools/export_schemas.gd
```

The `--headless` flag is the §1.5 "headless everything" principle instantiated. A Godot command that requires a display is a loop-blocker; the agent must always be able to run Godot in a terminal.

**Failure mode:** if Godot 4.3 is not installed or not on `PATH`, the loop blocks at the first §6 architecture test. The mitigation: `tools/check_prereqs.sh` runs at the start of every loop, lists missing prerequisites, and aborts with a clear error message. The agent's `loop_memory.md` entry from Loop 6 (the Godot 4 Deep Dive) is the precedent: when the agent encounters a missing tool, it logs the failure, surfaces the install command, and continues with whatever work does not depend on the missing tool.

### 11.3 Python Data Tooling

The §8 pipeline is predominantly Python: fetchers, extractors, translators, and validators. The locked choice (per §6.5) is Python 3.12 with `jsonschema`, `Pillow`, `requests`, and `pyyaml` as core dependencies. The rationale: Python is the agent's strongest scripting language, the libraries are mature, and the `jsonschema` library is the industry standard for JSON Schema validation.

The toolchain needs:

- **Python 3.12** (the minimum version that supports `match` statements and the modern type-hint syntax used in the §6.5 schema validators). Installed via the system package manager or via `pyenv`/`uv`. The `uv` choice (already installed on the host, per the environment notes) is preferred because it provides hermetic Python environments per-project.
- **The `jsonschema` library** for JSON Schema validation. Pinned to version 4.21+ for the `2020-12` schema dialect support.
- **The `Pillow` library** for TIM→PNG conversion (per §8.3 and §10.4). Pinned to version 10.0+ for the modern image format support.
- **The `requests` library** for fetching open-license sources (per §8.2's source acquisition). Pinned to 2.31+ for security fixes.
- **The `pyyaml` library** for parsing YAML config files (used in `PIPELINE_STATE.json` and the `tools/*.yaml` config).
- **The `pytest` library** for running the §8.6 test suite. Pinned to 7.4+.

The Python toolchain is managed via `uv`:

```
# Set up the project environment (one-time)
uv venv .venv
uv pip install -r requirements.txt

# Run a pipeline script
uv run python tools/translate_characters.py

# Run the test suite
uv run pytest tests/ -v
```

The `uv run` command is the agent's standard invocation: it ensures the correct Python version and the correct library versions are used, regardless of what Python is on `PATH`. The `requirements.txt` is the lockfile: every dependency is pinned, no floating versions. This is the §1.5 "deterministic builds" principle at the Python level.

**Alternatives:** the user could substitute Poetry or pip-tools for `uv`. The trade-off is `uv` is faster, has better hermetic-environment support, and is already installed on the host. Poetry is more established but slower and requires a separate lockfile management step. The decision is committed to `uv` in §6.5 and confirmed here.

**Failure mode:** if `uv` is missing, the agent falls back to `python3 -m venv` and `pip install` with a clear warning in `loop_memory.md`. If a specific library is missing, the failing script's error message names the missing library and the install command. The agent does not silently substitute a missing library with a similar one.

### 11.4 PS1 Asset Extraction Tools

§8.3 specifies the asset extraction stage. §10.4 lists the 10 PS1-era formats the extractors must handle. The toolchain needs:

- **DuckStation** (the §10.6 default emulator) for CD-ROM image mounting and disc-level access. Used to extract `SLUS_010.41` (the Chrono Cross disc image) and the table-of-contents files. DuckStation's CLI mode is invoked via `duckstation-cli -disc cuesheet.cue`. The `cuesheet.cue` is generated by the agent at the §8.2 source acquisition step. DuckStation is licensed GPLv3; the binary is downloaded from the official GitHub releases and committed to `tools/duckstation/` (the §1.6 legal posture requires that emulators are not subject to the "no original code" rule; they are clean-room reimplementations of the PS1 hardware and are themselves open-source).
- **Python with Pillow** for TIM→PNG conversion. The TIM parser is hand-rolled in `tools/extract_tim.py` (per §10.4 — TIM is a simple format, ~150 lines of Python).
- **`timidity++`** for SEQ→OGG conversion (per §10.4 and §10.6). `timidity` is a long-established MIDI-to-audio renderer. The `--config` flag points to a custom SoundFont bank that approximates the original PS1's audio quality.
- **A custom SEQ parser** in `tools/extract_seq.py`. SEQ is a PS1-specific MIDI-variant; the parser reads the VAB (Voice Archive Block) for instrument definitions and the SEQ for sequence data. The parser outputs a `.mid` file that `timidity++` can render.
- **A custom dialog parser** in `tools/extract_dialog.py`. The original Chrono Cross stores dialog in a compressed binary format on the disc. The parser decompresses and emits JSON. The compression algorithm is documented in the Chrono Cross modding community's wiki and is clean-room reimplemented in Python.
- **A custom map parser** in `tools/extract_map.py`. The map format is a tile-based grid with elevation and event data. The parser emits a `map.json` per map with the schema defined in §6.5.
- **A custom stat extractor** in `tools/extract_stats.py`. The character and enemy stat tables are in a packed binary format with a documented layout. The parser emits per-character `character.json` files in the §6.5 schema.

The PS1 extraction toolchain is the most heterogeneous part of the pipeline: one binary (DuckStation) for disc-level access, one system tool (`timidity++`) for audio rendering, and five hand-rolled Python scripts for format parsing. The scripts are versioned with the project, and their outputs are content-addressed (§8.2's `MANIFEST.json`).

**Failure mode:** if DuckStation is not installed, the §8.2 source acquisition step fails (the user must run DuckStation manually and place the extracted files in `sources/disc/`). The agent's §8.2 fetcher detects a missing binary, aborts with a clear error, and the loop advances to a non-PS1 step (e.g., a design-doc section, a §7 subsystem test). If `timidity++` is missing, the SEQ→OGG step fails and audio assets are missing; the §8.4 translation step emits a warning and continues without audio. The game's audio is silent until `timidity++` is installed and the audio step is re-run.

### 11.5 Image and Audio Conversion Tools

The PS1 extraction produces assets in original formats (TIM, SEQ, ADPCM-in-VAB). The §8.3-8.4 translation stages convert these to Godot 4-friendly formats (PNG, OGG, WAV). Beyond `Pillow` and `timidity++`, the toolchain needs:

- **`ffmpeg`** for any video-format conversion (the YouTube playthroughs in §8.2 are downloaded as MP4, and the agent extracts individual frames for visual reference). `ffmpeg` is the standard tool for this; alternatives are `mencoder` and `gstreamer`, both less universally available.
- **A custom PNG-to-PNG-optimizer** in `tools/optimize_png.py`. The PS1 sprites are 16-bit indexed-color images; the agent converts them to 32-bit RGBA, then runs an optimization pass that reduces the color palette where possible. The optimizer uses `Pillow`'s `quantize()` method.
- **A custom OGG-quality-checker** in `tools/check_ogg.py`. The §8.6 audio regression tests check that the OGG files are at the expected bitrate and have no clipping. The checker uses `ffprobe` to read the file's metadata and a custom waveform-analysis to detect clipping.
- **`audacity`** (optional, GUI tool) for manual audio cleanup. The agent does not use Audacity, but the user may want to clean up specific tracks by hand. The toolchain's role is to support manual cleanup: the §8.4 translation step outputs OGG files that are also importable into Audacity for the user's review.

The image and audio toolchain is intentionally minimal: one system tool (`ffmpeg`), one library (`Pillow`), and the OGG/PNG validation scripts. The discipline is "do not introduce more tools than necessary." Each new tool is a dependency to maintain, a version to pin, and a failure mode to handle.

**Alternatives:** the user could substitute `sox` for `ffmpeg` (for audio), ImageMagick for `Pillow` (for images), or a commercial tool like Adobe Audition for the audio cleanup. The trade-off is `ffmpeg` + `Pillow` is the open-source standard, well-maintained, and the agent is fluent in both. The commercial tools are stronger for manual cleanup but require a human in the loop.

**Failure mode:** if `ffmpeg` is missing, the video-frame-extraction step in §8.2 fails and the agent cannot use YouTube playthroughs as a content source. The agent's fallback is to use screenshot images provided directly by the user (placed in `sources/screenshots/`). If `Pillow` is missing, the TIM→PNG conversion fails and the entire asset pipeline halts at Stage 3 — the loop is blocked until `Pillow` is installed.

### 11.6 Version Control

The locked choice is `git` (per §6.3's project structure and §8.10's content-addressing). The toolchain's git-specific requirements:

- **A git repository at the project root** (`D:\Game Design\Remaster Engine\.git`). Initialized with `git init`, the main branch is `main`.
- **A `.gitignore` that excludes transient files** but commits the vendored binaries. The committed-in-vendored-binaries choice is the §6.2 "deterministic builds" principle: the Godot binary, DuckStation, and the export templates are all committed so a fresh clone is immediately runnable. The `.gitignore` excludes `.venv/`, `__pycache__/`, `build/`, `*.tmp`, and the `user://` Godot save directory.
- **A branching model.** §9.4 commits to per-TDD-cycle commits on `main`. The main branch is the always-runnable state; experimental work happens on feature branches (`feature/character-augmentation`, `fix/battle-determinism`, `docs/section-11`) and is merged to `main` after passing tests. The user can review feature branches before merge.
- **Commit message convention.** Each commit message starts with a one-word category (`draft:`, `fix:`, `test:`, `doc:`, `data:`, `refactor:`, `chore:`) followed by a short description. This is the "Conventional Commits" convention, adapted for the project's categories. The convention makes the git log scannable: `git log --oneline --grep draft:` shows every section-drafting commit.
- **A pre-commit hook that runs the validation scripts.** The hook runs `validate_data.py` (schema check) and `pytest tests/unit/` (fast unit tests) on every commit. Slower tests (integration, visual regression) run in CI, not at commit time.

The agent's git workflow per loop:

```
# 1. After drafting a section, write to disk
write _s11_draft.md

# 2. After regenerating the docx, validate everything
uv run python tools/validate_data.py
uv run pytest tests/unit/

# 3. If valid, commit with the conventional-commits format
git add remaster_engine_design_spec.md
git commit -m "draft: §11 Toolchain (X words, Y decisions)"

# 4. Push to remote (if configured)
git push origin main
```

The remote is optional for a single-developer project; the local git repository is sufficient for the §1.5 "deterministic builds" principle (every artifact is reproducible from the committed state). The user may want to push to GitHub or GitLab for backup; the toolchain does not require it but supports it via the standard `git remote add` workflow.

**Failure mode:** if git is missing, the project has no version control, the §1.5 "deterministic builds" principle is violated, and the loop is operating without a safety net. The `tools/check_prereqs.sh` script flags this. The agent does not proceed without git installed; this is the one tool the toolchain refuses to operate without.

### 11.7 CI / Test Runner

§8.6 specifies five test batteries. The CI toolchain runs all five on every commit and on a nightly schedule. The locked choice is **GitHub Actions** (per §6.3 and §8.6's "the agent's TDD loop runs the same commands as CI" principle). The rationale: GitHub Actions is the most common CI provider, has a generous free tier, and is well-supported by the Godot community's existing `.github/workflows/` examples.

The CI configuration in `.github/workflows/test.yml`:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install uv
      - run: uv venv .venv
      - run: uv pip install -r requirements.txt
      - run: uv run python tools/validate_data.py
      - run: uv run pytest tests/unit/
      - run: uv run pytest tests/integration/
      - uses: josephbmanley/godot-ci-action@v1
        with:
          godot-version: '4.3'
      - run: godot --headless --path . res://tests/test_main.tscn
```

The CI runs in under 10 minutes (the slow tests are the visual regression suite, which runs on a separate nightly schedule). Every commit must pass CI before it lands on `main`. The user is notified via the loop summary when a CI failure occurs.

**Alternatives:** the user could substitute GitLab CI, CircleCI, Jenkins, or a self-hosted runner. The trade-off is GitHub Actions is the most common, but for a project that is intentionally not on GitHub (the §1.6 "fan work / clean-room" legal posture), a self-hosted runner is more privacy-preserving. The decision is committed to GitHub Actions in §6.3, with the caveat that the `.github/workflows/` directory is removable if the user prefers not to use GitHub.

**Failure mode:** if CI is not configured (no `.github/workflows/`), the §1.5 "sandboxed test loops" principle is degraded: the agent's local TDD loop is the only safety net, and the user must run CI manually before merging. The agent's loop summary reports this gap if it notices it.

### 11.8 Documentation Toolchain

This design document is itself a toolchain artifact. The Markdown source is human-edited and agent-edited; the .docx is generated for the user to read; the JSON schemas are exported to HTML for browsing. The toolchain needs:

- **pandoc** (already installed, per the loop state) for `.md` → `.docx` conversion. The command is the one in the cron prompt and §8's pipeline.
- **A custom JSON-Schema-to-HTML generator** in `tools/render_schemas.py`. The output is a browsable HTML page per schema, committed to `docs/schemas/`. The agent uses this when authoring new data files (the schemas are the "API documentation" for the data layer).
- **A custom Markdown-to-HTML site generator** in `tools/render_site.py`. The output is a static site in `docs/site/` that includes the design document, the schemas, the API documentation, and the loop memory. The site is for the user's reference; the .docx is the canonical reading format.
- **The user's preferred Markdown editor** for reading and editing the design document. The agent does not care which editor the user uses; the Markdown source is the contract.

The documentation toolchain is the lightest part of the project: pandoc is the only system dependency, the rest is Python scripts. The agent's standard documentation workflow is:

```
# 1. After drafting a section, regenerate the .docx
"C:\Users\14239\AppData\Local\Pandoc\pandoc.exe" -f markdown -t docx \
    -o "D:\Game Design\Remaster Engine\remaster_engine_design_spec.docx" \
    "D:\Game Design\Remaster Engine\remaster_engine_design_spec.md"

# 2. Regenerate the static site (optional, for users who prefer HTML)
uv run python tools/render_site.py
```

**Alternatives:** the user could use Sphinx, MkDocs, or Docusaurus for the static site. The trade-off is `tools/render_site.py` is hand-rolled (~200 lines) and produces a minimal site; Sphinx/MkDocs produce richer sites but require more configuration and a larger dependency footprint. The decision is the hand-rolled site, with the option to swap in MkDocs later if the user wants a richer experience.

### 11.9 Human-in-the-Loop Review Surface

The agent operates in cron loops. The user reviews the agent's work asynchronously, typically by reading the loop summary and the design document. The review surface is the toolchain too:

- **The loop summary message** (delivered to the user's chat automatically) is the primary review touchpoint. The format is the one in §9.9: "Loop N complete. Drafted: §N. <title> (~XXXX words). Updated: <files>. Decisions needed: <count>. Next loop: §N+1. <title>."
- **The `review.md` file** is the decision log. The user reviews this when a decision is needed and replies to the agent's loop summary with the chosen option.
- **The `loop_memory.md` file** is the lesson log. The user reviews this when they want to understand the agent's reasoning across loops.
- **The git log** is the change log. The user reviews this when they want to understand what changed in a specific loop.
- **The `PIPELINE_STATE.json` file** is the operational log. The user reviews this when they want to understand the current state of the data pipeline.
- **The .docx file** is the canonical reading format for the design document. The user opens this in Word, LibreOffice, or Google Docs.

The review surface is intentionally low-tech: plain text files and a chat summary. No web app, no notification system, no dashboard. The §1.5 "no magic" principle applies to the review surface too: a user who can `cat loop_memory.md` and `git log` should be able to understand the project's state without learning a custom tool.

**Failure mode:** if the user cannot find a specific decision or change, the review surface has failed. The agent's loop summary points to the relevant files; if a user says "I cannot find the decision on X," the agent's next loop includes a more explicit pointer. The §9.7 memory file protocol is the cross-loop indexing that prevents this failure mode.

### 11.10 Workstation Baseline

A fresh machine needs the following to run the toolchain end-to-end:

**Operating system:** Windows 10/11 (the host per the environment notes) or Linux/macOS for development. The agent's `terminal` tool runs `bash` on Windows (git-bash/MSYS) and the standard `bash` on Linux/macOS. The shell scripts in `tools/` are written in POSIX `sh` and `bash` with no PowerShell or `cmd.exe` dependencies.

**Hardware baseline:**
- 16 GB RAM minimum (Godot 4 + the editor + the data tools + a browser for web research = ~6 GB working set; 16 GB leaves headroom)
- 100 GB free disk (the vendored binaries, the git history, the `sources/` and `assets/` directories, the build artifacts)
- A GPU with Vulkan support (Godot 4 requires Vulkan 1.0+; integrated GPUs work, dedicated GPUs are faster for the visual regression tests)
- A 1080p display (for the user's reading of the .docx; the agent's loop is headless and does not need a display)

**Software baseline (installed by `tools/setup.sh`):**

```bash
#!/bin/bash
# tools/setup.sh — workstation baseline setup

set -euo pipefail

# 1. System tools
if ! command -v git &> /dev/null; then
    echo "ERROR: git not installed. Install git first."
    exit 1
fi
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not installed. Install Python 3.12+ first."
    exit 1
fi

# 2. Python tooling
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    pip install uv
fi
uv venv .venv
uv pip install -r requirements.txt

# 3. Godot 4.3 (vendored binary in tools/godot/)
if [ ! -f "tools/godot/godot-4.3-stable" ]; then
    echo "ERROR: Godot 4.3 binary not found at tools/godot/godot-4.3-stable"
    echo "Download from https://godotengine.org/download and place in tools/godot/"
    exit 1
fi

# 4. Export templates
EXPECTED_TPL_DIR="$HOME/.local/share/godot/export_templates/4.3.stable/"
if [ ! -d "$EXPECTED_TPL_DIR" ]; then
    echo "Setting up Godot export templates..."
    mkdir -p "$EXPECTED_TPL_DIR"
    # The agent downloads the official templates .zip and unzips
    wget -q "https://github.com/godotengine/godot-builds/releases/download/4.3-stable/Godot_v4.3-stable_export_templates.tpz" \
        -O /tmp/godot_templates.tpz
    unzip -q /tmp/godot_templates.tpz -d "$EXPECTED_TPL_DIR"
    rm /tmp/godot_templates.tpz
fi

# 5. Image / audio tools
if ! command -v ffmpeg &> /dev/null; then
    echo "WARNING: ffmpeg not installed. YouTube frame extraction will fail."
fi
if ! command -v timidity &> /dev/null; then
    echo "WARNING: timidity++ not installed. SEQ→OGG conversion will fail."
fi

# 6. Pandoc (for .docx generation)
if ! command -v pandoc &> /dev/null; then
    echo "WARNING: pandoc not installed. .docx generation will fail."
fi

# 7. DuckStation (for PS1 disc access)
if [ ! -f "tools/duckstation/duckstation-cli" ]; then
    echo "WARNING: DuckStation not installed. PS1 disc access will fail."
fi

# 8. Verify
echo "Toolchain setup complete. Running verification..."
tools/check_prereqs.sh
```

The `tools/check_prereqs.sh` script is the §9.4 "agent's TDD loop" first step: verify the environment is sane before doing anything else. The script is short (~50 lines) and reports each missing prerequisite with the install command.

**The hermetic-environment option.** The setup script above installs tools at the system level. The alternative is a hermetic environment: a Docker container with all tools pre-installed, mounted onto the user's machine via VS Code's dev container extension. The trade-off is hermetic environments are more reproducible (the container is the same on every machine) but require Docker and a slightly more complex setup. The decision is system-level installation for simplicity, with the option to switch to a container if the user wants stricter reproducibility.

### 11.11 The Toolchain as a Whole

The toolchain as a whole is the assembly of all of the above into a coherent working environment. Three principles recur across the categories:

1. **All binaries are versioned.** Godot 4.3, Python 3.12, pandoc 3.10, etc. A `tools/VERSIONS.md` file lists the exact version of every binary and library, with the source URL and the install date. The §1.5 "deterministic builds" principle requires this.
2. **All libraries are pinned.** `requirements.txt` uses exact versions (`Pillow==10.4.0`, `jsonschema==4.23.0`). No floating versions, no `^` operators, no `latest` tags.
3. **All conventions are documented.** The GDScript typing rules in §6.4, the JSON Schema validation rules in §6.5, the commit message convention in §11.6, the loop summary format in §9.9, the file naming conventions in §8 — every convention the agent operates under is documented somewhere in the project. A future contributor (human or agent) can read the design document and learn the conventions without having to reverse-engineer them from the code.

The "toolchain as a whole" mental model is what makes the project reproducible. A new contributor who has the design document (this file) can reproduce the entire development environment by running `tools/setup.sh` and reading `tools/VERSIONS.md`. The §15 (Next Steps) proof-of-concept scope will be the test: if a fresh machine can run `tools/setup.sh` and produce a working Godot 4.3 project in under 30 minutes, the toolchain is complete.

### 11.12 What the Toolchain Does Not Include

The toolchain is a working set, not a wishlist. Things deliberately excluded:

- **A custom game engine.** The project uses Godot 4.3 as-is (with the §7 modifications). The toolchain is the layer on top, not a replacement for the engine.
- **A custom IDE.** The agent edits GDScript in Godot's built-in editor (for the visual editing) or in any text editor for the .gd files. No VS Code extension, no JetBrains plugin — the agent is fluent in plain text and does not need IDE integration.
- **A custom test framework.** The toolchain uses pytest for Python tests and Godot's built-in test framework (via `res://tests/`) for GDScript tests. No custom test runner.
- **A custom asset pipeline.** The §8.3 extractors are Python scripts, not a custom tool. The toolchain is a collection of standard tools orchestrated by a script, not a new system.
- **A custom build system.** Godot's built-in export pipeline (invoked via `godot --headless --script tools/build_export.gd`) is the build system. No Make, no CMake, no Bazel.

This exclusion list is the §1.5 "no magic" principle at the toolchain level: every tool is a well-known, well-documented, widely-used system. A future contributor who has used Python, git, and a text editor can learn the project in a week. A future contributor who has to learn a custom build system and a custom test framework and a custom IDE integration is starting from a much harder place.

### 11.13 Decisions Needed

These are choices the section commits to but the user may want to revisit:

- **The Python package manager (`uv` vs. Poetry vs. pip-tools).** §11.3 commits to `uv` because it is fast, hermetic, and already installed on the host. The alternative is Poetry (more established, slower) or `pip-tools` (simpler, no hermetic environment). The trade-off is `uv` is the modern choice and the agent is fluent in it; Poetry is the conservative choice. Recommendation: `uv` as the default, with the option to swap in Poetry if the user has a strong preference.

- **The CI provider (GitHub Actions vs. self-hosted).** §11.7 commits to GitHub Actions. The alternative is a self-hosted runner (Jenkins, GitLab CI, Drone) for projects that are not on GitHub. The trade-off is GitHub Actions is the most common and best-supported, but it requires a GitHub account and a public or private repository, which conflicts with the §1.6 fan-work/clean-room legal posture for some users. Recommendation: GitHub Actions with a private repository; the project can be moved to self-hosted if the user wants stricter privacy.

- **The static-site generator for documentation.** §11.8 commits to a hand-rolled `tools/render_site.py` (~200 lines of Python). The alternative is MkDocs (richer themes, more dependencies), Sphinx (the most powerful, the most configuration), or Docusaurus (a React-based static site generator, the heaviest). The trade-off is the hand-rolled site is minimal and dependency-free; MkDocs/Sphinx/Docusaurus are richer but require more setup. Recommendation: the hand-rolled site, with the option to upgrade to MkDocs if the user wants a richer reading experience.

- **The hermetic-environment option (system install vs. Docker).** §11.10 commits to system-level installation. The alternative is a Docker container with all tools pre-installed, mounted via VS Code's dev container extension. The trade-off is Docker is more reproducible but adds a dependency on Docker and a layer of indirection. Recommendation: system install for simplicity; the `Dockerfile` and `.devcontainer/devcontainer.json` can be added later if the user wants stricter reproducibility.

- **The PS1 emulator (DuckStation vs. PCSX-Reborn vs. NoCash PSX-SPX).** §10.6 and §11.4 commit to DuckStation. The alternative is PCSX-Reborn (more mature, Linux-friendly) or NoCash's PSX-SPX (the most accurate for some edge cases, less user-friendly). The trade-off is DuckStation is the modern default and the agent is fluent in it. Recommendation: DuckStation, configurable via `REMASTER_PS1_EMULATOR` env var.

These are not blocking the document's continuation. §12 (Chrono Cross Walkthrough) is unblocked and can be drafted next. §12 will specify the chapter-by-chapter narrative arc of the redesign, with the design commitments from §3 (the 10-chapter structure, the 6-base party model, the form-change events) instantiated as a concrete walkthrough.

---

## 12. Chrono Cross Walkthrough (Expanded for Redesign)

### 12.1 What This Section Is

Sections 1–11 specified what the project is, why it is the way it is, what the redesign commits to, what engine runs it, what subsystems ride on top of that engine, what the pipeline produces, how the agent operates, what the PS1 source content looks like, and what tools make all of it executable. This section turns the §3 design contract into a *narrative* — the chapter-by-chapter walkthrough of the redesign's 10-chapter, 6-base, level-based progression.

The walkthrough is a design artifact, not a script. It is the test that proves the §3 design holds together: that the 6 bases have enough story to fill 10 chapters, that the form-change story beat lands at a chapter boundary, that the level-based magic progression gives the player meaningful growth at each chapter, that the 36 supports have roles to play, and that the timeline (Heroes' Trial → FATE reveal → Schala → Chrono Cross) can be compressed into a single central loop without losing the original's emotional weight.

Every chapter in this section assumes the §3.16 locked design. Element specialization is character-bound. Form-change is a fixed chapter event. Magic tiers are unlocked by character level, not by player choice. The basic attack line is the spine of each base's combat identity. Supports are augmentations, not replacements. The party grows from 1 → 6 across the chapters.

### 12.2 The Compressed Timeline

The original *Chrono Cross* spans at least twenty years of in-universe chronology: Serge's childhood drowning, the parallel-world split, the present-day adventure, the Frozen Flame's time-paradox reveal, Schala's fate in the Darkness Beyond Time, and the creation of the Chrono Cross element. The redesign compresses this into a single ten-chapter sequence because the redesign's chapter structure is about *party progression*, not about *time*. The agent's task is to retain the emotional weight of the original's time-jumps while collapsing the chronology into one central loop.

The redesign's compressed timeline, mapped to chapters:

- **Chapter 1: The Drowning (10 years before main events).** Prologue. Serge on the beach with Leena. The fever, the rescue attempt, the alternate-self apparition. Closes with the wave that almost kills him.
- **Chapter 2: The Wake (present day, opening).** Two months after the form-change event. Serge in Lynx's body, alone, on the beach at Lizard Rock.
- **Chapter 3–10: Present-day adventure.** The recruitment arc. Serge (in Lynx body for ch. 2–6, in his own body from ch. 7 onward) gathers the party, traverses El Nido, reaches the Frozen Flame, and resolves the time paradox.

This compression means some original subplots (Kid's orphanage past, the Fargo/Marle-stand-in relationship, the time-travel mechanics) are trimmed or moved. The redesign's commitment is to the *central story* and the *main cast*, not to every subplot. The trade-off is documented in §3.15: a 30-hour JRPG with fewer subplots, not a 50-hour JRPG with all of them.

### 12.3 The Six Recruitment Beats

Each base has a recruitment beat — a scripted scene that adds them to the active party. The redesign's recruitment beats are larger than the original's because the bases are full characters, not silent recruits. The recruitment beat is a chapter event, not a side quest.

| Chapter | Base | Element | Recruitment Beat |
|---|---|---|---|
| 1 | Serge/Lynx | White | The game opens with Serge in his Lynx body. He is the protagonist, no recruitment needed; the "recruitment" is the player accepting the form. |
| 2 | Kidd | Red | Serge meets Kidd at the Lizard Coast after the Viper Manor assault. Kidd is impressed by Serge's survival instinct and agrees to travel together. |
| 3 | Nikki | Blue | Serge and Kidd reach Guldove and meet Nikki. The deal: Serge helps Nikki stage the show; Nikki joins the party for the Guldove arc. |
| 4 | Glenn | Green | Glenn defects from the Dragoons after confronting General Viper at the Manor. He joins the party at the Hydra Marshes waypoint. |
| 5 | (form) | — | No new base. Herle appears as a story character; her recruitment is in ch. 6. |
| 6 | Herle | Black | Herle leaves the Magic Kingdom's surviving council after the form-return ritual. She joins as the Black base. |
| 7 | (light techs) | — | No new base. Serge's return to his own body is the chapter event. |
| 8 | Norris | Yellow | Norris rescues the party from the Isle of the Damned's dragon-keeper. He joins as the Yellow base. |
| 9 | (climax) | — | No new base. The full party tackles the Frozen Flame dungeon. |
| 10 | (epilogue) | — | No new base. The party disbands, the story resolves, New Game+ unlocks. |

The recruitment beats are designed for dramatic pacing: ch. 1–4 fill the party in steady rhythm (one new base per chapter), ch. 5 is the form-change breather, ch. 6 brings Herle, ch. 7 is the form-return and light-tech unlock, ch. 8 brings the final base, ch. 9 is the climax, ch. 10 is the wind-down. The player is never without a chapter event to look forward to.

### 12.4 Chapter 1 — The Wave (Serge Alone, White)

**Setting.** Opal Beach, ten years ago. Serge and Leena are children. The chapter opens on a still afternoon; closes on the wave.

**Active party.** Serge alone. Lynx is not yet a separate identity — he is the alternate Serge that Leena saw. The player plays as Serge, learns the controls, and meets Leena for the first time as a playable moment (a flashback).

**Combat encounters.** Two scripted fights. The first is a tutorial fight (Serge vs. a single combot — the Combot is the standard PS1-era low-tier enemy, the original's stand-in for "a thing to hit that doesn't kill you"). The player learns the basic attack line. The second is the *failed* fight — Serge tries to fight something in the water, fails, and the wave takes him. The failed fight is a teaching moment: the player sees what happens when they try to attack the wave itself.

**Magic tier system (this chapter).** At level 1, Serge has access to 1× tier-1 slot. The slot is filled by Dash and Slash (the §3.4 basic attack line, tier 1). The player learns the magic-tier system as "what each slot does at this level" rather than as a UI dump. The Combot fight is the first time the player sees a magic slot used.

**The wave event.** The wave that almost kills Serge is not a combat encounter. It is a *cutscene-driven event* with one scripted QTE (press the button to grab the rope, fail = Leena saves you). The event plays out the way the original describes: Serge drowns, Leena calls for help, Serge is rescued. The event ends with Serge waking on a beach — this time, the chapter-end splash screen fades to "Two Months Later," and the player is now in Lynx's body.

**Chapter-end scene.** The form-change is revealed not as a "you are now Lynx" but as "you wake up in a body that is not yours, and the first thing you see is Kid walking away from a stranger on the beach." The player is now playing as Lynx without yet knowing it. The dramatic weight lands in chapter 2.

**Design notes.** Chapter 1 is the shortest chapter (about 30 minutes of play). Its job is to teach the magic tier system, the basic attack line, and the form-change premise. The §3.7 Pip reframing has not yet activated — Devil Pip is a future reward, not a present one. Angelic Pip is a future reward too.

### 12.5 Chapter 2 — The Thief (Lynx + Kidd, White + Red)

**Setting.** Opal Beach (Lynx waking up), Lizard Coast, the road to Guldove. The chapter spans Lynx's first day in his alternate body and the meeting with Kidd.

**Active party.** Lynx (the player, in Serge's body but called "Lynx" by the world) + Kidd, joined at the chapter's midpoint.

**Combat encounters.** 6–8 encounters across the Lizard Coast. The encounters are scaled for 1–2 characters: Combot fights, Dwarves, a mini-boss (a Dire Hyena) at the end of the coast. The Lynx's basic attack (Dash and Slash) is the same as Serge's; the difference is *which augments are available* (per §3.7, during the Lynx form, Devil Pip augments are active).

**The Kidd recruitment beat.** Lynx is found on the beach by Kid, who mistakes him for a victim of the Viper Manor assault. Kid helps Lynx up, offers to take him to safety, and discovers that Lynx has no memory of his own identity. Kid takes Lynx to the road to Guldove, where they are ambushed by Viper's soldiers. The fight is a recruitment fight: Lynx uses Dash and Slash to hold off three soldiers, Kid uses Red Pin to flank, and after the fight, Kid agrees to travel with Lynx ("You fight okay. I'm Kidd. You're coming with me."). The recruitment is *earned* through combat cooperation, not through dialog choice.

**Magic tier system (this chapter).** Lynx is at level 1 with 1× tier-1 slot. Kidd is at level 1 with 1× tier-1 slot. The player now has two characters and two tier-1 slots. The party screen shows the magic progression: at level 3, each character gets a second tier-1 slot; at level 5, the first tier-2 slot opens. The player is *told* this through a UI hint but does not need to manage it actively.

**Kidd's basic attack line.** Red Pin is introduced as the second basic attack. The player sees that the second character has a *different* basic attack — Kidd throws projectiles, Lynx slashes. The two characters' basic attacks work together: Lynx's slash is single-target, Kidd's pin hits one target but can be aimed to hit a different one. The encounter design exploits this — every encounter has at least one "pin the runner, slash the front" opportunity.

**Devil Pip augments (this chapter).** The §3.7 Pip reframing says that during the Lynx form, the Devil Pip support slot is unlocked, granting access to Lynx's dark techs as augments of the basic attack line. In chapter 2, this means: at level 3, when Lynx gets his second tier-1 slot, the slot can be filled with *either* a normal augment (Riddle, Steena, or Doc) *or* the Devil Pip augment. The player sees the choice in the level-up UI: "Second tier-1 slot unlocked. Available augments: Riddle's status effect, Steena's heal-on-hit, or Devil Pip's dark magic." Picking Devil Pip commits the player to the dark-tech path; the other choices are recoverable later.

**Chapter-end scene.** Lynx and Kid reach the Guldove outskirts. Kid is hurt; Lynx is disoriented. The chapter ends with the Guldove gate in the distance. Chapter 3 begins with the Guldove introduction.

**Design notes.** Chapter 2 is the recruitment that does not feel like a recruitment. The player is not asked "do you want to recruit Kidd?" — the player is *given* Kidd by the scene. The recruitment beat is a 2-minute cinematic that ends with the party of two walking toward Guldove. The chapter also introduces the Devil Pip choice early, so the player knows the dark-tech path is a real option before the form-change in chapter 4.

### 12.6 Chapter 3 — The Show (Lynx + Kidd + Nikki, + Blue)

**Setting.** Guldove, the S.S. Zelbetta (the docked ship), Nikki's stage. The chapter is urban and social — fewer dungeons, more NPC interaction.

**Active party.** Lynx + Kidd + Nikki.

**Combat encounters.** 4–5 encounters (Guldove is a city, so most encounters are scripted ambushes, not random battles). The party is now 3 characters, and the encounter design uses 3-character mechanics: one encounter has Lynx and Nikki on a back-line defense while Kidd flanks; another has all three on a single target; another tests the player's ability to use Nikki's buffs (healing, status-cleanse) on the front-line characters.

**The Nikki recruitment beat.** Nikki is staging a show in Guldove, and the S.S. Zelbetta's crew has refused to let her perform. The deal: Lynx and Kid help Nikki clear the crew's debt to the Guldove guard captain (a side quest, ~15 minutes of play), and Nikki stages the show. The show is a scripted scene: Nikki performs, the crew forgives the debt, and Nikki offers to travel with Lynx and Kid as a "tour guide" (her real reason: she has a debt of her own, and the party is heading to the Viper Manor, which is on her way).

**Nikki's basic attack line.** Grand Finale is a single-target musical strike that scales with audio status effects (Silence, Confusion, Evasion Down). The player sees that Nikki's basic attack is *different in flavor* from Lynx's and Kidd's — Lynx is melee, Kidd is thrown, Nikki is performance. The three basic attacks form a triangle: physical, ranged, performance. The encounter design exploits this — every encounter has a "pick the right basic attack for this enemy" choice.

**Magic tier system (this chapter).** By the end of chapter 3, the player has been in enough fights that Lynx and Kidd are at level 3, and Nikki is at level 1. The level-ups happen mid-chapter as scripted rewards (a major combat win gives +1 level to the character who landed the killing blow). The level-based progression is *visible* in the party screen but not intrusive — the player does not need to grind.

**The "supports" are recruited passively.** The redesign's support recruitment is *not* a player choice. Riddle is met in Guldove and offers to join Lynx's support grid; Steena is met at the Guldove hospital and offers her heal-on-hit augment; Doc is met at the Guldove clinic and offers his status-cleanse augment. Each recruitment is a 1-minute scene with a dialog beat. The supports are story characters, not silent recruits.

**Chapter-end scene.** The party leaves Guldove for Viper Manor. Chapter 4 begins with the Manor approach.

**Design notes.** Chapter 3 is the *expansion* chapter — the player now has 3 characters, the basic attacks form a triangle, and the supports are starting to fill out. The §3.13 main-cast focus is operational here: Nikki has a real recruitment scene with dialog, motivation, and a deal that the player makes (clearing her debt). The §3.4 basic attack line is also operational: Nikki's Grand Finale is *her* basic attack, not a generic "musical strike," and the encounter design uses the difference between physical, thrown, and performance attacks.

### 12.7 Chapter 4 — The Sword, The Form (Lynx + Kidd + Nikki + Glenn, + Green, form-change)

**Setting.** Viper Manor, the Hydra Marshes, the return to the present-day beach. The chapter is the densest in the redesign — Manor infiltration, Glenn recruitment, and the form-change event.

**Active party.** Lynx + Kidd + Nikki + Glenn. The party grows from 3 to 4 mid-chapter.

**Combat encounters.** 10+ encounters across the Manor, the Marshes, and the escape route. The encounters are scaled for 3–4 characters: boss fights at the Manor's end (a duel with Glenn, then a joint fight against General Viper), the Hydra mini-boss in the Marshes, and a sequence of 4-on-6 encounters during the escape.

**The Glenn recruitment beat.** Glenn is defending the Manor against Lynx's party in the original's "you are thieves" misunderstanding. The redesign flips this: Glenn is already questioning the Dragoons' orders, and the party arrives in time to help him hold off a FATE-orchestrated monster (a "combot swarm" — a scripted combat that tests the party's ability to fight 6+ enemies). After the fight, Glenn defects. The recruitment is a 3-minute scene: Glenn removes his Dragoon armor, takes a sword from the armory, and says "I owe you. I'm coming with you." The player now has 4 characters.

**Glenn's basic attack line.** Dash and Gash is a sword strike; Sonic Sword is the ultimate (tier 8). Dash and Gash scales with combo length and parry chance. The encounter design exploits this: the Manor duels are *parry-timing fights* where the player learns that Glenn's basic attack is a parry-attack, not a damage-attack.

**The form-change event (chapter-end).** The party returns to the present-day beach (the same beach where Serge drowned ten years ago, but in the "Other World" timeline — the redesign's central loop visits this beach multiple times). The form-change is the chapter-end cutscene: Lynx collapses, the fever takes him, and when he wakes, he is in *his own body* — but the world has changed. The form-change is *not* a "you are now Serge" notification. It is a scene where Lynx looks at his hands and sees that they are not his hands. The chapter ends with the player in Serge's body, alone on the beach, with the party's camp visible in the distance.

**Magic tier system (this chapter).** By the end of chapter 4, the party is at level 5–7 (Lynx is the highest, having been in combat since chapter 2). The level-based progression means: by chapter 4, Lynx has access to 2× tier-1 slots + 1× tier-2 slot. The Devil Pip augments are *active* — Lynx's dark techs (Feral Cats, Hell's Fury, Forever Zero) are usable as augments. The player has had a chapter and a half to learn the dark-tech path.

**Chapter-end scene.** Serge (in his own body) walks back to the camp. Kid does not recognize him. The form-change is the act-1 break.

**Design notes.** Chapter 4 is the longest chapter (about 5 hours of play) and the densest. It is the chapter that proves the redesign's structure works: the 4-character party, the parry-timing combat, the dark-tech augments, and the form-change event all happen in sequence without crowding each other. The §3.7 Pip reframing is fully operational by the end of the chapter — the dark techs are usable, and the player has had time to commit to the path.

### 12.8 Chapter 5 — The Dark (No new base, dark-tech consolidation)

**Setting.** The Dead Sea, the dragon trials, the approach to the Dark Fort. The chapter is the Lynx-arc continuation, but with Serge now in his own body.

**Active party.** Serge + Kidd + Nikki + Glenn (4 characters).

**Combat encounters.** 8–10 encounters, with a focus on the dragon trials (4 scripted boss fights against the dragon elementals). The trials are designed to test the party's use of the dark-tech augments: each dragon is weak to a different augment, and the player has to pick the right augment for the right dragon.

**Herle's appearance (this chapter).** Herle is met at the Dead Sea's edge, traveling with a Dragoon escort. She is a story character in chapter 5, not a base. The player interacts with her as a dialog NPC: she offers information about the Frozen Flame, agrees to meet the party at the Dark Fort, and departs. Her recruitment is in chapter 6.

**Magic tier system (this chapter).** Serge is at level 7–8 by the end of the chapter. The tier-1 and tier-2 slots are full, and the tier-3 slot is opening. The dark-tech augments are *consolidated* — the player has been using them for two chapters, and the encounter design rewards the dark-tech path with bonus damage against the dragon elementals.

**The "no game over" flag (this chapter).** Per the resolved review decision, the "no game over" late-game flag triggers here. After the chapter-5 boss (the first dragon elemental), the game no longer shows a Game Over screen on party wipe — instead, the party wakes at the last save point with full HP and a "the story continues" cutscene. The flag is invisible to the player but real in the code. The §10.9 "no-late-game-game-over" commitment is operational.

**Chapter-end scene.** The party reaches the Dark Fort. Herle is waiting at the gate. Chapter 6 begins with the Fort infiltration.

**Design notes.** Chapter 5 is a "consolidation" chapter — no new base, but the dark-tech path is locked in, the dragon trials are the combat test, and Herle's appearance sets up the next chapter's recruitment. The §3.13 main-cast focus is operational in the Herle scene: she is a *character*, not a stat block. The player learns her motivation (she is investigating the Frozen Flame for the Magic Kingdom), her conflict (she disagrees with the Magic Kingdom's leadership), and her promise (she will join the party if they survive the Fort).

### 12.9 Chapter 6 — The Return (Herle, + Black, form-return)

**Setting.** The Dark Fort, the FATE chamber, the return to the present-day beach. The chapter is the second densest — Fort infiltration, Herle recruitment, and the form-return event.

**Active party.** Serge + Kidd + Nikki + Glenn + Herle. The party grows from 4 to 5 mid-chapter.

**Combat encounters.** 8–10 encounters in the Fort, plus the form-return boss (a FATE-orchestrated "Dark Serge" — the Lynx-body Serge that the player has been playing as, now revealed as the antagonist). The Dark Serge fight is a 5-on-1 mirror match: the player's party against the Lynx-body's dark-tech augments. The fight is the design's test of the augmentation model — the player has been building augments all game, and the boss uses the same system in reverse.

**The Herle recruitment beat.** Herle joins after the form-return. The recruitment is a *post-form-return* scene: Serge wakes in his own body, Herle is standing over him, and she says "You were him. Now you are you. I will travel with you, because the dark techs you carried belong to me now." The §3.7 migration happens here: the dark techs that were Serge's (during the Lynx form) migrate to Herle's support grid. Mechanically, Herle's tier-1 and tier-2 slots open with the dark techs as augments.

**Herle's basic attack line.** Moonshine is a dark magic bolt; Lunairetic is the ultimate (tier 8). Moonshine scales with curse chance and dark damage. The encounter design exploits this: Herle's basic attack is a *ranged magic attack*, which gives the party a fifth combat role (after physical, thrown, performance, and sword). The five basic attacks form a pentagon: each is distinct in flavor and in encounter role.

**The form-return event (chapter-end).** The party returns to the present-day beach. Serge is in his own body. Kid recognizes him. The party is now Serge + Kidd + Nikki + Glenn + Herle. The form-return is the act-2 break.

**Magic tier system (this chapter).** Serge is at level 9, Herle is at level 1 (just recruited). The level-based progression means: Serge's tier-3 and tier-4 slots are now open, and the light-tech augments (Angelic Pip path) are *available*. The player now has access to the §3.7 light-tech path as a post-form-return reward.

**Chapter-end scene.** The party camps on the beach. Serge looks at his own hands and smiles. The chapter ends with the "post-form-return" UI hint: "Light techs now available. Angelic Pip slot unlocked at level 10."

**Design notes.** Chapter 6 is the form-return and the Herle recruitment. The §3.7 Pip reframing is operational in full: dark techs migrate to Herle, light techs unlock for Serge. The redesign's promise — "Pip is a story beat, not a balance accident" — is visible to the player. The dark-tech augments that the player invested in during chapters 4–5 are *not lost*; they migrate to a new base. The light-tech augments are a *reward* for the form-return, not a one-battle buff.

### 12.10 Chapter 7 — The Light (No new base, light-tech consolidation)

**Setting.** Guldove (return), the Isle of the Damned approach, the Chronosopolis preparation. The chapter is a denouement and a setup.

**Active party.** Serge + Kidd + Nikki + Glenn + Herle (5 characters).

**Combat encounters.** 6–8 encounters, with a focus on the light-tech path. The chapter's encounters are *designed* to reward light-tech augments: enemies are weak to light, and the player has new tools.

**The light-tech consolidation.** Serge is at level 10 by the end of the chapter. The light-tech augments (Luminaire, Heaven's Call, Flying Arrow) are usable as augments of the basic attack line. The player sees the contrast: dark techs (chapters 4–6) were aggressive; light techs (chapter 7 onward) are restorative. The redesign's commitment to *both* paths is operational.

**Story beats (this chapter).** Serge visits Leena in Guldove, has a 2-minute scene that resolves the childhood subplot, and receives the encouragement to "go to the Frozen Flame and fix this." The party prepares for the Chronosopolis approach. The chapter is the slowest-paced of the redesign — it is meant to be a breather between the form-return and the final-base recruitment.

**Magic tier system (this chapter).** Serge is at level 10, with full tier-1, tier-2, and tier-3 slots. The player has all the augments the redesign commits to. Herle is at level 3 by the end of the chapter (she was recruited in chapter 6 and has had one chapter of combat). Kidd, Nikki, and Glenn are at level 7–8.

**Chapter-end scene.** The party leaves Guldove for the Isle of the Damned. Chapter 8 begins with the Isle approach.

**Design notes.** Chapter 7 is a "denouement" chapter — no new base, no major form-change, no major boss. Its job is to let the light-tech path mature, to resolve the Leena subplot, and to set up the Norris recruitment. The §3.13 main-cast focus is operational in the Leena scene: she is a *character*, and her subplot has emotional weight. The §3.4 basic attack line is operational in the light-tech encounters: Serge's basic attack is still Dash and Slash, and the light-tech augments ride on top of it.

### 12.11 Chapter 8 — The Hunter (Norris, + Yellow, full party)

**Setting.** The Isle of the Damned, the dragon-keeper's lair, the Sea of Eden approach. The chapter is the final-base recruitment and the full-party unlock.

**Active party.** Serge + Kidd + Nikki + Glenn + Herle + Norris. The party grows from 5 to 6 mid-chapter. The party is now *full*.

**Combat encounters.** 8–10 encounters on the Isle, plus the Norris recruitment fight (a duel against a Dragonian — a high-tier enemy that tests the party's ability to fight as a 6-character team). The duel is the design's test of the full-party mechanics: 6 characters on the field, 6 actions per turn, all six basic attacks working in concert.

**The Norris recruitment beat.** Norris is the dragon-keeper, defending the Isle against intruders. The party arrives, Norris fights them to a standstill, and then agrees to join after a 2-minute scene where he explains his motivation (he has been watching the Frozen Flame's influence for years, and he wants to see it ended). The recruitment is *not* a "you beat me, I join" — it is a "we both want the same thing, let's go together."

**Norris's basic attack line.** Sunshower is a precision shot; Top Shot is the ultimate (tier 8). Sunshower scales with accuracy and crit chance. The encounter design exploits this: Norris's basic attack is a *single-target high-damage shot*, which gives the party a sixth combat role. The six basic attacks form a hexagon: physical, thrown, performance, sword, magic, precision. Each is distinct in flavor and in encounter role.

**The full party (this chapter).** The party screen now shows all 6 characters, with their magic tier progression visible. The player has access to all 6 basic attack lines, all 6 support grids, and the full augmentation system. The combat encounters from this chapter onward are *designed for 6 characters* — the player is expected to use all 6.

**Magic tier system (this chapter).** Serge is at level 11, the other characters are at level 5–8. The level-based progression means: by chapter 8, the player has access to most of the magic tier system's content. The tier-8 ults are still locked — those unlock in chapter 9 as the story beats land.

**Chapter-end scene.** The party leaves the Isle for the Sea of Eden. Chapter 9 begins with the Sea of Eden approach.

**Design notes.** Chapter 8 is the final-base recruitment. The party is now full, the basic attacks form a hexagon, and the encounters are designed for 6 characters. The §3.13 main-cast focus is operational in Norris's scene: he is a *character*, not a stat block. The §3.4 basic attack line is operational in the recruitment duel: Norris's Sunshower is *his* basic attack, and the duel tests the player's ability to counter a precision-shot enemy with a 6-character party.

### 12.12 Chapter 9 — The Flame (Full party, Frozen Flame dungeon)

**Setting.** The Sea of Eden, the Chronosopolis, the Frozen Flame chamber. The chapter is the climax — the dungeon, the boss gauntlet, the resolution of the time paradox.

**Active party.** Serge + Kidd + Nikki + Glenn + Herle + Norris (6 characters, full party).

**Combat encounters.** 12+ encounters, including the boss gauntlet (4–5 sequential boss fights against FATE-orchestrated enemies, culminating in the final boss). The encounters are designed for 6 characters, with each boss exploiting a different basic attack line's weakness (so the player has to rotate characters).

**The Frozen Flame dungeon.** The dungeon is a 6-floor affair, with each floor themed to a different element (White floor, Red floor, Blue floor, Green floor, Black floor, Yellow floor — one per base). The floors are *designed* to test each base's basic attack line: the White floor has enemies weak to physical, the Red floor has enemies weak to thrown, etc. The player rotates the party's lead character to match the floor.

**The tier-8 unlocks.** As the party traverses the dungeon, the tier-8 ults unlock at scripted moments:
- Serge's Glide Hook unlocks at the White floor's end (a cutscene where Serge remembers his childhood).
- Kidd's Hotshot unlocks at the Red floor's end (a cutscene where Kid confronts the thief who taught her).
- Nikki's Limelight unlocks at the Blue floor's end (a cutscene where Nikki stages the show that she never got to stage in Guldove).
- Glenn's Sonic Sword unlocks at the Green floor's end (a cutscene where Glenn confronts the Dragoon who killed his sister).
- Herle's Lunairetic unlocks at the Black floor's end (a cutscene where Herle confronts the Magic Kingdom's leader who abandoned her).
- Norris's Top Shot unlocks at the Yellow floor's end (a cutscene where Norris confronts the dragon-keeper who raised him).

Each unlock is a 1-minute scene with a "you have grown" emotional beat. The §3.13 main-cast focus is operational in full: each base has a personal arc, and the arc's resolution is the tier-8 unlock.

**The final boss.** The final boss is a 6-on-6 fight against the "Time Devourer" — a FATE-orchestrated entity that uses all six elements. The fight is designed to require all six basic attack lines: the boss shifts elements every turn, and the player has to rotate characters to match. The fight has 3 phases, each harder than the last. The phase-3 victory triggers the time-paradox resolution cutscene.

**The time-paradox resolution.** The cutscene is the original's emotional climax: Serge confronts the Frozen Flame, the time-devourer is revealed as Schala, the party makes the choice to "save her" rather than "defeat her." The redesign's resolution is *not* a victory screen — it is a choice: the player can pick "let her go" (the original's bittersweet ending) or "bring her back" (a new ending where Schala returns to the present). Both endings are valid; both unlock the New Game+ mode.

**Chapter-end scene.** The party escapes the Frozen Flame as the dungeon collapses. The chapter ends with the party on the beach (the same beach from chapter 1, but in the "present day" timeline), looking at the sunrise.

**Design notes.** Chapter 9 is the longest chapter (about 6 hours of play) and the densest. It is the chapter that proves the redesign's combat works at the full-party scale: 6 characters, 6 basic attack lines, 6 ults, and 6 personal arcs all resolving in a single dungeon. The §3.13 main-cast focus is operational in full. The §3.4 basic attack line is operational in the boss gauntlet: each floor is themed to a different element, and the player rotates the lead character to match.

### 12.13 Chapter 10 — The Epilogue (Full party, denouement)

**Setting.** Guldove (return), the S.S. Zelbetta, the beach. The chapter is the wind-down — the story resolves, the party disbands, and the New Game+ mode unlocks.

**Active party.** Serge + Kidd + Nikki + Glenn + Herle + Norris (6 characters, but the chapter is mostly dialog and exploration, not combat).

**Combat encounters.** 0 random encounters. The chapter has 2–3 scripted fights (a "farewell duel" with each base, where the player fights the base one-on-one to test their skills), but no random encounters. The chapter is *narrative*, not combat.

**The epilogue scenes.** Each base has a 3–5 minute epilogue scene:
- Serge returns to the beach and meets Leena. The scene is the childhood-subplot resolution.
- Kidd returns to the orphanage and confronts the thief who raised her. The scene is the thief-past resolution.
- Nikki stages the show she always wanted to stage. The scene is the entertainer-past resolution.
- Glenn returns to the Dragoons and reconciles with the general. The scene is the warrior-past resolution.
- Herle returns to the Magic Kingdom and confronts the council. The scene is the magic-past resolution.
- Norris returns to the Isle of the Damned and releases the dragons. The scene is the hunter-past resolution.

Each epilogue scene is a 1-minute dialog with a "you have grown" beat. The scenes are *not* voiced (the redesign has placeholder audio per §2.4), but the dialog is the original's.

**The New Game+ unlock.** After the final epilogue scene, the player is given the choice: "Start New Game+" or "End." New Game+ preserves the level-based magic progression (the player keeps their levels and tier slots) but resets the story. The §3.7 Pip reframing means: the dark-tech and light-tech augments are preserved on Herle and Serge, so a New Game+ run starts with the full augmentation set.

**Chapter-end scene.** The party disbands. The screen fades to black. The credits roll. The "The End" splash appears.

**Design notes.** Chapter 10 is the shortest chapter after chapter 1 (about 1 hour of play). Its job is to let each base have a personal-resolution scene, to unlock New Game+, and to give the player a sense of completion. The §3.13 main-cast focus is operational in full: each base has an epilogue, and the player's time with the character is honored.

### 12.14 The Pacing as a Whole

The 10-chapter pacing, measured in approximate play time:

| Chapter | Approximate Play Time | New Base | Major Event |
|---|---|---|---|
| 1 | 30 min | Serge (Lynx form) | Prologue, drowning, form-change |
| 2 | 2 hours | Kidd | Recruitment, dark-tech choice |
| 3 | 2.5 hours | Nikki | Guldove arc, show staging |
| 4 | 5 hours | Glenn | Manor infiltration, form-change |
| 5 | 3 hours | — | Dragon trials, dark-tech consolidation |
| 6 | 4 hours | Herle | Dark Fort, form-return, dark-tech migration |
| 7 | 2 hours | — | Light-tech consolidation, Leena scene |
| 8 | 3 hours | Norris | Isle of the Damned, full-party unlock |
| 9 | 6 hours | — | Frozen Flame dungeon, final boss, time-paradox resolution |
| 10 | 1 hour | — | Epilogues, New Game+ unlock |
| **Total** | **~29 hours** | **6 bases** | — |

The total play time is approximately 29 hours, which is in the §2.6 "30-hour JRPG" target. The 5-hour chapter 4 and 6-hour chapter 9 are the longest, which is appropriate (they are the densest). The 30-minute chapter 1 and 1-hour chapter 10 are the shortest, which is also appropriate (they are the framing).

The pacing's design commitment: the player is never without a chapter event. The chapter-event density is at least one major event per chapter (recruitment, form-change, dungeon, or boss). The player is not "filling time" between events — the events *are* the play.

### 12.15 The Magic Progression Across Chapters

The level-based magic progression, mapped to chapters:

| Chapter | Average Party Level | Tier Slots Available (per character) |
|---|---|---|
| 1 | 1 | 1× tier-1 |
| 2 | 1–2 | 1× tier-1 |
| 3 | 2–3 | 1× tier-1 (most), 2× tier-1 (Lynx) |
| 4 | 3–5 | 2× tier-1 (most), 2× tier-1 + 1× tier-2 (Lynx) |
| 5 | 5–7 | 2× tier-1 + 1× tier-2 (most), 2× tier-1 + 1× tier-2 + 1× tier-3 (Lynx) |
| 6 | 6–8 | 2× tier-1 + 1× tier-2 + 1× tier-3 (most), 2× tier-1 + 1× tier-2 + 1× tier-3 + 1× tier-4 (Lynx) |
| 7 | 7–9 | Tier-3 to tier-4 (most), tier-4 to tier-5 (Lynx) |
| 8 | 8–10 | Tier-3 to tier-4 (most), tier-4 to tier-5 (Lynx), tier-1 (Norris) |
| 9 | 9–11 | Tier-4 to tier-5 (most), tier-5 to tier-6 (Lynx) |
| 10 | 10–12 | Tier-5 to tier-6 (most), tier-6+ (Lynx) |

The progression is *gradual*: the player gains tier slots as the characters level up, and the chapter-by-chapter level curve is designed to keep the player on the "gaining a new slot" feeling without overwhelming them. By chapter 9, the average party member has 4–5 tier slots open, which is the full set for most of the game. The tier-8 ults are unlocked by chapter progression, not by level, which is the §3.8 "tier 8 is a story reward" commitment.

### 12.16 The Supports Across Chapters

The 36 supports are recruited passively, in chapter order. The chapter-by-chapter support recruitment is not a player choice — it is a story event. The player sees the support in a 1-minute scene and the support joins the base's grid.

| Chapter | Base | Supports Recruited | Cumulative |
|---|---|---|---|
| 1 | Serge | (none) | 0 |
| 2 | Serge | Riddle, Steena | 2 |
| 3 | Serge | Doc, Leena+Poshul (combined) | 5 |
| 4 | Serge | Starky, Angelic Pip (form-locked) | 7 |
| 4 | Glenn | Karsh, Razzly | 9 |
| 5 | (dark-tech consolidation) | Radius, Van | 11 |
| 6 | Herle | Guile, Luccia, Mojo, Devil Pip (form-locked) | 15 |
| 6 | Glenn | Sprigg, Turnup+NeoFio (combined) | 18 |
| 7 | (light-tech consolidation) | Skelly, Grobyc | 20 |
| 7 | Kidd | Greco, Janice, Miki | 23 |
| 8 | Norris | Sneff, Leah, Mel, Zoah, Viper, Funguy | 29 |
| 8 | Nikki | Marcy, Korcha+Macha (combined), Fargo, Irene, Orhla, Pierre | 35 |
| 9 | (Frozen Flame) | (no new supports) | 35 |
| 10 | (epilogue) | (no new supports) | 35 |

(Note: the cumulative counts above include the Pip-form supports, which are not normal supports. The actual normal-support count is 33 standalone + 3 combined = 36, plus the 2 Pip-form entries. Total slots filled: 36 + 2 = 38, of which 36 are normal and 2 are Pip-form. The Pip-form slots are not part of the level-based magic progression — they are unlocked by story events.)

The supports are recruited in *story order*, not in player order. The player does not "choose" which support to recruit next — the story dictates. The support recruitment is a 1-minute scene with a dialog beat, and the support joins the base's grid as an augmentation.

### 12.17 The Form-Change Story Arc

The form-change is the redesign's narrative spine, and it deserves a dedicated subsection.

**The form-change events:**
- **Chapter 1 (prologue):** Serge drowns, is rescued, wakes in Lynx's body. The form-change is a *time-paradox event* — the original Serge who drowned is the one who became Lynx.
- **Chapter 4 (act-1 break):** The party reaches the beach where Serge drowned. The fever takes Lynx. He wakes in his own body. The form-change is *reversed*.
- **Chapter 6 (act-2 break):** The party reaches the Frozen Flame chamber. The form-change is *re-reversed*: Serge is in his own body, and the Lynx-body Serge becomes the antagonist (the "Dark Serge" boss).
- **Chapter 9 (climax):** The party defeats the Dark Serge. The form-change is *resolved*: Serge and Lynx are reconciled, and the player has access to both Serge's light techs and Herle's dark techs (via the §3.7 migration).

**The form-change story arc in the redesign's compressed timeline:**
- Prologue: Serge becomes Lynx (the form-change is the *cause* of the adventure).
- Act 1: Lynx is the protagonist (chapters 2–4).
- Act 2: Serge is the protagonist, Herle inherits the dark techs (chapters 6–8).
- Climax: The form-change is resolved, the protagonist is fully himself (chapter 9).

The form-change story arc is the redesign's main narrative contribution. The original's form-change is a plot twist; the redesign's form-change is a *character arc*. The player watches Serge/Lynx grow from a confused victim (ch. 1) to a decisive leader (ch. 9), and the form-change is the mechanism of that growth.

### 12.18 What the Walkthrough Proves

The walkthrough is the design's stress test. If the 10 chapters hold together as a 30-hour JRPG, the redesign works. If they fall apart (too short, too long, too many subplots, too few), the redesign needs adjustment.

**Things the walkthrough proves:**
- The 6-base structure is sufficient for 10 chapters. Each base has a personal arc that resolves across multiple chapters.
- The form-change story beat lands at chapter 4 (act-1 break) and chapter 6 (act-2 break), which is the right pacing for a 30-hour JRPG.
- The level-based magic progression gives the player meaningful growth at every chapter. The player is never "stuck" with the same tier slots for more than 2 chapters.
- The 36 supports are recruited in story order, and the recruitment is a 1-minute scene per support. The supports do not crowd the main plot.
- The basic attack line + augmentation model works in combat. The encounter design exploits the differences between the 6 basic attacks.
- The minigame removal (§3.12) is consistent with the redesign. The casino, the racing minigame, the cooking minigame — none are needed for the redesign's 30-hour experience.
- The single-loop story structure (§3.13) is consistent with the redesign. The player does not need to play the game twice; the major story beats all happen in one playthrough.

**Things the walkthrough does not prove (and that future loops need to address):**
- The exact support-tech effects (per-support, per-tier augmentations). The walkthrough uses "Dash and Slash with Sleep at 30% chance" as an example, but the actual ~60 fixed tech effects need to be designed.
- The exact dialog for each recruitment scene. The walkthrough uses placeholder dialog ("You fight okay. I'm Kidd. You're coming with me."), but the actual scenes need to be written.
- The exact layout of each dungeon. The walkthrough mentions the Manor's halls, the Dark Fort's corridors, the Frozen Flame's 6 floors, but the actual room-by-room design is not specified.
- The exact boss mechanics. The walkthrough mentions the dragon trials, the Dark Serge fight, the Time Devourer, but the actual boss patterns are not specified.

These are implementation-phase concerns, not design-phase concerns. The walkthrough proves the design holds together; the implementation phase fills in the details.

### 12.19 Decisions Needed

The walkthrough commits to several design choices that the user may want to revisit:

- **The chapter-to-base join order.** §3.9 commits to Serge→Kidd→Nikki→Glenn→(form)→Herle→Norris, and the walkthrough instantiates this order. The user has already confirmed this order in the resolved review. No new decision needed unless the user wants to reorder.
- **The form-change chapter boundary.** The walkthrough commits to the form-change at chapter 4 (act-1 break) and the form-return at chapter 6 (act-2 break). The user may want different pacing (e.g., form-change at chapter 5 and form-return at chapter 7). Not blocking.
- **The Norris recruitment chapter.** The walkthrough commits to Norris joining in chapter 8 (act-3 break). The user may want Norris to join earlier (e.g., chapter 5) to fill the dark-tech arc. Not blocking.
- **The level-by-chapter pacing.** The walkthrough commits to a gradual level curve (party average level 1 in ch. 1, level 10–12 in ch. 10). The user may want a faster or slower curve. Not blocking.
- **The epilogue's New Game+ choice.** The walkthrough commits to two endings ("let her go" / "bring her back"). The user may want a single ending. Not blocking.

These decisions are not blocking the document's continuation. §13 (Risks & Open Questions) is unblocked and can be drafted next. §13 will list the project's risks, the open questions that the redesign does not answer, and the decisions that future loops may need to revisit.

---

---

## 13. Risks, Open Questions, and Failure Modes

This section enumerates the risks the project has accepted, the open questions the design does not yet answer, and the failure modes the team (agent and user) is committing to handle. The purpose is not to predict the future. The purpose is to make the unknowns *legible* so that, when a future loop hits one, the response is rehearsed rather than improvised.

The document so far has been optimistic — committing to design choices, locking in toolchains, instantiating walkthroughs. This section is the corrective. Every project of this scope has failure modes that the design cannot anticipate. The discipline is to name them now, attach a mitigation to each, and review the list at every phase transition. The list is not exhaustive. New risks will be added as they are discovered; the list grows over the project's life, never shrinks.

The structure is three sub-sections, each addressing a different category of unknown. **13.1 — Risks** names the things that could go wrong during execution. **13.2 — Open Questions** names the things the design has not yet committed to. **13.3 — Failure Modes** names the systemic ways the project could fail to deliver. The three categories are not independent — a risk can become an open question, and an open question can become a failure mode — but the distinction is useful: risks are *known threats with mitigations*, open questions are *known unknowns awaiting decisions*, and failure modes are *systemic patterns the project must avoid*.

A note on framing. The risk list is not "things that will probably go wrong." It is "things that *could* go wrong, and the cost if they do." A 5% risk of a 6-month setback is a more serious risk than a 50% risk of a 1-day setback. The list is prioritized by expected cost, not by probability. The high-probability/low-cost risks are the bottom of the list; the low-probability/high-cost risks are the top.

### 13.1 Risks

The risks are organized by category. Each risk has a one-line description, a "what this looks like in practice" example, a probability estimate (low/medium/high), a cost estimate (low/medium/high — measured in calendar days of agent work), and a mitigation that the project will execute. The probability and cost estimates are honest guesses, not commitments. Future loops should re-estimate as the project matures.

**R-1: PS1 asset format incompatibility.** *Description:* the format parsers written for the §8.3 extractors fail on edge cases not covered by the format documentation. *Example:* a TIM file with a non-standard CLUT (color lookup table) crashes the extractor; the agent has to write a format-specific workaround. *Probability:* medium. *Cost:* medium (1–5 days of debugging per incompatibility). *Mitigation:* the §11.4 toolchain commits to Python parsers with explicit format documentation in their docstrings; the agent logs every format edge case to `assets/EXTRACTION_NOTES.md`; edge cases that cannot be handled are flagged for the user. The §10.4 format-archaeology list is the format inventory; edge cases outside the list are an R-1 hit.

**R-2: Source material unavailability.** *Description:* the source material (Chrono Cross disc, the wikis, the YouTube playthroughs, the script dumps) becomes unavailable partway through the project. *Example:* a wiki page is taken down; an emulator stops building on the current platform. *Probability:* low (the source material is widely archived). *Cost:* high (the agent would have to find or recreate the source). *Mitigation:* the §8.2 MANIFEST-based content addressing means every fetched source is logged with its URL/hash; the agent maintains a local copy of all source material in `sources/` (with the personal-use license gate); the §10.6 multi-emulator research gives the agent DuckStation as the default but with PCSX-Reborn and mednafen as fallbacks. If a source is lost, the local copy is the backup; if the local copy is lost, the MANIFEST hash is the breadcrumb to refetch.

**R-3: Godot 4.3 bug or breaking change.** *Description:* Godot 4.3 has a bug that affects the project, or Godot 4.4/4.5 introduces a breaking change that the project has to adapt to. *Example:* a renderer bug that crashes the HD-2D pipeline; a GDScript change that breaks the §6.4 typed-subset conventions. *Probability:* low (Godot 4.3 is a stable release, and the project is pinned to it per §6.2). *Cost:* medium (1–10 days depending on the bug's scope). *Mitigation:* the §11.6 vendoring plan pins the exact Godot binary; the §6.11 known-gotchas list is the project-specific bug reference; the §8.6 visual regression tests catch renderer bugs early. If a Godot bug is found, the agent files an upstream issue and works around it locally; if a Godot breaking change happens, the agent re-evaluates the version pin per the §6.2 versioning policy.

**R-4: Scope creep.** *Description:* the project grows beyond the 30-hour, 10-chapter, 6-base commitment. *Example:* the user asks for a 50-hour expansion; the agent decides to add a fourth tier-8 ult per base; the §3.13 main-cast focus is expanded to 10 characters. *Probability:* medium (design projects naturally expand). *Cost:* high (a 50-hour project takes ~17 months at the loop's 10–20 minutes per section pace). *Mitigation:* the §2.6 "30-hour JRPG" target is the project's primary goal; the §3.16 locked-design summary is the size budget; the §2.7 explicit non-goals are the anti-scope list. If the user asks for an expansion, the agent says "the design commits to 30 hours and 6 bases; expansion requires a §3 amendment, which I can draft but not implement." The §9.5 design-gate protocol is the enforcement mechanism.

**R-5: AI-agent reliability drift.** *Description:* the agent's outputs degrade in quality over the project's life, either through model degradation, prompt drift, or context-window exhaustion. *Example:* the agent starts producing stubs instead of full sections; the agent forgets the locked design; the agent re-derives decisions that were already locked. *Probability:* low to medium (depends on the model's stability). *Cost:* high (corrupted state requires manual repair). *Mitigation:* the §9.12 long-running-project discipline is the primary defense — the agent optimizes for the 100th loop, not the 1st; the §9.4 TDD loop catches errors early; the §9.10 anti-patterns list is the failure-mode list for the agent itself; the §9.7 memory file protocol makes the agent's reasoning legible to a future human or agent reviewer. If drift is detected, the agent pauses, reads the §9.10 anti-patterns, and corrects.

**R-6: User availability.** *Description:* the user becomes unavailable for an extended period (weeks to months), leaving the agent to make decisions that would normally be gates. *Example:* the user goes on vacation; the user is occupied with a different project; the user is unresponsive to `review.md` items. *Probability:* medium (user attention is finite). *Cost:* medium (decisions accumulate in `review.md`, slowing Phase 1/2 progression). *Mitigation:* the §9.5 design-gate protocol commits to "ask only when the answer is in the locked design, working assumption when reversible, gate when not recoverable" — the agent makes working assumptions freely, gates only when truly necessary, and never blocks on user input. The §2.6 definition of "Phase 1 done" is the project's milestone; the agent can iterate on Phase 1 indefinitely without the user. The §3.16 locked design is the contract; the agent does not need the user to confirm every decision.

**R-7: Community/legal objection.** *Description:* the project's fan-work posture provokes a takedown request, a community objection, or a legal challenge. *Example:* a rights-holder objects to the project; a community member claims the project is "stealing" original work. *Probability:* low (the §1.6 clean-room posture and §10.7 legal posture are well-defined). *Cost:* high (a takedown would force the project to be private or discontinued). *Mitigation:* the §10.7 legal posture is conservative — no original code, no original assets, original interpretation of design, attribution for any fan art; the project is private by default (not published to a public repo); the §1.6 autonomy model frames the project as skill development, not commercial. If a challenge arises, the agent pauses, escalates to the user, and follows the user's legal guidance.

**R-8: Performance regression at scale.** *Description:* the §6.9 HD-2D rendering pipeline or the §7.10 combat engine performs poorly at the §3.16 full-party scale (6 characters + 6 supports + 6 enemies = 18 animated sprites, 5-layer parallax, screen-space shaders). *Example:* the frame rate drops below 30 FPS on the §11.10 workstation baseline; the memory usage exceeds 4 GB. *Probability:* medium (HD-2D is a known-performant style, but the §7.9 layer count is high). *Cost:* medium (1–10 days of optimization). *Mitigation:* the §6.7 deterministic combat means performance is benchmarkable; the §8.6 visual regression tests catch frame-rate regressions; the §6.11 known-gotchas list includes specific Godot 4.3 performance notes; the §7.9 HD-2D rendering stack is designed with explicit LOD (level of detail) hooks (e.g., parallax layers can be culled when off-screen). If a regression is found, the agent profiles with Godot's built-in profiler and optimizes the hot path.

**R-9: Design coherence loss.** *Description:* the project's design commitments drift apart from each other as new sections are added. *Example:* a §14 success criterion contradicts a §3 design choice; a §11 toolchain assumption contradicts a §6 Godot 4 architecture. *Probability:* medium (large documents naturally drift). *Cost:* low to medium (caught by review, but requires rework). *Mitigation:* the §9.4 TDD loop catches code-level drift; the §9.6 review file protocol is the design-level drift detector; the §1.5 design principles are the coherence check — every new section should be testable against them. The agent reviews prior sections when drafting new ones (the §9.1 working set read includes the design document). If a contradiction is found, the agent flags it in `review.md` and proposes a resolution.

**R-10: Save-game compatibility break.** *Description:* a Phase 3 design change makes Phase 1 save games incompatible, breaking the user experience. *Example:* the form-change state machine's data model changes between Phase 1 and Phase 3, invalidating old saves. *Probability:* medium (design changes are expected; some will touch the save model). *Cost:* low (the §7.11 migration layer is designed to handle this) to medium (if a migration is not feasible). *Mitigation:* the §7.11 SaveSystem's `schema_version` field and `MigrationRegistry` are the explicit mechanism for handling save evolution; the §8.6 integration tests include a "Phase 1 save game loads in Phase 3 build" test; the agent maintains a set of representative save games at `tests/saves/` for regression. If a breaking change is unavoidable, the agent writes a migration script and tests it on the saved games.

**R-11: Walkthrough incoherence.** *Description:* the §12 walkthrough does not actually fit the §3 design commitments when implemented. *Example:* the chapter pacing is too tight; the supports crowd the main plot; the magic progression does not match the level curve. *Probability:* medium (the walkthrough is a *design stress test*, not a verified implementation). *Cost:* medium to high (the walkthrough is the design's narrative instantiation; if it fails, the design has to change). *Mitigation:* the §12.18 "what the walkthrough proves" subsection is the honest assessment — the walkthrough proves the *design holds together*, not that every scene works. When the implementation phase begins, the agent will discover specific incoherences and resolve them via working assumptions (escalating only when the resolution is not in the locked design). The §9.5 design-gate protocol handles escalations.

**R-12: Toolchain breakage.** *Description:* a tool in the §11 toolchain breaks or is deprecated. *Example:* `uv` releases a breaking change; `pandoc` is no longer maintained; `DuckStation` stops building on Windows. *Probability:* low (most tools are stable). *Cost:* low to medium. *Mitigation:* the §11.6 version pinning is the primary defense; the §11.7 CI is the early-warning system; the §11.10 setup script is the rebuild procedure. The agent commits to specific versions in `tools/VERSIONS.md`; breaking changes are absorbed by version bumps, not by tool substitution.

**R-13: Recruit-by-element system confusion.** *Description:* the §3.10 "recruit by element" system (where a character's element determines which supports they can recruit) is confusing to players, undermining the §3.13 main-cast focus commitment. *Example:* the player recruits the wrong support because the element system is opaque. *Probability:* low to medium (the system is novel; the original's system was also confusing). *Cost:* low (the system is information, not mechanic — the cost is a frustrating player experience, not a broken game). *Mitigation:* the §3.10 commitment is documented with examples in §12.3 (the six recruitment beats); the in-game UI surfaces the element-system in the recruitment dialog ("Your element is White. Serge is the White base. You can recruit Riddle, Steena, Doc, Leena+Poshul, Starky, or Angelic Pip."); the §14 success criteria includes "the element system is comprehensible to a first-time player." If confusion is reported, the agent adjusts the UI copy, not the design.

**R-14: Documentation rot.** *Description:* the design document becomes out of date as the project evolves, reducing its value as a reference. *Example:* a §7 subsystem is implemented differently from the spec; a §12 walkthrough scene is rewritten without updating the document. *Probability:* medium (large documents rot). *Cost:* low (the document is reference, not source). *Mitigation:* the §9.6 review file protocol commits to "when a design decision changes, update the design document in the same loop"; the §9.7 memory file protocol commits to recording the rationale; the agent periodically (at phase transitions) re-reads the full design document to catch drift. If rot is detected, the agent opens a "documentation cleanup" loop and brings the document back in line.

The 14 risks above are the project's known threats. Each is named, costed, and mitigated. The list is not exhaustive — new risks will be added as the project executes. The discipline is to *catch* a new risk, *name* it, and *attach* a mitigation. A risk without a mitigation is a worry; a risk with a mitigation is a known threat that the project can plan around.

### 13.2 Open Questions

Open questions are the design decisions the document has not yet committed to. They are different from risks: a risk is "this could go wrong"; an open question is "we have not yet decided this." Open questions are not failures — they are honest acknowledgments that the design is incomplete. The list below is the questions that the §1–§12 design has flagged but not answered. Each has a context (why it matters), a current working assumption (what the agent will do if the question is never answered), and a proposed resolution path (what would need to happen to commit).

**Q-1: How much of the original Chrono Cross dialog is preserved?** *Context:* the §3.13 main-cast focus commitment includes "expanded interaction scenes," but the scope of the original dialog preservation is not specified. *Working assumption:* the original's main-plot dialog is preserved verbatim; the support-cast interaction scenes are new (replacing the original's "silent recruitment"); the optional NPC chatter is omitted. *Resolution path:* the §8.4 translation stage's per-character scripts decide this per character; a future loop could produce a `data/dialog_preservation_policy.md` if the user wants explicit scope.

**Q-2: What is the exact support-tech effects catalog?** *Context:* the §3.5 augmentation model uses "Dash and Slash with Sleep at 30% chance" as an example, but the actual ~60 fixed tech effects need to be designed. *Working assumption:* the §8.4 per-character translation scripts are the design surface; each script defines its character's tech effects as data. *Resolution path:* the implementation phase will produce the catalog as a side effect; the agent does not need to commit to specific effects in this design phase.

**Q-3: How is the form-change's mid-game state preserved across saves?** *Context:* the §3.7 Pip reframing and the §7.6 form-change state machine interact with the §7.11 save system. The save must record the form-change history so that a player who saves in Serge form, becomes Lynx, saves again, and loads the first save does not lose continuity. *Working assumption:* the §7.6 migration log is part of the save data; loading a save restores the log, and the form-change state machine reads the log to determine the current state. *Resolution path:* the implementation phase will define the exact log format; the §8.6 integration tests will verify save/load cycles.

**Q-4: What is the New Game+ content?** *Context:* §12.13 commits to a New Game+ mode that preserves level-based progression and unlocked techs. The question is: what *new* content does the New Game+ offer? *Working assumption:* the New Game+ offers the same 10 chapters with the same enemies, but with the player's preserved levels (so the player can experiment with different support configurations); the "bring her back" ending unlocks a 15-minute epilogue scene unique to New Game+. *Resolution path:* the user will decide if the redesign wants more New Game+ content; a future loop can draft a §12.20 New Game+ expansion if the user requests it.

**Q-5: How is the recruit-by-element system surfaced in the UI?** *Context:* the §3.10 recruitment system and the §12.3 recruitment beats commit to a specific UI: when the player meets a potential support, the dialog includes a line explaining the element system. *Working assumption:* the dialog is "Your element is X. You can recruit [list]." A new line is added for each support, generated from the `data/recruitment_pool.json` data. *Resolution path:* the implementation phase will produce the UI; the §14 success criteria includes "the element system is comprehensible to a first-time player" as a testable success criterion.

**Q-6: What is the level-by-chapter pacing in detail?** *Context:* the §12.15 table shows a gradual level curve, but the curve's specific shape (linear, exponential, front-loaded, back-loaded) is not committed. *Working assumption:* the curve is linear, with the party averaging 1.5 levels per chapter. *Resolution path:* the implementation phase will tune the curve via playtesting; the §8.6 integration tests will verify level-up events trigger correctly.

**Q-7: What is the boss mechanic for the chapter-9 Time Devourer?** *Context:* the §12.12 walkthrough describes the Time Devourer as a 6-on-6 fight with 3 phases, but the specific mechanics are not designed. *Working assumption:* the boss uses all 6 elements and shifts element every turn; the player has to rotate the lead character to match. *Resolution path:* the implementation phase will design the boss; the §14 success criteria includes "the final boss requires all 6 basic attack lines to defeat."

**Q-8: How are the supports "balanced"?** *Context:* the §3.5 augmentation model says supports are augmentations, not replacements. The question is: how is the augmentation power balanced across supports? *Working assumption:* the §8.4 per-character scripts define the augmentation effects; the §14 success criteria includes "no single support dominates the meta." *Resolution path:* the implementation phase will balance via playtesting; the §8.6 integration tests will verify that augmentations are within a defined power band.

**Q-9: How is the music handled?** *Context:* the original Chrono Cross has a famous soundtrack by Yasunori Mitsuda. The redesign's §2.4 "placeholder audio" commitment says the redesign uses placeholder music for the proof-of-concept. *Working assumption:* Phase 1 and Phase 2 use placeholder music; Phase 3 may or may not license the original music (a separate decision). *Resolution path:* the user will decide if the project will attempt to use the original music (with the §10.7 legal constraints) or use a new soundtrack.

**Q-10: How are the §3.13 "expanded interaction scenes" written?** *Context:* the §3.13 commitment to expanded interaction scenes for the 6 main characters + their supporting cast is not detailed. *Working assumption:* each base has 3–5 expanded scenes (5–10 minutes total) with their closest supports; the scenes are unlocked at specific chapter events. *Resolution path:* the §12.3 recruitment beats and §12.16 support recruitment table provide the chapter-by-chapter scene triggers; the implementation phase will write the actual dialog.

**Q-11: What is the exact end-game content?** *Context:* the §12.13 walkthrough commits to two endings ("let her go" / "bring her back") and a New Game+ mode. The "bring her back" ending is new content. *Working assumption:* the "bring her back" ending is a 15-minute epilogue scene where Schala returns to the present; the New Game+ preserves level and tech state. *Resolution path:* the user will decide if the redesign wants more new content; a future loop can draft additional end-game content if requested.

**Q-12: How is the difficulty curve across chapters?** *Context:* the §3.4 basic attack line and §3.8 magic tier system together define a difficulty curve. The curve is not yet specified. *Working assumption:* the curve is gradual, with the chapter-4 and chapter-6 bosses as the difficulty spikes. *Resolution path:* the implementation phase will tune the curve via playtesting; the §14 success criteria includes "the player is challenged at every chapter but not frustrated."

The 12 open questions are the design's known unknowns. They are not failures — they are honest acknowledgments that the design is incomplete. The discipline is to *flag* a new open question, *attach* a working assumption, and *commit* to a resolution path. A question without a working assumption is a blocker; a question with a working assumption is a known unknown that the project can move past.

### 13.3 Failure Modes

Failure modes are the systemic ways the project could fail to deliver. Unlike risks (specific threats) and open questions (specific unknowns), failure modes are *patterns* — ways of working that, if left unchecked, would cause the project to fail even if every individual risk is mitigated. The list below is the project's defense against the failure patterns that the agent's prior projects have shown.

**F-1: Stubs instead of substance.** *Pattern:* the agent writes sections that *look* complete but actually contain placeholders ("[design TBD]") and shortcuts. *Failure:* the document appears done but is hollow; the implementation phase has to redesign every section. *Defense:* the §9.4 TDD loop's commitment to "tests as the definition of done" — if a section has no testable claim, it is a stub. The §9.10 anti-pattern "writing stubs that promise future content" is the explicit prohibition. The §1.5 "no magic" principle is the philosophical underpinning: every claim in the document must be backed by a concrete design choice or flagged as an open question.

**F-2: Design drift across sections.** *Pattern:* later sections contradict earlier sections because the agent does not re-read the design before drafting. *Failure:* the document is internally inconsistent; the implementation phase has to reconcile. *Defense:* the §9.1 working-set read order (state, then design doc, then skills) is the primary defense; the §1.5 design principles are the coherence check; the §9.4 TDD loop catches design-level inconsistencies via integration tests.

**F-3: Decision fatigue.** *Pattern:* the agent asks the user for input on every minor decision, overwhelming the user. *Failure:* the user disengages from the project; the agent blocks on user input. *Defense:* the §9.5 design-gate protocol commits to "ask only when the answer is in the locked design, working assumption when reversible, gate when not recoverable." The §9.10 anti-pattern "asking when the answer is in the locked design" is the explicit prohibition. The §1.6 autonomy model is the philosophical underpinning: the agent is "mostly autonomous with design gates," not "constantly checking in."

**F-4: Review file bloat.** *Pattern:* `review.md` grows to hundreds of items, becoming un-reviewable. *Failure:* the user stops reading the review file; the agent's decisions go un-reviewed. *Defense:* the §9.6 review file protocol commits to "5–15 active items" and to "every item has a context, options, and a resolution path." The §9.10 anti-pattern "bloating review.md" is the explicit prohibition. The §2.3 definition of "done" includes a review-process quality bar.

**F-5: Loop fatigue.** *Pattern:* the loop's pace slows as the project matures, with each loop producing less forward progress. *Failure:* the project stalls. *Defense:* the §9.12 long-running-project discipline is the primary defense — the agent optimizes for the 100th loop, not the 1st. The §9.8 iteration cycle commits to 10–20 minutes per typical draft loop; if a loop exceeds 30 minutes, the agent should split the work. The §2.3 definition of "done" is the project's milestone, and the project is "done" at the milestone, not when the document is "complete."

**F-6: Design perfectionism.** *Pattern:* the agent keeps revising sections instead of moving forward, trying to reach a perfect design. *Failure:* the document never converges; the implementation phase never starts. *Defense:* the §2.3 "definitions of done" is the convergence target — the document is "done" when it meets the §2.3 quality bar, not when it is perfect. The §3.16 locked-design summary is the design's convergence point; the agent commits to the locked design and stops re-deriving it. The §1.5 "ship" principle is the philosophical underpinning: a shipped design that is good is better than an unshipped design that is perfect.

**F-7: Implementation-phase paralysis.** *Pattern:* the agent cannot start the implementation phase because "the design is not ready." *Failure:* the design document grows indefinitely without any actual game being built. *Defense:* the §2.3 "Project done" definition is "Phase 1 faithfully remastered and runnable in Godot 4" — the project is done when the game runs, not when the design is complete. The §8 pipeline + §11 toolchain is the implementation surface; the design document is the design surface, but the implementation does not wait for the design to be perfect. The §1.5 "ship" principle is the philosophical underpinning.

**F-8: User disengagement.** *Pattern:* the user stops responding to `review.md` items and loop summaries. *Failure:* the agent makes decisions without user input, drifting from the user's intent. *Defense:* the §9.6 review file protocol keeps the review file scannable; the §9.7 memory file protocol keeps the loop summary concise; the §9.5 design-gate protocol limits the number of items the user has to weigh in on. The agent's loop summary is the user's daily review touchpoint — if the user disengages, the agent should still produce the summary, and the user can re-engage at any phase transition.

**F-9: Toolchain rot.** *Pattern:* the §11 toolchain falls behind upstream changes, becoming incompatible. *Failure:* the agent cannot run the pipeline; the project stalls. *Defense:* the §11.6 version pinning is the primary defense; the §11.7 CI is the early-warning system. The agent commits to specific versions in `tools/VERSIONS.md`; breaking changes are absorbed by version bumps.

**F-10: Source rot.** *Pattern:* the §10 source material (PS1 disc dumps, wikis, YouTube playthroughs) becomes unavailable. *Failure:* the agent cannot verify design choices against the source. *Defense:* the §8.2 MANIFEST-based content addressing means every fetched source is logged; the §10.7 personal-use license gate keeps a local copy in `sources/`. The §10.6 multi-emulator research gives the agent multiple fallbacks for PS1 emulation.

The 10 failure modes are the systemic patterns the project must avoid. They are not specific threats — they are *meta-threats*, ways of working that would cause the project to fail even if every individual risk is mitigated. The discipline is to *recognize* a failure mode when it starts, *name* it explicitly in the loop memory, and *correct* course. A failure mode that is not named is invisible; a failure mode that is named is a bug to fix.

### 13.4 The Risk Register

The risk register is the consolidated view of risks (13.1), open questions (13.2), and failure modes (13.3). The agent maintains this register in `RISKS.md` (separate from `loop_memory.md` and `review.md`) and updates it at every phase transition. The register's purpose is to make the project's unknowns *legible* to the user and to the agent itself.

The register's format is:

```
# Risk Register

## Active Risks
- [R-N] <description> | Probability: <L/M/H> | Cost: <L/M/H> | Mitigation: <description> | Status: <open/mitigated/closed>

## Open Questions
- [Q-N] <description> | Working Assumption: <description> | Resolution Path: <description>

## Failure Modes (Defended)
- [F-N] <description> | Defense: <description>
```

The register is updated at every phase transition. Risks that are mitigated are marked `mitigated`; risks that turn out to be non-issues are marked `closed`. Open questions that are resolved are moved to the "Resolved" section. Failure modes are static — once defended, they remain defended.

### 13.5 The Risk Review Protocol

The risk register is reviewed at every phase transition (Phase 1 → Phase 2 → Phase 3) and at every 30-day milestone. The review is performed by the agent (the user is not expected to read the register unless they want to). The review's output is a one-page summary added to the loop memory: "Phase N — Risks: <open/mitigated/closed counts>. Open Questions: <count>. Failure Modes Defended: <count>. New risks identified: <list>."

The review is *not* a redesign. It is a check that the project's risk posture is still aligned with reality. If a new risk is identified, the agent adds it to the register and proposes a mitigation. If an open question has been resolved, the agent marks it resolved. If a failure mode has been observed, the agent names it and corrects.

### 13.6 The Long-Tail Risk

The long-tail risk is the project's existential risk — the things that could cause the project to fail in year 2 or year 3, not in the next loop. The long-tail risks are *not* in the risk register (the register is for near-term risks). The long-tail risks are philosophical, not operational.

The long-tail risks include:

- **The project outlasts the agent's context window.** The agent's effective context is finite; the project may grow beyond what the agent can hold in mind. The §9.7 memory file protocol is the mitigation: the memory file is the agent's external memory, and the agent re-reads it at every loop start.
- **The project outlasts the user's interest.** The user's attention is finite; the project may outlast the user's willingness to engage. The §9.8 iteration cycle commits to "10–20 minutes per loop" — the project is sustainable at any pace the user wants, including "the user does not engage for months at a time."
- **The project outlasts the original game's relevance.** Chrono Cross is a 1999 game; the cultural context may shift. The §10.7 legal posture is conservative — the project is private, not public — so the project's relevance to the broader world is not a primary concern.
- **The project outlasts the technology stack.** Godot 4.3 may be deprecated by 2030. The §6.2 versioning policy commits to "pinned to a stable LTS-equivalent version"; the §11.6 vendoring plan means the project does not depend on external infrastructure; the project can be migrated to a newer Godot version if necessary.

The long-tail risks are not in the register because they are not actionable. They are philosophical framings of the project's finite life. The project is a 2-year effort, not a 10-year effort. The agent commits to making the project *work* in that timeframe, not to making it *last* forever.

### 13.7 Decisions Needed

This section does not commit any new design decisions; it surfaces the open questions and risks that the user may want to weigh in on. The full list is in §13.1 (risks), §13.2 (open questions), and `review.md`. The most important questions, in priority order, are:

- **The element-system UI surfacing (Q-5).** The §3.10 recruit-by-element system is the most novel commitment in the redesign. The user may want a different UI than the §13.2 working assumption ("Your element is X. You can recruit [list]."). This is the highest-priority open question because it affects player comprehension.
- **The "bring her back" ending (Q-11).** The §12.13 commitment to two endings is new content, not original. The user may want a single ending (faithful to original) or two endings (Phase 3 modification). This is the second-highest because it is the redesign's main new content.
- **The music handling (Q-9).** The §13.2 working assumption is "placeholder music for proof-of-concept." The user may want to license the original music (with the §10.7 legal constraints) or commission a new soundtrack. This is the third-highest because it affects the project's cultural footprint.
- **The level-by-chapter pacing (Q-6).** The §12.15 curve is a working assumption. The user may want a faster or slower curve. This is the fourth-highest because it affects player feel.

These four questions are not blocking the document's continuation. The agent will continue with §14 (Success Criteria) and §15 (Proof of Concept) using the working assumptions, and the user can revisit the questions at any phase transition.

---

## 14. Success Criteria

This section specifies what the project must achieve at each phase boundary, and at each phase's intermediate checkpoints, to count as "done." Success criteria are the testable claims that turn the design document from aspiration into contract. Every criterion below is something an external observer can verify — by running the game, by inspecting the data, by reading the audit log, or by replaying a deterministic test. The §1.5 "no magic" principle applied to project completion: a section that does not produce a verifiable result is not a section, it is a wish.

The success criteria split along three axes. First, by phase: Phase 1, Phase 2, and Phase 3 each have their own completion conditions, because a Phase 1 success is not a Phase 3 success (the bar rises). Second, by audience: player-facing criteria (does the game feel right?) and agent-facing criteria (does the system run reproducibly?) are not the same criteria, even when they overlap. Third, by domain: combat, story, art, audio, performance, mod support, and determinism each have their own quality bar, because a game that is excellent in combat but unplayable in art is not a success. The three axes are independent and the criteria below are organized accordingly.

### 14.1 What Success Criteria Are For

A success criterion is not a wish, not a goal, and not a direction. A success criterion is a measurable claim with a verification method. "Combat is fun" is a goal. "A first-time player completes chapter 1 in 90 minutes and chooses to start chapter 2" is a success criterion, because the second part is observable. The bar for the document is that every success criterion below is observable — by the user, by the agent, by a third-party reviewer, or by an automated test.

The success criteria are also the answer to a question the document has been building toward since §1: *how do we know when the project is done?* §1.6 set the autonomy model (mostly autonomous with design gates). §2.3 set the three definitions of "done" (document, phase, project). §14 commits those definitions to specific, verifiable tests. A future maintainer — human or agent — who wants to know "is the project done?" reads §14 and runs the tests. A future maintainer who wants to know "is this specific subsystem done?" reads the relevant subsection of §14 (e.g., 14.5 for combat, 14.5 for mod support).

The success criteria are not static. They are reviewed at every phase transition (§13.5 risk review protocol) and revised if the project learns something that invalidates a criterion. The §9.5 design-gate protocol applies here: if a success criterion turns out to be wrong (e.g., the player-completion-time claim is impossible to verify in practice), the agent revises the criterion, not the project. Revisions are logged in `RISKS.md` and surfaced in the next loop summary. A success criterion that the agent has quietly abandoned is a §13.3 F-2 design-drift failure mode.

### 14.2 Phase 1 Success Criteria — Faithful Remaster

Phase 1 is the most concrete of the three phases, because the success criteria are anchored to a known reference: the original Chrono Cross. A Phase 1 success criterion is either "matches the original on this dimension" or "is a deliberate, documented modernization that preserves the player's experience." The Phase 1 bar is *recognizability*: a player who has played the original should be able to play the remaster and say "this is the same game, but it looks better and runs at 60 FPS."

The Phase 1 criteria, in priority order:

**P1-1: The game runs from a clean clone of the repository.** A new contributor (human or agent) clones the repo, runs `tools/setup.sh`, runs the pipeline, and gets a runnable Godot 4 project. The contributor does not need to read the design document; the `tools/setup.sh` script and the `README.md` are sufficient. The runnable project opens to the title screen, plays the intro, and saves/loads successfully. This is the §2.3 "project done" definition instantiated.

**P1-2: Every chapter from the original is reachable in the remaster.** The 10-chapter structure (§12) covers the original's 20+ year chronology in a single central loop, but every named event from the original appears in some chapter. A player who has played the original should not encounter a "where is this scene?" moment. The verification is a coverage matrix in `data/coverage_matrix.json` mapping original scenes to remaster chapters; a coverage audit script (`tools/audit_coverage.py`) compares the matrix against the original's scene list and reports any missing items. The audit is part of the §8.6 content-accuracy test battery.

**P1-3: The 6 main characters from the redesign are playable.** Serge/Lynx, Kidd, Nikki, Glenn, Herle, and Norris are all in the active party by chapter 10, each with their locked tier-1 and tier-8 techs (§3.16 locked-design summary). A player who reaches chapter 10 can switch to any of the 6 bases and use their basic attack line + tier-8 tech without crashes or missing data. The verification is the §8.6 integration test "6-character party active by chapter 10."

**P1-4: The 36 supports are all recruitable.** The 3 combined units (Leena+Poshul, Korcha+Macha, Turnup+NeoFio) and the 33 standalone supports (§3.3) are all present in the data and can be recruited by meeting the element-recruitment condition. A player who meets the conditions in §3.10 sees the support in the dialog and can add them to the party. The verification is the §8.6 integration test "36 supports all present, all recruitable."

**P1-5: The combat system is deterministic for a given seed.** A player who starts a battle with seed `S` and inputs action `A` gets result `R` every time. The §6.7 BattleRNG and §7.2 determinism layer are the implementation; the §8.6 determinism test battery is the verification. The test runs the same battle 100 times with the same seed and verifies identical outcomes. A single non-determinism is a blocker for Phase 1 completion.

**P1-6: The save system round-trips correctly.** A player can save at any save point, quit the game, reload, and continue from the save. The save contains: party composition, character levels, unlocked techs, equipped supports, story flags, current chapter, current map, and current form (Serge or Lynx). The verification is the §8.6 integration test "save/load preserves all state." The test specifically includes a save in Serge form, a form-change to Lynx, a save in Lynx form, a load of the Lynx save, and a verification that the form-change history is intact (per §7.6).

**P1-7: The visual style is HD-2D throughout.** The §3.4 visual style and §10.3 modernization rules are applied consistently: 2D sprites for all characters, 2D/2.5D layered backgrounds, screen-space lighting, modern resolution. The verification is the §8.6 visual regression test battery with ~200+ baselines per §10.4. A scene that does not match its baseline is a visual regression and a Phase 1 blocker.

**P1-8: The audio is placeholder but functional.** Per §2.4 and the §13.2 Q-9 working assumption, the Phase 1 audio is placeholder music and sound effects. The criterion is *functional*, not *excellent*: the music plays in the right scenes, the sound effects trigger on the right actions, and the audio is not silent or broken. The verification is the §8.6 audio regression test battery (manual review, since placeholder audio is not regression-testable in the same way as extracted audio).

**P1-9: The 30-day stability gate is achieved.** Per §2.4 and the §13.2 Q-9 working assumption's sibling (the §8.10 Phase 2 audit trigger), Phase 1 must run stably for 30 consecutive days of agent playthrough before Phase 2 begins. A "stability day" is a day where the agent plays through at least 2 chapters without encountering a crash, a soft-lock, a save corruption, a determinism violation, or a visual regression. The 30 days need not be calendar days; they are playthrough days.

**P1-10: The documentation is complete.** The design document (this file) is at the §2.3 "document done" quality bar, the loop memory is up to date through the Phase 1 completion, and the `README.md` accurately describes how to run the project. The verification is a checklist: every §2.3 document-done criterion is checked, and any missing item is a blocker.

The 10 Phase 1 criteria together are the "Phase 1 done" bar. Missing any one of them is a Phase 1 blocker. A Phase 1 that satisfies 9 of 10 is "Phase 1 nearly done," not "Phase 1 done." The §13.3 F-7 implementation-paralysis failure mode is the threat: the agent must not declare Phase 1 done without running every criterion.

### 14.3 Phase 2 Success Criteria — Stabilization Audit

Phase 2 is the audit. The success criteria here are about *decisions made and documented*, not about features added. A Phase 2 success is a document — the Phase 2 audit log — that records every vestigial design choice from Phase 1, classifies it (preserve, modify, remove), and justifies the classification. The §1.4 "vestigial design choice" concept is the input; the §14.3 success criteria are the output.

The Phase 2 criteria, in priority order:

**P2-1: Every vestigial design choice from Phase 1 is enumerated.** The agent produces a complete list of Phase 1 design choices that are vestigial — that is, choices that were preserved from the original Chrono Cross for faithfulness but that the redesign's §3.16 locked design now questions. The list lives in `PHASE2_AUDIT.md` and includes: the 3-character party limit, the original element-trap mechanic, the recruit-by-element system, the magic tier distribution, the 6-base-vs-40+-character roster, the level-based progression (replacing the original's element-level progression), the 10-chapter structure, the 2-row combat formation, and any other design choice where the original's behavior is preserved for faithfulness but the redesign's commitments suggest a change.

**P2-2: Each enumerated choice is classified.** Every item in `PHASE2_AUDIT.md` has a classification: `preserve` (Phase 1 choice is correct as-is), `modify` (Phase 1 choice is changed in Phase 3, with a documented reason), or `remove` (Phase 1 choice is eliminated in Phase 3, with a documented reason). The classification is not a vote; it is a justified decision with a reference to the relevant §3.16 commitment or §13 risk.

**P2-3: Every `modify` and `remove` decision is justified.** The classification alone is not enough; the agent must explain *why* the choice is being changed. The justification references the §3.16 locked design (what the redesign commits to), the §13 risk register (what risk the change mitigates), or the §6/§7 implementation reality (what the engine cannot do, or cannot do well). A `modify` or `remove` decision without a justification is not a decision; it is a guess.

**P2-4: The audit log is reviewable.** The `PHASE2_AUDIT.md` is structured so the user can read it in 30 minutes and either approve, reject, or request revision on every decision. The format is: item name → classification → justification → impact (what changes in Phase 3) → risk (what could go wrong). The user reads the log, marks each item with one of {approve, reject, revise}, and the agent proceeds.

**P2-5: The 30-day stability gate is preserved.** Phase 2 does not begin until Phase 1 has been stable for 30 consecutive playthrough days (§8.10, P1-9). The audit is performed on a stable Phase 1; the audit's recommendations apply to Phase 3, not to a moving Phase 1 target. If the audit reveals a Phase 1 bug, the bug is fixed before the audit continues, and the 30-day clock resets.

**P2-6: No Phase 2 decision contradicts §3.16 locked design.** The locked design is the contract. If the audit recommends a change that contradicts §3.16, the recommendation is escalated to a §9.5 design gate, not silently applied. The §3.16 commitments (6 bases, 36 supports, 8 magic tiers, level-based progression, 10 chapters, 6-character party, basic attack line + augmentation model) are not negotiable in Phase 2; they are the inputs to the audit, not the outputs.

**P2-7: The audit log is committed to the project repository.** `PHASE2_AUDIT.md` is a versioned artifact. Every change to the audit is a git commit. The audit log is not in `loop_memory.md` (which is for the agent's working notes) and not in `review.md` (which is for open questions); it is a first-class project artifact, like the design document itself.

The 7 Phase 2 criteria together are the "Phase 2 done" bar. The Phase 2 output is a document, not a game. The game does not change in Phase 2; only the agent's understanding of the design does. A Phase 2 that produces a 200-item audit log with 30 modifications and 10 removals is a Phase 2 success; a Phase 2 that produces a 20-item audit log with 1 modification is a Phase 2 success (the agent decided the rest is correct). The size of the audit is not the criterion; the rigor is.

### 14.4 Phase 3 Success Criteria — Modifications

Phase 3 is the application of the audit and the implementation of the redesign. The success criteria here are about *features delivered and verified*. A Phase 3 success is a runnable game that satisfies every §3.16 locked design commitment, every §14.4 criterion below, and every Phase 1 criterion that was preserved (i.e., not removed by the audit). The Phase 3 bar is *coherence*: the game should feel like one design, not a Phase 1 with a Phase 3 patch on top.

The Phase 3 criteria, in priority order:

**P3-1: Every `modify` decision from P2-4 is implemented.** The audit log's `modify` items each produce a Phase 3 change. The change is implemented, tested, and documented. A `modify` decision that is not implemented is a Phase 3 blocker. The verification is the §8.6 integration test battery with tests added for each `modify` decision.

**P3-2: Every `remove` decision from P2-4 is implemented.** The audit log's `remove` items each produce a Phase 3 removal. The removal is implemented, the related data is deleted (or marked deprecated in the schema), and the user-facing surface is updated. A `remove` decision that is not implemented is a Phase 3 blocker.

**P3-3: The 6-character party is combat-ready.** The §3.11 commitment to a 6-character party (up from the original's 3) is implemented with all 6 characters selectable, controllable, and capable of executing their basic attack line + tier-8 tech + 3 support techs (per the §3.5 augmentation model). The verification is the §8.6 integration test "6-character party combat round." The test simulates a full round of combat with all 6 characters taking actions and verifies that the simulation produces the expected outcomes.

**P3-4: The 36 supports are all integrated with their bases.** Each of the 6 bases has 6 supports (§3.3), of which 3 are combined units (Leena+Poshul, Korcha+Macha, Turnup+NeoFio) and 33 are standalone. The integration means: each support can be assigned to its base, the augmentation is applied to the base's basic attack line, and the augmented attack behaves as designed. The verification is the §8.6 integration test "36 supports all augment correctly." The test iterates over the (base, support) pairs and verifies the augmentation produces the documented effect.

**P3-5: The 8 magic tiers are all reachable.** The level-based progression (§3.8) reaches tier 8 by level 40-50 on average. A character who has played through chapter 10 has access to at least tier 5 slots. A character who has played through New Game+ has access to tier 8 slots. The verification is the §8.6 integration test "magic tier progression by level." The test simulates a character at levels 1, 5, 10, 15, 20, 30, 40, 50 and verifies the correct number of tier slots is available.

**P3-6: The form-change story arc is fully implemented.** The §3.7 Pip reframing and the §12.17 form-change arc are operational: the form-change happens at chapter 1 (cause), is reversed at chapter 4 (act-1 break), is re-reversed at chapter 6 (act-2 break), and is resolved at chapter 9 (climax). The dark techs migrate to Herle on form-return; the light techs unlock post-return via Angelic Pip. The verification is the §7.6 form-change state machine test, which simulates the full form-change history and verifies the migration log is correct.

**P3-7: The 2 endings work as designed.** Per §12.13, the player chooses between "let her go" and "bring her back" at the climax. Both endings are reachable, both play through to completion, and both produce the documented epilogue. The verification is the §8.6 integration test "two endings reachable." The test runs both endings from a chapter-9 save and verifies the epilogue triggers correctly for each.

**P3-8: The expanded interaction scenes are present.** Per §3.13, the 6 main characters have 3-5 expanded interaction scenes each with their closest supports. The scenes total 5-10 minutes per base, unlocked at specific chapter events. The verification is a content-accuracy audit: the script `tools/audit_interaction_scenes.py` reads `data/interaction_scenes.json` and verifies that each base has the required number of scenes, each scene has the expected participants, and each scene triggers at the documented chapter event.

**P3-9: The HD-2D visual style is preserved through Phase 3 changes.** Every Phase 3 change that affects a visual element is verified against the visual regression baseline. The §8.6 visual regression test battery is the verification. A Phase 3 change that breaks a visual baseline is a Phase 3 blocker, even if the change is otherwise correct — the change must be made in a way that preserves the visual style.

**P3-10: The Phase 1 criteria that were preserved are still passing.** The Phase 2 audit's `preserve` items are commitments: those Phase 1 criteria must continue to pass after Phase 3. The §8.6 test battery is run on the Phase 3 build and compared against the Phase 1 baseline. A regression in a `preserve`d criterion is a Phase 3 blocker.

**P3-11: The Phase 3 mod API is operational.** Per §7.13, the mod API exposes the data layer + scene composition + combat engine to mod authors. The verification is a test mod (`tests/mods/test_mod/`) that registers a custom character, custom tech, and custom support, and verifies that the mod loads, validates, and functions in-game. The test mod is itself a piece of documentation: it shows mod authors how to use the API.

**P3-12: The Phase 3 documentation is updated.** The design document is updated to reflect Phase 3 reality. The `README.md` is updated to describe the Phase 3 build. The `loop_memory.md` is updated through Phase 3 completion. The verification is the same checklist as P1-10, applied to the Phase 3 version.

The 12 Phase 3 criteria together are the "Phase 3 done" bar. Phase 3 is the longest and most feature-heavy phase, so the criteria are correspondingly more numerous. The §13.3 F-6 design-perfectionism failure mode is the threat: the agent must not declare Phase 3 done without running every criterion, and must not invent new criteria mid-Phase 3 to handle edge cases the existing criteria do not cover.

### 14.5 Quality Bars by Domain

The phase criteria are organized by *time* (Phase 1, 2, 3). The quality bars are organized by *domain* (combat, story, art, audio, performance, mod support, determinism). A Phase 1 success on combat does not guarantee a Phase 1 success on audio; the agent must verify each domain independently. The quality bars below apply at every phase; the phase-specific criteria (§14.2-§14.4) are the *additional* bar on top.

**Combat quality bar.** A first-time player can complete any random encounter without consulting a guide. The combat is readable: the player understands what each character is doing, what each status effect means, and what the enemy's next move will be. The 6-character party is manageable: the player can switch characters, use support techs, and execute the basic attack line without confusion. The combat is *not* a stats game: the player's tactical choices (which character to lead with, which support to use, which status effect to apply) matter more than the character's level. The verification is a playtest with a new player (the user, or a designated playtester); the new player is observed for 30 minutes of combat and asked to verbalize their decisions.

**Story quality bar.** The story is comprehensible on a first playthrough without reading external material. The 10 chapters cover the §3.13 compressed timeline without major plot holes. The form-change story arc (§3.7) is the emotional spine, and the player should feel the form-change as a turning point, not a mechanics change. The expanded interaction scenes (§3.13) make the 6 main characters feel like *people*, not stats. The dialog is lean per the §10.9 GBA-style constraint. The verification is a playtest with a new player; the new player is asked to summarize the story after completing chapter 5 and again after completing chapter 10.

**Art quality bar.** The HD-2D style is applied consistently across all maps, all battles, all UI screens, and all cutscenes. The 2D character sprites are distinct and recognizable. The 2D/2.5D backgrounds are layered with parallax depth. The lighting is atmospheric, not garish. The art is *not* photorealistic; the §3.4 commitment is to the HD-2D aesthetic, not to a 3D-rendered look. The verification is the §8.6 visual regression test battery with ~200+ baselines and manual review of any scene that has been modified.

**Audio quality bar.** (Placeholder for Phase 1; see P1-8 and §13.2 Q-9.) For Phase 3, if the user decides to license the original music or commission a new soundtrack, the audio quality bar rises to: the music matches the scene's emotional register, the sound effects are distinct and recognizable, the audio mix does not overpower the dialog. The verification is a playtest with a new player; the new player is asked to comment on the audio at specific chapter events.

**Performance quality bar.** The game runs at 60 FPS on the §11.10 workstation baseline (16 GB RAM, modern GPU with Vulkan support). The load time for any map is under 3 seconds. The save/load time is under 1 second. The memory footprint is under 4 GB. The verification is the §8.6 performance test battery, which runs the game through chapter 1 with FPS counters, load-time logging, and memory profiling enabled.

**Mod support quality bar.** A mod author can create a new character, a new tech, a new support, or a new map without reading the design document. The §7.13 mod API + the §6.5 schema-validated data layer is the implementation. The verification is the P3-11 test mod + a documentation review: a new mod author (a designated tester) is given the test mod + the API reference and asked to create a simple mod within 2 hours. If the new mod author succeeds, the mod support quality bar is met.

**Determinism quality bar.** A given seed produces the same combat outcomes, the same treasure drops, the same dialog choices, and the same story events every time. The §6.7 BattleRNG and §7.2 derived PRNGs are the implementation. The verification is the §8.6 determinism test battery: 100 runs of the same battle with the same seed, compared for identical outcomes. A single non-determinism is a §13.1 R-9 performance-regression or a determinism-layer bug.

The 7 domain quality bars are the cross-cutting success criteria. A Phase 1 success must satisfy all 7 (audio is the only domain where the bar is reduced for Phase 1); a Phase 3 success must satisfy all 7 at full bar. The agent commits to verifying each domain at every phase transition, not just the phase-specific criteria.

### 14.6 Testable Claims — The Document's Self-Audit

The §1.5 "no magic" principle says that every claim in the document must be backed by a concrete design choice or flagged as an open question. The success criteria above are the *external* version of that principle — claims about the *project*. The testable claims below are the *internal* version: claims about the *document itself*. A testable claim is a statement in the document that the agent can verify is still true at any point in the project's life.

The testable claims are not in §14.5 (which is about project quality) or §14.2-§14.4 (which are about phase completion). The testable claims are about the *internal consistency* of the document. Examples:

- **TC-1: Every §3 commitment is referenced in §6, §7, §8, or §12.** The §3.16 locked-design summary is the contract. If a §3 commitment is not referenced in the implementation sections (§6, §7, §8) or the walkthrough (§12), it is a §3 commitment that has no implementation, which is a §13.3 F-1 stub failure mode. The verification is a grep: `grep -F "§3.X" §6 §7 §8 §12` should return matches for every §3.X subsection.
- **TC-2: Every §4 criterion is referenced in §5.** The §4 criteria are the spine; §5 applies them. If a §4 criterion is not in §5's matrix, the criterion is unused. The verification is a similar grep across §4 and §5.
- **TC-3: Every §6 architecture decision is referenced in §7.** §6 is the chassis; §7 is the body. If a §6 decision is not built on in §7, the chassis is unused. The verification is similar.
- **TC-4: Every §7 subsystem is tested in §8.6 or §14.5.** The §7 subsystems are the implementation; the §8.6 test battery is the verification. If a §7 subsystem has no test, the subsystem is unverified. The verification is a cross-reference: each §7.X subsection should map to at least one §8.6 or §14.5 test.
- **TC-5: Every §12 chapter is reachable from a §7 chapter transition.** The §12 walkthrough is the narrative; the §7.8 chapter transition system is the implementation. If a §12 chapter does not have a corresponding §7.8 chapter data, the chapter is unreachable in code.
- **TC-6: Every `loop_state.json.locked_design` key is referenced in the document.** The locked design is the source of truth; if a locked-design key is not in the document, the agent has not internalized it.

The 6 testable claims are the document's self-audit. A future maintainer who wants to know "is this document still consistent?" runs the 6 greps and reports the failures. The agent runs the self-audit at every phase transition (§13.5 risk review protocol) and at every 30-day milestone. The §13.3 F-2 design-drift failure mode is the threat: a document that drifts across phases is worse than a document that is incomplete.

### 14.7 Player-Facing vs Agent-Facing Success Criteria

A success criterion can be observed by the player, by the agent, or by both. The split matters because the two audiences have different verification methods. A player-facing criterion is verified by playing the game; an agent-facing criterion is verified by running a script. A criterion that is both is the strongest (two independent verifications), but most criteria are one or the other.

Player-facing criteria (verified by the user or a designated playtester):

- The game is fun to play (P3 implicit, §14.5 combat and story bars)
- The story is comprehensible (§14.5 story bar)
- The art is appealing (§14.5 art bar)
- The audio is appropriate (§14.5 audio bar)
- The game is challenging but not frustrating (§14.5 implicit)
- The form-change lands emotionally (§3.7, §12.17)
- The expanded interaction scenes make the 6 bases feel like people (§3.13)

Agent-facing criteria (verified by automated test):

- The game runs from a clean clone (P1-1)
- The 36 supports are all present (P1-4)
- The combat is deterministic (P1-5)
- The save system round-trips (P1-6)
- The visual regression baselines pass (P1-7, P3-9)
- The form-change state machine is correct (P3-6)
- The two endings are reachable (P3-7)
- The mod API is functional (P3-11)
- The 6 testable claims pass (TC-1 through TC-6)
- The performance counters are within bounds (P-bar in §14.5)

A criterion that is *only* agent-facing is verified by automation; a criterion that is *only* player-facing is verified by playtest. The agent commits to maintaining both verification paths. A Phase 3 success requires both: the agent-facing tests pass *and* the player-facing playtest is positive. An agent-facing test that passes while the game is not fun is a §13.3 F-7 implementation-paralysis failure mode; a player-facing playtest that is positive while the agent-facing tests fail is a §13.3 F-9 toolchain-rot failure mode.

The §1.2 audience split ("the agent is not the player") is the philosophical underpinning. The agent cannot perceive "fun" directly; the agent can perceive "deterministic" and "30 supports present" directly. Both are valid success criteria; the verification methods differ.

### 14.8 What Success Is Not

The success criteria above are positive — they specify what the project must do. The list below specifies what success is *not*, to prevent scope creep and category errors. The list is the §3.16 anti-list in success-criterion form.

The project is not successful when:

- **The code is "clean."** Code quality is a means, not an end. The §1.5 design principles say the code should be readable, testable, and modifiable, but a clean codebase that does not deliver a fun game is not a success. The success criteria are about the *game*, not the *code*. (The code quality is checked by the §8.6 test battery and the §14.6 testable claims, not by a separate "code quality" criterion.)
- **The project uses the latest Godot version.** The §6.2 versioning policy commits to Godot 4.3-stable, not "the latest." A success on Godot 4.3 is a success; a migration to Godot 4.4 or 4.5 is a §11.6 vendoring decision, not a success criterion. A project that is "successful on Godot 4.3 but stuck on Godot 4.3 forever" is still a success; the project does not need to track upstream.
- **The design document is "complete."** The §2.3 "document done" criterion is a *quality bar*, not a "no more words needed" bar. The document can grow at any phase; the success criteria are about the *content* of the document, not the *length*. A 60,000-word document that satisfies every §2.3 criterion is a "done" document; a 100,000-word document that does not is not.
- **The project is "feature-complete."** The §3.16 locked design specifies 6 bases, 36 supports, 8 tiers, 10 chapters. A project that delivers these is "feature-complete" by the locked design. A project that adds more (e.g., a 7th base, a 9th tier) is "scope-crept," not "feature-complete." The success criteria are about the *committed* features, not the *possible* features.
- **The project is "polished."** Polish is a §14.5 quality bar, not a separate criterion. A polished Phase 1 that has not yet entered Phase 2 is not a successful project; it is a successful Phase 1. A project that is "polished" but does not satisfy the Phase 2 or Phase 3 criteria is a polished Phase 1, not a successful project.
- **The community approves.** The project is private, not public (§10.7 legal posture). Community approval is not a criterion; user approval is. The user's loop summary (§9.9) is the user-approval touchpoint.
- **The original Chrono Cross community accepts the redesign.** The redesign is a Phase 3 modification, not a faithful remaster. The §1.4 "vestigial design choice" concept is the agent's license to make changes; the user's loop summary is the user-approval touchpoint. The broader Chrono Cross community is not a stakeholder.

The 7 anti-criteria are the project's defense against scope creep, perfectionism, and category errors. A future maintainer who says "but the code is so clean, surely that counts as a success?" gets the answer: no, the success is the game, not the code. A future maintainer who says "but the document is 80,000 words, surely that's a complete document?" gets the answer: no, the success is the *content*, not the *length*.

### 14.9 Decisions Needed

The success criteria above are committed. They are derived from the §1.6 autonomy model, the §2.3 definitions of "done," the §3.16 locked design, and the §13 risk register. They are not new design decisions; they are the *consequences* of the design decisions already made. The only decisions that remain open are the questions surfaced in §13.7 and the questions in `review.md`. The success criteria commit to *how* the project will be measured; they do not introduce new *what* the project will deliver.

The specific decisions that affect the success criteria, in priority order:

- **Q-5: The element-system UI surfacing (§13.7).** The §3.10 recruit-by-element system needs a UI. The success criterion for the UI is implicit in §14.5 (combat and story bars), but the *specific* UI design is open. The agent proceeds with the working assumption ("Your element is X. You can recruit [list].") and the user can revise.
- **Q-9: Music handling (§13.7).** The §14.5 audio quality bar is reduced for Phase 1 (placeholder) and depends on the user's decision for Phase 3. The success criterion is "audio quality bar met at the level the user has authorized." If the user does not authorize original music, the bar remains placeholder; if the user does, the bar rises to "matches the scene's emotional register."
- **Q-11: "Bring her back" ending (§13.7).** The §14.4 P3-7 criterion ("two endings work as designed") depends on the user's decision to keep both endings. If the user decides on a single ending, the criterion is revised to "the chosen ending works as designed." The agent proceeds with two endings and the user can revise.
- **Q-6: Level-by-chapter pacing (§13.7).** The §14.4 P3-5 criterion ("8 magic tiers are reachable") is satisfied by any level curve that reaches tier 8 by level 40-50. The specific curve shape is open. The agent proceeds with the linear curve and the user can revise.

The 4 open decisions are not blocking the document's continuation. The success criteria are committed; the *specific design choices that satisfy the criteria* are open in the 4 areas above. The agent will continue with §15 (Proof of Concept) using the working assumptions, and the user can revisit the 4 questions at any phase transition.

---

---

## 15. Next Steps and Proof-of-Concept Scope

### 15.1 What This Section Is For

This is the final section of the design document. The first 14 sections specified *what* the project is (§1-§3), *how* it is built (§4-§7), *how* it is operated (§8-§9), and *how* it is verified (§13-§14). Section 15 specifies the *order in which to do it next*. The goal is to convert a 70,000-word design document into a runnable project without losing the discipline the document encodes. A naive reading of the document — "start at section 6, implement the architecture, fill in the data, run the tests" — sounds linear but is wrong. The reality is that the project has multiple *threads* that must advance in parallel, and the sequence of which thread advances first is itself a design decision.

§15 is the answer to the question every project lead eventually asks: "Given everything in §1-§14, what do I literally do this week?" The answer is a proof-of-concept (PoC) scope: a minimal, runnable, end-to-end slice of the project that exercises every part of the architecture without implementing every feature. The PoC is not a Phase 1 milestone — it is a *de-risking milestone* that comes before Phase 1 begins. Its purpose is to verify that the §6 architecture works, that the §7 subsystems wire together, that the §8 pipeline runs, and that the §9 agent loop is operable on real code. A PoC that fails forces a design revision; a PoC that succeeds gives the green light for the Phase 1 build-out.

The §15 scope commits to a specific PoC: a single character, a single map, a single combat encounter, and a single save/load round-trip — all running in Godot 4.3 with the §6.5 schema-validated data layer, the §6.7 ECS-style combat simulation, the §7.2 determinism layer, and the §9.4 TDD loop. No HD-2D art, no audio, no support characters, no chapter transitions, no form-change. The minimal slice that proves the architecture. If the slice works, the architecture is real; if the slice fails, the architecture is theoretical. Everything else in §15 is the discipline around that slice.

### 15.2 The PoC Scope — Four Endpoints and Two Connectors

The PoC is specified as four endpoints and two connectors. Each endpoint is a *thing the user can do or observe*; each connector is the *data path* between endpoints. The endpoints exercise every architectural subsystem in the document; the connectors exercise the integration points that §7.14's cross-subsystem integration test will eventually verify.

**Endpoint 1: The character screen.** The user opens the project, sees Serge in a 2D field sprite (placeholder rectangle, not art), and the character screen shows his name, his element (White), his basic attack line ("Dash and Slash"), his current level (1), and his tier-1 magic slot (one empty slot for a tier-1 white element). This exercises the §6.5 schema-validated `data/characters/serge.json` resource, the §6.6 character-screen scene, the §6.7 CombatSimulator state (initialization), and the §9.4 TDD loop (one test: "serge.json validates against the schema").

**Endpoint 2: The map.** The user navigates Serge from a 2D placeholder start position to a 2D placeholder end position on a single map (a 16x12 grid of placeholder tiles, hand-built for the PoC). This exercises the §6.6 map scene composition, the §7.8 chapter transition (a trivial one-step "this is the start of the game" transition), the §7.10 combat engine's "out of combat" state, and the §9.4 TDD loop (one test: "pressing the action button near a tile transitions the player to that tile").

**Endpoint 3: The combat encounter.** The user steps on a designated tile, the screen transitions to a 2D battle scene (Serge vs. one placeholder enemy), the user selects "Attack" from a placeholder combat menu, and the attack resolves: the basic attack line executes, the enemy's HP drops by a deterministic amount, and the enemy is defeated. This exercises the §6.7 ECS-style combat simulation, the §6.4 typed GDScript data model (a `Tech` resource for Dash and Slash), the §7.3 augmentation system (no augmentations in the PoC, but the data structure is in place), the §7.2 determinism layer (BattleRNG), the §7.10 combat engine's "in combat" state, and the §9.4 TDD loop (the §7.14 cross-subsystem integration test, in its PoC form: "deterministic combat resolves identically across two runs").

**Endpoint 4: Save and load.** The user opens the in-game menu, selects "Save," quits the game, relaunches, loads the save, and is back in the same map at the same position with the same character state. This exercises the §6.5 save-game data layer, the §7.11 SaveSystem autoload, the §7.11 schema_version field, the §7.11 MigrationRegistry (empty for the PoC but structured), and the §9.4 TDD loop (one test: "save/load round-trip preserves player state").

The two connectors are: (a) the data path from `data/characters/serge.json` through the schema validator to the runtime `CharacterData` resource, and (b) the data path from the in-game menu's "Save" button through the SaveSystem autoload to `user://saves/slot_1.tres` and back. Connector (a) exercises the §6.5 / §8.4 / §8.5 translation pipeline (in its PoC form: one translator, one schema, one resource). Connector (b) exercises the §7.11 save subsystem end-to-end. Both connectors have tests; both connectors are observable in the running game.

The four endpoints and two connectors together form the PoC. A PoC with fewer endpoints does not exercise enough of the architecture; a PoC with more endpoints takes longer than the de-risking milestone should. Four endpoints is the right number because each one corresponds to a distinct §6 / §7 subsystem, and the two connectors correspond to the two cross-cutting concerns (data validation and persistence) that the document treats as separate layers. A future maintainer who wants to extend the PoC can add a fifth endpoint (e.g., "recruit a support character") and a third connector ("save the party roster, not just Serge") without disturbing the existing four.

### 15.3 What the PoC Does NOT Include

The PoC is minimal. The list of things it does not include is as important as the list of things it does — every "not included" item is a Phase 1 task that the PoC explicitly defers. The discipline of saying "no" to a list is what keeps the PoC a 2-week milestone instead of a 2-month milestone.

The PoC does not include HD-2D art. The character sprite is a placeholder rectangle; the map tiles are placeholder colors; the battle background is a solid color. The §6.9 / §7.9 HD-2D rendering stack is implemented in code (so the architecture is in place) but the visual output is placeholder. The §8.6 visual regression test battery does not run in the PoC — there are no baselines. The PoC commits to *the architecture for HD-2D* without *the content of HD-2D*. A future maintainer who tries to add art to the PoC should resist; art is a Phase 1 task.

The PoC does not include audio. There is no background music, no sound effects, no voice. The §7 audio subsystems are not in the PoC. The §14.5 audio quality bar is reduced to "no audio" for the PoC. A PoC with audio is a PoC with one more thing to test and zero new architectural exercises; the de-risking value of audio is low.

The PoC does not include support characters. There is no Kidd, no Nikki, no Glenn, no Herle, no Norris. The 36 supports do not exist in the PoC. The `data/characters/` directory has one file: `serge.json`. The §3.3 commitment to 6 bases + 36 supports is deferred to Phase 1. A PoC with supports would exercise the §7.3 augmentation system, but the PoC scope is to verify that *one character's* augmentation data structure works, not to verify that *36 characters' worth* of augmentations work.

The PoC does not include chapter transitions. The map is a single hand-built scene; there are no chapter events, no cinematic beats, no party changes. The §7.8 chapter transition system is implemented (so the data structure is in place) but the §12 walkthrough's 10 chapters are deferred. A PoC with chapter transitions would require at least two chapters to be meaningful, which would require content, which would require art, which would be Phase 1.

The PoC does not include the form-change. Serge is Serge throughout. The §3.7 Pip reframing, the §7.6 form-change state machine, the §12.17 form-change story arc — all deferred to Phase 3. The form-change is the redesign's most narratively interesting part; it is also the most architecturally risky. The PoC defers the risk.

The PoC does not include the magic tier system. Serge has one tier-1 magic slot (empty) and zero tier-2 through tier-8 slots. The §3.8 commitment to 8 magic tiers and the §3.6 level-based progression are deferred. A PoC with the full tier system would require the level-up curve, the tier-slot-unlock logic, the element catalog, and the inventory — a Phase 1 worth of work. The PoC has the data structure for a single tier-1 slot; the rest is Phase 1.

The PoC does not include the mod API. The §7.13 ModAPI autoload is not in the PoC. The data layer is already a mod surface (§7.13's "Phase 1 requirement because the §6.5 data layer is already a mod surface"), so a mod author who can write JSON files can already make changes. The autoload is the missing registration layer; it is Phase 1 work.

The PoC does not include the cross-subsystem integration test (§7.14 in its full form). The PoC has a *subset* of that test: the combat-encounter endpoint exercises the same code path, but the test asserts only "combat resolves deterministically," not the full 8-step integration scenario. The full §7.14 test is a Phase 1 task.

The PoC does not include documentation beyond the design document. The §7.13 mod API documentation, the §11.10 workstation setup script, the §8.6 test battery documentation — all deferred. The design document *is* the PoC's documentation. A PoC with separate documentation would be a documentation PoC, not an architecture PoC.

The "not included" list is longer than the "included" list. This is intentional. The PoC's discipline is to say "no" to anything that does not exercise a §6 / §7 architecture decision. A future maintainer who wants to add a feature to the PoC should ask: "Does this exercise a new §6 / §7 subsystem, or does it add content to an existing one?" If the answer is "add content," the answer is no. The PoC is not a content milestone; it is an architecture milestone.

### 15.4 The PoC Implementation Order

The PoC has 4 endpoints and 2 connectors. The implementation order is not the endpoint order; it is the *dependency* order. The character screen (Endpoint 1) depends on the data layer (Connector 1). The map (Endpoint 2) depends on the character screen. The combat encounter (Endpoint 3) depends on the map. The save/load (Endpoint 4) depends on the combat encounter (because the PoC's save point is after the first combat). The data layer (Connector 1) is the foundation; the save subsystem (Connector 2) is the capstone. The implementation order is:

**Step 1 (Days 1-2): Data layer foundation.** Write `data/characters/serge.json` (one character, hand-authored for the PoC). Write `data/schemas/character.schema.json` (the §6.5 schema, minimal version covering the PoC's data needs). Write `tools/validate_data.py` (the §6.5 schema validator, one file, ~50 lines). Write one test: `serge.json validates against the schema`. This is the §6.5 / §8.4 / §8.5 pipeline in its minimum viable form. If the validator works, the data layer is real.

**Step 2 (Days 2-3): GDScript data classes.** Write `scripts/character_data.gd` (a static-typed GDScript class that loads `CharacterData` from JSON). Write `scripts/tech_data.gd` (a static-typed GDScript class for `Tech` resources, including the §6.4 typed-GDScript subset patterns). Write the `from_dict` factory methods per §6.4. Write one test: "CharacterData.from_dict('serge') returns a valid CharacterData with element=White and basic_attack='Dash and Slash'." This is the §6.4 / §6.5 GDScript side of the data layer.

**Step 3 (Days 3-4): Character screen.** Build the §6.6 character-screen scene. Place a placeholder Serge sprite (a colored rectangle). Wire the scene to the GDScript data classes. The screen shows Serge's name, element, basic attack, level, and tier-1 slot. Write one test: "Opening the character screen displays Serge's name from the JSON." This is Endpoint 1 of the PoC. If the screen shows Serge's data, the data layer + scene composition + GDScript wiring is verified.

**Step 4 (Days 4-5): Map scene.** Build the §6.6 map scene. A 16x12 grid of placeholder tiles. A `Player` scene (a colored rectangle, controllable by arrow keys or WASD). A `MapData` resource that defines which tile triggers a combat encounter. Write one test: "Pressing the action button on the encounter tile transitions the scene to combat." This is Endpoint 2 of the PoC. If the player can walk the map and trigger the encounter, the map scene composition is verified.

**Step 5 (Days 5-7): Combat engine.** This is the heaviest step. Build the §6.7 CombatSimulator with the §7.2 determinism layer (BattleRNG with derived PRNGs scoped by tag). Build the §7.10 combat engine's "in combat" state. Build the §6.4 `Tech` resource for "Dash and Slash." Build a placeholder enemy (one enemy, hand-defined in JSON). Build the §6.6 battle scene with a placeholder combat menu. Write the §7.14 cross-subsystem integration test in its PoC form: "Run the combat 100 times with the same seed; verify identical outcomes." This is Endpoint 3 of the PoC. If the combat resolves deterministically, the §6.7 / §7.2 / §7.10 architecture is verified. This is the highest-risk step; allocate buffer.

**Step 6 (Days 7-8): Save and load.** Build the §7.11 SaveSystem autoload. Build the §7.11 schema_version field. Build the §7.11 MigrationRegistry (empty for the PoC, but the data structure is in place). Build the in-game menu's "Save" and "Load" buttons. Write the save/load test: "Save at (5, 7) on the map with 50 HP; load; verify (5, 7) and 50 HP." This is Endpoint 4 of the PoC. If the round-trip works, the persistence layer is verified.

**Step 7 (Days 8-9): End-to-end smoke test.** A hand-driven playthrough: start a new game, see Serge in the character screen, walk the map, trigger the combat, win, save, quit, reload, continue. The test asserts that every step works in sequence. This is the §7.14 cross-subsystem integration test in its looser form: a single script that exercises the entire PoC end-to-end. If the smoke test passes, the PoC is complete.

**Step 8 (Days 9-10): Documentation and review.** Update the design document with any PoC-discovered changes (the §15.5 "what the PoC might reveal" section). Write a `README.md` that describes the PoC and how to run it. Run the §13.5 risk review protocol. Hand the PoC to the user for review. The user approves or sends back for revision. This is the §9.9 user-review touchpoint.

The 10-day timeline is aggressive. A PoC that takes 14 days is fine; a PoC that takes 21 days is a signal that the scope was wrong. The §13.3 F-7 implementation-paralysis failure mode is the threat: the agent must not let the PoC expand into a Phase 1 prototype. The "not included" list (§15.3) is the discipline that keeps the scope honest.

### 15.5 What the PoC Might Reveal

A PoC is a learning exercise, not a verification exercise. The expected outcome is that the PoC works — the architecture is sound, the §6 / §7 subsystems wire together, the §8 pipeline runs, the §9 agent loop operates. But the *interesting* outcome is the set of things the PoC reveals that the design document did not anticipate. The §1.4 "vestigial design choice" concept applies to the design document itself: the document is the current best understanding, and the PoC is the first opportunity to test that understanding against reality.

The most likely PoC discoveries, in order of probability:

- **The GDScript static-typing story is less smooth than §6.4 implies.** The §6.4 worked example (the `TechEffect` data class) is clean, but writing 5 more data classes in the same style may reveal boilerplate that the document does not address. The likely fix is a `tools/gdscript_class_generator.py` script that produces the data class skeletons from JSON Schema. This is a §11 toolchain addition, not a §6 architecture change.

- **The §6.7 ECS-style combat simulation is more code than expected.** The §6.7 state machine is well-specified, but the actual implementation of "5-step action lifecycle" may require more components than the document lists. The likely fix is to add 2-3 components to the §7.10 component list, not to change the architecture. The ECS choice itself is unlikely to be wrong.

- **The §7.2 determinism layer needs more derived PRNGs than the document specifies.** The PoC may discover that "combat" alone needs 3 derived PRNGs (one for hit rolls, one for damage variance, one for status effect application), not the 1 the document implies. The fix is to expand the PRNG tag list in `data/rng_tags.json`, not to change the determinism architecture.

- **The §6.5 schema validator is more verbose than the document shows.** The `jsonschema` library is well-suited to the PoC, but writing schemas for every data type may produce 200+ lines of schema per data type. The likely fix is a `tools/schema_generator.py` that produces schemas from Python dataclasses, which is the inverse of the current pipeline. This is a §11 toolchain addition.

- **The §7.11 save format is more complex than the document implies.** The PoC may discover that saving the player's position, HP, current map, and current scene state requires more fields than the document's "save file format" example shows. The likely fix is to expand the save resource structure, not to change the save format (text .tres stays).

- **The Godot 4.3 headless test workflow has a rough edge.** The §11.2 Godot 4.3 headless commands work, but the actual `godot --headless --quit` invocation for a CI test may produce a stack trace that does not match the test assertion. The likely fix is a custom test runner that wraps the Godot CLI and normalizes the output. This is a §11 toolchain addition.

The 6 likely discoveries are all *toolchain expansions* or *minor architecture details*, not *architecture changes*. The §6 / §7 architecture is unlikely to be wrong; the *implementation cost* of the architecture is likely higher than the document estimates. The §1.5 "no magic" principle means the cost must be visible — every additional tool or expanded data structure is a new file in the repo, not a hidden complexity. A PoC that reveals 5 new toolchain files is a successful PoC; a PoC that reveals 0 new files is a PoC that did not test the architecture hard enough.

The §15.5 list is not exhaustive. A PoC that reveals a §6 / §7 architecture change (e.g., "ECS is the wrong choice") is a PoC that the document got wrong. The §9.5 design-gate protocol applies: the change is escalated to the user for review, the design document is revised, the PoC is rebuilt. A PoC that forces a §6 / §7 revision is not a failure; it is the de-risking milestone working as designed. The point of the PoC is to discover architecture problems *before* Phase 1 build-out, not after.

### 15.6 The PoC's Deliverables

The PoC produces a set of artifacts that the rest of the project can build on. The artifacts are concrete: a working `godot` project, a test suite that runs in CI, a `README.md` that explains how to run the project, and a set of design-document revisions that the PoC revealed as necessary. The PoC is "done" when all four artifacts exist and the user has approved them.

**Artifact 1: A runnable Godot 4.3 project.** The project is checked into the repo at `D:\Game Design\Remaster Engine\`. The project has the §6.3 directory structure (minimal version: `data/`, `scripts/`, `scenes/`, `tests/`, `tools/`). The project runs from a clean clone: `git clone`, `tools/setup.sh`, `godot --headless --path . --quit` to verify, then `godot --path .` to play. The project has one character (Serge), one map, one combat encounter, and one save/load round-trip. The project has placeholder art and no audio. The project is "Phase 1 of 0.1" — a working slice, not a feature-complete game.

**Artifact 2: A test suite that runs in CI.** The test suite is the §8.6 test battery in its PoC form: 5-8 tests covering the schema validator, the GDScript data classes, the character screen, the map, the combat (with determinism), and the save/load round-trip. The tests run via `godot --headless --path .` with a custom test runner. The tests run in GitHub Actions on every commit. A commit that breaks a test is a §9.4 TDD failure. The test suite is the §14.6 testable claims (TC-1 through TC-6) in executable form.

**Artifact 3: A `README.md`.** The `README.md` describes the PoC's scope, the four endpoints, the two connectors, the 10-day implementation order, and how to run the project. The `README.md` is the project's first human-facing artifact — a future maintainer who clones the repo reads the `README.md` first, runs the setup script, and plays the PoC. The `README.md` is also the §9.9 user-review touchpoint: the user reads the `README.md` and the design document together, then approves or sends back for revision.

**Artifact 4: Design-document revisions.** The PoC may reveal that §6, §7, §8, §9, §11, or §14 needs revision. The revisions are committed to the design document as a new loop (a "fix" loop per §9.3, not a "draft" loop). The revisions are minimal and targeted — the PoC is not a license to rewrite the document. The §14.6 testable claims (TC-1 through TC-6) are re-run after the revisions to verify the document is still internally consistent. A design-document revision that breaks a testable claim is a §13.3 F-2 design-drift failure mode.

The 4 artifacts together are the PoC's "done" bar. A PoC that produces 3 of the 4 is incomplete; a PoC that produces all 4 is ready for Phase 1.

### 15.7 Phase 1 Entry Criteria

The PoC is the gate to Phase 1. Phase 1 begins when the PoC is approved and the 4 artifacts are committed. Phase 1 is the long build-out: implementing the 6 bases, the 36 supports, the 8 magic tiers, the 10 chapters, the HD-2D art, the audio placeholders, the chapter transitions, the form-change state machine, the mod API, and the full §8.6 test battery. Phase 1 is the most content-heavy of the three phases; the PoC is the de-risking milestone that makes Phase 1 feasible.

The Phase 1 entry criteria are the §14.2 P1-1 through P1-10 success criteria, with two modifications. First, P1-1 ("clean-clone runnability") is *partially* satisfied by the PoC — the PoC's `README.md` + setup script is the foundation, but the Phase 1 build-out adds more dependencies and the criterion must be re-verified. Second, the PoC's test suite (5-8 tests) is the *seed* of the §8.6 test battery, but Phase 1 expands the battery to the full set (unit, integration, determinism, content-accuracy, visual regression with 200+ baselines). A Phase 1 entry that has only the PoC's test suite is incomplete; the test battery is a Phase 1 task.

The Phase 1 entry also requires a *schedule*. The §2.3 "definitions of done" lists a project-level schedule as an open question; the PoC's 10-day timeline is a useful precedent for Phase 1. A Phase 1 schedule of 6-12 months is plausible for a 6-base, 36-support, 10-chapter, HD-2D game with 1 developer (the agent) and 1 reviewer (the user). The schedule is committed in the Phase 1 kickoff loop, not in §15; the PoC is the milestone, not the schedule.

The Phase 1 entry also requires a *user sign-off*. The user reviews the PoC's 4 artifacts, plays the PoC, and either approves ("Phase 1 begins") or sends back for revision. The §9.9 user-review touchpoint is the sign-off moment. A PoC that the user does not approve is a PoC that did not de-risk the right things; the PoC is iterated, not abandoned. The iteration cost is bounded by the §15.4 10-day timeline — a PoC that takes 30 days to converge is a signal that the scope was wrong.

### 15.8 Phase 2 and Phase 3 Entry Criteria

The document's three phases have entry criteria and exit criteria. §15.7 specified the Phase 1 entry. The Phase 2 entry is the §13.5 30-day stability gate: Phase 1 must be faithfully remastered and stable for 30 consecutive days of agent playthrough before Phase 2 begins. The §14.2 P1-1 through P1-10 success criteria are the Phase 1 *exit* criteria. The Phase 2 *entry* criteria are the §14.3 P2-1 through P2-7 success criteria applied to the Phase 1 build (i.e., the agent has enumerated every vestigial design choice in the Phase 1 build, classified each one, and committed to the classification in `data/audit/vestigial_choices.json`).

The Phase 2 exit is the §14.3 P2-1 through P2-7 success criteria, with the additional constraint that the §13.5 risk review protocol has been run and the §13.6 long-tail risks have been re-evaluated. Phase 2 is shorter than Phase 1 (1-3 months is plausible) because the work is *analysis*, not *content*. The Phase 2 deliverable is `data/audit/vestigial_choices.json` plus a revised design document.

The Phase 3 entry is the Phase 2 exit + the user's approval of the audit's `modify` and `remove` items. The §14.4 P3-1 through P3-12 success criteria are the Phase 3 *exit* criteria. The Phase 3 deliverable is the §3.16 locked design, fully implemented and verified. Phase 3 is the longest phase (6-12 months is plausible) because the work is the most content-heavy: 6 bases, 36 supports, 8 magic tiers, 10 chapters, HD-2D art, the form-change story arc, the two endings, and the expanded interaction scenes.

The phase boundaries are *not* equal. Phase 1 is content build-out. Phase 2 is design analysis. Phase 3 is redesign implementation. The PoC is a *de-risking milestone* that comes before Phase 1, not a "Phase 0." The document's three-phase model (§1.6, §2.1, §3.16) is the project's defining structure; the PoC is a separate, pre-Phase-1 milestone that exists because the de-risking is too important to defer to Phase 1 itself.

The 30-day stability gate is the discipline that makes Phase 2 possible. A Phase 1 that is not stable for 30 days is a Phase 1 that is not done; the §14.2 P1-9 criterion enforces the discipline. The 30 days is a *consecutive* playthrough — the agent plays the game from start to finish, every day, for 30 days, with no crashes, no data corruption, no missing content, no broken interactions. A single crash resets the counter. The discipline is severe but necessary: a Phase 1 that crashes on day 14 is a Phase 1 that the agent cannot honestly audit in Phase 2.

### 15.9 The Project as a Whole

The PoC + Phase 1 + Phase 2 + Phase 3 is the project's life. The PoC is 2 weeks. Phase 1 is 6-12 months. Phase 2 is 1-3 months. Phase 3 is 6-12 months. The total is 14-28 months. The §13.6 long-tail risks (the project outlasting the agent's context window, the user's interest, the original game's relevance, the technology stack) are the *reason* the project's life is bounded. The 14-28 month estimate is the project's reasonable lifespan; beyond that, the §13.6 risks dominate.

The project is not a 10-year effort. The §13.6 framing is honest: the agent commits to making the project work in a 14-28 month window, not in a 10-year window. The PoC is the first step in that window. The design document is the project's source of truth for the next 14-28 months. The agent's loop protocol is the project's operating system for the next 14-28 months. The user's loop summary is the project's review surface for the next 14-28 months. The 14-28 month window is the project's life; everything in §1-§15 is calibrated to that window.

The project is also not a 1-month effort. A PoC that takes 1 week is a PoC that did not test the architecture hard enough. A Phase 1 that takes 2 months is a Phase 1 that is incomplete. The §15.4 10-day PoC timeline and the §15.7 6-12 month Phase 1 timeline are not arbitrary; they are calibrated to the *content* of the work. A 6-base, 36-support, 10-chapter, HD-2D game is a 6-12 month build at 1 developer. A 2-week PoC is a 2-week de-risking milestone. The timelines are honest.

### 15.10 The First Concrete Action

The design document is complete. §1-§14 specified the project's design, architecture, workflow, and verification. §15 specifies the order in which to do the work. The first concrete action — the action the user (or the agent, on the user's behalf) takes *after* the design document is approved — is to create the PoC's repository structure: the §6.3 directory tree (minimal version), the `data/characters/serge.json` file, the `data/schemas/character.schema.json` file, the `tools/validate_data.py` script, and the first test (`tests/test_character_schema.py`).

The first concrete action is small. It is not the implementation of the combat engine, not the drawing of the map, not the recording of the audio. It is the *first line of code in the project*: a JSON file, a schema, a validator, a test. The 4 files together are the seed of the project. Everything else in §1-§15 grows from these 4 files.

The first concrete action is also *automatable*. The §9.4 TDD loop commits to one commit per TDD cycle; the first TDD cycle is "the schema validator passes for serge.json." The agent can run the first cycle without further user input, given the design document's §6.5 schema, the §11.3 Python toolchain (uv + jsonschema), and the §15.4 Step 1 instructions. The user reviews the result in the next loop summary.

A project that begins with a 4-file seed is a project that begins with discipline. The seed files are the §1.5 "no magic" principle in action: every later file in the project references these 4 files, validates against the schema, runs through the validator, and is tested by the test. The PoC's 4-file seed is the project's *invariants*: the things that do not change as the project grows. The §6.5 schema is the invariant for the data layer. The §7.2 determinism layer is the invariant for the simulation. The §7.11 save format is the invariant for the persistence layer. The §9.4 TDD loop is the invariant for the agent's workflow. The 4 invariants together are the project's spine.

The design document is the spine's specification. The PoC is the spine's first test. The phases are the spine's build-out. The 14-28 month window is the spine's life. The user is the spine's reviewer. The agent is the spine's operator. The original Chrono Cross is the spine's source. The §3.16 locked design is the spine's destination.

### 15.11 Closing — What the Document Is

The design document is a *contract*. It commits to a specific architecture (§6 / §7), a specific workflow (§8 / §9), a specific set of risks (§13), a specific set of success criteria (§14), and a specific next step (§15). The contract is not aspirational; it is enforceable. The §14.6 testable claims are the contract's self-audit; the §14.5 quality bars are the contract's domain tests; the §14.2-§14.4 phase criteria are the contract's milestones.

The design document is also a *history*. Every section records a decision that was made, an option that was considered, a risk that was identified. The §3.16 locked design is the current best understanding; the §13 risk register is the current best worry; the §15 next-steps is the current best plan. A future maintainer who reads §1-§15 in order sees the project's evolution: the design (§1-§3), the criteria (§4), the engine choice (§5-§6), the engine additions (§7), the pipeline (§8), the workflow (§9), the source constraints (§10), the tools (§11), the narrative (§12), the risks (§13), the success criteria (§14), and the next step (§15). The 15 sections are the project's autobiography.

The design document is also *the project's first deliverable*. A project that has a 70,000-word design document is a project that has thought about what it is doing. A project without a design document is a project that is exploring. The two are not the same. The user's investment in the design document is the project's foundation; the agent's investment in implementing the design document is the project's execution. The PoC is the bridge between the two: the design document becomes code, the code becomes a game, the game becomes the project.

The design document is complete. The next step is the PoC. The PoC's first concrete action is a 4-file seed. The 4 files are JSON, schema, validator, test. The 4 files are the project's beginning.

---