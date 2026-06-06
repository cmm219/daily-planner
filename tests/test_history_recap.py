"""History store + monthly recap tests (Phase 3).

Two layers, both GUI-free where possible:
  1. Pure model functions: planner_is_empty, make_history_snapshot,
     update_history, available_months, aggregate_month, build_recap_cards.
  2. Handler-level QA against a stub Page (Flet 0.80 renders to canvas, so we
     drive the real open_recap / playback handlers and assert side effects).

The user's normal planner data file is never touched.
"""
import json
import os
import sys
import types

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import flet as ft  # noqa: E402
import daily_planner as dp  # noqa: E402


# --- stub Page (mirrors test_planner_actions.py) -------------------------

class FakeControl:
    def __init__(self, value=None):
        self.value = value


class FakeEvent:
    def __init__(self, value=None):
        self.control = FakeControl(value)


class FakeKey:
    def __init__(self, key, ctrl=False, shift=False, alt=False, meta=False):
        self.key = key
        self.ctrl = ctrl
        self.shift = shift
        self.alt = alt
        self.meta = meta


class StubPage:
    def __init__(self):
        self.window = types.SimpleNamespace(width=700, height=900, icon=None)
        self.controls = []
        self.dialogs = []
        self.title = None
        self.bgcolor = None
        self.padding = None
        self.scroll = None
        self.on_keyboard_event = None

    def show_dialog(self, d):
        self.dialogs.append(d)

    def pop_dialog(self):
        if self.dialogs:
            self.dialogs.pop()

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self, *a, **k):
        pass

    def run_task(self, coro, *a, **k):
        # Don't actually run the async playback in tests; just close it cleanly.
        try:
            res = coro(*a, **k) if callable(coro) else coro
            if hasattr(res, "close"):
                res.close()
        except Exception:
            pass


def _walk(control):
    yield control
    content = getattr(control, "content", None)
    if content is not None and hasattr(content, "__class__"):
        yield from _walk(content)
    kids = getattr(control, "controls", None)
    if isinstance(kids, (list, tuple)):
        for k in kids:
            if k is not None:
                yield from _walk(k)


def _find(root, predicate):
    for c in _walk(root):
        if predicate(c):
            return c
    return None


# --- fixtures ------------------------------------------------------------

@pytest.fixture
def app(tmp_path):
    data_path = tmp_path / "planner.json"
    data_path.write_text(json.dumps(dp.get_default_data()), encoding="utf-8")
    old = dp.DATA_FILE
    dp.DATA_FILE = str(data_path)
    planner = dp.DailyPlanner(StubPage())
    planner._qa_path = str(data_path)
    yield planner
    dp.DATA_FILE = old


def _load(app):
    return json.loads(open(app._qa_path, encoding="utf-8").read())


def _seeded_all_data():
    """all_data with two months of history + some archived tasks."""
    data = dp.get_default_data()
    data["history"] = {
        "2026-05-30": {
            "date": "2026-05-30", "task_score": "8",
            "sections": {
                "gratitude": [{"text": "sunny walk"}],
                "lesson": [{"text": "ship smaller"}],
                "top_priorities": [{"text": "do taxes", "done": True}],
            },
        },
        "2026-06-01": {
            "date": "2026-06-01", "task_score": "6",
            "sections": {
                "gratitude": [{"text": "good coffee"}, {"text": "call with mom"}],
                "lesson": [{"text": "rest matters"}],
            },
        },
        "2026-06-03": {
            "date": "2026-06-03", "task_score": "",
            "sections": {"gratitude": [{"text": "finished feature"}]},
        },
    }
    data["tabs"][0]["data"]["archive"] = [
        {"text": "old task", "section": "important", "dateCompleted": "2026-05-15"},
        {"text": "june task", "section": "top_priorities", "dateCompleted": "2026-06-02"},
        {"text": "june task 2", "section": "important", "dateCompleted": "2026-06-03"},
    ]
    return data


