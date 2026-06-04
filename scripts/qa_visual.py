"""Visual QA harness for the daily-planner Flet app.

Serves the REAL app in web mode against a TEMP data file -- the real
C:\\Users\\Cmcna\\daily_planner.json is never opened or written. Flet 0.80 renders
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
    http://127.0.0.1:8771/?qa=presets      settings -> Presets
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
    "presets": "Presets",
}


def _seed_temp_data_file():
    """Write a seeded planner JSON to a temp path and point the app at it."""
    data = dp.get_default_data()
    tab = data["tabs"][0]["data"]
    tab["top_priorities"] = [
        {"text": "Send Invoice", "done": False, "dateAdded": "2026-06-04"},
        {"text": "Work on Github", "done": True, "dateAdded": "2026-06-04"},
        {"text": "Make video advertising PCM", "done": False, "dateAdded": "2026-06-04"},
    ]
    tab["important"] = [{"text": "Review settings UI", "done": False, "dateAdded": "2026-06-04"}]
    fd, path = tempfile.mkstemp(prefix="qa_planner_", suffix=".json")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    dp.DATA_FILE = path  # redirect ALL reads/writes away from the real file
    return path


def qa_main(page: ft.Page):
    app = dp.DailyPlanner(page)
    # Drive to a settings subtab if requested via ?qa=...
    key = None
    try:
        key = page.query.get("qa")
    except Exception:
        key = None
    if key in SUBTAB_BY_KEY:
        app.open_settings()
        app._settings_select(SUBTAB_BY_KEY[key])
        page.update()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8771)
    args = ap.parse_args()

    temp_path = _seed_temp_data_file()
    print(f"[qa_visual] temp data file: {temp_path}")
    print(f"[qa_visual] real data file is UNTOUCHED")

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
