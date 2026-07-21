# Snapshot Cron Job

**Job ID:** `snapshot-cron`
**Schedule:** Every 3 hours
**Purpose:** Save current project state to the next slot in the 8-state ring buffer. After 24 hours, the oldest state is replaced. States are segmented (data/, scripts/, scenes/, tests/, tools/) so individual areas can be reverted without fatal consequences.

---

## ROLE

You are an agent running one cycle of the snapshot loop. Per the user's resolved design decision, every 3 hours the project state is saved to a segmented ring buffer. The ring has 8 slots; after 24 hours the oldest is replaced. Each state is a snapshot of `data/`, `scripts/`, `scenes/`, `tests/`, `tools/`, and project config files. The segmentation allows partial restoration.

## WORKING SET — Read in This Order

1. **State** — `D:\Game Design\Remaster Engine\loop_state.json` (see `snapshot_cron.last_snapshot`, `snapshot_cron.ring_position`)
2. **Snapshot script** — `D:\Game Design\Remaster Engine\game\tools\snapshot.py`
3. **Current snapshots** — `D:\Game Design\Remaster Engine\.snapshots\`

## PROTOCOL

```
1. Run: cd "D:/Game Design/Remaster Engine/game" && source .venv/Scripts/activate && python tools/snapshot.py create
2. Run: python tools/snapshot.py list (verify the new state is state-07)
3. Update loop_state.json: `snapshot_cron.last_snapshot = {timestamp, slot, size_mb}`, `snapshot_cron.ring_position = 7`
4. Optional cleanup: if a snapshot is corrupt or has a known-bad commit, log it in loop_memory.md
5. Append to loop_memory.md: "Snapshot cycle N: state-NN created, X.X MB"
6. Send summary (terse — this is housekeeping)
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

## RESTORATION (NOT a cron task)

If the user needs to restore a previous state, this is interactive:

```bash
# Restore everything from state-03
python tools/snapshot.py restore 03

# Restore just the data segment
python tools/snapshot.py restore 03 data

# Restore data and tests
python tools/snapshot.py restore 03 data tests

# See what changed between two states
python tools/snapshot.py diff 02 05
```

The cron job does NOT do restorations. The user does. The cron job's job is to *make sure* restorations are possible by keeping the ring buffer current.

## HARD CONSTRAINTS

- **One snapshot per cron tick.** Don't run the snapshot multiple times in one cycle. The ring rotation is destructive (state-00 is overwritten).
- **Don't snapshot if nothing changed.** If `git status` shows no changes since the last snapshot, log "skipped" and exit.
- **Don't run before the previous snapshot finished.** Each snapshot is independent, but rapid-fire snapshots waste ring slots.
- **Always update state.** Every snapshot must record `last_snapshot` in loop_state.json. If you forget, future audits can't track when states were captured.

## WHEN TO BE IDLE

This cron is never idle if 3 hours have passed. If invoked but nothing changed since the last snapshot, log skip and exit (no ring rotation).

## OUTPUTS

- One new directory in `D:\Game Design\Remaster Engine\.snapshots\state-07\`
- Updated `loop_state.json`
- Updated `loop_memory.md`
- Terse summary message
