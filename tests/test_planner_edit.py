"""Tests for scripts/planner_edit.py -- the AI-helper control surface.

Exercises the safety contract: backup-before-write, append/merge only, reorder
is a strict permutation, section name resolution by key or label. Always runs
against a temp file; the real planner JSON is never opened.
"""
import json
import os
import sys
import glob

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import daily_planner as dp  # noqa: E402
import planner_edit as pe  # noqa: E402


@pytest.fixture
def planner_file(tmp_path):
    data = dp.get_default_data()
    # Give Top Priorities a couple of real rows + a known label.
    data["tabs"][0]["data"]["top_priorities"] = [
        {"text": "task A", "done": False, "dateAdded": "2026-06-04"},
        {"text": "task B", "done": False, "dateAdded": "2026-06-04"},
    ]
    p = tmp_path / "planner.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


def _read(path):
    return json.loads(open(path, encoding="utf-8").read())


def _active(all_data):
    return pe.active_tab_data(all_data)


# --- resolution ----------------------------------------------------------

def test_resolve_by_key(planner_file):
    ad = pe.load(planner_file)
    assert pe.resolve_section(ad, "top_priorities") == "top_priorities"


def test_resolve_by_label_substring(planner_file):
    ad = pe.load(planner_file)
    # Default label contains "TOP PRIORITIES"
    assert pe.resolve_section(ad, "top priorities") == "top_priorities"


def test_resolve_unknown_raises(planner_file):
    ad = pe.load(planner_file)
    with pytest.raises(KeyError):
        pe.resolve_section(ad, "nonsense section")


# --- add -----------------------------------------------------------------

def test_add_appends_without_clobber(planner_file):
    ad = pe.load(planner_file)
    n = pe.add_rows(ad, "top_priorities", ["task C", "  ", "task D"])
    assert n == 2  # blank skipped
    rows = [r["text"] for r in _active(ad)["top_priorities"]]
    assert rows == ["task A", "task B", "task C", "task D"]


def test_add_checkbox_section_gets_done(planner_file):
    ad = pe.load(planner_file)
    pe.add_rows(ad, "top_priorities", ["new"])
    assert _active(ad)["top_priorities"][-1]["done"] is False


def test_add_noncheckbox_section_no_done(planner_file):
    ad = pe.load(planner_file)
    pe.add_rows(ad, "gratitude", ["thankful"])
    assert "done" not in _active(ad)["gratitude"][-1]


# --- reorder -------------------------------------------------------------

def test_reorder_permutes(planner_file):
    ad = pe.load(planner_file)
    pe.add_rows(ad, "top_priorities", ["task C"])  # now A,B,C
    pe.reorder(ad, "top_priorities", [3, 1, 2])
    rows = [r["text"] for r in _active(ad)["top_priorities"]]
    assert rows == ["task C", "task A", "task B"]


def test_reorder_rejects_non_permutation(planner_file):
    ad = pe.load(planner_file)  # 2 rows
    with pytest.raises(ValueError):
        pe.reorder(ad, "top_priorities", [1, 1])
    with pytest.raises(ValueError):
        pe.reorder(ad, "top_priorities", [1, 2, 3])


# --- backup / save -------------------------------------------------------

def test_save_makes_backup(planner_file):
    ad = pe.load(planner_file)
    pe.add_rows(ad, "gratitude", ["x"])
    pe.save(ad, planner_file)
    baks = glob.glob(planner_file + ".aibak-*")
    assert len(baks) == 1
    # Backup holds the PRE-edit content (no "x" in gratitude yet).
    pre = json.loads(open(baks[0], encoding="utf-8").read())
    grat = [r.get("text", "") for r in pre["tabs"][0]["data"]["gratitude"]]
    assert "x" not in grat


# --- set-score + summary -------------------------------------------------

def test_set_score(planner_file):
    ad = pe.load(planner_file)
    pe.set_score(ad, 9)
    assert _active(ad)["task_score"] == "9"


def test_summarize_lists_rows(planner_file):
    ad = pe.load(planner_file)
    summ = pe.summarize(ad)
    assert summ["sections"]["top_priorities"]["rows"] == ["task A", "task B"]


# --- CLI end-to-end ------------------------------------------------------

def test_cli_add_then_summary(planner_file, capsys):
    rc = pe.main(["--data-file", planner_file, "add",
                  "--section", "top_priorities", "--text", "from cli"])
    assert rc == 0
    saved = _read(planner_file)
    rows = [r["text"] for r in saved["tabs"][0]["data"]["top_priorities"]]
    assert rows[-1] == "from cli"


def test_cli_summary_json(planner_file, capsys):
    rc = pe.main(["--data-file", planner_file, "summary", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "top_priorities" in parsed["sections"]


def test_cli_missing_file_errors(tmp_path):
    missing = str(tmp_path / "nope.json")
    rc = pe.main(["--data-file", missing, "summary"])
    assert rc == 2
