"""Headless QA for EVERY interactive control in the planner (not just settings).

Flet 0.80 renders to a canvas, so we drive the real handler methods the buttons /
keys are wired to, against a stub Page, and assert the side effects (data mutations,
JSON persistence, dialogs). The real daily_planner.json is never touched.

Covers: tab switch / add / close / rename, theme toggle, add row, archive row
(+ guards), checkbox, text change + blur auto-delete, score, undo/redo, snackbar,
and all Ctrl+ keyboard shortcuts.
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
        try:
            coro.close()
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


def _active_data(app):
    return app.get_active_tab_data()


# --- Rows ----------------------------------------------------------------

def test_add_row_requires_focus(app):
    # No focus -> guard fires, no crash, no new row.
    before = len(_active_data(app)["top_priorities"])
    app.focused_section = None
    app.add_row()
    assert len(_active_data(app)["top_priorities"]) == before
    assert any(isinstance(d, ft.SnackBar) for d in app.page.dialogs)


def test_add_row_inserts(app):
    app.focused_section = "top_priorities"
    app.focused_index = 0
    before = len(app.data["top_priorities"])
    app.add_row()
    assert len(app.data["top_priorities"]) == before + 1
    assert _load(app)["tabs"][0]["data"]["top_priorities"]  # persisted


def test_checkbox_toggle_persists(app):
    app.on_checkbox_change(FakeEvent(True), "top_priorities", 0)
    assert app.data["top_priorities"][0]["done"] is True
    assert _load(app)["tabs"][0]["data"]["top_priorities"][0]["done"] is True


def test_text_change_then_blur_saves(app):
    app.data["important"][0]["text"] = ""
    app.on_text_change(FakeEvent("buy milk"), "important", 0)
    assert app.data["important"][0]["text"] == "buy milk"
    app.on_field_blur(FakeEvent("buy milk"), "important", 0)
    assert _load(app)["tabs"][0]["data"]["important"][0]["text"] == "buy milk"


def test_blur_autodeletes_empty_nonfirst_row(app):
    app.data["important"].append({"text": "", "done": False, "dateAdded": "2026-06-04"})
    assert len(app.data["important"]) == 2
    app.on_field_blur(FakeEvent(""), "important", 1)
    assert len(app.data["important"]) == 1  # empty non-first row removed


def test_archive_empty_row_blocked(app):
    app.focused_section = "low_priority"
    app.focused_index = 0
    app.focused_textfield = FakeControl("")
    app.data["low_priority"][0]["text"] = ""
    app.archive_row()
    assert len(app.data["archive"]) == 0
    assert any(isinstance(d, ft.SnackBar) for d in app.page.dialogs)


def test_archive_completed_row(app):
    app.data["top_priorities"][0] = {"text": "ship it", "done": True, "dateAdded": "2026-06-01"}
    app.focused_section = "top_priorities"
    app.focused_index = 0
    app.focused_textfield = FakeControl("ship it")
    app.archive_row()
    arch = app.data["archive"]
    assert len(arch) == 1
    assert arch[0]["text"] == "ship it"
    assert arch[0]["section"] == "top_priorities"
    assert _load(app)["tabs"][0]["data"]["archive"][0]["text"] == "ship it"


def test_archive_incomplete_first_checkbox_blocked(app):
    app.data["top_priorities"][0] = {"text": "todo", "done": False, "dateAdded": "2026-06-01"}
    app.focused_section = "top_priorities"
    app.focused_index = 0
    app.focused_textfield = FakeControl("todo")
    app.archive_row()
    assert len(app.data["archive"]) == 0  # must check the box first


def test_score_change_and_blur(app):
    app.on_score_change(FakeEvent("8"))
    assert app.data["task_score"] == "8"
    app.on_score_blur(FakeEvent("8"))
    assert _load(app)["tabs"][0]["data"]["task_score"] == "8"


# --- Undo / redo ---------------------------------------------------------

def test_undo_redo_cycle(app):
    app.focused_section = "top_priorities"
    app.focused_index = 0
    app.add_row()
    n_after_add = len(app.data["top_priorities"])
    app.undo()
    assert len(app.data["top_priorities"]) == n_after_add - 1
    app.redo()
    assert len(app.data["top_priorities"]) == n_after_add


def test_undo_empty_shows_snackbar(app):
    app.undo_stack.clear()
    app.undo()
    assert any(isinstance(d, ft.SnackBar) for d in app.page.dialogs)


# --- Tabs ----------------------------------------------------------------

def test_add_tab(app):
    before = len(app.all_data["tabs"])
    app.add_tab()
    assert len(app.all_data["tabs"]) == before + 1
    # New tab is active.
    assert app.all_data["activeTab"] == app.all_data["tabs"][-1]["id"]


def test_switch_tab(app):
    app.add_tab()
    first = app.all_data["tabs"][0]["id"]
    app.switch_tab(first)
    assert app.all_data["activeTab"] == first


def test_close_last_tab_blocked(app):
    assert len(app.all_data["tabs"]) == 1
    app.close_tab(app.all_data["activeTab"])
    assert len(app.all_data["tabs"]) == 1  # last tab protected
    assert any(isinstance(d, ft.SnackBar) for d in app.page.dialogs)


def test_close_tab_with_two(app):
    app.add_tab()
    assert len(app.all_data["tabs"]) == 2
    target = app.all_data["activeTab"]
    app.close_tab(target)
    assert len(app.all_data["tabs"]) == 1


def test_rename_tab(app):
    tid = app.all_data["activeTab"]
    app.rename_tab_dialog(tid)
    dlg = app.page.dialogs[-1]
    field = _find(dlg, lambda c: isinstance(c, ft.TextField))
    assert field is not None
    field.value = "Groceries"
    save_btn = next(b for b in dlg.actions if isinstance(b, ft.TextButton) and b.content == "Save")
    save_btn.on_click(FakeEvent())
    name = next(t["name"] for t in app.all_data["tabs"] if t["id"] == tid)
    assert name == "Groceries"


# --- Tab bar buttons exist & are wired ----------------------------------

def test_tab_bar_has_theme_and_gear(app):
    bar = app.build_tab_bar()
    icon_btns = [c for c in _walk(bar) if isinstance(c, ft.IconButton)]
    assert len(icon_btns) >= 2
    assert all(getattr(b, "on_click", None) for b in icon_btns)


def test_tab_bar_close_button_wired(app):
    bar = app.build_tab_bar()
    # The "✕" close control is a Container with on_click and a Text "✕".
    close = _find(bar, lambda c: isinstance(c, ft.Container) and getattr(c, "on_click", None)
                  and _find(c, lambda t: isinstance(t, ft.Text) and getattr(t, "value", "") == "✕"))
    assert close is not None


def test_theme_toggle(app):
    assert app.settings["preset"] == "Dark"
    app.toggle_theme()
    assert app.settings["preset"] == "Light"
    app.toggle_theme()
    assert app.settings["preset"] == "Dark"


# --- Keyboard shortcuts --------------------------------------------------

def test_kb_ctrl_enter_adds_row(app):
    app.focused_section = "top_priorities"
    app.focused_index = 0
    before = len(app.data["top_priorities"])
    app.on_keyboard(FakeKey("Enter", ctrl=True))
    assert len(app.data["top_priorities"]) == before + 1


def test_kb_ctrl_z_and_y(app):
    app.focused_section = "top_priorities"
    app.focused_index = 0
    app.add_row()
    n = len(app.data["top_priorities"])
    app.on_keyboard(FakeKey("Z", ctrl=True))
    assert len(app.data["top_priorities"]) == n - 1
    app.on_keyboard(FakeKey("Y", ctrl=True))
    assert len(app.data["top_priorities"]) == n


def test_kb_ctrl_shift_z_redoes(app):
    app.focused_section = "top_priorities"
    app.focused_index = 0
    app.add_row()
    n = len(app.data["top_priorities"])
    app.on_keyboard(FakeKey("Z", ctrl=True))            # undo
    app.on_keyboard(FakeKey("Z", ctrl=True, shift=True))  # redo
    assert len(app.data["top_priorities"]) == n


def test_kb_ctrl_t_adds_tab(app):
    before = len(app.all_data["tabs"])
    app.on_keyboard(FakeKey("T", ctrl=True))
    assert len(app.all_data["tabs"]) == before + 1


def test_kb_ctrl_w_closes_tab(app):
    app.add_tab()
    before = len(app.all_data["tabs"])
    app.on_keyboard(FakeKey("W", ctrl=True))
    assert len(app.all_data["tabs"]) == before - 1


def test_kb_ctrl_r_opens_rename(app):
    app.on_keyboard(FakeKey("R", ctrl=True))
    assert any(isinstance(d, ft.AlertDialog) for d in app.page.dialogs)


def test_kb_ctrl_comma_opens_settings(app):
    app.on_keyboard(FakeKey(",", ctrl=True))
    assert any(isinstance(d, ft.AlertDialog) for d in app.page.dialogs)
    assert app._settings_subtab == "Colors"
