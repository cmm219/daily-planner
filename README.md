# Daily Planner

A paper-style daily planner desktop app built with [Flet](https://flet.dev/)
(Python). Dynamic rows, multi-day tabs, task archiving with completion tracking,
and a reflections section — designed to feel like a physical day-planner page.

![status: alpha](https://img.shields.io/badge/status-alpha-orange)
![python](https://img.shields.io/badge/python-3.12-blue)

## Features

- Multi-day **tabs** (one page per day)
- **Dynamic rows** you can add/remove on the fly
- **Archive** completed rows with completion tracking
- **Reflections** section per day
- Multi-step **undo / redo**
- Local JSON persistence (no account, no cloud)

## Quick Start

```bash
pip install -r requirements.txt
python daily_planner.py
```

A desktop window opens. Your data is saved to a local JSON file (see
[Data](#data)).

## Hotkeys

| Key | Action |
| --- | --- |
| `Ctrl+Enter` | Add a new row to the current section |
| `Ctrl+Backspace` | Archive the current row |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Enter` | New line within the current field |

## Data

The planner persists to a single JSON file on your machine. The current build
writes to `C:/Users/Cmcna/daily_planner.json`. Making this path portable
(`~/daily_planner.json` / `%APPDATA%`) is tracked as a pre-public task in the
project backlog.

## Development

This repo follows a lightweight serious-project standard: versioned releases
(`VERSION` + `CHANGELOG.md`), a runtime registry (`bots.json` / `BOTS.md`), and
agent control notes in the separate notes vault. Contributor and agent
instructions live in `AGENTS.md` and `CLAUDE.md`.

## License

MIT — see [LICENSE](LICENSE).
