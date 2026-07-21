"""8-state ring buffer snapshot system.

Per the user's resolved design decision: every 3 hours, save current
progress to one of 8 segmented state slots, transitioning the project
between active states. After 24 hours, the first state is replaced
by the new 9th state. Each state is segmented (scenes/, scripts/,
data/, tests/, configs/) so different areas can be reverted if errors
occur without it being fatal to the entire program.

Usage:
    python tools/snapshot.py create          # Create next snapshot in ring
    python tools/snapshot.py list            # List existing snapshots
    python tools/snapshot.py restore 03      # Restore state-03 in full
    python tools/snapshot.py restore 03 data # Restore just the data segment
    python tools/snapshot.py restore 03 scenes scripts  # Restore multiple segments
    python tools/snapshot.py diff 02 05      # Show what changed between states
    python tools/snapshot.py rotate          # Force rotation (testing)

The 8-state ring buffer: state-00 (oldest) through state-07 (newest).
A new snapshot first deletes state-00, then renumbers state-01..07
to state-00..06, then creates the new state-07 from current files.

Segments are subdirectories of game/. Anything not in a segment is
ignored (e.g., the .venv/ virtualenv is not snapshotted).
"""
import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Project layout
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent  # game/tools/snapshot.py -> game/
SNAPSHOTS_DIR = PROJECT_DIR / ".snapshots"  # game/.snapshots/

# We use game/.snapshots/ (project-local) rather than a higher-up
# location. Keeps the snapshots next to the project for easy
# version control, backup, and per-project rotation.

# Ring buffer config
RING_SIZE = 8

# Segments to snapshot (relative to game/). Anything not listed is ignored.
SEGMENTS = ["data", "scripts", "scenes", "tests", "tools", "conftest.py", "requirements.txt", "project.godot"]


def get_state_dir(slot: int) -> Path:
    """Return the path to state-NN directory."""
    return SNAPSHOTS_DIR / f"state-{slot:02d}"


def list_states() -> list[Path]:
    """Return all existing state directories, sorted by slot number."""
    if not SNAPSHOTS_DIR.exists():
        return []
    return sorted(SNAPSHOTS_DIR.glob("state-*"),
                  key=lambda p: int(p.name.split("-")[1]))


def rotate() -> None:
    """Shift the ring: delete state-00, shift state-01..07 down to state-00..06."""
    if not SNAPSHOTS_DIR.exists():
        return
    # Reverse iterate: from highest slot to lowest, shift down
    # Step 1: Remove the oldest slot (it will be discarded)
    oldest = get_state_dir(0)
    if oldest.exists():
        shutil.rmtree(oldest)
    # Step 2: Shift each slot one position lower (slot N -> slot N-1)
    for slot in range(1, RING_SIZE):
        src = get_state_dir(slot)
        dst = get_state_dir(slot - 1)
        if src.exists():
            src.rename(dst)
    # After this: old state-01 is at state-00, ..., old state-07 is at state-06.
    # state-07 is now empty and will be filled by the new snapshot.


def create_snapshot() -> Path:
    """Create a new snapshot in the next ring slot. Returns the new state directory."""
    SNAPSHOTS_DIR.mkdir(exist_ok=True)
    rotate()  # make room

    new_state = get_state_dir(RING_SIZE - 1)  # state-07
    new_state.mkdir()

    # Copy each segment
    for seg in SEGMENTS:
        src = PROJECT_DIR / seg
        dst = new_state / seg
        if not src.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    # Write metadata
    meta = new_state / "snapshot.json"
    meta.write_text(
        f'{{"created_at": "{datetime.now(timezone.utc).isoformat()}", "slots": {RING_SIZE}}}\n',
        encoding="utf-8"
    )

    return new_state


def restore_snapshot(slot: int, segments: list[str] | None = None) -> None:
    """Restore from state-NN. If segments is given, restore only those segments."""
    if not 0 <= slot < RING_SIZE:
        print(f"ERROR: slot must be 0-{RING_SIZE - 1}, got {slot}", file=sys.stderr)
        sys.exit(1)

    state = get_state_dir(slot)
    if not state.exists():
        print(f"ERROR: state {slot} does not exist", file=sys.stderr)
        sys.exit(1)

    targets = segments if segments else SEGMENTS
    for seg in targets:
        src = state / seg
        dst = PROJECT_DIR / seg
        if not src.exists():
            print(f"  [SKIP] {seg} (not in snapshot)")
            continue
        if dst.exists():
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        print(f"  [OK]   restored {seg}")


def list_snapshots() -> None:
    """Print all existing snapshots with timestamps."""
    states = list_states()
    if not states:
        print("No snapshots yet.")
        return
    print(f"Snapshots ({len(states)}/{RING_SIZE} slots used):")
    for state in states:
        slot = int(state.name.split("-")[1])
        meta_file = state / "snapshot.json"
        timestamp = "unknown"
        if meta_file.exists():
            try:
                import json
                m = json.loads(meta_file.read_text(encoding="utf-8"))
                timestamp = m.get("created_at", "unknown")
            except Exception:
                pass
        size_mb = sum(f.stat().st_size for f in state.rglob("*") if f.is_file()) / (1024 * 1024)
        print(f"  state-{slot:02d}  {timestamp}  ({size_mb:.1f} MB)")


def diff_snapshots(slot_a: int, slot_b: int) -> None:
    """Show what files differ between two snapshot slots."""
    a = get_state_dir(slot_a)
    b = get_state_dir(slot_b)
    if not a.exists() or not b.exists():
        print(f"ERROR: one of the snapshots does not exist", file=sys.stderr)
        sys.exit(1)

    a_files = {f.relative_to(a) for f in a.rglob("*") if f.is_file()}
    b_files = {f.relative_to(b) for f in b.rglob("*") if f.is_file()}

    only_a = a_files - b_files
    only_b = b_files - a_files
    common = a_files & b_files

    if only_a:
        print(f"\nOnly in state-{slot_a:02d} (deleted in state-{slot_b:02d}):")
        for f in sorted(only_a):
            print(f"  - {f}")

    if only_b:
        print(f"\nOnly in state-{slot_b:02d} (added since state-{slot_a:02d}):")
        for f in sorted(only_b):
            print(f"  + {f}")

    if common:
        print(f"\nCommon files with content differences:")
        for f in sorted(common):
            af = a / f
            bf = b / f
            if af.read_bytes() != bf.read_bytes():
                print(f"  ~ {f}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("create", help="Create next snapshot in ring")
    sub.add_parser("list", help="List existing snapshots")
    sub.add_parser("rotate", help="Force ring rotation (testing)")

    restore_p = sub.add_parser("restore", help="Restore from a state slot")
    restore_p.add_argument("slot", type=int, help="Slot number 0-7")
    restore_p.add_argument("segments", nargs="*", help="Specific segments to restore (default: all)")

    diff_p = sub.add_parser("diff", help="Show what changed between two states")
    diff_p.add_argument("slot_a", type=int)
    diff_p.add_argument("slot_b", type=int)

    args = parser.parse_args()

    if args.cmd == "create":
        new_state = create_snapshot()
        print(f"Created {new_state.name}")
    elif args.cmd == "list":
        list_snapshots()
    elif args.cmd == "rotate":
        rotate()
        print("Ring rotated.")
    elif args.cmd == "restore":
        restore_snapshot(args.slot, args.segments or None)
    elif args.cmd == "diff":
        diff_snapshots(args.slot_a, args.slot_b)

    return 0


if __name__ == "__main__":
    sys.exit(main())
