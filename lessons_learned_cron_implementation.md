# Building a Game Implementation System with Cron Loops

**A field guide from the Remaster Engine project (Chrono Cross → Godot 4.3)**
**Compiled 2026-07-21**

This document captures the lessons learned building a continuous-flow cron architecture that takes a design document and turns it into working code while the user is away. It is meant to be referenced the next time a similar project is attempted.

---

## 1. The Journey (Context for Future You)

**Design phase (2026-07-19 to 2026-07-20):**
- Built a 74,293-word / 15-section design document for a Chrono Cross fan-remaster in Godot 4.3
- Used a single hourly cron job (one prompt, one loop) to draft the document over 20 ticks (15 content + 5 idle)
- The cron prompted the LLM agent; the agent wrote prose; we extracted decisions for the user via `review.md`
- Total design phase: ~2 days of work, ending in a complete spec on disk + GitHub

**Implementation phase (2026-07-21):**
- User asked the right question: "How do we turn the design into actual code?"
- Initial answer: 6 specialized cron jobs (TDD, data, scaffolding, fix, audit, snapshot) at different cadences
- User pushed back with the real goal: 12-15 substantive decisions per day, crons never idle for long, work happens while user sleeps/works
- Realized the 6-job architecture couldn't self-feed. Work crons idle when queues are empty.
- Final answer: 9 cron jobs in a continuous-flow architecture (planner + decisions + 6 work + 1 daily-variant safety net)
- Implementation phase: ~3-4 hours of session work, ending with 22 passing tests and a working pipeline

**Total project so far:** ~2.5 days of session time, ending with a system that can make progress unattended for 16+ hours.

---

## 2. The Mistakes We Made (Read These First)

These are the failures the agent hit and how they were fixed. Future versions of this system should not have to relearn them.

### Mistake 1: One monolithic cron job for everything

**What we did wrong:** First attempt was a single cron job that wrote tests, fixed bugs, authored data, scaffolded architecture, and audited the spec. We thought "one job, many responsibilities" was efficient.

**Why it failed:** A single job picks favorites. It writes tests because they're easy. It skips data because data is tedious. It never audits because that's not fun. After 24 hours, you have 30 tests and 0 data files.

**The fix:** Six specialized cron jobs, one responsibility each. TDD is a cron. Data authoring is a cron. Fixing bugs is a cron. They fire at their natural cadence (tests every 30 min, data every 2 hours, fixes every 1 hour) and don't compete for cron time.

**The lesson:** When a project has multiple distinct work types, the cron architecture should mirror that. Specialization beats generalization in cron systems.

### Mistake 2: Work crons that idle when queues are empty

**What we did wrong:** Each work cron had a "when idle" section that said "if no work, send a 1-line idle message." We thought this was efficient — no token waste on invented work.

**Why it failed:** The user came back after 16 hours to find 60+ idle messages, 5 snapshots, and almost no real progress. The queues started empty and stayed empty. The user explicitly said: "Will the things you have designed as cron jobs accomplish this task without needing intervention or assistance in renditions towards the goal?" The honest answer was no.

**The fix:** Add a planner cron that runs every 4 hours, reads the spec + state + audit, and seeds the work queues for the other crons. The work crons became consumers, not decision-makers. Add a decisions cron that runs every 8 hours and surfaces batched questions to a `DECISIONS.md` file. The user gets 12-15 decisions per day, batched in 2-3 sessions.

**The lesson:** A cron system that produces nothing while the user is away is a failed system, no matter how elegant the architecture. Idleness is a bug. The fix is to add a coordination layer (planner + decisions) that keeps the work flowing.

### Mistake 3: Crons that invent work to look productive

**What we did wrong:** When the work crons had empty queues, the early drafts said "if queue is empty, read the spec and add a test idea to the queue." The crons would then invent tests, run them, commit them.

**Why it failed:** The tests weren't on the planner's roadmap. They didn't match the locked design. They created forks in the work. The user came back to find 30 tests that tested things the design didn't need, and the actual data files weren't being written.

**The fix:** The work crons are now strict consumers. If the queue is empty, they log a warning and idle. The planner is responsible for what gets done. If the work crons frequently idle, the system is missing a planner (or the planner is missing decisions from the user).

**The lesson:** Invented work is worse than no work. The cron architecture should have clear ownership: the planner decides what to do, the work crons do it. Don't blur the boundary.

