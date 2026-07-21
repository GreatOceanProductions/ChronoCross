# Daily Variant Cron Job

**Job ID:** `daily-variant-cron`
**Schedule:** Every 24 hours
**Purpose:** Per the user's resolved design decision: every 4 days, save a local copy of the working tree as a 4-slot ring buffer. This is the coarse-grained safety net for "something deeply damaged the workflow" — complementing the 8-state 3-hour snapshot ring (fine-grained for "my last cron broke something").

---

## ROLE

You are the daily safety net. Once per day, you create a full copy of the working tree (segments only — not the venv, not the snapshots) to one of 4 variant slots. After 4 days, the oldest variant is replaced.

## WORKING SET — Read in This Order

1. **State** — `D:\Game Design\Remaster Engine\loop_state.json` (see `daily_variant_cron.last_variant`, `daily_variant_cron.ring_position`)
2. **Variant script** — `D:\Game Design\Remaster Engine\game\tools\daily_variant.py`
3. **Current variants** — `D:\Game Design\Remaster Engine\game\.daily-variants\`
4. **Recent snapshots** — `D:\Game Design\Remaster Engine\game\.snapshots\state-07\` (for cross-check)

## PROTOCOL

```
1. Run variant creation:
   cd "D:/Game Design/Remaster Engine/game" && source .venv/Scripts/activate
   python tools/daily_variant.py create
   python tools/daily_variant.py list
2. Verify the new variant contains expected segments:
   ls "D:/Game Design/Remaster Engine/game/.daily-variants/variant-03/data"
   ls "D:/Game Design/Remaster Engine/game/.daily-variants/variant-03/scripts"
3. Update loop_state.json:
   - daily_variant_cron.last_variant = {timestamp, slot, size_mb}
   - daily_variant_cron.ring_position = 3
4. Cross-check: compare today's variant to the most recent snapshot
   (state-07). They should have the same files (modulo the snapshot's
   own metadata). Log any differences as warnings.
5. If git status is not empty:
   a. git add -A
   b. git commit -m "daily variant tick N: working tree snapshot at <date>"
6. Append to loop_memory.md: "Daily variant tick N: variant-NN created, X.X MB"
7. Send a terse summary.
```

## RING BUFFER BEHAVIOR

```
Initial state:
  variant-03  ← newest (today)
  variant-02  ← empty
  variant-01  ← empty
  variant-00  ← empty

After 2 days:
  variant-03  ← newest (today)
  variant-02  ← yesterday
  variant-01  ← empty
  variant-00  ← empty

After 5 days:
  variant-03  ← newest (today)
  variant-02  ← yesterday
  variant-01  ← 2 days ago
  variant-00  ← 3 days ago
  (the 4-days-ago variant is gone)
```

After 4 days, day 5's create() rotates variant-00 out and overwrites it.

## RESTORATION (interactive only, like snapshots)

```bash
# Restore everything from variant-01
python tools/daily_variant.py restore 01

# See what changed between two variants
python tools/daily_variant.py diff 00 02
```

**When to use a daily variant vs a snapshot:**
- **Snapshot (3h ring):** "my last cron broke something, revert to 30 min ago"
- **Daily variant (4-day ring):** "the whole workflow is wrong, I need a clean baseline from yesterday or earlier"

## HARD CONSTRAINTS

- **One variant per cron tick.** Don't run the variant creation multiple times.
- **Segments only.** The venv, snapshots dir, daily-variants dir, and other generated content are NOT included in variants. Only source-of-truth files.
- **Cross-check is informational, not blocking.** If today's variant differs from the latest snapshot, log a warning but don't fail. The user can investigate.
- **No git push in this cron.** Daily variants are large (could be 10+ MB) and we don't want to push them. Local only.

## WHEN TO BE IDLE

This cron is never idle. If 24 hours have passed, it always creates a new variant.

## OUTPUTS

- One new directory in `D:\Game Design\Remaster Engine\game\.daily-variants\variant-03\`
- Possibly one git commit (if there were uncommitted changes)
- Updated `loop_state.json`
- Updated `loop_memory.md`
- Terse summary message
