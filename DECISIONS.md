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

**The 12-hour timeout:** If you don't answer within 12 hours of filing, the cron will
auto-apply the suggested default and mark the decision resolved-with-default. You can
override later by re-filing with a `[x] OVERRIDE` marker.

---

## Open Decisions

(none — file the first one as work progresses)

## Resolved Decisions

(none yet)
