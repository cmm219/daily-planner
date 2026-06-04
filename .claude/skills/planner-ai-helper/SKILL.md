---
name: planner-ai-helper
description: Help with the daily-planner app by reading and editing its JSON from OUTSIDE the app — no in-app AI, no API keys. Use when the user wants help ordering Top Priorities, brainstorming Gratitude or a Lesson, or summarizing a month. TRIGGER when the user references the daily planner and asks to prioritize a brain dump, get unstuck on gratitude/lessons, or recap a month. SKIP for unrelated apps or for editing planner code.
---

# Daily Planner AI Helper

This skill assists with the **daily-planner** desktop app (`daily_planner.py`)
without embedding any AI in the app. You (Claude/Codex) read the planner's data
file, decide what to suggest, and apply changes through one safe CLI:
`scripts/planner_edit.py`. The running app shows your changes after it reloads
(reopen the app, or it re-reads on next launch/save).

## Where the data lives

- Real file: `C:/Users/Cmcna/daily_planner.json` (the user's personal data).
- The app keeps `tabs` (each a day's planner), the active tab id, `settings`
  (section labels/visibility, theme), and `history` (per-date snapshots used by
  the monthly recap).

## The only safe way to edit: `scripts/planner_edit.py`

All edits go through this script. It always backs up first
(`<file>.aibak-YYYYMMDD-HHMMSS`), only touches the one section you name, and
never rewrites the schema or clears existing rows.

```bash
# See current state (use this FIRST, every time):
python scripts/planner_edit.py summary
python scripts/planner_edit.py summary --json     # machine-readable

# Append rows to a section (by key OR by header label, case-insensitive):
python scripts/planner_edit.py add --section "Top Priorities" --text "Call bank" --text "Email Sam"

# Re-order existing rows (1-based; must be a permutation, can't add/drop):
python scripts/planner_edit.py reorder --section top_priorities --order "3,1,2"

# Set today's average task score:
python scripts/planner_edit.py set-score --value 8

# Operate on a COPY instead of the real file (safe practice when unsure):
python scripts/planner_edit.py summary --data-file C:/tmp/planner_copy.json
```

Section names accept the exact key (`top_priorities`, `gratitude`, `lesson`,
`important`, `low_priority`, `one_win`, `tomorrow_top`, `first_action`, or any
`custom_*`) or the visible header text (e.g. `"Top Priorities — Non-Negotiables"`).

## What you should actually help with (keep scope tight)

1. **Top Priorities (the main one).** The user dumps everything on their plate;
   you order their non-negotiables for today. Read `summary`, propose an order
   with one-line reasons, get a yes, then `reorder` (if the rows already exist)
   or `add` the prioritized list.
2. **Gratitude / Lesson — on request only, never automatic.** If the user is
   stuck, offer a couple of prompts; only `add` what they approve.
3. **Monthly recap narrative (optional).** Use `summary --json` plus the app's
   recap (the 📅 button) to describe recurring themes for a month.

## Hard rules

- **Always run `summary` before editing** so you act on current state.
- **Never overwrite the file by hand or delete rows.** Use only this script's
  `add` / `reorder` / `set-score`. The script's backup is your safety net.
- **One section per change**, and only the section the user asked about.
- **Confirm before applying.** Show the proposed rows/order; apply on approval.
- **Append/merge, don't replace.** `add` appends; `reorder` permutes. There is
  no "clear" verb by design.
- If the app is open, tell the user to reopen it (or it will reload on next
  launch) to see the change.
