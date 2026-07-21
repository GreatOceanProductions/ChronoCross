"""Update loop_state.json after data-cron cycle 50 (white element meta-def)."""
import json
from pathlib import Path

PATH = Path(r"D:\Game Design\Remaster Engine\loop_state.json")
data = json.loads(PATH.read_text(encoding="utf-8"))

# 1) top-level bookkeeping
data["last_updated"] = "2026-07-21T15:30:00+00:00"
data["last_loop_completed"] = "2026-07-21T15:30:00+00:00"
data["total_loops_completed"] = 51

# 2) data_cron block
dc = data["data_cron"]
dc["last_data_authored"] = "white.json"
dc["last_data_type"] = "element_meta"
dc["last_data_run_at"] = "2026-07-21T15:30:00+00:00"
dc["last_status"] = "committed"
dc["last_action"] = (
    "Cycle: authored element_meta/white (first of 7 element meta-defs, "
    "Serge's element, §7.4 element grid canonical resistance chart) -> "
    "validate_data.py 9/9 OK -> pytest 104/104 OK -> commit be70a93. "
    "Resistance values per CANONICAL_CHART (2 strong + 2 weak per color "
    "element per the §7.4 hexagonal graph): white vs black/yellow = 2.0 "
    "strong, white vs red/blue = 0.5 weak, white vs self/green/neutral = "
    "1.0. Planner queue note was incomplete (listed only 1 of each); the "
    "on-disk data uses the canonical 2+2 form to match element_grid.py "
    "CANONICAL_CHART."
)

# 3) authored.elements
elements = dc["authored"].setdefault("elements", [])
if "white" not in elements:
    elements.append("white")

# 4) advance the target_queue: drop the white element_meta, prepend a new
#    black element_meta to the back (one-element-meta-per-tick pace per
#    the planner's source comment for black_hellbound), so the next data-
#    cron cycle authors the next meta-def in series.
queue = dc["target_queue"]
if queue and queue[0].get("id") == "white" and queue[0].get("type") == "element_meta":
    queue.pop(0)
# Append the next element_meta (black) to the back of the queue, keeping
# the existing element/tech queue items in their relative order.
queue.append({
    "type": "element_meta",
    "id": "black",
    "source": (
        "phase_3_redesign.element_catalog.elements.Black + DEC-001 mirrored "
        "pairs + DEC-006 'neutral as 7th'. The 2nd of 7 element meta-defs. "
        "Black is Herle's element. Per the planner's 'one-element-meta-per-"
        "tick' pace (see the black_hellbound source comment), this was "
        "promoted to the back of the queue after cycle 50 authored the "
        "white meta-def. The next element_meta after this one will be red "
        "(cycle 52), then blue, green, yellow, and finally neutral (which "
        "is the trivial all-1.0 row)."
    ),
})

PATH.write_text(
    json.dumps(data, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
print("loop_state.json updated: cycle 51, white element_meta authored.")
