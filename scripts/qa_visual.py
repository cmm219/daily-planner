"""Visual QA harness for the daily-planner Flet app.

Serves the real app in web mode against a temporary data file; your normal
planner data file is never opened or written. Flet 0.80 renders
to a CanvasKit canvas, so DOM-selector clicking is infeasible; instead the app is
driven by its OWN handlers in-process. A `?qa=<subtab>` query param opens the
settings dialog on a given subtab so a screenshotter can capture each state.

Usage:
    python scripts/qa_visual.py            # serve on 127.0.0.1:8771
    python scripts/qa_visual.py --port N

Then screenshot:
    http://127.0.0.1:8771/                 main view
    http://127.0.0.1:8771/?qa=colors       settings -> Colors
    http://127.0.0.1:8771/?qa=headers      settings -> Headers / Bold
    http://127.0.0.1:8771/?qa=fonts        settings -> Fonts
    http://127.0.0.1:8771/?qa=sections     settings -> Sections
    http://127.0.0.1:8771/?qa=presets      settings -> Presets
    http://127.0.0.1:8771/?qa=recap        Month-in-Review dialog (seeded history)
    http://127.0.0.1:8771/?qa=play         recap playback mode
"""
import argparse
import json
import os
import sys
import tempfile
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import flet as ft  # noqa: E402
import daily_planner as dp  # noqa: E402

SUBTAB_BY_KEY = {
    "colors": "Colors",
    "headers": "Headers / Bold",
    "fonts": "Fonts",
    "sections": "Sections",
    "presets": "Presets",
}


def _seed_temp_data_file():
    """Write a seeded planner JSON to a temp path and point the app at it."""
    data = dp.get_default_data()
    tab = data["tabs"][0]["data"]
    tab["top_priorities"] = [
        {"text": "Send Invoice", "done": False, "dateAdded": "2026-06-04"},
        {"text": "Publish project update", "done": True, "dateAdded": "2026-06-04"},
        {"text": "Draft customer follow-up", "done": False, "dateAdded": "2026-06-04"},
    ]
    tab["important"] = [{"text": "Review settings UI", "done": False, "dateAdded": "2026-06-04"}]
    # Seed a month of history + archived tasks so the recap has real content.
    data["history"] = {
        "2026-06-01": {"date": "2026-06-01", "task_score": "7",
                       "sections": {"gratitude": [{"text": "Shipped the settings panel"}],
                                    "lesson": [{"text": "Ship smaller, verify sooner"}]}},
        "2026-06-02": {"date": "2026-06-02", "task_score": "8",
                       "sections": {"gratitude": [{"text": "Good gym session"},
                                                  {"text": "Call with a friend"}],
                                    "lesson": [{"text": "Protect the morning block"}]}},
        "2026-06-03": {"date": "2026-06-03", "task_score": "6",
                       "sections": {"gratitude": [{"text": "Finished the history store"}]}},
    }
    tab["archive"] = [
        {"text": "Bootstrap project home", "section": "important",
         "dateCompleted": "2026-06-01", "daysToComplete": 0},
        {"text": "Themeable settings panel", "section": "top_priorities",
         "dateCompleted": "2026-06-02", "daysToComplete": 1, "wasCompleted": True},
        {"text": "Daily history store", "section": "top_priorities",
         "dateCompleted": "2026-06-03", "daysToComplete": 0, "wasCompleted": True},
    ]
    fd, path = tempfile.mkstemp(prefix="qa_planner_", suffix=".json")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    dp.DATA_FILE = path  # redirect ALL reads/writes away from the real file
    return path


def qa_main(page: ft.Page):
    app = dp.DailyPlanner(page)
    # Drive to a view if requested. Prefer the ?qa=<key> query param; fall back
    # to the QA_VIEW env var (CanvasKit web sessions don't always surface the
    # query string to page.query, so the env var is the reliable screenshot path).
    key = None
    try:
        key = page.query.get("qa")
    except Exception:
        key = None
    if not key:
        key = os.environ.get("QA_VIEW") or None
    if key in SUBTAB_BY_KEY:
        app.open_settings()
        app._settings_select(SUBTAB_BY_KEY[key])
        page.update()
    elif key == "recap":
        app.open_recap()
        app._recap_month = "2026-06"
        app._recap_render()
        page.update()
    elif key == "play":
        app.open_recap()
        app._recap_month = "2026-06"
        app._recap_play()
        page.update()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8771)
    args = ap.parse_args()

    temp_path = _seed_temp_data_file()
    print(f"[qa_visual] temp data file: {temp_path}")
    print(f"[qa_visual] normal planner data file is UNTOUCHED")

    # Suppress the auto-opened browser tab (WEB_BROWSER view calls this).
    webbrowser.open = lambda *a, **k: True

    print(f"[qa_visual] serving on http://127.0.0.1:{args.port}/")
    ft.run(
        qa_main,
        view=ft.AppView.WEB_BROWSER,
        port=args.port,
        host="127.0.0.1",
    )


if __name__ == "__main__":
    main()