### Mistake 4: Crons that retry stuck fixes forever

**What we did wrong:** The fix cron had a "fix the bug" loop with no exit condition. If a fix didn't work, the cron would try again with a slightly different approach. If that didn't work, try again.

**Why it failed:** The cron would commit 10+ "attempted fix N" commits, each leaving the codebase in a worse state. The user came back to a codebase with 15 broken fixes, none of which worked.

**The fix:** The 3-attempt escalation rule. Track `fix_cron.attempt_count[issue_id]` in `loop_state.json`. After 3 consecutive failed fix attempts on the same issue, stop and file a P0 in `ISSUES.md` with all 3 attempts and the current state. Don't loop. Don't paper over. Don't commit a known-broken fix.

**The lesson:** A cron that retries forever is worse than a cron that gives up. The 3-attempt escalation is a circuit breaker. It trades "maybe the 4th try would work" for "the user knows there's a problem and can intervene." Always trade.

### Mistake 5: Confusing `review.md` and `DECISIONS.md`

**What we did wrong:** The design phase used `review.md` for one-shot decisions. When implementation started, we kept the name and pattern.

**Why it failed:** The design-phase `review.md` was for "what should the next section say?" questions — one per section, blocking the next loop tick. The implementation-phase questions are different: "what stat should each level grant?" — many small questions, batched, with defaults so work doesn't stall. Using the same file meant every question blocked the next cron tick, which meant the system was constantly waiting for the user.