# --- Feature 1: history store -------------------------------------------

def test_default_data_has_history():
    assert dp.get_default_data()["history"] == {}


def test_migrate_backfills_history():
    old = {"tabs": [{"id": "a", "name": "x", "data": dp.get_default_planner()}],
           "activeTab": "a"}
    migrated = dp.migrate_data(old)
    assert isinstance(migrated["history"], dict)


def test_planner_is_empty_for_blank_default():
    assert dp.planner_is_empty(dp.get_default_planner()) is True


def test_planner_not_empty_with_text():
    d = dp.get_default_planner()
    d["top_priorities"][0]["text"] = "ship it"
    assert dp.planner_is_empty(d) is False


def test_planner_not_empty_with_score_only():
    d = dp.get_default_planner()
    d["task_score"] = "7"
    assert dp.planner_is_empty(d) is False


def test_snapshot_keeps_only_nonempty_rows_and_done():
    d = dp.get_default_planner()
    d["top_priorities"] = [
        {"text": "a", "done": True, "dateAdded": "2026-06-04"},
        {"text": "", "done": False, "dateAdded": "2026-06-04"},
    ]
    d["task_score"] = "9"
    snap = dp.make_history_snapshot(d, "2026-06-04")
    assert snap["date"] == "2026-06-04"
    assert snap["task_score"] == "9"
    rows = snap["sections"]["top_priorities"]
    assert rows == [{"text": "a", "done": True}]  # blank row dropped


def test_snapshot_excludes_archive_and_lastupdated():
    d = dp.get_default_planner()
    d["top_priorities"][0]["text"] = "x"
    d["archive"] = [{"text": "done", "dateCompleted": "2026-06-01"}]
    snap = dp.make_history_snapshot(d, "2026-06-04")
    assert "archive" not in snap["sections"]
    assert "lastUpdated" not in snap["sections"]


def test_snapshot_includes_custom_sections():
    d = dp.get_default_planner()
    d["custom_abc"] = [{"text": "read book", "dateAdded": "2026-06-04"}]
    snap = dp.make_history_snapshot(d, "2026-06-04")
    assert snap["sections"]["custom_abc"] == [{"text": "read book"}]


def test_update_history_skips_empty_day():
    all_data = {"history": {}}
    dp.update_history(all_data, dp.get_default_planner(), "2026-06-04")
    assert all_data["history"] == {}  # blank planner not archived


def test_update_history_records_and_is_idempotent():
    all_data = {"history": {}}
    d = dp.get_default_planner()
    d["gratitude"][0]["text"] = "v1"
    dp.update_history(all_data, d, "2026-06-04")
    assert all_data["history"]["2026-06-04"]["sections"]["gratitude"][0]["text"] == "v1"
    # last write wins for the day
    d["gratitude"][0]["text"] = "v2"
    dp.update_history(all_data, d, "2026-06-04")
    assert len(all_data["history"]) == 1
    assert all_data["history"]["2026-06-04"]["sections"]["gratitude"][0]["text"] == "v2"


def test_update_history_creates_map_if_missing():
    all_data = {}
    d = dp.get_default_planner()
    d["gratitude"][0]["text"] = "hi"
    dp.update_history(all_data, d, "2026-06-04")
    assert "2026-06-04" in all_data["history"]


def test_save_data_writes_history(app):
    app.data["gratitude"][0]["text"] = "grateful for tests"
    app.save_data()
    today = dp.datetime.now().strftime("%Y-%m-%d")
    hist = _load(app)["history"]
    assert today in hist
    assert hist[today]["sections"]["gratitude"][0]["text"] == "grateful for tests"


def test_save_data_blank_day_not_archived(app):
    # Fresh default planner is blank -> no history entry written.
    app.save_data()
    assert _load(app)["history"] == {}


# --- Feature 2: monthly recap aggregation -------------------------------

