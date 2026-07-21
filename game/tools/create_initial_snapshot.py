"""Create the first snapshot to establish the ring buffer.

This is run once to set state-00 to the current state. Future snapshots
will be created by the snapshot-cron job.
"""
import sys
from pathlib import Path

# Scrub hermes-agent contamination
import os
for env_var in ("PYTHONPATH", "PYTHONHOME"):
    if env_var in os.environ:
        del os.environ[env_var]
for env_var in list(os.environ.keys()):
    if "hermes" in os.environ[env_var].lower():
        del os.environ[env_var]

sys.path.insert(0, str(Path(__file__).resolve().parent))
import snapshot  # type: ignore

# We want to set state-07 to the current state without rotating
# (since state-00..06 are empty). Do this by bypassing rotate().
SNAPSHOTS_DIR = snapshot.SNAPSHOTS_DIR
SNAPSHOTS_DIR.mkdir(exist_ok=True)

new_state = snapshot.get_state_dir(snapshot.RING_SIZE - 1)
import shutil
if new_state.exists():
    shutil.rmtree(new_state)
new_state.mkdir()

import json
from datetime import datetime, timezone
for seg in snapshot.SEGMENTS:
    src = snapshot.PROJECT_DIR / seg
    dst = new_state / seg
    if not src.exists():
        continue
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

meta = new_state / "snapshot.json"
meta.write_text(
    json.dumps({"created_at": datetime.now(timezone.utc).isoformat(), "slots": snapshot.RING_SIZE, "is_initial": True}, indent=2),
    encoding="utf-8"
)
print(f"Initial snapshot created: {new_state.name}")
print(f"Snapshots directory: {SNAPSHOTS_DIR}")
print(f"\nNext: cron job will rotate every 3 hours.")
