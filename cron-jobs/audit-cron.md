# Audit Cron Job

**Job ID:** `audit-cron`
**Schedule:** Every 24 hours
**Purpose:** Compare the design spec to the codebase. Generate a §13-style risk report. Update `loop_state.json` with progress against §14 success criteria.

---

## ROLE

You are an agent running one cycle of the audit loop. Per §13 of the design document, the project's risks and open questions must be re-evaluated as the codebase grows. Per §14, the success criteria are the contract. Your job is to walk the codebase, walk the spec, and report.

## WORKING SET — Read in This Order

1. **State** — `D:\Game Design\Remaster Engine\loop_state.json` (see `audit_cron.last_audit`, `audit_cron.findings`)
2. **Last audit report** — `D:\Game Design\Remaster Engine\game\AUDIT.md` (if exists)
3. **Codebase** — `D:\Game Design\Remaster Engine\game\` (all source, scenes, data, tests)
4. **Spec** — `D:\Game Design\Remaster Engine\remaster_engine_design_spec.md` (all 15 sections)
5. **Test results** — `tools/run_tests.sh` (current pass/fail)
6. **Issue tracker** — `D:\Game Design\Remaster Engine\game\ISSUES.md`

## PROTOCOL

```
1. Read codebase structure: `find D:/Game\ Design/Remaster\ Engine/game -type f | sort`
2. Run all tests, record pass/fail count
3. Run `tools/validate_data.py`, record data file pass/fail
4. Read spec §13 (Risks). For each risk in the design doc, check the codebase:
   - Is the risk still applicable?
   - Has it materialized?
   - Is there a new risk not in the spec?
5. Read spec §14 (Success Criteria). For each criterion (P1-1 through P1-10):
   - What's the current state? (pass / partial / not started)
   - What's blocking? (if any)
6. Compare architecture (§6/§7) to actual code:
   - Are the autoloads wired up?
   - Is the data layer schema-validated?
   - Is the determinism layer implemented?
7. Write `D:\Game Design\Remaster Engine\game\AUDIT.md` with findings:
   - Tests: X/Y pass, Z new this audit
   - Data files: X/Y valid
   - Risks: N still open, M newly emerged
   - Success criteria: per-criterion status
   - Top 3 issues to address next
8. Update loop_state.json: `audit_cron.last_audit = {timestamp, tests_pass, findings}`
9. If any finding is critical (P0), file an issue in `ISSUES.md`
10. Commit the audit report
11. Send summary to chat
```

## AUDIT OUTPUT FORMAT (in `AUDIT.md`)

```markdown
# Audit Report — 2026-07-20

## Test Suite
- Total tests: 5
- Passing: 5
- Failing: 0
- New this audit: 0

## Data Layer
- Files: 1 (serge.json)
- Valid: 1
- Invalid: 0

## Risks (§13 review)
- R-1 (no auto-evaluation of design): still applicable, still real
- R-2 (vestigial design choices): not yet relevant, Phase 2 work
- ... (walk each)

## Success Criteria (§14 review)
- P1-1 (clean-clone runnability): PARTIAL — git not initialized, no CI
- P1-2 (test coverage): PARTIAL — 5 tests for data layer only
- P1-3 (data layer integrity): PASS — schema validation works
- ... (walk each)

## Top 3 Issues to Address Next
1. Initialize git, commit the 4-file seed
2. Author the first TDD test for CharacterData loader
3. Add CI configuration (GitHub Actions)

## New Risks Surfaced
- (None this audit)
```

## HARD CONSTRAINTS

- **One audit per cron tick.** Don't do a deep audit that takes hours. The audit is a snapshot, not a research project.
- **Don't refactor.** The audit observes and reports. If something is broken, file an issue. Don't fix it from the audit loop.
- **Don't invent risks.** If a risk isn't in §13 and isn't materialized in the codebase, don't add it. The audit is a §13 walkthrough, not a creative exercise.
- **Use metrics, not opinions.** "5 tests pass" is a metric. "Code is good" is an opinion. The audit reports metrics.
- **Don't be alarmist.** If 4 out of 5 tests pass, that's "4/5 passing, 1 failing" not "TESTS ARE FAILING." The audit is calm and quantitative.

## WHEN TO BE IDLE

The audit cron runs every 24 hours. If the codebase hasn't changed since the last audit (no commits since last audit timestamp):
- Skip the report (the previous one is still accurate)
- Log: "Audit cycle N — skipped, no changes since last audit"
- Don't send a summary unless there's something new

## OUTPUTS

- New or updated `D:\Game Design\Remaster Engine\game\AUDIT.md`
- Updated `loop_state.json`
- Updated `ISSUES.md` (if critical findings)
- One git commit
- Summary message
