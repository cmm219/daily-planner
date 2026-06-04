"""planner_edit -- safe control surface for the daily-planner JSON.

This is the *control surface* for the external AI-helper skill (Phase 3,
Feature 3). There is NO AI in the planner app and no API keys anywhere; an
external Claude/Codex skill reads the planner, decides what to suggest, then
calls THIS script to apply the change. The app picks it up on next load.

Safety contract (enforced here, not just documented):
  * Every write makes a timestamped backup first (`<file>.aibak-YYYYMMDD-HHMMSS`).
  * Edits are append/merge into ONE target section of the active tab. We never
    rewrite the schema, never touch other sections, never clear existing rows.
  * `reorder` only permutes existing rows; it cannot add or drop content.
  * Loads go through the app's own migrate/normalize, so the file stays valid.

Usage (run from the repo root):
  python scripts/planner_edit.py summary
  python scripts/planner_edit.py add --section "Top Priorities" --text "Call bank" --text "Email Sam"
  python scripts/planner_edit.py reorder --section top_priorities --order "3,1,2"
  python scripts/planner_edit.py set-score --value 8
  # Operate on a test/copy instead of the real file:
  python scripts/planner_edit.py summary --data-file C:/tmp/planner.json

Exit code 0 on success, non-zero on a usage/lookup error.
"""
import argparse
import json
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import daily_planner as dp  # noqa: E402

CHECKBOX_SECTIONS = set(dp.CHECKBOX_SECTIONS)


def load(data_file):
    """Read + migrate + normalize the planner JSON. Returns the full all_data."""
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    data = dp.migrate_data(data)
    dp.normalize_settings(data)
    if not isinstance(data.get("history"), dict):
        data["history"] = {}
    return data


def backup(data_file):
    """Copy the current file to a timestamped `.aibak-*` sibling. Returns the
    backup path, or None if the source doesn't exist yet."""
    if not os.path.exists(data_file):
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = f"{data_file}.aibak-{stamp}"
    with open(data_file, "r", encoding="utf-8") as src:
        blob = src.read()
    with open(path, "w", encoding="utf-8") as dst:
        dst.write(blob)
    return path


def save(all_data, data_file):
    """Backup then write. Always call load()->mutate->save() so we never clobber
    unrelated keys."""
    backup(data_file)
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)


def active_tab_data(all_data):
    active = all_data.get("activeTab")
    for tab in all_data.get("tabs", []):
        if tab.get("id") == active:
            return tab["data"]
    if all_data.get("tabs"):
        return all_data["tabs"][0]["data"]
    raise KeyError("no tabs in planner data")


def resolve_section(all_data, name):
    """Map a user/AI-supplied section name to a real section key. Accepts the
    exact key, or a case-insensitive substring match against the section label."""
    settings = all_data.get("settings", {})
    sections = settings.get("sections", {})
    if name in sections:
        return name
    active = active_tab_data(all_data)
    if name in active:
        return name
    needle = name.strip().lower()
    # Exact label match first, then substring.
    for key, meta in sections.items():
        if (meta.get("label", "") or "").strip().lower() == needle:
            return key
    for key, meta in sections.items():
        if needle and needle in (meta.get("label", "") or "").lower():
            return key
    raise KeyError(f"no section matches {name!r}")


def add_rows(all_data, section_key, texts):
    """Append non-empty text rows to a section of the active tab. Checkbox
    sections get done=False. Existing rows are untouched."""
    data = active_tab_data(all_data)
    rows = data.setdefault(section_key, [])
    today = datetime.now().strftime("%Y-%m-%d")
    added = 0
    for text in texts:
        text = (text or "").strip()
        if not text:
            continue
        row = {"text": text, "dateAdded": today}
        if section_key in CHECKBOX_SECTIONS:
            row["done"] = False
        rows.append(row)
        added += 1
    return added


def reorder(all_data, section_key, order):
    """Permute existing rows by 1-based indices. `order` must be a permutation of
    the section's current row indices -- no add, no drop."""
    data = active_tab_data(all_data)
    rows = data.get(section_key, [])
    n = len(rows)
    if sorted(order) != list(range(1, n + 1)):
        raise ValueError(
            f"order {order} is not a permutation of 1..{n} for {section_key!r}")
    data[section_key] = [rows[i - 1] for i in order]
    return n


def set_score(all_data, value):
    data = active_tab_data(all_data)
    data["task_score"] = str(value)


def summarize(all_data):
    """Plain-dict summary the skill reads to see current state."""
    data = active_tab_data(all_data)
    settings = all_data.get("settings", {})
    sections = settings.get("sections", {})
    out = {"sections": {}, "task_score": data.get("task_score", "")}
    for key, meta in sections.items():
        if not meta.get("enabled", True):
            continue
        rows = [r.get("text", "") for r in data.get(key, [])
                if isinstance(r, dict) and r.get("text", "").strip()]
        out["sections"][key] = {"label": meta.get("label", key), "rows": rows}
    out["history_months"] = dp.available_months(all_data)
    return out


def _default_data_file():
    return dp.DATA_FILE


def main(argv=None):
    ap = argparse.ArgumentParser(prog="planner_edit", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-file", default=None,
                    help="planner JSON path (default: the app's DATA_FILE)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_sum = sub.add_parser("summary", help="print current active-tab state as JSON")
    p_sum.add_argument("--json", action="store_true", help="raw JSON (default human)")

    p_add = sub.add_parser("add", help="append rows to a section")
    p_add.add_argument("--section", required=True)
    p_add.add_argument("--text", action="append", required=True,
                       help="row text (repeatable)")

    p_re = sub.add_parser("reorder", help="permute existing rows (1-based)")
    p_re.add_argument("--section", required=True)
    p_re.add_argument("--order", required=True, help='e.g. "3,1,2"')

    p_sc = sub.add_parser("set-score", help="set today's average task score")
    p_sc.add_argument("--value", required=True)

    args = ap.parse_args(argv)
    data_file = args.data_file or _default_data_file()

    try:
        all_data = load(data_file)
    except FileNotFoundError:
        print(f"error: no planner file at {data_file}", file=sys.stderr)
        return 2

    if args.cmd == "summary":
        summary = summarize(all_data)
        if getattr(args, "json", False):
            print(json.dumps(summary, indent=2))
        else:
            print(f"task_score: {summary['task_score'] or '(none)'}")
            for key, blk in summary["sections"].items():
                print(f"\n[{key}] {blk['label']}")
                for r in blk["rows"]:
                    print(f"  - {r}")
            if summary["history_months"]:
                print(f"\nhistory months: {', '.join(summary['history_months'])}")
        return 0

    if args.cmd == "add":
        key = resolve_section(all_data, args.section)
        n = add_rows(all_data, key, args.text)
        save(all_data, data_file)
        print(f"added {n} row(s) to {key}")
        return 0

    if args.cmd == "reorder":
        key = resolve_section(all_data, args.section)
        try:
            order = [int(x) for x in args.order.split(",") if x.strip()]
        except ValueError:
            print(f"error: bad --order {args.order!r}", file=sys.stderr)
            return 2
        reorder(all_data, key, order)
        save(all_data, data_file)
        print(f"reordered {key}")
        return 0

    if args.cmd == "set-score":
        set_score(all_data, args.value)
        save(all_data, data_file)
        print(f"set task_score to {args.value}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
