"""Daily-variant ring buffer: 4 slots, 1 day each, 4 days of history.

Per the user's resolved design decision: every 4 days, save a local
copy of the working tree. The 4-slot ring keeps 4 days of history.
After 4 days, the oldest variant is replaced.

This is SEPARATE from the 8-state 3-hour snapshot ring. The daily
variant is a coarser-grained safety net for "something deeply damaged
the workflow" scenarios. The 3-hour snapshot is the fine-grained
recovery for "my last cron broke something" scenarios.

Usage:
    python tools/daily_variant.py create      # Create today's variant (slot 0-3)
    python tools/daily_variant.py list        # List existing variants
    python tools/daily_variant.py restore 01  # Restore variant at slot 01 (overwrites working tree)
    python tools/daily_variant.py diff 00 02  # Show what changed between variants

Variants are stored as full directory copies in `.daily-variants/variant-NN/`.
The 4 slots cycle: after 4 days, the next create() overwrites the oldest.
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Scrub hermes-agent contamination
for env_var in ("PYTHONPATH", "PYTHONHOME"):
    if env_var in os.environ:
        del os.environ[env_var]
for env_var in list(os.environ.keys()):
    if "hermes" in os.environ[env_var].lower():
        del os.environ[env_var]

# Project layout
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent  # game/tools/ -> game/
DAILY_DIR = PROJECT_DIR / ".daily-variants"  # game/.daily-variants/

RING_SIZE = 4
# Subset of segments (we keep all game/ except the venv)
SEGMENTS = ["data", "scripts", "scenes", "tests", "tools", "conftest.py", "requirements.txt", "project.godot"]


def get_slot_dir(slot: int) -> Path:
    return DAILY_DIR / f"variant-{slot:02d}"


def list_variants() -> list[Path]:
    if not DAILY_DIR.exists():
        return []
    return sorted(DAILY_DIR.glob("variant-*"), key=lambda p: int(p.name.split("-")[1]))


def rotate() -> None:
    """Shift the ring: delete variant-00, shift variant-01..03 down to variant-00..02.

    The previous version had a multi-iteration loop that double-moved
    snapshots and lost data. Correct approach: shift each slot one
    position lower, exactly once.
    """
    if not DAILY_DIR.exists():
        return
    # Step 1: Remove the oldest slot (it will be discarded)
    oldest = get_slot_dir(0)
    if oldest.exists():
        shutil.rmtree(oldest)
    # Step 2: Shift everything down by one (slot N -> slot N-1, in decreasing N order)
    for slot in range(1, RING_SIZE):
        src = get_slot_dir(slot)
        dst = get_slot_dir(slot - 1)
        if src.exists():
            src.rename(dst)
    # After this: old variant-01 is at variant-00, old variant-02 at variant-01,
    # old variant-03 at variant-02, variant-03 is now empty (will be filled next)


def create_variant() -> Path:
    """Create today's variant. Rotates the ring first."""
    DAILY_DIR.mkdir(exist_ok=True)
    rotate()
    new_slot = get_slot_dir(RING_SIZE - 1)  # variant-03
    new_slot.mkdir()
    for seg in SEGMENTS:
        src = PROJECT_DIR / seg
        dst = new_slot / seg
        if not src.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    meta = new_slot / "variant.json"
    meta.write_text(
        json.dumps({
            "created_at": datetime.now(timezone.utc).isoformat(),
            "slots": RING_SIZE,
        }, indent=2),
        encoding="utf-8"
    )
    return new_slot


def restore_variant(slot: int) -> None:
    if not 0 <= slot < RING_SIZE:
        print(f"ERROR: slot must be 0-{RING_SIZE - 1}, got {slot}", file=sys.stderr)
        sys.exit(1)
    v = get_slot_dir(slot)
    if not v.exists():
        print(f"ERROR: variant {slot} does not exist", file=sys.stderr)
        sys.exit(1)
    for seg in SEGMENTS:
        src = v / seg
        dst = PROJECT_DIR / seg
        if not src.exists():
            print(f"  [SKIP] {seg} (not in variant)")
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


def list_cmd() -> None:
    variants = list_variants()
    if not variants:
        print("No daily variants yet.")
        return
    print(f"Daily variants ({len(variants)}/{RING_SIZE} slots used):")
    for v in variants:
        slot = int(v.name.split("-")[1])
        meta = v / "variant.json"
        ts = "unknown"
        if meta.exists():
            try:
                m = json.loads(meta.read_text(encoding="utf-8"))
                ts = m.get("created_at", "unknown")
            except Exception:
                pass
        size = sum(f.stat().st_size for f in v.rglob("*") if f.is_file()) / (1024 * 1024)
        print(f"  variant-{slot:02d}  {ts}  ({size:.1f} MB)")


def diff_variants(slot_a: int, slot_b: int) -> None:
    a = get_slot_dir(slot_a)
    b = get_slot_dir(slot_b)
    if not a.exists() or not b.exists():
        print("ERROR: one of the variants does not exist", file=sys.stderr)
        sys.exit(1)
    a_files = {f.relative_to(a) for f in a.rglob("*") if f.is_file()}
    b_files = {f.relative_to(b) for f in b.rglob("*") if f.is_file()}
    only_a = a_files - b_files
    only_b = b_files - a_files
    common = a_files & b_files
    if only_a:
        print(f"\nOnly in variant-{slot_a:02d}:")
        for f in sorted(only_a):
            print(f"  - {f}")
    if only_b:
        print(f"\nOnly in variant-{slot_b:02d}:")
        for f in sorted(only_b):
            print(f"  + {f}")
    if common:
        print(f"\nCommon with content differences:")
        for f in sorted(common):
            if (a / f).read_bytes() != (b / f).read_bytes():
                print(f"  ~ {f}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("create", help="Create today's variant")
    sub.add_parser("list", help="List existing variants")
    restore_p = sub.add_parser("restore", help="Restore a variant")
    restore_p.add_argument("slot", type=int)
    diff_p = sub.add_parser("diff", help="Diff two variants")
    diff_p.add_argument("slot_a", type=int)
    diff_p.add_argument("slot_b", type=int)
    args = parser.parse_args()
    if args.cmd == "create":
        new = create_variant()
        print(f"Created {new.name}")
    elif args.cmd == "list":
        list_cmd()
    elif args.cmd == "restore":
        restore_variant(args.slot)
    elif args.cmd == "diff":
        diff_variants(args.slot_a, args.slot_b)
    return 0


if __name__ == "__main__":
    sys.exit(main())
