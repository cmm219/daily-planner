# Daily Planner Usage

## Running The App

Install dependencies and start the desktop app:

```bash
python -m pip install -r requirements.txt
python daily_planner.py
```

Daily Planner is local-first. It does not require an account or cloud service.

## Local Data

The app stores planner data in a single JSON file.

Default locations:

- Windows: `%APPDATA%\DailyPlanner\daily_planner.json`
- macOS/Linux: `~/.daily_planner/daily_planner.json`

Override the data file with `DAILY_PLANNER_DATA_FILE`:

```powershell
$env:DAILY_PLANNER_DATA_FILE = "C:\path\to\daily_planner.json"
python .\daily_planner.py
```

This is useful for portable folders, testing, or running separate planner files.

## Planner Flow

- Use tabs for different days.
- Add rows in priority, work, reflection, and custom sections.
- Archive completed rows to keep the day clean while preserving history.
- Open Month in Review with `Ctrl+M` or the calendar button.
- Use playback mode to review the month as a guided recap.

## Settings

The settings panel supports:

- color presets and custom colors;
- font family and size controls;
- header styling;
- section renaming;
- hiding built-in sections;
- adding custom sections.

The blue planner headers are not fixed. Open the gear menu, choose the Sections tab, then rename labels like `TOP PRIORITIES`, hide sections you do not use, or add custom sections for your own workflow.

## Month In Review Playback

Month in Review summarizes logged days, completed tasks, gratitude, and lessons for the selected month. Press `Play` to turn the recap into a guided playback view so you can review the month card by card.

## Local Automation

`scripts/planner_edit.py` provides a small safe CLI for a chosen data file. It can summarize, append, reorder, or score planner sections without launching the UI.

Example:

```bash
python scripts/planner_edit.py --data-file path/to/daily_planner.json summary --json
```

The CLI requires an explicit `--data-file` path so automation does not accidentally edit the wrong planner file.
