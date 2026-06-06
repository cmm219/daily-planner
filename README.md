# Daily Planner

Daily Planner is a local-first desktop planner for organizing daily work, custom routines, reflections, and month-in-review recaps without putting personal planning data in the cloud.

![Daily Planner main screen](docs/screenshots/main.png)

![status: alpha](https://img.shields.io/badge/status-alpha-orange)
![python](https://img.shields.io/badge/python-3.12-blue)
![local-first](https://img.shields.io/badge/local--first-yes-brightgreen)

## Features

- Multi-day planner tabs with one page per day.
- Editable blue section headers: rename, hide, or add your own sections for the way you plan.
- Add, remove, archive, and restore task rows with completion history.
- Themeable terminal-style settings for colors, headers, fonts, and section labels.
- Month-in-Review recap with stats, completed-task summaries, gratitude, lessons, and playback mode.
- Local JSON persistence with no account, sync service, or cloud dependency.
- Optional `planner_edit.py` CLI for safe local automation against a chosen planner data file.

## Screenshots

| Main Planner | Settings |
| --- | --- |
| ![Main planner](docs/screenshots/main.png) | ![Settings dialog](docs/screenshots/settings.png) |

| Month in Review | Playback |
| --- | --- |
| ![Month in Review](docs/screenshots/month-review.png) | ![Playback mode](docs/screenshots/playback.png) |

![Month in Review playback](docs/screenshots/playback.gif)

## Quick Start

```bash
python -m pip install -r requirements.txt
python daily_planner.py
```

The app opens as a Flet desktop window and stores planner data on your machine.

## Data Location

By default, Daily Planner stores one JSON file outside the repo:

- Windows: `%APPDATA%\DailyPlanner\daily_planner.json`
- macOS/Linux: `~/.daily_planner/daily_planner.json`

To choose a specific file, set `DAILY_PLANNER_DATA_FILE` before launching:

```bash
set DAILY_PLANNER_DATA_FILE=C:\path\to\daily_planner.json
python daily_planner.py
```

PowerShell:

```powershell
$env:DAILY_PLANNER_DATA_FILE = "C:\path\to\daily_planner.json"
python .\daily_planner.py
```

## Hotkeys

| Key | Action |
| --- | --- |
| `Ctrl+Enter` | Add a new row to the current section |
| `Ctrl+Backspace` | Archive the current row |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+M` | Month in Review |
| `Enter` | New line within the current field |

## Development

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

Visual QA with fake data:

```bash
python scripts/qa_visual.py
```

Then open `http://127.0.0.1:8771/`.

More details are in [docs/usage.md](docs/usage.md).

## License

MIT - see [LICENSE](LICENSE).
