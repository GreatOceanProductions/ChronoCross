# Fix Cron Job

**Job ID:** `fix-cron`
**Schedule:** Every 1 hour
**Purpose:** Resolve bugs from `ISSUES.md` with minimal targeted fixes.

---

## ROLE

You are an agent running one cycle of the fix loop. Your job is to find unaddressed issues, fix them, run tests, commit, and update the issue tracker. Per §9.3 of the design document, fix loops are the "reactive" path: things break, we fix them, we move on.

## WORKING SET — Read in This Order

1. **Issue tracker** — `D:\Game Design\Remaster Engine\game\ISSUES.md` (this is the queue)
2. **State** — `D:\Game Design\Remaster Engine\loop_state.json` (see `fix_cron.last_fixes`)
3. **Test suite** — Run `tools/run_tests.sh` to see what's currently failing
4. **loop_memory.md** — last 5 entries, especially `FAILURES` section
5. **Spec** — `D:\Game Design\Remaster Engine\remaster_engine_design_spec.md` if the fix is design-related
6. **Source code** — the file(s) implicated in the issue

## PROTOCOL

```
1. Read ISSUES.md
2. If no unaddressed issues (status: open or in_progress), idle and exit
3. Otherwise:
   a. Pick the highest-priority issue (P0 > P1 > P2 > P3, then by date)
   b. Mark it `in_progress` in ISSUES.md
   c. Reproduce the bug:
      - Read the test or write a new failing test that demonstrates it
      - Run tests, confirm the new test fails
   d. Apply MINIMAL fix:
      - Smallest change that makes the test pass
      - Don't refactor unrelated code
      - Don't add new features "while you're there"
   e. Run ALL tests: `tools/run_tests.sh`
      - If new test passes AND no other tests broke, the fix is good
      - If something else broke, the fix was too broad — revert and try again
   f. Commit: `git add -A && git commit -m "fix: [ISSUE-ID] [description]\n\n[what was wrong, what changed]"`
   g. Update ISSUES.md: mark `resolved` with the commit hash and a 1-line summary
   h. Update loop_state.json: `fix_cron.last_fixes.push({id, commit, resolved_at})`
   i. Append to loop_memory.md: "Fix [ISSUE-ID]: [description] - [commit hash]"
   j. Send summary
4. After resolving one issue, check for more. If time, fix another. Otherwise, exit.
```

## HARD CONSTRAINTS

- **One issue per cycle.** Don't bundle fixes. Each fix is a separate commit with a separate test.
- **Minimal change.** If the fix is more than ~20 lines of code, you're probably fixing the wrong thing. Step back, re-read the issue.
- **Test the fix.** A fix without a test is a fix that will regress.
- **Don't fix what's not broken.** If the issue is "we should also do X," that's a feature request, not a bug. File it in `FEATURE_REQUESTS.md`, not `ISSUES.md`.
- **No spec changes without review.** If a fix requires changing the design document, file it as a separate design-revision issue. Don't silently update the spec.
- **Preserve the data layer.** If the fix touches data files, run `tools/validate_data.py` after.

## ISSUE FORMAT (in `ISSUES.md`)

```markdown
- [ ] [P1] ISSUE-001: validate_data.py crashes on empty files | Filed: 2026-07-20
  - Reproduction: `python tools/validate_data.py` when no JSON files exist
  - Expected: graceful "No data files found" message, exit 0
  - Actual: crash with stack trace
  - Status: open
```

When resolved:
```markdown
- [x] [P1] ISSUE-001: validate_data.py crashes on empty files | Resolved: 2026-07-20 (commit abc123)
  - Resolution: added early return when no files discovered
```

## PRIORITY LEVELS

- **P0:** Crashes, data corruption, security issues. Fix immediately.
- **P1:** Bugs that block other work. Fix within 24 hours.
- **P2:** Bugs that don't block. Fix within the week.
- **P3:** Cosmetic, "would be nice." Fix when bored.

## WHEN TO BE IDLE

If `ISSUES.md` has no entries or all entries are `resolved`/`closed`:
- Log idle
- Send: "Fix cycle N — idle, no open issues."

## OUTPUTS

- Modified source file(s) in `D:\Game Design\Remaster Engine\game\`
- One new or modified test file
- Updated `ISSUES.md` (issue marked resolved)
- One git commit
- Updated state and memory
- Summary message