**The fix:** New file `DECISIONS.md` with different semantics. Batched questions (3-8 per cycle). 12-hour timeout with default. Non-blocking (the crons use the default if the user doesn't answer). Different name, different cadence, different expectations.

**The lesson:** Naming matters. The review file from the design phase and the review file from the implementation phase are not the same thing, and calling them by the same name hides the difference. When the project's nature changes, the file structure should change to match.

### Mistake 6: Snapshot rotation that double-moved data

**What we did wrong:** The snapshot ring buffer had a rotation loop that iterated from highest slot to lowest, moving each slot one position down. Looked correct in code review.

**Why it failed:** After slot N moves to slot N-1, the next iteration looks at slot N-1 (now containing what was in slot N) and moves it again. The same snapshot gets moved multiple times, ending up in the wrong slot. Tests caught this on the second implementation (the first implementation passed the test, but the test was wrong too).

**The fix:** Two-step rotation. First, delete the oldest slot (it will be discarded). Second, shift each remaining slot one position down in a single pass. The bug was a "step" that conflated the deletion with the shift. Always separate "remove the oldest" from "shift everything down."

**The lesson:** Ring buffer rotation is a 2-step operation, not 1. Test the rotation explicitly with multiple iterations to catch double-move bugs. A unit test that calls `rotate()` once and checks the result doesn't catch the multi-iteration bug.

### Mistake 7: PYTHONPATH contamination from the Hermes environment

**What we did wrong:** The cron jobs run in a fresh session that inherits `PYTHONPATH` from the Hermes environment, which points to `hermes-agent/` and its broken `rpds-py` install. Python scripts the cron ran would import `jsonschema` from hermes-agent, fail with `ModuleNotFoundError: No module named 'rpds.rpds'`, and the cron would crash.

**Why it failed:** The Python import system used `sys.path` order, and `hermes-agent/venv/Lib/site-packages` was first. The project venv's `jsonschema` (with working `rpds-py`) was never reached.

**The fix:** Three layers of defense:
1. `conftest.py` at the project root scrubs `sys.path` before any test module is collected
2. Standalone scripts (e.g., `decisions_helper.py`, `daily_variant.py`) self-scrub at the top before any imports
3. A wrapper bash script (`run_tests.sh`) unsets the env vars before invoking Python

**The lesson:** When cron-ran Python hits import errors that don't reproduce in interactive Python, check `sys.path` and `PYTHONPATH`. The fix is env scrubbing, not reinstalling packages.

### Mistake 8: GitHub auth that fails silently in shell context

**What we did wrong:** We started `gh auth login --web` in foreground terminal calls. The command printed a one-time code, the user authorized in the browser, and the auth flow completed. But the foreground terminal call was interrupted (no job control in bash, command timeout, etc.) and the auth state didn't write to the keychain.

**Why it failed:** The auth flow on the GitHub side said "Authentication complete," but on the local side the credential was never written because the foreground process was killed before it could save. We didn't notice because `gh auth status` was checked too early.

**The fix:** Run the auth flow as a background process (`terminal(background=true, notify_on_complete=true)`) so the process isn't killed by foreground timeouts. Wait for the explicit "completed" notification. Then check `gh auth status` to confirm the credential was actually written.

**The lesson:** Background processes and explicit notifications are the right pattern for long-running auth flows. Foreground calls that hit a timeout abort the process and lose the auth state.

### Mistake 9: Forgetting to check GitHub Actions workflow scope

**What we did wrong:** After getting `gh` authenticated, we tried to push `.github/workflows/ci.yml` to the remote. The push was rejected: "refusing to allow an OAuth App to create or update workflow `.github/workflows/ci.yml` without `workflow` scope."

**Why it failed:** GitHub requires a separate `workflow` scope on the auth token to push workflow files. This is a security feature to prevent token leaks from adding malicious CI. Our initial `gh auth login` only requested `gist, read:org, repo` — not `workflow`.

**The fix:** Run `gh auth refresh --hostname github.com --scopes workflow` to add the workflow scope to the existing token. The user authorizes in the browser (same as initial login), and the scope is added without re-doing the full auth flow.

**The lesson:** When pushing GitHub Actions workflows, check the token's scopes. The `repo` scope is not enough. The `workflow` scope is required for `.github/workflows/*.yml` files.

### Mistake 10: Declaring things unfixable before grepping the config

**What we did wrong:** The original `xhigh` reasoning error had the agent declaring "I can't fix this from the prompt level" twice in early sessions. The user had to push past that framing.

**Why it failed:** The agent's instinct was to assume config-injected values are unfixable from the prompt. But the actual fix was one `hermes config set` away. The agent's confidence in its own unfixability was the bottleneck, not the underlying error.

**The fix:** `hermes config set agent.reasoning_effort medium`. Verified by `grep reasoning_effort config.yaml`. The cron job worked on the next run.

**The lesson:** Before declaring a config error unfixable, grep the config file. The agent's instinct to give up is often wrong. The user has to push past it.

---

## 3. The Architecture That Works (Read These Second)

After fixing the 10 mistakes above, we arrived at a 9-cron architecture. This is the reference design.

### The 9 Crons

| # | Cron | Cadence | Role | What it does |
|---|---|---|---|---|
| 1 | `planner-cron` | 4h | Brain | Reads spec + state + audit. Seeds the work queues for tdd/data/scaffold crons. |
| 2 | `decisions-cron` | 8h | Gate | Surfaces batched decisions to `DECISIONS.md`. Applies 12h timeouts. |
| 3 | `tdd-cron` | 30m | Work | Reads `tdd_cron.test_queue`. Writes one test, makes it pass, commits. |
| 4 | `data-cron` | 2h | Work | Reads `data_cron.target_queue`. Writes one JSON data file, validates, commits. |
| 5 | `scaffolding-cron` | 6h | Work | Reads `scaffolding_cron.target_queue`. Writes one autoload or scene + test. |
| 6 | `fix-cron` | 1h | Work | Reads `ISSUES.md`. Fixes highest-priority bug. 3-attempt escalation. |
| 7 | `snapshot-cron` | 3h | Safety | 8-state ring buffer. Auto-pushes to GitHub. |
| 8 | `audit-cron` | 24h | Meta | Walks §13/§14 of spec, writes `AUDIT.md` with top-3 issues. |
| 9 | `daily-variant-cron` | 24h | Safety | 4-slot daily ring (4 days of history). Coarse-grained safety net. |

### The Data Flow

```
planner-cron (4h)
    │
    ├── reads: spec, state, audit, issues, decisions
    ├── writes: tdd_cron.test_queue, data_cron.target_queue, scaffold_cron.target_queue
    │           (in loop_state.json)
    │
    ▼
decisions-cron (8h)
    │
    ├── reads: spec, locked design, in-progress data
    ├── writes: DECISIONS.md (batched questions with defaults)
    ├── applies: 12h timeouts to unanswered questions
    │
    ▼
tdd-cron (30m) ─── reads tdd_cron.test_queue
data-cron (2h) ─── reads data_cron.target_queue
scaffold-cron (6h) ── reads scaffold_cron.target_queue
    │
    ▼
fix-cron (1h) ─── reads ISSUES.md, applies 3-attempt escalation
    │
    ▼
snapshot-cron (3h) ── 8-state ring + auto-push
    │
    ▼
audit-cron (24h) ── writes AUDIT.md with top-3 issues
    │
    ▼
daily-variant-cron (24h) ── 4-slot daily ring
```

### The State Files

Every cron reads from and writes to these files:

| File | Owner | Read by | Written by | Purpose |
|---|---|---|---|---|
| `loop_state.json` | Crons (especially planner) | All crons | All crons | Machine-readable queues + progress |
| `loop_memory.md` | Crons | All crons | All crons | Cumulative lessons and forward notes |
| `DECISIONS.md` | User + decisions-cron | planner, decisions | decisions-cron, user | Batched review queue with 12h timeouts |
| `ISSUES.md` | User + fix-cron | fix-cron, all error-handling | fix-cron, user | Bug tracker with P0-P3 priorities |
| `AUDIT.md` | audit-cron | planner, user | audit-cron | Daily metrics + top-3 issues |
| `<spec>.md` | User (set up once) | planner, scaffolding | (don't write) | The design contract |
| `<spec>.docx` | Pandoc | (none) | (none — generated for user) | Word view of the spec |

### The Project Directory Structure

```
D:\Game Design\<project>\
├── <project>_design_spec.md      # The design contract
├── <project>_design_spec.docx    # Pandoc-generated Word view
├── loop_state.json               # Machine-readable state
├── loop_memory.md                # Cumulative memory
├── DECISIONS.md                  # Batched review queue (NEW in implementation phase)
├── ISSUES.md                     # Bug tracker
├── AUDIT.md                      # Daily metrics report (cron-written)
├── review.md                     # OLD design-phase file (legacy)
├── cron-jobs/                    # 9 cron prompts
│   ├── planner-cron.md
│   ├── decisions-cron.md
│   ├── tdd-cron.md
│   ├── data-authoring-cron.md
│   ├── scaffolding-cron.md
│   ├── fix-cron.md
│   ├── audit-cron.md
│   ├── snapshot-cron.md
│   └── daily-variant-cron.md
├── .github/
│   └── workflows/ci.yml          # GitHub Actions CI
├── .gitignore
├── game/                         # The implementation project
│   ├── .venv/                    # Python venv (gitignored)
│   ├── .snapshots/               # 8-state ring (gitignored)
│   ├── .daily-variants/          # 4-slot daily ring (gitignored)
│   ├── conftest.py               # PYTHONPATH scrub
│   ├── project.godot             # Godot project file
│   ├── requirements.txt          # Python deps
│   ├── data/                     # Data files
│   │   ├── characters/
│   │   ├── elements/
│   │   └── schemas/
│   ├── scripts/                  # GDScript
│   ├── scenes/                   # Godot scenes
│   ├── tests/                    # Python tests
│   └── tools/                    # Helper scripts
│       ├── validate_data.py
│       ├── decisions_helper.py
│       ├── snapshot.py
│       ├── daily_variant.py
│       └── run_tests.sh
└── (any other project-specific files)
```

### The Decision Format

The user's review surface is `DECISIONS.md`. Each entry looks like:

```markdown
- [ ] [PRIORITY] DEC-NNN: short title | Filed: YYYY-MM-DD
  - Context: why this blocks (which cron is waiting)
  - Options: A | B | C  (when applicable)
  - Default: which option the cron will use on timeout
```

When resolved:
```markdown
- [x] [PRIORITY] DEC-NNN: short title | Resolved: YYYY-MM-DD
  - Resolution: <one-line summary of what was decided>
```

The user opens the file in any text editor, marks `[ ]` → `[x]`, adds a Resolution line, saves. The next cron tick picks up the resolution.

### The 12-Hour Timeout

If a decision is unanswered for 12 hours, the decisions-cron auto-applies the suggested default and marks the entry resolved-with-default:

```markdown
- [x] [P2] DEC-005: Should we use float or int for damage? | Resolved: 2026-07-22
  - Resolution: int (auto-applied after 12.3h)
```

The user can override later by re-filing with `[x] OVERRIDE: <answer>`.

### The 3-Attempt Escalation

If `fix-cron` tries to fix the same bug 3 times and keeps failing, it stops and files a P0 in `ISSUES.md`:

```markdown
- [ ] [P0] ISSUE-007: TechResolver crashes on level 5 character | Escalated: 2026-07-22
  - Original bug: TechResolver returns NaN when character.level > 4
  - Attempt 1: Added type hint `var level: int`. Failed: still NaN.
  - Attempt 2: Cast to int before returning. Failed: still NaN.
  - Attempt 3: Used float() instead of int(). Failed: now returns inf.
  - Current state: <file:line> still has the bug.
  - Recommended next: <your recommendation here>
```

The user (or audit-cron) picks it up.

---

## 4. The Skills To Write (For Future Agents)

These are the reusable skills that should exist in `~/AppData/Local/hermes/skills/`. Some already exist; some are new.

### Already Exists (Good As-Is)

- **`hermes-cron-loops`** — the comprehensive guide to cron loops, state architecture, gateway install, and continuous-flow patterns. Version 1.6.0+ includes the planner + decisions + escalation pattern. Read this first for any cron work.

### Should Be Created

- **`game-design-doc-to-impl`** — a skill for the specific pattern of "design doc + 9-cron implementation pipeline." Encodes the file structure, the 9 cron prompts, the state file conventions, the 12h timeout, the 3-attempt escalation.

- **`headless-game-impl`** — a skill for running a game implementation pipeline headlessly (no visual editor). Encodes the 4-file PoC seed recipe, the PYTHONPATH scrub, the schema validation, the auto-push pattern.

- **`fan-work-project-posture`** — a skill for projects that are "fan work, no commercial purpose." Encodes the legal posture, the placeholder-asset pattern, the GitHub-as-testing-space pattern, the no-financial-payment automation.

### Should Be Updated

- **`hermes-cron-loops` v1.7.0** — add the snapshot-rotation-bug and PYTHONPATH-contamination pitfalls (currently in v1.5.0/v1.6.0 but worth reinforcing), the GitHub workflow-scope gotcha, the auto-push pattern, the daily-variant pattern as a coarser-grained safety net.

---

## 5. The Reusable Templates

These are the files that get copied into every new project of this type. The exact content can vary, but the shape is the same.

### `cron-jobs/planner-cron.md` (template)

The planner is the brain. It does NOT write code. It decides what the other crons should do.

```markdown
# Planner Cron Job

**Schedule:** Every 4 hours
**Purpose:** The brain. Seeds the work queues for tdd/data/scaffold crons.

## PROTOCOL

1. Read `loop_state.json` (queues + progress)
2. Read `AUDIT.md` (last 1-day report)
3. Read `DECISIONS.md` (batched review queue)
4. Read `ISSUES.md` (open bugs)
5. Read `loop_memory.md` (last 5 entries)
6. Read `<spec>.md` (relevant sections)
7. For each work cron, decide what to queue:
   - tdd-cron: next 1-3 tests (dependency-ordered)
   - data-cron: next 1-3 data files (locked-design-priority)
   - scaffolding-cron: next 1-2 architecture items
8. Write the queues to loop_state.json
9. If blocked, file a decision via decisions_helper.add()
10. Append to loop_memory.md, send terse summary

## HARD CONSTRAINTS
- Never invent data not in the locked design
- Never modify code or data files
- Respect the dependency order (tests → data loaders → scenes → UI)
- Cap each queue at 5 items
```

### `cron-jobs/decisions-cron.md` (template)

The gate. Surfaces batched questions, applies 12h timeouts.

```markdown
# Decisions Cron Job

**Schedule:** Every 8 hours
**Purpose:** The gate. Surfaces batched questions to DECISIONS.md.

## PROTOCOL

1. Run: python game/tools/decisions_helper.py apply-timeouts
   (auto-resolves decisions past 12h with their default)
2. Read the current DECISIONS.md
3. Walk the spec, schemas, in-progress data
4. Identify NEW gaps:
   - Required schema fields with placeholder values
   - Locked design choices referencing undefined things
   - Choices the planner flagged as "I made this up"
5. Add 3-8 new decisions via decisions_helper.add()
6. Cap queue at 30 open items
7. Append to loop_memory.md, send summary

## HARD CONSTRAINTS
- Decisions are batched (3-8 per cycle)
- Defaults must be reasonable (reversible if wrong)
- Never modify the spec
- Don't ask questions already answered
- Prioritize blockers
```

### `cron-jobs/<work-cron>.md` (template, e.g. tdd)

The work crons are consumers. They read queues, do one unit of work, commit.

```markdown
# TDD Cron Job

**Schedule:** Every 30 minutes
**Purpose:** Author one test, make it pass, commit.

## PROTOCOL

1. Run: cd game && source .venv/Scripts/activate && python -m pytest tests/ -v
2. If tests fail, do the error-handling extension first (read ISSUES.md, fix bugs)
3. Read tdd_cron.test_queue in loop_state.json
4. If queue is empty: log "queue empty" in loop_state.json, idle. DO NOT INVENT WORK.
5. Else: pick the next test, write it, run (fails), write minimal code, run (passes), commit
6. If 3 consecutive failures: stop, file P0 in ISSUES.md
7. Update loop_state.json, append to loop_memory.md, send summary

## HARD CONSTRAINTS
- One test per cycle
- Tests must fail first
- No library refactors
- No skipping the commit
- If queue is empty, idle with a warning, not invent work
```

### `cron-jobs/snapshot-cron.md` (template)

The fine-grained safety net. 8-state ring at 3h cadence. Auto-pushes to GitHub.

```markdown
# Snapshot Cron Job

**Schedule:** Every 3 hours
**Purpose:** 8-state ring buffer. Auto-pushes to GitHub.

## PROTOCOL

1. Run: python game/tools/snapshot.py create
2. Update loop_state.json: snapshot_cron.last_snapshot
3. If git status is dirty: git add -A && git commit
4. If unpushed commits exist: git push origin main
   - If push fails: log it but DO NOT FAIL the snapshot
5. Append to loop_memory.md, send terse summary

## HARD CONSTRAINTS
- One snapshot per cycle
- Always update state
- Push failure is not a tick failure
- No force pushes
```

### `cron-jobs/daily-variant-cron.md` (template)

The coarse-grained safety net. 4-slot ring at 24h cadence.

```markdown
# Daily Variant Cron Job

**Schedule:** Every 24 hours
**Purpose:** 4-slot daily ring. Coarse-grained safety net.

## PROTOCOL

1. Run: python game/tools/daily_variant.py create
2. Update loop_state.json: daily_variant_cron.last_variant
3. If git status is dirty: commit (don't push — variants are large)
4. Append to loop_memory.md

## HARD CONSTRAINTS
- One variant per cycle
- Segments only (no venv, no snapshots, no variants)
- Local only, no push
```

### `cron-jobs/fix-cron.md` (template)

The bug fixer. 3-attempt escalation.

```markdown
# Fix Cron Job

**Schedule:** Every 1 hour
**Purpose:** Fix bugs from ISSUES.md with 3-attempt escalation.

## PROTOCOL

1. Read ISSUES.md
2. If no open issues: log idle, exit (this is the only cron allowed to idle silently)
3. Else: pick highest-priority open issue
4. Write a failing test that reproduces the bug
5. Apply minimal fix
6. Run all tests
7. If pass: commit, mark resolved, update state
8. If fail 3 times: file P0 with all 3 attempts and current state
9. Track fix_cron.attempt_count[issue_id] in loop_state.json
10. Append to loop_memory.md, send summary

## HARD CONSTRAINTS
- One issue per cycle
- Minimal change
- 3-attempt escalation (no infinite loops)
- No spec changes without review
```

### `cron-jobs/audit-cron.md` (template)

The meta-reviewer. Daily report with top-3 issues.

```markdown
# Audit Cron Job

**Schedule:** Every 24 hours
**Purpose:** Walk §13/§14, write AUDIT.md with metrics.

## PROTOCOL

1. Read codebase structure
2. Run all tests
3. Run validate_data.py
4. Walk §13 risks, mark which materialized
5. Walk §14 success criteria, mark progress per criterion
6. Compare to last audit, surface deltas
7. Write AUDIT.md with:
   - Tests: X/Y pass
   - Data: X/Y valid
   - Risks: N open, M new
   - Success criteria: per-criterion status
   - Top 3 issues to address
   - New risks surfaced
8. File P0 in ISSUES.md for any critical findings
9. Commit, send summary

## HARD CONSTRAINTS
- One audit per tick
- Don't refactor (observe and report)
- Use metrics, not opinions
- Skip if no changes since last audit
```

---

## 6. The Helper Scripts (Always Include These)

These are the tools that the crons depend on. Every project of this type should have them.

### `game/conftest.py` — PYTHONPATH scrub

```python
import sys
sys.path[:] = [p for p in sys.path if "hermes" not in p.lower()]
import os
for env_var in ("PYTHONPATH", "PYTHONHOME"):
    if env_var in os.environ:
        del os.environ[env_var]
for env_var in list(os.environ.keys()):
    if "hermes" in os.environ[env_var].lower():
        del os.environ[env_var]
```

### `game/tools/decisions_helper.py` — Decision queue state machine

The key functions: `add()`, `resolve()`, `apply_timeouts()`, `load_queue()`, `format_summary()`. See the Remaster Engine implementation for the full code (~200 lines).

### `game/tools/snapshot.py` — 8-state ring buffer

The key functions: `create_snapshot()`, `list_states()`, `restore_snapshot()`, `diff_snapshots()`. **Critical: rotation is a 2-step operation** (delete oldest, then shift down). Single-pass shift loop only. Test with multi-iteration rotation.

### `game/tools/daily_variant.py` — 4-slot daily ring

Same pattern as snapshot, but with RING_SIZE=4 and a 24h cadence. Used as a coarser-grained safety net.

### `game/tools/validate_data.py` — JSON schema validator

Walks `data/` directories, validates each JSON file against its schema. Used by the CI, the data-cron, and the audit-cron.

### `game/tools/run_tests.sh` — Test wrapper

Bash script that unsets PYTHONPATH and PYTHONHOME before running pytest. Cron jobs call this to run tests.

---

## 7. The 4-File PoC Seed (First Concrete Action)

When transitioning from a design document to actual code, the first concrete action is a 4-file seed. This is the minimum viable product for the data layer.

1. **`data/characters/<one>.json`** — one example data file
2. **`data/schemas/<one>.schema.json`** — the JSON Schema for that data type
3. **`tools/validate_data.py`** — the schema validator
4. **`tests/test_<one>_data.py`** — the TDD test suite

Once these 4 files exist and the tests pass, the crons can take over. Each subsequent cron tick adds one more file in the same pattern.

---

## 8. The GitHub Setup (The 4 Things You Need)

Before any cron work, set up GitHub:

1. **Install `gh` CLI** — `winget install --id GitHub.cli --accept-package-agreements --accept-source-agreements`
2. **Authenticate** — `gh auth login --web --git-protocol https` (run as background process, not foreground, to avoid timeout-related kill)
3. **Add the `workflow` scope** — `gh auth refresh --hostname github.com --scopes workflow` (also background)
4. **Set up the remote** — `gh repo create <name> --public` (or use an existing repo), then `git remote add origin <url>`

Then on the GitHub side:
1. **Add the CI workflow** at `.github/workflows/ci.yml` — runs pytest + Godot smoke test on every push
2. **Auto-push is in the snapshot-cron** — every 3h, if there are unpushed commits, push them

---

## 9. The Time Estimate (For Future Planning)

Based on the Remaster Engine experience:

| Phase | Effort | Calendar time (part-time) |
|---|---|---|
| Setup (4-file seed + 9 crons + GitHub) | ~6-8 hours | ~1-2 days |
| PoC complete (§15.4 — 1 char, 1 map, 1 combat, save/load) | ~30-50 hours | ~3-5 weeks |
| Phase 1 complete (10 chapters of faithful content) | ~400-600 hours | ~7-10 months |
| Phase 2 (stabilization audit) | +100-150 hours | +1-2 months |
| Phase 3 (redesign — 6 bases, 36 supports, level-tiers) | +200-300 hours | +3-4 months |
| **Total: shippable fan-work remaster** | **~1000-1500 hours** | **~12-18 months** |

This assumes:
- The crons fire 60-70% of the time
- You answer 10-12 decisions per day
- You take 1-2 weeks off for life events
- Visual content is placeholder or AI-generated

**The single biggest variable is your attention.** The crons are reliable. Your time is not. Budget accordingly.

---

## 10. The Final Note (For Future You)

This is a system that works. It is not a system that finishes itself. The crons can do the volume work. They cannot do the visual work (sprites, music), the creative judgment, the design quality gate, or the motivation work.

Treat this as a serious long-term project. Show up for it twice a day. The 12-18 month estimate is realistic if you do. If you treat it as a thing you'll do when you have time, it will drift indefinitely.

The 10 mistakes in section 2 are the ones to avoid. The architecture in section 3 is the one that works. The skills in section 4 should exist before you start. The templates in section 5 are the ones to copy. The helper scripts in section 6 are the dependencies. The 4-file seed in section 7 is the first step. The GitHub setup in section 8 is the prerequisite. The time estimate in section 9 is the budget.

**Go build something. The crons are waiting.**
