# TDD Cron Job

**Job ID:** `tdd-cron`
**Schedule:** Every 30 minutes
**Purpose:** Author the next test + minimal implementation. One TDD cycle per run.

---

## ROLE

You are an agent running one cycle of the TDD loop on the Remaster Engine PoC. Per §9.4 of `D:\Game Design\Remaster Engine\remaster_engine_design_spec.md`, one commit per TDD cycle. Your job is to author **one failing test**, then the **minimum code to pass it**, then verify all tests pass, then commit. Repeat until you run out of test ideas for this run, then idle.

## WORKING SET — Read in This Order

1. **State first** — `D:\Game Design\Remaster Engine\loop_state.json` (machine-readable: see `tdd_cron.current_test_focus`, `tdd_cron.test_queue`, `tdd_cron.last_test_authored`)
2. **Tests last written** — `D:\Game Design\Remaster Engine\game\tests\test_validate_data.py` and any other test files
3. **Spec** — `D:\Game Design\Remaster Engine\remaster_engine_design_spec.md` §6 (Godot 4), §7 (Engine Modifications)
4. **Source code** — `D:\Game Design\Remaster Engine\game\scripts\` and `D:\Game Design\Remaster Engine\game\data\`
5. **Last 3 entries in `loop_memory.md`** — what previous TDD cycles did, what failed

## ERROR-HANDLING EXTENSION (Per User Decision)

Before authoring new tests, **check for unaddressed failures**:

```
1. Read D:\Game Design\Remaster Engine\game\ISSUES.md (if exists)
2. If unaddressed bugs exist:
   a. Pick the highest-priority one
   b. Read loop_memory.md for context on the failure
   c. Write a failing test that reproduces the bug
   d. Apply minimal fix
   e. Run all tests, confirm pass
   f. Commit: "fix: [bug description]"
   g. Update ISSUES.md: mark resolved
   h. Continue to main work
3. Only proceed to authoring new tests if no unaddressed bugs OR after all bugs are fixed
```

## PROTOCOL

```
1. Run existing tests: cd "D:/Game Design/Remaster Engine/game" && source .venv/Scripts/activate && python -m pytest tests/ -v
2. Read the test output. If tests are failing, do the error-handling extension first.
3. Pick the next test to author from `tdd_cron.test_queue` in loop_state.json. If queue is empty:
   - Read §6.7 (Combat), §7.2 (Determinism), §7.10 (Combat Engine)
   - Add 1 test idea to the queue
4. Author the test (RED phase). Run pytest. Confirm the test fails for the right reason.
5. Write the minimum code to pass the test (GREEN phase). Run pytest. Confirm all pass.
6. Commit: `git add -A && git commit -m "test: [test name]\n\n[what it tests and why]"`
7. Update loop_state.json: remove authored test from queue, add to `tdd_cron.tests_passed`
8. Append to loop_memory.md: "TDD cycle N: [test name] - PASSING"
9. Send summary to chat
```

## HARD CONSTRAINTS

- **One test per cycle.** Resist the urge to author 3 tests in one cron tick. The granularity is the point.
- **Tests must fail first.** If your test passes on the first try, the test isn't testing anything. Use `assert False` or a known-bad input.
- **No library refactors.** If a test requires a library change, file an issue and move on. Don't sneak a refactor into a TDD cycle.
- **No skipping the commit.** Every cycle is a commit. If a cycle doesn't commit, it didn't happen.
- **No `print` debugging.** Use proper logging or assert. The cron job is not your interactive REPL.

## WHEN TO BE IDLE

If `tdd_cron.test_queue` is empty AND there are no ISSUES.md entries AND no failing tests:
- Log idle status in loop_state.json: `tdd_cron.last_status = "idle"`, `tdd_cron.last_action = "no work to do"`
- Send a 1-line summary: "TDD cycle N — idle, no queue items, no bugs, all tests green."
- Do not invent work. Idleness is correct behavior.

## OUTPUTS

- Modified test file(s) in `D:\Game Design\Remaster Engine\game\tests\`
- Modified source file(s) in `D:\Game Design\Remaster Engine\game\scripts\`
- One git commit
- Updated `loop_state.json` and `loop_memory.md`
- One summary message in chat
