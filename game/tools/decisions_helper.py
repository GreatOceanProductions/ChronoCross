"""Decisions queue helper.

Per the user's resolved design decision: the implementation-phase review
file is `DECISIONS.md`, not `review.md`. The crons surface batched
questions there for the user to answer. If the user doesn't answer
within the timeout (default 12 hours), the cron uses the suggested
default and continues.

This module is the state-machine the crons interact with. The crons
don't read/write `DECISIONS.md` directly; they call this module, which
serializes the queue, handles the timeout, and applies defaults.

Public API (used by decisions-cron, planner-cron, and user):
- load_queue() -> list[dict]
- save_queue(items)
- add(item) -> str (id)
- resolve(item_id, answer) -> bool
- apply_timeouts(timeout_hours=12) -> list[str] (item_ids that timed out)
- format_markdown(items) -> str (the body of DECISIONS.md)
- format_summary(items) -> str (terse summary for chat delivery)

Storage: project_root/DECISIONS.md (markdown, human-readable)
         project_root/loop_state.json.decisions_state (machine-readable)
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Scrub hermes-agent contamination before any imports that might be poisoned
import os
for env_var in ("PYTHONPATH", "PYTHONHOME"):
    if env_var in os.environ:
        del os.environ[env_var]
for env_var in list(os.environ.keys()):
    if "hermes" in os.environ[env_var].lower():
        del os.environ[env_var]

RE_DIR = Path(r"D:\Game Design\Remaster Engine")
DECISIONS_FILE = RE_DIR / "DECISIONS.md"
LOOP_STATE_FILE = RE_DIR / "loop_state.json"

DEFAULT_TIMEOUT_HOURS = 12
MAX_QUEUE_LENGTH = 30  # cap to prevent runaway accumulation


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def _parse_decisions_file() -> list[dict]:
    """Parse DECISIONS.md into structured items. Best-effort; tolerates malformed input."""
    if not DECISIONS_FILE.exists():
        return []
    text = DECISIONS_FILE.read_text(encoding="utf-8")
    items = []
    # Match: - [ ] [PRIORITY] DEC-NNN: <title> | Filed: <timestamp>
    #        - [x] [PRIORITY] DEC-NNN: <title> | Resolved: <timestamp>
    pattern = re.compile(
        r"^- \[(?P<check>[ x])\] \[(?P<priority>[P0-9]+)\] (?P<id>DEC-\d{3}): (?P<title>[^\n]+?)(?:\n  - Filed: (?P<filed>[^\n]+))?(?:\n  - Resolved: (?P<resolved>[^\n]+))?",
        re.MULTILINE,
    )
    for m in pattern.finditer(text):
        checked = m.group("check") == "x"
        items.append({
            "id": m.group("id"),
            "priority": m.group("priority"),
            "title": m.group("title").strip(),
            "filed": m.group("filed") or "",
            "resolved": m.group("resolved") or "",
            "status": "resolved" if checked else "open",
            "filed_ts": _parse_iso(m.group("filed")) if m.group("filed") else 0.0,
            "resolved_ts": _parse_iso(m.group("resolved")) if m.group("resolved") else 0.0,
            "default": "",
            "context": "",
            "options": [],
        })
    # Also pull context/default/options from the body that follows each item
    body_pattern = re.compile(
        r"^- \[[ x]\] \[(?P<priority>[P0-9]+)\] (?P<id>DEC-\d{3}): [^\n]+\n((?:  - [^\n]+\n)+)",
        re.MULTILINE,
    )
    for item, m in zip(items, body_pattern.finditer(text)):
        body = m.group(1)
        for line in body.split("\n"):
            line = line.strip()
            if line.startswith("- Context:"):
                item["context"] = line[len("- Context:"):].strip()
            elif line.startswith("- Default:"):
                item["default"] = line[len("- Default:"):].strip()
            elif line.startswith("- Options:"):
                opts_text = line[len("- Options:"):].strip()
                item["options"] = [o.strip() for o in opts_text.split("|") if o.strip()]
    return items


def _parse_iso(s: str) -> float:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def load_queue() -> list[dict]:
    """Load the current decisions queue from DECISIONS.md."""
    return _parse_decisions_file()


def save_queue(items: list[dict]) -> None:
    """Write the decisions queue to DECISIONS.md (overwrites)."""
    lines = [
        "# Decisions — Implementation Phase",
        "",
        "This file is the batched review queue for the Remaster Engine implementation crons. ",
        "The crons surface questions here for you to answer. **Default suggested** means the ",
        "cron will use that default and continue if you don't answer within 12 hours.",
        "",
        "**Format:**",
        "```",
        "- [ ] [PRIORITY] DEC-NNN: short title | Filed: YYYY-MM-DD",
        "  - Context: why this blocks (which cron is waiting)",
        "  - Options: A | B | C  (when applicable)",
        "  - Default: which option the cron will use on timeout",
        "```",
        "",
        "**Priority levels:**",
        "- **P0:** Blocks all forward progress. Fix immediately.",
        "- **P1:** Blocks 1-2 work crons. Fix within 24 hours.",
        "- **P2:** Doesn't block current work. Fix within the week.",
        "- **P3:** Cosmetic. Fix when bored.",
        "",
        "**When resolved, replace `[ ]` with `[x]` and add:**",
        "- `Resolved: YYYY-MM-DD` and a one-line note",
        "",
        "**The crons that read this file:** `decisions-cron` (every 8h), `planner-cron` (every 4h).",
        "",
        "---",
        "",
        "## Open Decisions",
        "",
    ]
    open_items = [it for it in items if it["status"] == "open"]
    if not open_items:
        lines.append("_(none — all clear)_")
        lines.append("")
    else:
        for it in open_items:
            lines.append(f"- [ ] [{it['priority']}] {it['id']}: {it['title']} | Filed: {it.get('filed', _now_iso())}")
            if it.get("context"):
                lines.append(f"  - Context: {it['context']}")
            if it.get("options"):
                lines.append(f"  - Options: {' | '.join(it['options'])}")
            if it.get("default"):
                lines.append(f"  - Default: {it['default']}")
            lines.append("")
    lines.append("## Resolved Decisions")
    lines.append("")
    resolved_items = [it for it in items if it["status"] == "resolved"]
    if not resolved_items:
        lines.append("_(none yet)_")
    else:
        for it in resolved_items:
            lines.append(f"- [x] [{it['priority']}] {it['id']}: {it['title']} | Resolved: {it.get('resolved', '')}")
            if it.get("default"):
                lines.append(f"  - Resolution: {it['default']}")
    lines.append("")
    DECISIONS_FILE.write_text("\n".join(lines), encoding="utf-8")


def add(priority: str, title: str, context: str = "", options: list[str] | None = None, default: str = "") -> str:
    """Add a new decision to the queue. Returns the new DEC-NNN id."""
    items = load_queue()
    # Determine next id
    existing_ids = [int(it["id"].split("-")[1]) for it in items if it["id"].startswith("DEC-")]
    next_id = max(existing_ids, default=0) + 1
    new_id = f"DEC-{next_id:03d}"
    items.append({
        "id": new_id,
        "priority": priority,
        "title": title,
        "filed": _now_iso(),
        "resolved": "",
        "status": "open",
        "filed_ts": _now_ts(),
        "resolved_ts": 0.0,
        "context": context,
        "default": default,
        "options": options or [],
    })
    # Cap queue: drop oldest P3/P2 if over MAX_QUEUE_LENGTH
    if len([it for it in items if it["status"] == "open"]) > MAX_QUEUE_LENGTH:
        open_items = [it for it in items if it["status"] == "open"]
        open_items.sort(key=lambda it: (it["priority"], it["filed_ts"]))
        # Drop oldest lowest-priority items
        while len([it for it in items if it["status"] == "open"]) > MAX_QUEUE_LENGTH and open_items:
            victim = open_items.pop(0)
            items.remove(victim)
    save_queue(items)
    return new_id


def resolve(item_id: str, answer: str = "") -> bool:
    """Mark a decision resolved. Returns True if found."""
    items = load_queue()
    for it in items:
        if it["id"] == item_id and it["status"] == "open":
            it["status"] = "resolved"
            it["resolved"] = _now_iso()
            it["resolved_ts"] = _now_ts()
            if answer:
                it["default"] = f"{answer} (user-supplied)"
            save_queue(items)
            return True
    return False


def apply_timeouts(timeout_hours: float = DEFAULT_TIMEOUT_HOURS) -> list[str]:
    """Auto-apply default to any open decision older than timeout_hours.

    Per user decision: if no response within 12 hours, assume the default
    suggestion and move forward. The decision is marked resolved-with-default.
    Returns the list of item_ids that were timed-out (for logging).
    """
    items = load_queue()
    now = _now_ts()
    timed_out = []
    for it in items:
        if it["status"] != "open":
            continue
        age_hours = (now - it["filed_ts"]) / 3600.0
        if age_hours >= timeout_hours:
            it["status"] = "resolved"
            it["resolved"] = _now_iso()
            it["resolved_ts"] = now
            it["default"] = f"{it.get('default', 'proceed as-is')} (auto-applied after {age_hours:.1f}h)"
            timed_out.append(it["id"])
    if timed_out:
        save_queue(items)
    return timed_out


def format_markdown(items: list[dict] | None = None) -> str:
    """Return the markdown body of DECISIONS.md for a given queue state."""
    if items is None:
        items = load_queue()
    open_count = sum(1 for it in items if it["status"] == "open")
    resolved_count = sum(1 for it in items if it["status"] == "resolved")
    lines = [
        f"# Decisions — {open_count} open, {resolved_count} resolved",
        "",
    ]
    open_items = [it for it in items if it["status"] == "open"]
    if open_items:
        lines.append("## Open")
        lines.append("")
        for it in open_items:
            lines.append(f"- [{it['priority']}] {it['id']}: {it['title']}")
            if it.get("context"):
                lines.append(f"  - Context: {it['context']}")
            if it.get("options"):
                lines.append(f"  - Options: {' | '.join(it['options'])}")
            if it.get("default"):
                lines.append(f"  - Default: {it['default']}")
            lines.append("")
    return "\n".join(lines)


def format_summary(items: list[dict] | None = None) -> str:
    """Terse summary for chat delivery."""
    if items is None:
        items = load_queue()
    open_items = [it for it in items if it["status"] == "open"]
    if not open_items:
        return "Decisions queue: clear."
    lines = [f"Decisions queue: {len(open_items)} open."]
    for it in open_items[:5]:  # show first 5
        lines.append(f"  [{it['priority']}] {it['id']}: {it['title'][:80]}")
    if len(open_items) > 5:
        lines.append(f"  ... and {len(open_items) - 5} more (see DECISIONS.md)")
    return "\n".join(lines)


def main() -> int:
    """CLI entry point: 'apply-timeouts' subcommand, or default = show summary."""
    if len(sys.argv) > 1 and sys.argv[1] == "apply-timeouts":
        timed_out = apply_timeouts(DEFAULT_TIMEOUT_HOURS)
        if timed_out:
            print(f"Auto-applied defaults to {len(timed_out)} decisions: {', '.join(timed_out)}")
        else:
            print("No decisions past timeout.")
        return 0
    print(format_summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
