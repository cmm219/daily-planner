"""Headless integration QA for the settings dialog.

Flet 0.80 renders to a CanvasKit canvas, so we cannot click DOM selectors. Instead
we instantiate the REAL DailyPlanner against a stub Page and drive the SAME handler
methods the gear icon / Ctrl+, wire up. This proves: the dialog builds, every subtab
pane builds without error, editing a hex mutates the draft, and Save persists to disk.

The real C:\\Users\\Cmcna\\daily_planner.json is never touched: dp.DATA_FILE is
redirected to a tmp file for the whole test.
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
    def __init__(self, value):
        self.control = FakeControl(value)


class StubPage:
    """Minimal stand-in for ft.Page covering only what DailyPlanner touches."""
    def __init__(self):
        self.window = types.SimpleNamespace(width=0, height=0, icon=None)
        self.controls = []
        self.dialogs = []
        self.title = None
        self.bgcolor = None
        self.padding = None
        self.scroll = None
        self.on_keyboard_event = None
        self.updates = 0

    def show_dialog(self, d):
        self.dialogs.append(d)

    def pop_dialog(self):
        if self.dialogs:
            self.dialogs.pop()

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self, *a, **k):
        self.updates += 1

    def run_task(self, coro, *a, **k):
        # We don't run the event loop; close the coroutine to avoid warnings.
        try:
            coro.close()
        except Exception:
            pass


def _walk(control):
    """Yield a control and all descendants via .content / .controls."""
    yield control
    content = getattr(control, "content", None)
    if content is not None and hasattr(content, "__class__"):
        yield from _walk(content)
    kids = getattr(control, "controls", None)
    if isinstance(kids, (list, tuple)):
        for k in kids:
            if k is not None:
                yield from _walk(k)


def _find(control, predicate):
    for c in _walk(control):
        if predicate(c):
            return c
    return None


@pytest.fixture
def app(tmp_path):
    data_path = tmp_path / "planner.json"
    data_path.write_text(json.dumps(dp.get_default_data()), encoding="utf-8")
    old = dp.DATA_FILE
    dp.DATA_FILE = str(data_path)
    page = StubPage()
    planner = dp.DailyPlanner(page)
    planner._qa_data_path = str(data_path)
    yield planner
    dp.DATA_FILE = old


def test_app_builds_and_seeds_page(app):
    assert app.page.title == "Daily Planner"
    assert app.page.controls, "build_ui should have added content to the page"
    assert app.settings["preset"] in dp.PRESETS


def test_open_settings_pushes_dialog(app):
    app.open_settings()
    assert len(app.page.dialogs) == 1
    assert app._settings_subtab == "Colors"


def test_every_subtab_pane_builds(app):
    app.open_settings()
    for sub in ["Colors", "Headers / Bold", "Fonts", "Presets"]:
        app._settings_select(sub)
        assert app._settings_subtab == sub
        assert app._settings_pane.content is not None


def test_edit_hex_then_save_persists(app):
    app.open_settings()
    app._settings_select("Colors")
    pane = app._settings_pane.content
    # Find the accent TextField: the row whose label Text == "Accent / focus".
    accent_label = "Accent / focus"
    field = None
    for row in _walk(pane):
        if isinstance(row, ft.Row):
            texts = [c for c in (row.controls or []) if isinstance(c, ft.Text)]
            has_label = any(getattr(t, "value", None) == accent_label for t in texts)
            if has_label:
                field = _find(row, lambda c: isinstance(c, ft.TextField))
                if field:
                    break
    assert field is not None, "accent hex TextField not found"

    field.on_change(FakeEvent("#abcdef"))
    assert app._settings_draft["colors"]["accent"] == "#abcdef"

    app._settings_save()
    # Settings dialog closed (a transient SnackBar may remain), live settings updated.
    assert not any(isinstance(d, ft.AlertDialog) for d in app.page.dialogs)
    assert app.settings["colors"]["accent"] == "#abcdef"
    # Persisted to disk.
    on_disk = json.loads(open(app._qa_data_path, encoding="utf-8").read())
    assert on_disk["settings"]["colors"]["accent"] == "#abcdef"
    # Legacy flag never reintroduced.
    assert "theme" not in on_disk


def test_preset_click_swaps_all_colors(app):
    app.open_settings()
    app._settings_select("Presets")
    pane = app._settings_pane.content
    # Find the Matrix preset chip and fire its on_click.
    chip = _find(pane, lambda c: isinstance(c, ft.Container) and getattr(c, "on_click", None)
                 and _find(c, lambda t: isinstance(t, ft.Text) and "Matrix" in str(getattr(t, "value", ""))))
    assert chip is not None, "Matrix preset chip not found"
    chip.on_click(FakeEvent(None))
    assert app._settings_draft["preset"] == "Matrix"
    assert app._settings_draft["colors"]["bg"] == dp.PRESETS["Matrix"]["bg"]
    app._settings_save()
    on_disk = json.loads(open(app._qa_data_path, encoding="utf-8").read())
    assert on_disk["settings"]["preset"] == "Matrix"


def test_header_bold_toggle_and_size(app):
    app.open_settings()
    app._settings_select("Headers / Bold")
    pane = app._settings_pane.content
    sw = _find(pane, lambda c: isinstance(c, ft.Switch))
    assert sw is not None
    sw.on_change(FakeEvent(False))
    assert app._settings_draft["header_bold"] is False
    app._settings_save()
    on_disk = json.loads(open(app._qa_data_path, encoding="utf-8").read())
    assert on_disk["settings"]["header_bold"] is False


def test_font_family_change_persists(app):
    app.open_settings()
    app._settings_select("Fonts")
    pane = app._settings_pane.content
    dd = _find(pane, lambda c: isinstance(c, ft.Dropdown))
    assert dd is not None
    dd.on_select(FakeEvent("JetBrains Mono"))
    assert app._settings_draft["font_family"] == "JetBrains Mono"
    app._settings_save()
    on_disk = json.loads(open(app._qa_data_path, encoding="utf-8").read())
    assert on_disk["settings"]["font_family"] == "JetBrains Mono"


def test_titlebar_dots_are_clickable(app):
    app.open_settings()
    title = app._settings_dialog.title
    dots = [c for c in title.controls if isinstance(c, ft.Container)
            and getattr(c, "on_click", None) and c.width == 12]
    assert len(dots) == 3, "expected 3 clickable traffic-light dots"


def test_green_dot_toggles_dialog_size(app):
    app.open_settings()
    assert app._settings_content.width == 560
    app._settings_toggle_size()
    assert app._settings_content.width > 560
    assert app._settings_content.height > 340
    app._settings_toggle_size()
    assert app._settings_content.width == 560
    assert app._settings_content.height == 340


def test_red_dot_closes_dialog(app):
    app.open_settings()
    # Red dot is wired to _settings_cancel.
    app._settings_cancel()
    assert not any(isinstance(d, ft.AlertDialog) for d in app.page.dialogs)


def test_color_picker_opens_and_applies(app):
    app.open_settings()
    app._settings_select("Colors")
    # Open the picker for the accent slot.
    app._open_color_picker("accent", "Accent / focus")
    picker = app.page.dialogs[-1]
    assert isinstance(picker, ft.AlertDialog)

    # Type a hex into the picker's field (drives on_hex).
    hexf = _find(picker.content, lambda c: isinstance(c, ft.TextField))
    assert hexf is not None
    hexf.on_change(FakeEvent("#123456"))

    # Click "Use color" (the FilledButton in actions).
    use_btn = next(b for b in picker.actions if isinstance(b, ft.FilledButton))
    use_btn.on_click(FakeEvent(None))

    assert app._settings_draft["colors"]["accent"] == "#123456"
    # Picker closed; settings dialog still underneath.
    assert app.page.dialogs and isinstance(app.page.dialogs[-1], ft.AlertDialog)


def test_color_picker_has_sv_square_and_hue(app):
    app.open_settings()
    app._open_color_picker("bg", "Background")
    picker = app.page.dialogs[-1]
    assert _find(picker.content, lambda c: isinstance(c, ft.GestureDetector)) is not None
    assert _find(picker.content, lambda c: isinstance(c, ft.Slider)) is not None


def test_swatch_is_clickable(app):
    app.open_settings()
    app._settings_select("Colors")
    pane = app._settings_pane.content
    gestures = [c for c in _walk(pane) if isinstance(c, ft.GestureDetector)
                and getattr(c, "on_tap", None)]
    # One clickable swatch per color slot.
    assert len(gestures) == len(dp.COLOR_SLOTS)


def test_cancel_reverts_live_changes(app):
    app.open_settings()
    before = app.settings["colors"]["accent"]
    app._settings_select("Presets")
    pane = app._settings_pane.content
    chip = _find(pane, lambda c: isinstance(c, ft.Container) and getattr(c, "on_click", None)
                 and _find(c, lambda t: isinstance(t, ft.Text) and "Amber CRT" in str(getattr(t, "value", ""))))
    chip.on_click(FakeEvent(None))
    app._settings_apply()  # live preview
    assert app.settings["preset"] == "Amber CRT"
    app._settings_cancel()
    assert app.settings["colors"]["accent"] == before
    assert not any(isinstance(d, ft.AlertDialog) for d in app.page.dialogs)


# --- Sections subtab -----------------------------------------------------

TOP_LABEL = "TOP PRIORITIES - NON-NEGOTIABLES (DO FIRST)"
IMP_LABEL = "IMPORTANT / IN PROGRESS"


def _section_row(pane, label):
    """Return (checkbox, textfield) for the section row whose field == label."""
    for row in _walk(pane):
        if isinstance(row, ft.Row):
            kids = row.controls or []
            cbs = [c for c in kids if isinstance(c, ft.Checkbox)]
            flds = [c for c in kids if isinstance(c, ft.TextField)]
            if cbs and flds and flds[0].value == label:
                return cbs[0], flds[0]
    return None, None


def _page_has_text(app, value):
    for c in app.page.controls:
        for w in _walk(c):
            if isinstance(w, ft.Text) and getattr(w, "value", None) == value:
                return True
    return False


def test_sections_subtab_builds(app):
    app.open_settings()
    app._settings_select("Sections")
    assert app._settings_subtab == "Sections"
    pane = app._settings_pane.content
    assert pane is not None
    checkboxes = [c for c in _walk(pane) if isinstance(c, ft.Checkbox)]
    assert len(checkboxes) == len(dp.SECTION_DEFS)


def test_section_rename_persists(app):
    app.open_settings()
    app._settings_select("Sections")
    _, field = _section_row(app._settings_pane.content, TOP_LABEL)
    assert field is not None
    field.on_change(FakeEvent("MY DAY"))
    assert app._settings_draft["sections"]["top_priorities"]["label"] == "MY DAY"
    app._settings_save()
    assert app.settings["sections"]["top_priorities"]["label"] == "MY DAY"
    on_disk = json.loads(open(app._qa_data_path, encoding="utf-8").read())
    assert on_disk["settings"]["sections"]["top_priorities"]["label"] == "MY DAY"
    # Renamed header now shows in the live UI.
    assert _page_has_text(app, "MY DAY")


def test_section_blank_rename_reverts(app):
    app.open_settings()
    app._settings_select("Sections")
    _, field = _section_row(app._settings_pane.content, TOP_LABEL)
    field.value = ""
    field.on_blur(FakeEvent(""))
    assert app._settings_draft["sections"]["top_priorities"]["label"] == TOP_LABEL
    assert field.value == TOP_LABEL


def test_section_hide_removes_from_ui(app):
    app.open_settings()
    app._settings_select("Sections")
    cb, _ = _section_row(app._settings_pane.content, IMP_LABEL)
    assert cb is not None
    cb.on_change(FakeEvent(False))
    assert app._settings_draft["sections"]["important"]["enabled"] is False
    app._settings_save()
    assert app._sec_on("important") is False
    assert not _page_has_text(app, IMP_LABEL)
    on_disk = json.loads(open(app._qa_data_path, encoding="utf-8").read())
    assert on_disk["settings"]["sections"]["important"]["enabled"] is False


def test_add_section_creates_section_and_data(app):
    app.open_settings()
    app._settings_select("Sections")
    before = len(app._settings_draft["sections"])
    btn = _find(app._settings_pane.content,
                lambda c: isinstance(c, ft.TextButton) and "Add section" in str(getattr(c, "content", "")))
    assert btn is not None
    btn.on_click(FakeEvent(None))
    assert len(app._settings_draft["sections"]) == before + 1
    new_keys = [k for k, v in app._settings_draft["sections"].items() if v.get("custom")]
    assert new_keys
    key = new_keys[0]
    app._settings_save()
    # Custom section got a data list in the active tab and renders in the UI.
    assert key in app.data
    assert _page_has_text(app, "NEW SECTION")
    on_disk = json.loads(open(app._qa_data_path, encoding="utf-8").read())
    assert any(key in t["data"] for t in on_disk["tabs"])
    assert on_disk["settings"]["sections"][key]["custom"] is True


def test_remove_custom_section(app):
    app.open_settings()
    app._settings_select("Sections")
    btn = _find(app._settings_pane.content,
                lambda c: isinstance(c, ft.TextButton) and "Add section" in str(getattr(c, "content", "")))
    btn.on_click(FakeEvent(None))
    key = [k for k, v in app._settings_draft["sections"].items() if v.get("custom")][0]
    # The ✕ delete control is a Container with on_click in the new section's row.
    pane = app._settings_pane.content
    x = _find(pane, lambda c: isinstance(c, ft.Container) and getattr(c, "on_click", None)
              and _find(c, lambda t: isinstance(t, ft.Text) and getattr(t, "value", "") == "✕"))
    assert x is not None
    x.on_click(FakeEvent(None))
    assert key not in app._settings_draft["sections"]


def test_reset_section_names(app):
    app.open_settings()
    app._settings_select("Sections")
    app._settings_draft["sections"]["top_priorities"]["label"] = "CHANGED"
    app._refresh_settings_pane()
    btn = _find(app._settings_pane.content,
                lambda c: isinstance(c, ft.TextButton) and "Reset section names" in str(getattr(c, "content", "")))
    assert btn is not None
    btn.on_click(FakeEvent(None))
    assert app._settings_draft["sections"]["top_priorities"]["label"] == dp.SECTION_DEFAULT_LABELS["top_priorities"]