def test_month_of():
    assert dp._month_of("2026-06-04") == "2026-06"
    assert dp._month_of("nope") == ""
    assert dp._month_of(None) == ""


def test_available_months_from_history_and_archive():
    months = dp.available_months(_seeded_all_data())
    # 2026-06 + 2026-05 from history; 2026-05 also from archive.
    assert months == ["2026-06", "2026-05"]


def test_aggregate_month_rolls_up():
    agg = dp.aggregate_month(_seeded_all_data(), "2026-06")
    assert agg["days_logged"] == 2  # 06-01 and 06-03 have history
    grat = [g["text"] for g in agg["gratitude"]]
    assert "good coffee" in grat and "finished feature" in grat
    lessons = [l["text"] for l in agg["lessons"]]
    assert "rest matters" in lessons
    # avg of the one numeric score (6) in June; 06-03 score was blank
    assert agg["avg_score"] == 6.0
    assert agg["score_count"] == 1
    completed = [c["text"] for c in agg["completed"]]
    assert completed == ["june task", "june task 2"]  # sorted by dateCompleted


def test_aggregate_empty_month():
    agg = dp.aggregate_month(_seeded_all_data(), "2026-01")
    assert agg["days_logged"] == 0
    assert agg["avg_score"] is None
    assert agg["completed"] == []


def test_build_recap_cards_structure():
    agg = dp.aggregate_month(_seeded_all_data(), "2026-06")
    cards = dp.build_recap_cards(agg)
    kinds = [c["kind"] for c in cards]
    assert kinds[0] == "intro"
    assert "gratitude" in kinds
    assert "lessons" in kinds
    assert "completed" in kinds
    assert "score" in kinds
    assert kinds[-1] == "outro"


def test_build_recap_cards_empty_month_has_fallback():
    agg = dp.aggregate_month(_seeded_all_data(), "2026-01")
    cards = dp.build_recap_cards(agg)
    assert len(cards) == 1
    assert cards[0]["kind"] == "intro"
    assert any("Nothing logged" in line for line in cards[0]["lines"])


# --- Feature 2: recap UI handlers (stub Page) ---------------------------

def _app_with_history(app):
    app.all_data["history"] = _seeded_all_data()["history"]
    app.all_data["tabs"][0]["data"]["archive"] = \
        _seeded_all_data()["tabs"][0]["data"]["archive"]
    return app


def test_open_recap_shows_dialog(app):
    _app_with_history(app)
    app.open_recap()
    assert any(isinstance(d, ft.AlertDialog) for d in app.page.dialogs)
    # Month dropdown present in the title row.
    dlg = app.page.dialogs[-1]
    dd = _find(dlg.title, lambda c: isinstance(c, ft.Dropdown))
    assert dd is not None


def test_recap_render_sets_pane(app):
    _app_with_history(app)
    app.open_recap()
    assert app._recap_pane.content is not None


def test_recap_month_label(app):
    assert app._recap_month_label("2026-06") == "June 2026"
    assert app._recap_month_label("bad") == "bad"


def test_kb_ctrl_m_opens_recap(app):
    app.on_keyboard(FakeKey("M", ctrl=True))
    assert any(isinstance(d, ft.AlertDialog) for d in app.page.dialogs)


def test_recap_play_builds_dialog(app):
    _app_with_history(app)
    app.open_recap()
    # Hit Play -> a playback dialog with transport controls appears, no crash.
    app._recap_play()
    dlg = app.page.dialogs[-1]
    icon_btns = [c for c in _walk(dlg) if isinstance(c, ft.IconButton)]
    assert len(icon_btns) >= 3  # prev / pause / next


def test_tab_bar_has_recap_button(app):
    bar = app.build_tab_bar()
    btn = _find(bar, lambda c: isinstance(c, ft.IconButton)
                and getattr(c, "icon", None) == ft.Icons.CALENDAR_MONTH)
    assert btn is not None and btn.on_click is not None
