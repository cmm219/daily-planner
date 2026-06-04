# Daily Planner — History, Monthly Recap, and AI Helper (Phase 3 plan)

Status: **planned, not started.** Written 2026-06-04 as a handoff spec so a fresh
chat can build this without re-deriving context. Baseline = release `0.2.0.0`
(themeable settings panel + editable/hideable/custom sections).

## What we're building (two features + one foundation)

1. **Daily history store** (foundation — build first).
2. **Monthly recap** — an "Apple Memories"-style look-back over a month of
   gratitude, lessons, completed tasks, and task-score.
3. **AI helper** — *not in-app.* A Claude/Codex skill that reads and controls the
   planner externally.

---

## Locked decisions (from the user)

- **History granularity: one entry per calendar date.** We do NOT build a
  multi-tab-per-day picker (rejected as too fiddly). Whatever is filled in for a
  given date is that date's entry.
- **No in-app AI and no API keys.** AI assistance happens *outside* the app via a
  Claude/Codex skill that references/controls the planner (edits the JSON and/or
  drives the app). Nothing embedded, no per-user key, no runtime cost.
- The recap should *feel* like a video/slideshow (playback), but a real exported
  MP4 is a later, optional tier — not required for v1.

---

## Feature 1 — Daily history store (foundation)

Everything monthly depends on having dated history. Today each tab holds one
planner's data; tabs are renameable and not strictly per-day, so we need an
explicit dated archive.

**Design:**
- Add `all_data["history"]` = a map keyed by `YYYY-MM-DD` → a snapshot of that
  day's planner data (the section row lists + task_score). Lives in the same
  JSON, so it rides the existing `save_data()` path (no new files).
- **When to snapshot:** on save and/or on day-rollover (when the app opens on a
  new calendar date than the last write). Snapshot the *active day's* data under
  today's date, overwriting that date's entry (idempotent — last write wins for
  the day).
- Keep snapshots lightweight: store the section contents + score + date; skip
  empty days (don't archive a blank planner).
- Migration/normalize: ensure `history` exists (default `{}`); never destructive.

**Open sub-questions for the build chat:**
- Do we snapshot on every save, or once per day at first save? (Lean: update
  today's entry on every save; cheap and always current.)
- Should custom sections (from the Sections subtab) be included in the snapshot?
  (Lean: yes — snapshot whatever sections exist.)

**QA:** model tests for snapshot create/overwrite/skip-empty + normalize backfill,
mirroring the existing `tests/test_settings_model.py` style.

---

## Feature 2 — Monthly recap

Reads `all_data["history"]`, filters by chosen month, aggregates.

### v1 — "Month in Review" screen (build first; ~80% of the value)
- Entry point: a button/icon (e.g. a 📅 in the tab bar) → opens a recap view or
  dialog.
- Month picker (default = current month).
- Aggregates for the month:
  - All **gratitude** lines (what went right).
  - All **lessons** (what I learned / noticed).
  - All **completed / archived tasks**.
  - **Average task score** + count of days logged.
- Rendered in the existing terminal style (reuse theme + fonts + header helpers).
- Scrollable. Read-only.

### v2 — Playback mode (the "feels like a video" part)
- Auto-advance through entries one card at a time.
- Terminal type-on effect per card; soft fade between cards.
- A count-up flourish ("23 things you got done this month").
- Pause/next/prev controls. Still no video file — it just *plays*.

### v3 — Export (optional, later, its own mini-project)
- PNG collage via PIL (we already use PIL for the icon), OR
- MP4/GIF via frames → imageio/ffmpeg. Heavier; defer.

**Data dependency:** v1/v2 are only meaningful once Feature 1 has accumulated
history. For testing, seed a temp JSON with several dated history entries.

---

## Feature 3 — AI helper (external skill, no keys)

Scope is deliberately small — AI is only useful in a few spots:
- **Top Priorities** — the main one. "Here's my brain dump, help me order my
  non-negotiables for today."
- **On request only:** Gratitude and Lesson — a "help me think" assist if the
  user is stuck. Never automatic.
- Optional: generate the monthly-recap narrative / "recurring themes" summary.

**How it works (no embedded AI):**
- A Claude/Codex **skill** that:
  - Reads the planner JSON (`DATA_FILE`) to see current state.
  - Writes suggestions back by editing the JSON (then the app reloads), and/or
    drives the running app via the same handler methods our QA harness uses
    (`scripts/qa_visual.py` shows the in-process driving pattern).
- Because it's an external skill, it works for "others" only insofar as they run
  Claude/Codex — there is nothing to configure inside the planner itself.

**Must-haves for the skill to be safe:**
- Never clobber the user's real `C:\Users\Cmcna\daily_planner.json` without a
  backup; prefer append/merge into the target section, not overwrite the file.
- Respect the section model: only touch the requested section's row list.

**Open question for the build chat:**
- Which control surface for the skill — direct JSON edit (simplest, app must
  reload to show changes) vs. driving the live app (immediate, but needs the app
  running and a control channel). Lean: start with JSON edit + reload.

---

## Recommended build order

1. Daily history store (+ tests).
2. Monthly recap v1 (Month in Review screen).
3. Monthly recap v2 (playback).
4. AI helper skill (JSON-edit version first).
5. (Optional, later) recap export v3.

## Nice-to-have ideas raised (not committed)
- Consistency streak ("logged 18/30 days").
- Task-score sparkline / trend.
- AI-summarized recurring themes (ties Feature 2 + 3).
- Search across all days.
- One-tap export of the review as an image.

## Pointers for the build chat
- App: `daily_planner.py`. Settings/section model: `SECTION_DEFS`,
  `normalize_settings`, `ensure_section_data`, `_sec_label`/`_sec_on`.
- Section snapshot source: `get_active_tab_data()` / `self.data`.
- QA pattern: stub-Page handler-driven tests — see `tests/test_settings_*.py`
  and `tests/test_planner_actions.py` (Flet 0.80 renders to canvas; no DOM
  clicking). Visual harness: `scripts/qa_visual.py`.
- Flet 0.80 gotchas: `ft.Dropdown` uses `on_select` not `on_change`; dialogs via
  `page.show_dialog`/`page.pop_dialog`; GestureDetector uses `local_position`.
