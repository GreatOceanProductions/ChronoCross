"""One-shot helper to update loop_state.json after cycle 48 data authoring.

This is a temp script — it will be removed in a future cycle. The
content matches what the data-cron needs to record for the Fireball
tech authoring cycle.
"""
import json

PATH = r"D:\Game Design\Remaster Engine\loop_state.json"

with open(PATH, "rb") as f:
    data = f.read()
text = data.decode("utf-8")
state = json.loads(text)

# Bump top-level counters
state["last_updated"] = "2026-07-21T13:00:00+00:00"
state["last_loop_completed"] = "2026-07-21T13:00:00+00:00"
state["total_loops_completed"] = state.get("total_loops_completed", 47) + 1

# Update data_cron block
dc = state["data_cron"]
dc["last_data_authored"] = "fireball.json"
dc["last_data_type"] = "tech"
dc["last_data_run_at"] = "2026-07-21T13:00:00+00:00"
dc["authored"] = {
    "characters": ["kidd", "serge", "nikki", "glenn", "herle", "norris"],
    "techs": ["fireball"],
    "elements": [],
    "maps": [],
    "chapters": [],
}
dc["last_status"] = "committed"
dc["last_action"] = (
    "Cycle: authored tech/fireball (red tier-1 single-enemy damage spell "
    "from element_catalog.Red[2]) -> validate_data.py 8/8 OK -> "
    "pytest 97/97 OK -> commit fc0d676"
)
dc["target_queue"] = [
    {
        "type": "element",
        "id": "white_recoverall",
        "source": "phase_3_redesign.element_catalog.elements.White[5] \u2014 "
        "RecoverAll (level 3\u00b15, All Allies, 'Restores HP (Medium)')",
    },
    {
        "type": "element",
        "id": "black_hellbound",
        "source": "phase_3_redesign.element_catalog.elements.Black[8] \u2014 "
        "HellBound (level 4\u00b10, Single Enemy, 'Sends your enemy on a "
        "trip to hell'). Picked because (a) it's a single-target "
        "status-applying tech that exercises the \u00a77.5 status effect "
        "engine, and (b) it's a black element which means it's "
        "available to Herle.",
    },
    {
        "type": "element",
        "id": "red_firepillar",
        "source": "phase_3_redesign.element_catalog.elements.Red[7] \u2014 "
        "FirePillar (level 3\u00b15, Single Enemy, 'Burns enemy in a "
        "pillar of flames'). Next tier-3 red damage spell with burn "
        "status potential.",
    },
    {
        "type": "element",
        "id": "blue_cure",
        "source": "phase_3_redesign.element_catalog.elements.Blue[1] \u2014 "
        "Cure (level 1\u00b17, Single Enemy/Ally, 'Restores HP (Small)'). "
        "Heals to mirror Fireball's damage role for blue element.",
    },
]

# Write back, preserve CRLF style
new_text = json.dumps(state, indent=2, ensure_ascii=False)
new_data = new_text.replace("\n", "\r\n").encode("utf-8")
with open(PATH, "wb") as f:
    f.write(new_data)

# Re-validate
with open(PATH, "rb") as f:
    reloaded = json.loads(f.read().decode("utf-8"))
print("OK")
print("last_data_authored:", reloaded["data_cron"]["last_data_authored"])
print("total_loops_completed:", reloaded["total_loops_completed"])
print("target_queue[0]:", reloaded["data_cron"]["target_queue"][0]["id"])
