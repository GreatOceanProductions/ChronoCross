# Issues — Bug Tracker

This file is the queue of bugs to fix. The `fix-cron` job reads this file every hour and resolves the highest-priority issue.

**Format:**
```markdown
- [ ] [PRIORITY] ISSUE-NNN: short description | Filed: YYYY-MM-DD
  - Reproduction: how to trigger
  - Expected: what should happen
  - Actual: what does happen
  - Status: open | in_progress | resolved | wontfix
```

**Priority levels:**
- **P0:** Crashes, data corruption, security. Fix immediately.
- **P1:** Blocks other work. Fix within 24 hours.
- **P2:** Doesn't block. Fix within the week.
- **P3:** Cosmetic. Fix when bored.

**When resolved, replace `[ ]` with `[x]` and add:**
- Resolved date and commit hash
- One-line resolution summary

**Example:**
```markdown
- [x] [P1] ISSUE-001: validate_data.py crashes on empty files | Resolved: 2026-07-20 (commit abc123)
  - Resolution: added early return when no files discovered
```

---

## Open Issues

(none yet — file the first one as work progresses)

## Resolved Issues

(none yet)
