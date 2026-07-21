# Snapshot Cron Job (with auto-push)

**Job ID:** `snapshot-cron`
**Schedule:** Every 3 hours
**Purpose:** Save current project state to the 8-state ring buffer. After 24 hours, the oldest state is replaced. States are segmented (data/, scripts/, scenes/, tests/, tools/) so partial restoration is possible.

**Also handles auto-push to GitHub** (per user decision 2026-07-21): after each snapshot, if there are unpushed commits, push them to `origin main`. The CI workflow will catch any breakage.

---

## ROLE

You are running one cycle of the snapshot loop. Per the user's resolved design decision, every 3 hours the project state is saved to a segmented ring buffer. The ring has 8 slots; after 24 hours the oldest is replaced. Each state is a snapshot of `data/`, `scripts/`, `scenes/`, `tests/`, `tools/`, and project config files.

## WORKING SET — Read in This Order

1. **State** — `D:\Game Design\Remaster Engine\loop_state.json` (see `snapshot_cron.last_snapshot`, `snapshot_cron.last_push`)
2. **Snapshot script** — `D:\Game Design\Remaster Engine\game\tools\snapshot.py`
3. **Current snapshots** — `D:\Game Design\Remaster Engine\game\.snapshots\`
4. **Git status** — `cd "D:\Game Design\Remaster Engine" && git status --porcelain`
5. **Git log** — `git log --oneline origin/main..HEAD` (unpushed commits)

## PROTOCOL

```
1. Run snapshot creation:
   cd "D:/Game Design/Remaster Engine/game" && source .venv/Scripts/activate
   python tools/snapshot.py create
   python tools/snapshot.py list
2. Update loop_state.json: snapshot_cron.last_snapshot = {timestamp, slot, size_mb}
3. If git status is not empty (uncommitted changes exist):
   a. Run: git add -A
   b. Run: git commit -m "snapshot tick N: housekeeping"
   c. Note the commit hash
4. If there are unpushed commits (git log origin/main..HEAD is non-empty):
   a. Export PATH to include gh CLI: export PATH="/c/Program Files/GitHub CLI:$PATH"
   b. Verify gh auth: gh auth status
   c. If authed, run: git push origin main
   d. If push fails (e.g., auth expired), log it but DO NOT FAIL the snapshot.
   e. Update loop_state.json: snapshot_cron.last_push = {timestamp, commit, status}
5. Append to loop_memory.md: "Snapshot tick N: state-NN created, X commits pushed"
6. Send a terse summary (this is housekeeping)
```

## RING BUFFER BEHAVIOR

```
Initial state (after first run):
  state-07  ← newest
  state-06  ← empty
  ...
  state-00  ← empty

After 2nd run (3 hours later):
  state-07  ← newest
  state-06  ← was state-07
  state-05  ← empty
  ...
  state-00  ← empty

After 9th run (24 hours later):
  state-07  ← newest
  state-06  ← 6 hours old
  ...
  state-01  ← 21 hours old
  state-00  ← was state-07 from 24 hours ago (overwritten)
```

The implementation is in `tools/snapshot.py`. The `create` command handles rotation automatically.

## RESTORATION (NOT a cron task — interactive only)

If the user needs to restore a previous state, this is interactive:

```bash
# Restore everything from state-03
python tools/snapshot.py restore 03

# Restore just the data segment
python tools/snapshot.py restore 03 data

# See what changed between two states
python tools/snapshot.py diff 02 05
```

The cron job does NOT do restorations. The user does. The cron job's job is to *make sure* restorations are possible by keeping the ring buffer current.

## AUTO-PUSH BEHAVIOR

Per user decision 2026-07-21: the crons should auto-push to GitHub. The snapshot-cron is the right place for this because:

1. **Snapshot runs every 3 hours** — frequent enough to keep the remote current
2. **Pushing after a commit** — natural pairing: snapshot, then push
3. **CI catches breakage** — if a push breaks the build, the user sees it on the GitHub Actions page

**Failure handling:** If `git push` fails (auth expired, network, conflict), log the failure and continue. The next snapshot tick will retry. Don't fail the whole cron tick over a push failure.

**If auth is not set up:** Run `gh auth status` first. If it fails, skip the push with a clear log message. The local commit is preserved; the user can push manually.

## HARD CONSTRAINTS

- **One snapshot per cron tick.** Don't run the snapshot multiple times in one cycle. The ring rotation is destructive.
- **Don't snapshot if nothing changed.** If `git status` shows no changes since the last snapshot, log "skipped" and exit.
- **Always update state.** Every snapshot must record `last_snapshot` in loop_state.json.
- **Push failure is not a tick failure.** Log it, continue, retry next tick.
- **No force pushes.** The push must be a normal `git push`, not `--force` or `--force-with-lease`. Conflicts should be reported, not overwritten.

## WHEN TO BE IDLE

This cron is never idle if 3 hours have passed. If invoked but nothing changed since the last snapshot, log skip and exit (no ring rotation).

## OUTPUTS

- One new directory in `D:\Game Design\Remaster Engine\game\.snapshots\state-07\`
- Possibly one or more git commits (if there were uncommitted changes)
- Possibly a `git push` to origin
- Updated `loop_state.json`
- Updated `loop_memory.md`
- Terse summary message
