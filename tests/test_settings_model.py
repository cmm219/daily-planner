"""Settings data-model tests: defaults, legacy migration, backfill, round-trip.

Pure logic — no GUI. Imports daily_planner at module scope (importing only runs
module-level constants/functions; main() is never called).
"""
import copy
import importlib.util
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import daily_planner as dp  # noqa: E402


def test_default_settings_complete():
    s = dp.get_default_settings()
    for key in dp.DEFAULT_SETTINGS:
        assert key in s
    # All 10 color slots present.
    for slot, _label in dp.COLOR_SLOTS:
        assert slot in s["colors"]


def test_default_settings_is_a_copy():
    a = dp.get_default_settings()
    b = dp.get_default_settings()
    a["colors"]["bg"] = "#deadbe"
    assert b["colors"]["bg"] != "#deadbe"
    # Mutating a returned copy must not corrupt the module template.
    assert dp.DEFAULT_SETTINGS["colors"]["bg"] != "#deadbe"


def test_all_presets_have_all_slots():
    slots = {slot for slot, _ in dp.COLOR_SLOTS}
    for name, preset in dp.PRESETS.items():
        missing = slots - set(preset)
        assert not missing, f"preset {name} missing slots {missing}"


def test_legacy_dark_flag_migrates():
    data = {"theme": "dark"}
    s = dp.normalize_settings(data)
    assert s["preset"] == "Dark"
    assert s["colors"]["bg"] == dp.PRESETS["Dark"]["bg"]
    # Legacy flag lives alongside; the app drops it on commit, not here.
    assert data["settings"] is s


def test_legacy_light_flag_migrates():
    data = {"theme": "light"}
    s = dp.normalize_settings(data)
    assert s["preset"] == "Light"
    assert s["colors"]["bg"] == dp.PRESETS["Light"]["bg"]


def test_missing_settings_gets_defaults():
    data = {}
    s = dp.normalize_settings(data)
    assert s["preset"] == "Dark"
    assert s["font_family"] == "Consolas"
    assert "settings" in data


def test_missing_top_level_keys_backfilled():
    data = {"settings": {"preset": "Light", "colors": dict(dp.PRESETS["Light"])}}
    s = dp.normalize_settings(data)
    # header_size etc. were absent -> backfilled from DEFAULT_SETTINGS.
    assert s["header_size"] == dp.DEFAULT_SETTINGS["header_size"]
    assert s["body_size"] == dp.DEFAULT_SETTINGS["body_size"]
    assert s["header_bold"] == dp.DEFAULT_SETTINGS["header_bold"]


def test_missing_color_slots_backfilled():
    data = {"settings": {"preset": "Matrix", "colors": {"bg": "#000000"}}}
    s = dp.normalize_settings(data)
    for slot, _label in dp.COLOR_SLOTS:
        assert slot in s["colors"]
    # Untouched custom value preserved; missing slots filled from the named preset.
    assert s["colors"]["bg"] == "#000000"
    assert s["colors"]["header"] == dp.PRESETS["Matrix"]["header"]


def test_custom_color_preserved_through_normalize():
    data = {"settings": dp.get_default_settings()}
    data["settings"]["colors"]["accent"] = "#abcdef"
    data["settings"]["font_family"] = "JetBrains Mono"
    s = dp.normalize_settings(data)
    assert s["colors"]["accent"] == "#abcdef"
    assert s["font_family"] == "JetBrains Mono"


def test_save_load_round_trip(tmp_path, monkeypatch):
    """A full settings block survives a JSON write+read cycle."""
    data = dp.get_default_data()
    data["settings"]["colors"]["bg"] = "#112233"
    data["settings"]["font_family"] = "Fira Code"
    data["settings"]["header_size"] = 22
    data["settings"]["header_bold"] = False

    f = tmp_path / "planner.json"
    f.write_text(json.dumps(data), encoding="utf-8")

    loaded = json.loads(f.read_text(encoding="utf-8"))
    s = dp.normalize_settings(loaded)
    assert s["colors"]["bg"] == "#112233"
    assert s["font_family"] == "Fira Code"
    assert s["header_size"] == 22
    assert s["header_bold"] is False


def test_normalize_is_idempotent():
    data = {"theme": "light"}
    first = copy.deepcopy(dp.normalize_settings(data))
    second = dp.normalize_settings(data)
    assert first == second


# --- Section overrides ---------------------------------------------------

def test_default_settings_has_all_sections():
    s = dp.get_default_settings()
    for key, label in dp.SECTION_DEFS:
        assert s["sections"][key]["label"] == label
        assert s["sections"][key]["enabled"] is True
        assert s["sections"][key]["custom"] is False


def test_sections_backfilled_when_missing():
    data = {"settings": {"preset": "Dark", "colors": dict(dp.PRESETS["Dark"])}}
    s = dp.normalize_settings(data)
    for key, label in dp.SECTION_DEFS:
        assert s["sections"][key]["label"] == label


def test_section_rename_and_hide_survive_normalize():
    data = {"settings": dp.get_default_settings()}
    data["settings"]["sections"]["top_priorities"]["label"] = "MY DAY"
    data["settings"]["sections"]["lesson"]["enabled"] = False
    s = dp.normalize_settings(data)
    assert s["sections"]["top_priorities"]["label"] == "MY DAY"
    assert s["sections"]["lesson"]["enabled"] is False


def test_custom_section_preserved_through_normalize():
    data = {"settings": dp.get_default_settings()}
    data["settings"]["sections"]["custom_abc12345"] = {
        "label": "READING LIST", "enabled": True, "custom": True}
    s = dp.normalize_settings(data)
    assert s["sections"]["custom_abc12345"]["label"] == "READING LIST"
    assert s["sections"]["custom_abc12345"]["custom"] is True
    # Built-ins still present and ordered before the custom one.
    keys = list(s["sections"])
    assert keys[:len(dp.SECTION_DEFS)] == [k for k, _ in dp.SECTION_DEFS]
    assert keys[-1] == "custom_abc12345"


def test_ensure_section_data_creates_lists_in_all_tabs():
    data = dp.get_default_data()
    data["tabs"].append({"id": "t2", "name": "x", "data": dp.get_default_planner()})
    settings = dp.normalize_settings(data)
    settings["sections"]["custom_xyz99999"] = {
        "label": "X", "enabled": True, "custom": True}
    dp.ensure_section_data(data, settings)
    for tab in data["tabs"]:
        assert "custom_xyz99999" in tab["data"]
        assert isinstance(tab["data"]["custom_xyz99999"], list)
