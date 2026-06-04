"""
Daily Planner - Flet Desktop App
A paper-style daily planner with dynamic rows, task archiving, and reflections.

Run: pip install flet && python daily_planner.py

Hotkeys:
- Ctrl+Enter: Add new row to current section
- Ctrl+Backspace: Archive current row (moves to archive with completion tracking)
- Ctrl+Z: Undo
- Ctrl+Y: Redo
- Enter: New line within field (multi-line)
"""

import flet as ft
import json
import copy
import colorsys
import os
import uuid
from datetime import datetime

# Data file
DATA_FILE = r"C:\Users\Cmcna\daily_planner.json"

# Color slots every theme defines. Order drives the Colors settings subtab.
COLOR_SLOTS = [
    ("bg", "Background"),
    ("panel", "Panel / row box"),
    ("border", "Border"),
    ("text", "Body text"),
    ("text_dim", "Dim / hints"),
    ("accent", "Accent / focus"),
    ("green", "Checkbox green"),
    ("red", "Delete / close"),
    ("header", "Header (bold)"),
    ("divider", "Divider lines"),
]

# Built-in color presets. "Dark" is the historical default look.
PRESETS = {
    "Dark": {
        "bg": "#0d1117", "panel": "#161b22", "border": "#30363d",
        "text": "#c9d1d9", "text_dim": "#484f58", "accent": "#58a6ff",
        "green": "#238636", "red": "#f85149", "header": "#58a6ff", "divider": "#30363d",
    },
    "Light": {
        "bg": "#ffffff", "panel": "#f6f8fa", "border": "#d0d7de",
        "text": "#1f2328", "text_dim": "#656d76", "accent": "#0969da",
        "green": "#1a7f37", "red": "#cf222e", "header": "#0969da", "divider": "#d0d7de",
    },
    "Matrix": {
        "bg": "#021107", "panel": "#04210f", "border": "#0f5132",
        "text": "#39ff14", "text_dim": "#1f7a3d", "accent": "#7fff00",
        "green": "#39ff14", "red": "#ff5555", "header": "#7fff00", "divider": "#0f5132",
    },
    "Amber CRT": {
        "bg": "#1a1200", "panel": "#241900", "border": "#5c4400",
        "text": "#ffb000", "text_dim": "#8a6000", "accent": "#ffcf4d",
        "green": "#ffb000", "red": "#ff6b3d", "header": "#ffcf4d", "divider": "#5c4400",
    },
    "Solarized": {
        "bg": "#002b36", "panel": "#073642", "border": "#586e75",
        "text": "#93a1a1", "text_dim": "#586e75", "accent": "#268bd2",
        "green": "#859900", "red": "#dc322f", "header": "#b58900", "divider": "#586e75",
    },
}

# Font families offered in the Fonts subtab. Users can also type any installed font.
FONT_PRESETS = [
    "Consolas", "Cascadia Mono", "Cascadia Code", "JetBrains Mono",
    "Fira Code", "Courier New", "Segoe UI", "Calibri", "Georgia",
]

# Editable section headers, in display order. Drives the Sections settings subtab.
# Each entry: (key, default blue-header label). Users can rename, hide, or add to these.
SECTION_DEFS = [
    ("top_priorities", "TOP PRIORITIES - NON-NEGOTIABLES (DO FIRST)"),
    ("important", "IMPORTANT / IN PROGRESS"),
    ("low_priority", "LOW PRIORITY / PARKING LOT"),
    ("one_win", "ONE WIN TODAY (EVEN SMALL):"),
    ("task_score", "AVERAGE TASK SCORE TODAY (1-10):"),
    ("gratitude", "GRATITUDE - WHAT WENT RIGHT TODAY?"),
    ("lesson", "LESSON / AWARENESS"),
    ("tomorrow_top", "TOMORROW SETUP"),
    ("first_action", "FIRST ACTION TOMORROW MORNING:"),
]
SECTION_DEFAULT_LABELS = dict(SECTION_DEFS)


def _default_sections():
    """Fresh section-override map: every built-in kept + named at its default."""
    return {k: {"label": v, "enabled": True, "custom": False} for k, v in SECTION_DEFS}


# Default typography: terminal monospace, bold/large headers, smaller body.
DEFAULT_SETTINGS = {
    "preset": "Dark",
    "colors": dict(PRESETS["Dark"]),
    "font_family": "Consolas",
    "header_size": 16,
    "body_size": 13,
    "divider_size": 12,
    "header_bold": True,
    "sections": _default_sections(),
}


def get_default_settings():
    """Return a fresh copy of the default settings block."""
    s = dict(DEFAULT_SETTINGS)
    s["colors"] = dict(DEFAULT_SETTINGS["colors"])
    s["sections"] = {k: dict(v) for k, v in DEFAULT_SETTINGS["sections"].items()}
    return s


def normalize_settings(all_data):
    """Ensure all_data['settings'] exists and has every key. Migrates the old
    top-level 'theme': 'dark'|'light' flag into the settings/preset model."""
    settings = all_data.get("settings")
    if not isinstance(settings, dict):
        settings = get_default_settings()
        # Honor a legacy theme flag if present.
        legacy = all_data.get("theme")
        if legacy in ("dark", "light"):
            preset = "Light" if legacy == "light" else "Dark"
            settings["preset"] = preset
            settings["colors"] = dict(PRESETS[preset])
    # Backfill any missing top-level keys.
    for k, v in DEFAULT_SETTINGS.items():
        if k not in settings:
            settings[k] = dict(v) if isinstance(v, dict) else v
    # Backfill any missing color slots.
    base = PRESETS.get(settings.get("preset"), PRESETS["Dark"])
    if not isinstance(settings.get("colors"), dict):
        settings["colors"] = dict(base)
    for slot, _label in COLOR_SLOTS:
        settings["colors"].setdefault(slot, base.get(slot, "#000000"))
    # Backfill the section-override map: every built-in present + named, custom kept.
    sections = settings.get("sections")
    if not isinstance(sections, dict):
        sections = {}
    rebuilt = {}
    for key, default_label in SECTION_DEFS:
        existing = sections.get(key) if isinstance(sections.get(key), dict) else {}
        rebuilt[key] = {
            "label": existing.get("label", default_label),
            "enabled": existing.get("enabled", True),
            "custom": False,
        }
    # Preserve any user-added custom sections (appended after the built-ins).
    for key, val in sections.items():
        if key not in rebuilt and isinstance(val, dict) and val.get("custom"):
            rebuilt[key] = {
                "label": val.get("label", key),
                "enabled": val.get("enabled", True),
                "custom": True,
            }
    settings["sections"] = rebuilt
    all_data["settings"] = settings
    return settings


# Sections that have checkboxes
CHECKBOX_SECTIONS = ["top_priorities", "important", "low_priority"]

# All sections in order
ALL_SECTIONS = [
    "top_priorities", "important", "low_priority", "one_win",
    "gratitude", "lesson", "tomorrow_top", "first_action"
]


def get_default_planner():
    """Return default empty planner data for a single tab"""
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "top_priorities": [{"text": "", "done": False, "dateAdded": today}],
        "important": [{"text": "", "done": False, "dateAdded": today}],
        "low_priority": [{"text": "", "dateAdded": today}],
        "one_win": [{"text": "", "dateAdded": today}],
        "task_score": "",
        "gratitude": [{"text": "", "dateAdded": today}],
        "lesson": [{"text": "", "dateAdded": today}],
        "tomorrow_top": [{"text": "", "dateAdded": today}],
        "first_action": [{"text": "", "dateAdded": today}],
        "archive": [],
        "lastUpdated": today,
    }


def get_default_data():
    """Return default data structure with tabs"""
    today = datetime.now().strftime("%Y-%m-%d")
    tab_id = str(uuid.uuid4())[:8]
    return {
        "tabs": [
            {"id": tab_id, "name": today, "data": get_default_planner()}
        ],
        "activeTab": tab_id,
        "settings": get_default_settings(),
    }


def migrate_planner_data(data):
    """Migrate old planner format within a single tab"""
    today = datetime.now().strftime("%Y-%m-%d")

    for section in ALL_SECTIONS:
        if section not in data:
            if section in CHECKBOX_SECTIONS:
                data[section] = [{"text": "", "done": False, "dateAdded": today}]
            else:
                data[section] = [{"text": "", "dateAdded": today}]
        else:
            new_list = []
            for item in data[section]:
                if isinstance(item, str):
                    if section in CHECKBOX_SECTIONS:
                        new_list.append({"text": item, "done": False, "dateAdded": today})
                    else:
                        new_list.append({"text": item, "dateAdded": today})
                elif isinstance(item, dict):
                    if "dateAdded" not in item:
                        item["dateAdded"] = today
                    if section in CHECKBOX_SECTIONS and "done" not in item:
                        item["done"] = False
                    new_list.append(item)

            if not new_list:
                if section in CHECKBOX_SECTIONS:
                    new_list = [{"text": "", "done": False, "dateAdded": today}]
                else:
                    new_list = [{"text": "", "dateAdded": today}]

            data[section] = new_list

    if "archive" not in data:
        data["archive"] = []

    return data


def migrate_data(data):
    """Migrate data to tabs format if needed"""
    today = datetime.now().strftime("%Y-%m-%d")

    # Check if already in tabs format
    if "tabs" in data and isinstance(data["tabs"], list):
        # Migrate each tab's planner data
        for tab in data["tabs"]:
            if "data" in tab:
                tab["data"] = migrate_planner_data(tab["data"])
        return data

    # Old format: single planner - convert to tabs
    tab_id = str(uuid.uuid4())[:8]
    planner_data = migrate_planner_data(data)
    return {
        "tabs": [
            {"id": tab_id, "name": today, "data": planner_data}
        ],
        "activeTab": tab_id
    }


def ensure_section_data(all_data, settings):
    """Make sure every custom section key has an (empty) row list in every tab,
    so build_section/add_row never KeyError on a user-added section."""
    today = datetime.now().strftime("%Y-%m-%d")
    custom_keys = [k for k, v in settings.get("sections", {}).items() if v.get("custom")]
    for tab in all_data.get("tabs", []):
        data = tab.get("data")
        if not isinstance(data, dict):
            continue
        for key in custom_keys:
            if key not in data:
                data[key] = [{"text": "", "dateAdded": today}]


class DailyPlanner:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Daily Planner"
        self.page.bgcolor = PRESETS["Dark"]["bg"]  # Default, updated after settings load
        self.page.padding = 20
        self.page.window.width = 700
        self.page.window.height = 900
        _icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "planner_icon.ico")
        if os.path.exists(_icon):
            self.page.window.icon = _icon
        self.page.scroll = ft.ScrollMode.AUTO

        # Undo/redo
        self.undo_stack = []
        self.redo_stack = []
        self.MAX_UNDO = 50

        # Track focused field
        self.focused_section = None
        self.focused_index = None
        self.focused_textfield = None

        # Track pending focus after rebuild
        self.pending_focus_section = None
        self.pending_focus_index = None
        self.field_to_focus = None

        # Load all data (tabs structure)
        self.all_data = self.load_data()

        # Current tab's planner data (shortcut reference)
        self.data = self.get_active_tab_data()

        # Load settings (colors + fonts) and apply
        self.settings = normalize_settings(self.all_data)
        ensure_section_data(self.all_data, self.settings)
        self.theme = self.settings["colors"]
        self.apply_theme()

        # Build UI
        self.build_ui()

        # Keyboard handler
        self.page.on_keyboard_event = self.on_keyboard

    def get_active_tab_data(self):
        """Get the data for the currently active tab"""
        active_id = self.all_data.get("activeTab")
        for tab in self.all_data.get("tabs", []):
            if tab["id"] == active_id:
                return tab["data"]
        # Fallback to first tab
        if self.all_data.get("tabs"):
            return self.all_data["tabs"][0]["data"]
        return get_default_planner()

    def get_active_tab(self):
        """Get the currently active tab object"""
        active_id = self.all_data.get("activeTab")
        for tab in self.all_data.get("tabs", []):
            if tab["id"] == active_id:
                return tab
        if self.all_data.get("tabs"):
            return self.all_data["tabs"][0]
        return None

    # --- Section overrides (rename / hide / custom) ---
    def _sections(self):
        return self.settings.get("sections", {})

    def _sec_on(self, key):
        """Is this section enabled (visible)? Unknown keys default to visible."""
        meta = self._sections().get(key)
        return True if meta is None else bool(meta.get("enabled", True))

    def _sec_label(self, key):
        """The current header text for a section, falling back to its default."""
        meta = self._sections().get(key)
        if meta and meta.get("label"):
            return meta["label"]
        return SECTION_DEFAULT_LABELS.get(key, key)

    # --- Typography helpers (read from current settings) ---
    @property
    def font_family(self):
        return self.settings.get("font_family") or "Consolas"

    @property
    def header_size(self):
        return self.settings.get("header_size", 16)

    @property
    def body_size(self):
        return self.settings.get("body_size", 13)

    @property
    def divider_size(self):
        return self.settings.get("divider_size", 12)

    @property
    def header_weight(self):
        return ft.FontWeight.BOLD if self.settings.get("header_bold", True) else ft.FontWeight.W_500

    def apply_theme(self):
        """Apply current theme to page"""
        self.page.bgcolor = self.theme["bg"]

    def toggle_theme(self, e=None):
        """Quick toggle between the Dark and Light presets."""
        current = self.settings.get("preset")
        new_preset = "Light" if current != "Light" else "Dark"
        self.apply_preset(new_preset)

    def apply_preset(self, name):
        """Switch all color slots to a named preset and persist."""
        if name not in PRESETS:
            return
        self.settings["preset"] = name
        self.settings["colors"] = dict(PRESETS[name])
        self.theme = self.settings["colors"]
        self.apply_theme()
        self.save_data()
        self.rebuild_ui()

    def load_data(self):
        """Load data from JSON file"""
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                data = migrate_data(data)
                normalize_settings(data)
                return data
        except:
            return get_default_data()

    def save_data(self):
        """Save all data to JSON file"""
        # Update lastUpdated on current tab's data
        self.data["lastUpdated"] = datetime.now().strftime("%Y-%m-%d")
        # Backup
        try:
            with open(DATA_FILE, 'r') as f:
                backup = f.read()
            with open(DATA_FILE + ".bak", 'w') as f:
                f.write(backup)
        except:
            pass
        # Save entire tabs structure
        with open(DATA_FILE, 'w') as f:
            json.dump(self.all_data, f, indent=2)

    def snapshot_for_undo(self):
        """Save state before mutation"""
        self.undo_stack.append(copy.deepcopy(self.data))
        if len(self.undo_stack) > self.MAX_UNDO:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        """Undo last action"""
        if not self.undo_stack:
            self.show_snackbar("Nothing to undo")
            return
        self.redo_stack.append(copy.deepcopy(self.data))
        self.data = self.undo_stack.pop()
        self.save_data()
        self.rebuild_ui()
        self.show_snackbar("Undo")

    def redo(self):
        """Redo last undone action"""
        if not self.redo_stack:
            self.show_snackbar("Nothing to redo")
            return
        self.undo_stack.append(copy.deepcopy(self.data))
        self.data = self.redo_stack.pop()
        self.save_data()
        self.rebuild_ui()
        self.show_snackbar("Redo")

    def show_snackbar(self, message: str):
        """Show a brief notification"""
        sb = ft.SnackBar(
            content=ft.Text(message, color=self.theme["text"], font_family=self.font_family),
            bgcolor=self.theme["panel"],
            duration=1500,
        )
        self.page.show_dialog(sb)

    def rebuild_ui(self):
        """Rebuild UI after changes"""
        self.page.controls.clear()
        self.build_ui()
        self.page.update()

        # Focus the pending field after update
        if self.field_to_focus:
            field = self.field_to_focus
            self.field_to_focus = None
            async def do_focus():
                await field.focus()
                self.page.update()
            self.page.run_task(do_focus)

    def build_tab_bar(self):
        """Build the tab bar at the top"""
        tabs = []
        active_id = self.all_data.get("activeTab")

        for tab in self.all_data.get("tabs", []):
            is_active = tab["id"] == active_id
            tab_btn = ft.Container(
                content=ft.Text(
                    tab["name"],
                    size=self.body_size,
                    font_family=self.font_family,
                    color=self.theme["text"] if is_active else self.theme["text_dim"],
                    weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL,
                ),
                padding=ft.Padding(12, 8, 12, 8),
                bgcolor=self.theme["panel"] if is_active else self.theme["bg"],
                border=ft.Border.all(1, self.theme["accent"] if is_active else self.theme["border"]),
                border_radius=ft.BorderRadius.only(top_left=8, top_right=8),
                on_click=lambda e, tid=tab["id"]: self.switch_tab(tid),
            )
            tabs.append(tab_btn)

        # Small dim close button
        close_tab_btn = ft.Container(
            content=ft.Text("✕", size=11, color=self.theme["text_dim"], font_family=self.font_family),
            padding=ft.Padding(6, 8, 6, 8),
            on_click=lambda e: self.close_tab(self.all_data.get("activeTab")),
        )
        tabs.append(close_tab_btn)

        # Theme toggle button
        is_dark = self.settings.get("preset") != "Light"
        theme_btn = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE if is_dark else ft.Icons.DARK_MODE,
            icon_color=self.theme["text_dim"],
            tooltip="Toggle light/dark mode",
            on_click=self.toggle_theme,
        )

        # Settings (gear) button
        settings_btn = ft.IconButton(
            icon=ft.Icons.SETTINGS,
            icon_color=self.theme["accent"],
            tooltip="Settings (Ctrl+,)",
            on_click=self.open_settings,
        )

        return ft.Container(
            content=ft.Row(
                [ft.Row(tabs, spacing=2), ft.Row([theme_btn, settings_btn], spacing=0)],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.Padding(0, 0, 0, 10),
        )

    def build_ui(self):
        """Build the main UI. Section headers + visibility come from settings["sections"]."""
        controls = [self.build_tab_bar()]

        if self._sec_on("top_priorities"):
            controls += [self.build_header(self._sec_label("top_priorities")),
                         self.build_section("top_priorities", has_checkbox=True)]
        if self._sec_on("important"):
            controls += [self.build_divider(),
                         self.build_subheader(self._sec_label("important")),
                         self.build_section("important", has_checkbox=True)]
        if self._sec_on("low_priority"):
            controls += [self.build_divider(),
                         self.build_subheader(self._sec_label("low_priority")),
                         self.build_section("low_priority", has_checkbox=True)]
        if self._sec_on("one_win"):
            controls += [ft.Container(height=10),
                         self.build_subheader(self._sec_label("one_win")),
                         self.build_section("one_win")]
        if self._sec_on("task_score"):
            controls += [ft.Container(height=10), self.build_score_row()]
        if self._sec_on("gratitude"):
            controls += [self.build_header(self._sec_label("gratitude")),
                         self.build_section("gratitude", bullet=True)]
        if self._sec_on("lesson"):
            controls += [self.build_divider(),
                         self.build_subheader(self._sec_label("lesson")),
                         self.build_subheader("WHAT I LEARNED OR NOTICED TODAY:"),
                         self.build_section("lesson")]
        if self._sec_on("tomorrow_top"):
            controls += [self.build_divider(),
                         self.build_subheader(self._sec_label("tomorrow_top")),
                         self.build_subheader("TOMORROW'S TOP 1:"),
                         self.build_section("tomorrow_top")]
        if self._sec_on("first_action"):
            controls += [ft.Container(height=10),
                         self.build_subheader(self._sec_label("first_action")),
                         self.build_section("first_action")]

        # User-added custom sections render after the built-ins.
        for key, meta in self._sections().items():
            if meta.get("custom") and meta.get("enabled", True):
                controls += [self.build_divider(),
                             self.build_subheader(self._sec_label(key)),
                             self.build_section(key)]

        controls += [
            ft.Container(height=20),
            ft.Text(
                "Ctrl+T: New tab | Ctrl+R: Rename | Ctrl+W: Close | Ctrl+Enter: Add row | Ctrl+,: Settings",
                size=11,
                color=self.theme["text_dim"],
                font_family=self.font_family,
                text_align=ft.TextAlign.CENTER,
            ),
        ]

        content = ft.Column(
            controls=controls,
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        self.page.add(content)

    def build_header(self, text):
        """Build a major section header with lines above and below"""
        line = "=" * 60
        return ft.Column([
            ft.Container(height=15),
            ft.Text(line, size=self.divider_size, color=self.theme["divider"], font_family=self.font_family),
            ft.Text(text, size=self.header_size, color=self.theme["header"],
                    weight=self.header_weight, font_family=self.font_family),
            ft.Text(line, size=self.divider_size, color=self.theme["divider"], font_family=self.font_family),
        ], spacing=2)

    def build_divider(self):
        """Build a simple divider"""
        return ft.Column([
            ft.Container(height=10),
            ft.Text("-" * 60, size=self.divider_size, color=self.theme["divider"], font_family=self.font_family),
        ], spacing=2)

    def build_subheader(self, text):
        """Build a sub-section header"""
        return ft.Text(text, size=max(self.body_size, self.header_size - 3), color=self.theme["header"],
                       weight=self.header_weight, font_family=self.font_family)

    def build_section(self, section_key, has_checkbox=False, bullet=False):
        """Build a dynamic section with rows"""
        rows = []
        items = self.data.get(section_key, [])

        for i, item in enumerate(items):
            row = self.build_row(section_key, i, item, has_checkbox, bullet)
            rows.append(row)

        return ft.Column(rows, spacing=5)

    def build_row(self, section_key, index, item, has_checkbox=False, bullet=False):
        """Build a single row"""
        text = item.get("text", "") if isinstance(item, dict) else item
        done = item.get("done", False) if isinstance(item, dict) else False

        controls = []

        # Checkbox for task sections
        if has_checkbox:
            checkbox = ft.Checkbox(
                value=done,
                on_change=lambda e, sk=section_key, idx=index: self.on_checkbox_change(e, sk, idx),
                active_color=self.theme["green"],
                check_color=self.theme["bg"],
            )
            controls.append(checkbox)

        # Bullet point
        if bullet:
            controls.append(ft.Text("*", size=self.header_size, color=self.theme["accent"], font_family=self.font_family))

        # Check if this field should be auto-focused
        should_focus = (self.pending_focus_section == section_key and
                       self.pending_focus_index == index)

        # Text field
        textfield = ft.TextField(
            value=text,
            border_color=self.theme["border"],
            focused_border_color=self.theme["accent"],
            bgcolor=self.theme["panel"],
            color=self.theme["text"] if not done else self.theme["text_dim"],
            text_size=self.body_size,
            text_style=ft.TextStyle(font_family=self.font_family),
            content_padding=ft.Padding(10, 8, 10, 8),
            expand=True,
            multiline=True,
            min_lines=1,
            max_lines=5,
            on_change=lambda e, sk=section_key, idx=index: self.on_text_change(e, sk, idx),
            on_focus=lambda e, sk=section_key, idx=index: self.on_field_focus(e, sk, idx),
            on_blur=lambda e, sk=section_key, idx=index: self.on_field_blur(e, sk, idx),
        )

        # Store reference to field that needs focus
        if should_focus:
            self.field_to_focus = textfield
            self.pending_focus_section = None
            self.pending_focus_index = None
        if done:
            textfield.text_style = ft.TextStyle(
                decoration=ft.TextDecoration.LINE_THROUGH, font_family=self.font_family)

        controls.append(textfield)

        return ft.Row(controls, spacing=5)

    def build_score_row(self):
        """Build the task score input row"""
        score_field = ft.TextField(
            value=str(self.data.get("task_score", "")),
            border_color=self.theme["border"],
            focused_border_color=self.theme["accent"],
            bgcolor=self.theme["panel"],
            color=self.theme["text"],
            text_size=self.body_size,
            text_style=ft.TextStyle(font_family=self.font_family),
            width=60,
            text_align=ft.TextAlign.CENTER,
            content_padding=ft.Padding(10, 8, 10, 8),
            on_change=self.on_score_change,
            on_blur=self.on_score_blur,
        )

        return ft.Row([
            ft.Text(self._sec_label("task_score"),
                    size=max(self.body_size, self.header_size - 3), color=self.theme["header"],
                    weight=self.header_weight, font_family=self.font_family),
            score_field,
        ], spacing=10)

    # --- Settings dialog (terminal-styled, themeable) ---

    def open_settings(self, e=None):
        """Open the terminal-style settings dialog."""
        # Snapshot for cancel/revert; edit a draft copy.
        self._settings_backup = copy.deepcopy(self.settings)
        self._settings_draft = copy.deepcopy(self.settings)
        self._settings_subtab = "Colors"

        self._settings_pane = ft.Container(expand=True, padding=ft.Padding(16, 14, 16, 14))
        self._settings_subtabs_col = ft.Column(spacing=0, width=160)
        self._refresh_settings_subtabs()
        self._refresh_settings_pane()

        body = ft.Row(
            [
                ft.Container(self._settings_subtabs_col, bgcolor=self.theme["bg"],
                             border=ft.Border.only(right=ft.BorderSide(1, self.theme["border"]))),
                self._settings_pane,
            ],
            spacing=0, vertical_alignment=ft.CrossAxisAlignment.START,
        )

        self._settings_expanded = False
        self._settings_content = ft.Container(body, width=560, height=340)

        title = ft.Row([
            self._settings_dot(self.theme["red"], "Close", self._settings_cancel),
            self._settings_dot("#d29922", "Minimize", self._settings_minimize),
            self._settings_dot(self.theme["green"], "Expand / restore", self._settings_toggle_size),
            ft.Container(width=8),
            ft.Text("planner --settings", size=13, color=self.theme["text"], font_family=self.font_family),
        ], spacing=6)

        self._settings_dialog = ft.AlertDialog(
            modal=True,
            bgcolor=self.theme["panel"],
            title=title,
            content=self._settings_content,
            actions=[
                ft.TextButton("Reset to preset", on_click=self._settings_reset,
                              style=ft.ButtonStyle(color=self.theme["text_dim"])),
                ft.TextButton("Apply", on_click=self._settings_apply,
                              style=ft.ButtonStyle(color=self.theme["accent"])),
                ft.TextButton("Cancel", on_click=self._settings_cancel,
                              style=ft.ButtonStyle(color=self.theme["text_dim"])),
                ft.FilledButton("Save", on_click=self._settings_save,
                                style=ft.ButtonStyle(bgcolor=self.theme["accent"], color=self.theme["bg"])),
            ],
        )
        self.page.show_dialog(self._settings_dialog)

    def _settings_dot(self, color, tooltip, on_click):
        """A clickable traffic-light dot in the settings titlebar."""
        return ft.Container(
            width=12, height=12, border_radius=6, bgcolor=color,
            tooltip=tooltip, on_click=lambda e: on_click(e),
        )

    def _settings_minimize(self, e=None):
        """Yellow dot: minimize the app window (dialog stays open underneath)."""
        try:
            self.page.window.minimized = True
            self.page.update()
        except Exception:
            pass

    def _settings_toggle_size(self, e=None):
        """Green dot: toggle the dialog between compact and (near) full window."""
        self._settings_expanded = not getattr(self, "_settings_expanded", False)
        if self._settings_expanded:
            w = max(560, int(getattr(self.page.window, "width", 700) or 700) - 60)
            h = max(340, int(getattr(self.page.window, "height", 900) or 900) - 100)
        else:
            w, h = 560, 340
        self._settings_content.width = w
        self._settings_content.height = h
        self.page.update()

    # --- Color math + visual picker -------------------------------------
    @staticmethod
    def _hex_to_rgb(h):
        h = (h or "").lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) >= 6:
            try:
                return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            except ValueError:
                return 0, 0, 0
        return 0, 0, 0

    @staticmethod
    def _rgb_to_hex(r, g, b):
        return "#%02x%02x%02x" % (max(0, min(255, int(round(r)))),
                                  max(0, min(255, int(round(g)))),
                                  max(0, min(255, int(round(b)))))

    def _hsv_to_hex(self, hue, s, v):
        r, g, b = colorsys.hsv_to_rgb((hue % 360) / 360.0, s, v)
        return self._rgb_to_hex(r * 255, g * 255, b * 255)

    def _apply_picked_color(self, slot, hex_value):
        """Write a chosen color into the draft and refresh the Colors pane so
        the swatch + hex field both reflect it."""
        self._settings_draft["colors"][slot] = hex_value
        self._refresh_settings_pane()
        self.page.update()

    def _open_color_picker(self, slot, label):
        """Windows-Terminal-style picker: saturation/value square + hue slider +
        live hex. Writes to the draft on 'Use color'."""
        start = self._settings_draft["colors"].get(slot, "#000000")
        r, g, b = self._hex_to_rgb(start)
        h0, s0, v0 = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        st = {"h": h0 * 360.0, "s": s0, "v": v0}
        W, H = 224, 168

        base = ft.Container(width=W, height=H, border_radius=6,
                            bgcolor=self._hsv_to_hex(st["h"], 1, 1))
        white = ft.Container(width=W, height=H, border_radius=6,
                             gradient=ft.LinearGradient(begin=ft.Alignment.CENTER_LEFT,
                                                        end=ft.Alignment.CENTER_RIGHT,
                                                        colors=["#ffffffff", "#00ffffff"]))
        black = ft.Container(width=W, height=H, border_radius=6,
                             gradient=ft.LinearGradient(begin=ft.Alignment.TOP_CENTER,
                                                        end=ft.Alignment.BOTTOM_CENTER,
                                                        colors=["#00000000", "#ff000000"]))
        cursor = ft.Container(width=14, height=14, border_radius=7,
                              border=ft.Border.all(2, "#ffffff"),
                              left=st["s"] * W - 7, top=(1 - st["v"]) * H - 7)
        preview = ft.Container(width=44, height=44, border_radius=6, bgcolor=start,
                               border=ft.Border.all(1, self.theme["border"]))
        hexf = ft.TextField(value=start, width=120, text_size=13,
                            text_style=ft.TextStyle(font_family=self.font_family),
                            color=self.theme["text"], bgcolor=self.theme["bg"],
                            border_color=self.theme["border"],
                            focused_border_color=self.theme["accent"],
                            content_padding=ft.Padding(8, 6, 8, 6), text_align=ft.TextAlign.CENTER)

        def current_hex():
            return self._hsv_to_hex(st["h"], st["s"], st["v"])

        def redraw(update_hexfield=True):
            base.bgcolor = self._hsv_to_hex(st["h"], 1, 1)
            cursor.left = st["s"] * W - 7
            cursor.top = (1 - st["v"]) * H - 7
            hexv = current_hex()
            preview.bgcolor = hexv
            if update_hexfield:
                hexf.value = hexv
            self.page.update()

        def on_sv(e):
            pos = getattr(e, "local_position", None)
            if pos is None:
                return
            x = max(0.0, min(float(W), float(pos.x)))
            y = max(0.0, min(float(H), float(pos.y)))
            st["s"] = x / W
            st["v"] = 1 - y / H
            redraw()

        def on_hue(e):
            st["h"] = float(e.control.value)
            redraw()

        def on_hex(e):
            val = (e.control.value or "").strip()
            if not val.startswith("#"):
                val = "#" + val
            if len(val) in (4, 7):
                rr, gg, bb = self._hex_to_rgb(val)
                hh, ss, vv = colorsys.rgb_to_hsv(rr / 255.0, gg / 255.0, bb / 255.0)
                st["h"], st["s"], st["v"] = hh * 360.0, ss, vv
                hue_slider.value = st["h"]
                redraw(update_hexfield=False)

        hexf.on_change = on_hex

        sv_stack = ft.Stack([base, white, black, cursor], width=W, height=H)
        sv = ft.GestureDetector(content=sv_stack, on_pan_start=on_sv,
                                on_pan_update=on_sv, on_tap_down=on_sv)

        rainbow = ft.Container(
            height=12, border_radius=6,
            gradient=ft.LinearGradient(begin=ft.Alignment.CENTER_LEFT, end=ft.Alignment.CENTER_RIGHT,
                                       colors=["#ff0000", "#ffff00", "#00ff00", "#00ffff",
                                               "#0000ff", "#ff00ff", "#ff0000"]))
        hue_slider = ft.Slider(min=0, max=360, value=st["h"], on_change=on_hue,
                               active_color=self.theme["accent"])

        def use_color(e=None):
            self._apply_picked_color(slot, current_hex())
            self.page.pop_dialog()

        def cancel(e=None):
            self.page.pop_dialog()

        picker = ft.AlertDialog(
            modal=True, bgcolor=self.theme["panel"],
            title=ft.Text(f"pick: {label}", size=14, color=self.theme["text"],
                          font_family=self.font_family, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                ft.Column([
                    sv,
                    ft.Container(height=6),
                    rainbow,
                    hue_slider,
                    ft.Row([preview, hexf], spacing=12,
                           alignment=ft.MainAxisAlignment.START,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ], spacing=6, tight=True),
                width=W + 20, height=H + 150,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel,
                              style=ft.ButtonStyle(color=self.theme["text_dim"])),
                ft.FilledButton("Use color", on_click=use_color,
                                style=ft.ButtonStyle(bgcolor=self.theme["accent"], color=self.theme["bg"])),
            ],
        )
        self.page.show_dialog(picker)

    def _refresh_settings_subtabs(self):
        names = ["Colors", "Headers / Bold", "Fonts", "Sections", "Presets"]
        rows = []
        for name in names:
            active = name == self._settings_subtab
            rows.append(ft.Container(
                content=ft.Text((("> " if active else "  ") + name),
                                size=13, font_family=self.font_family,
                                color=self.theme["accent"] if active else self.theme["text_dim"],
                                weight=ft.FontWeight.BOLD if active else ft.FontWeight.NORMAL),
                padding=ft.Padding(14, 9, 14, 9),
                bgcolor=ft.Colors.with_opacity(0.08, self.theme["accent"]) if active else None,
                border=ft.Border.only(left=ft.BorderSide(3, self.theme["accent"] if active else "#00000000")),
                on_click=lambda e, n=name: self._settings_select(n),
            ))
        self._settings_subtabs_col.controls = rows

    def _settings_select(self, name):
        self._settings_subtab = name
        self._refresh_settings_subtabs()
        self._refresh_settings_pane()
        self.page.update()

    def _refresh_settings_pane(self):
        sub = self._settings_subtab
        if sub == "Colors":
            self._settings_pane.content = self._settings_colors_pane()
        elif sub == "Headers / Bold":
            self._settings_pane.content = self._settings_headers_pane()
        elif sub == "Fonts":
            self._settings_pane.content = self._settings_fonts_pane()
        elif sub == "Sections":
            self._settings_pane.content = self._settings_sections_pane()
        else:
            self._settings_pane.content = self._settings_presets_pane()

    def _settings_label(self, text):
        return ft.Text(text, size=12, color=self.theme["text_dim"], font_family=self.font_family)

    def _hex_row(self, slot, label):
        draft = self._settings_draft
        swatch = ft.Container(width=24, height=24, border_radius=5,
                              bgcolor=draft["colors"].get(slot, "#000000"),
                              border=ft.Border.all(1, self.theme["border"]),
                              tooltip="Click to pick a color")

        def on_change(e):
            val = (e.control.value or "").strip()
            if val and not val.startswith("#"):
                val = "#" + val
            if len(val) in (4, 7, 9):
                draft["colors"][slot] = val
                swatch.bgcolor = val
                self.page.update()

        field = ft.TextField(
            value=draft["colors"].get(slot, ""), width=110, text_size=12,
            text_style=ft.TextStyle(font_family=self.font_family),
            color=self.theme["text"], bgcolor=self.theme["bg"],
            border_color=self.theme["border"], focused_border_color=self.theme["accent"],
            content_padding=ft.Padding(8, 6, 8, 6), text_align=ft.TextAlign.CENTER,
            on_change=on_change,
        )
        # Clicking the swatch opens the visual picker; it writes the slot and the
        # field is kept in sync via _apply_picked_color (which rebuilds the pane).
        swatch_btn = ft.GestureDetector(
            content=swatch,
            on_tap=lambda e, s=slot, l=label: self._open_color_picker(s, l),
            mouse_cursor=ft.MouseCursor.CLICK,
        )
        return ft.Row(
            [ft.Text(label, size=13, color=self.theme["text"], font_family=self.font_family, expand=True),
             swatch_btn, field],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=8,
        )

    def _settings_colors_pane(self):
        rows = [self._settings_label("COLORS — type a hex value")]
        for slot, label in COLOR_SLOTS:
            rows.append(self._hex_row(slot, label))
        return ft.Column(rows, spacing=6, scroll=ft.ScrollMode.AUTO)

    def _settings_headers_pane(self):
        draft = self._settings_draft

        def on_bold(e):
            draft["header_bold"] = e.control.value

        def on_size(e):
            draft["header_size"] = int(e.control.value)
            size_lbl.value = f"Header size: {int(e.control.value)}"
            self.page.update()

        size_lbl = self._settings_label(f"Header size: {draft.get('header_size', 16)}")
        return ft.Column([
            self._settings_label("SECTION HEADERS (the bold titles)"),
            self._hex_row("header", "Header color"),
            ft.Row([ft.Text("Bold", size=13, color=self.theme["text"], font_family=self.font_family, expand=True),
                    ft.Switch(value=draft.get("header_bold", True), active_color=self.theme["accent"],
                              on_change=on_bold)],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=6),
            size_lbl,
            ft.Slider(min=11, max=28, divisions=17, value=draft.get("header_size", 16),
                      active_color=self.theme["accent"], on_change=on_size),
        ], spacing=8)

    def _settings_fonts_pane(self):
        draft = self._settings_draft

        def on_family(e):
            draft["font_family"] = e.control.value
            custom.value = e.control.value
            self.page.update()

        def on_custom(e):
            val = (e.control.value or "").strip()
            if val:
                draft["font_family"] = val
                family_dd.value = val if val in FONT_PRESETS else None
                self.page.update()

        def mk_size(key, lo, hi, label):
            lbl = self._settings_label(f"{label}: {draft.get(key)}")

            def on_change(e):
                draft[key] = int(e.control.value)
                lbl.value = f"{label}: {int(e.control.value)}"
                self.page.update()
            return ft.Column([lbl, ft.Slider(min=lo, max=hi, divisions=hi - lo,
                                              value=draft.get(key), active_color=self.theme["accent"],
                                              on_change=on_change)], spacing=2)

        cur = draft.get("font_family")
        family_dd = ft.Dropdown(
            value=cur if cur in FONT_PRESETS else None,
            options=[ft.DropdownOption(f) for f in FONT_PRESETS],
            text_size=13, width=240, on_select=on_family,
            bgcolor=self.theme["bg"], color=self.theme["text"],
            border_color=self.theme["border"],
        )
        custom = ft.TextField(
            value=cur, width=240, text_size=12, hint_text="e.g. Cascadia Code",
            text_style=ft.TextStyle(font_family=self.font_family),
            color=self.theme["text"], bgcolor=self.theme["bg"],
            border_color=self.theme["border"], focused_border_color=self.theme["accent"],
            content_padding=ft.Padding(8, 6, 8, 6), on_change=on_custom,
        )
        custom_caption = ft.Text(
            "or type any font installed on this PC",
            size=11, italic=True, color=self.theme["text_dim"],
        )
        return ft.Column([
            self._settings_label("FONT FAMILY"),
            family_dd,
            ft.Container(height=10),
            custom_caption,
            custom,
            ft.Container(height=10),
            self._settings_label("SIZES"),
            mk_size("header_size", 11, 28, "Header"),
            mk_size("body_size", 10, 20, "Body"),
            mk_size("divider_size", 8, 18, "Divider lines"),
        ], spacing=6, scroll=ft.ScrollMode.AUTO)

    def _settings_sections_pane(self):
        draft = self._settings_draft
        secs = draft.setdefault("sections", {})

        def toggle(key, val):
            secs[key]["enabled"] = bool(val)

        def rename(key, val):
            secs[key]["label"] = val

        def revert_if_blank(key, field):
            if not (field.value or "").strip():
                default = SECTION_DEFAULT_LABELS.get(key) or secs.get(key, {}).get("label") or key
                secs[key]["label"] = default
                field.value = default
                self.page.update()

        def remove_custom(key):
            secs.pop(key, None)
            self._refresh_settings_pane()
            self.page.update()

        def add_section(e=None):
            new_key = "custom_" + uuid.uuid4().hex[:8]
            secs[new_key] = {"label": "NEW SECTION", "enabled": True, "custom": True}
            self._refresh_settings_pane()
            self.page.update()

        def reset_names(e=None):
            for k, default in SECTION_DEFS:
                if k in secs:
                    secs[k]["label"] = default
            self._refresh_settings_pane()
            self.page.update()

        rows = [
            self._settings_label("SECTIONS"),
            self._settings_label("Uncheck to hide a section. Edit the text to rename its header."),
            ft.Container(height=4),
        ]
        for key, meta in secs.items():
            field = ft.TextField(
                value=meta.get("label", ""), width=288, text_size=12,
                text_style=ft.TextStyle(font_family=self.font_family),
                color=self.theme["text"], bgcolor=self.theme["bg"],
                border_color=self.theme["border"], focused_border_color=self.theme["accent"],
                content_padding=ft.Padding(8, 6, 8, 6),
            )
            field.on_change = lambda e, k=key: rename(k, e.control.value)
            field.on_blur = lambda e, k=key, f=field: revert_if_blank(k, f)
            row_controls = [
                ft.Checkbox(
                    value=meta.get("enabled", True),
                    active_color=self.theme["accent"], check_color=self.theme["bg"],
                    on_change=lambda e, k=key: toggle(k, e.control.value),
                ),
                ft.Text("✎", size=13, color=self.theme["text_dim"], font_family=self.font_family),
                field,
            ]
            if meta.get("custom"):
                row_controls.append(ft.Container(
                    content=ft.Text("✕", size=12, color=self.theme["red"], font_family=self.font_family),
                    padding=ft.Padding(6, 4, 6, 4), tooltip="Delete this section",
                    on_click=lambda e, k=key: remove_custom(k),
                ))
            rows.append(ft.Row(row_controls, spacing=6,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER))

        rows.append(ft.Container(height=6))
        rows.append(ft.Row([
            ft.TextButton("+ Add section", on_click=add_section,
                          style=ft.ButtonStyle(color=self.theme["accent"])),
            ft.TextButton("Reset section names", on_click=reset_names,
                          style=ft.ButtonStyle(color=self.theme["text_dim"])),
        ], spacing=4))
        return ft.Column(rows, spacing=8, scroll=ft.ScrollMode.AUTO)

    def _settings_presets_pane(self):
        draft = self._settings_draft

        def apply_preset(name):
            draft["preset"] = name
            draft["colors"] = dict(PRESETS[name])
            self._refresh_settings_pane()
            self.page.update()

        chips = []
        for name in PRESETS:
            cols = PRESETS[name]
            selected = draft.get("preset") == name
            swatches = ft.Row([
                ft.Container(width=16, height=16, border_radius=4, bgcolor=cols[k])
                for k in ("bg", "panel", "header", "accent", "green")
            ], spacing=3)
            chips.append(ft.Container(
                content=ft.Row([
                    ft.Text(("> " if selected else "  ") + name, size=13,
                            color=self.theme["accent"] if selected else self.theme["text"],
                            font_family=self.font_family, weight=ft.FontWeight.BOLD if selected else ft.FontWeight.NORMAL,
                            expand=True),
                    swatches,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.Padding(12, 10, 12, 10),
                bgcolor=self.theme["bg"],
                border=ft.Border.all(1, self.theme["accent"] if selected else self.theme["border"]),
                border_radius=6,
                on_click=lambda e, n=name: apply_preset(n),
            ))
        return ft.Column(
            [self._settings_label("PRESETS — one click sets all colors, then tweak in Colors")] + chips,
            spacing=8, scroll=ft.ScrollMode.AUTO,
        )

    def _commit_settings(self, draft):
        self.settings = copy.deepcopy(draft)
        self.all_data["settings"] = self.settings
        self.all_data.pop("theme", None)  # drop legacy flag
        ensure_section_data(self.all_data, self.settings)
        self.data = self.get_active_tab_data()
        self.theme = self.settings["colors"]
        self.apply_theme()

    def _settings_apply(self, e=None):
        """Live-preview the draft without closing or persisting."""
        self._commit_settings(self._settings_draft)
        self.rebuild_ui()

    def _settings_save(self, e=None):
        self._commit_settings(self._settings_draft)
        self.save_data()
        self.page.pop_dialog()
        self.rebuild_ui()
        self.show_snackbar("Settings saved")

    def _settings_cancel(self, e=None):
        # Restore the snapshot in case Apply changed the live view.
        self._commit_settings(self._settings_backup)
        self.page.pop_dialog()
        self.rebuild_ui()

    def _settings_reset(self, e=None):
        preset = self._settings_draft.get("preset", "Dark")
        self._settings_draft["colors"] = dict(PRESETS.get(preset, PRESETS["Dark"]))
        self._refresh_settings_pane()
        self.page.update()

    # --- Event Handlers ---

    def on_field_focus(self, e, section_key, index):
        """Track which field is focused"""
        self.focused_section = section_key
        self.focused_index = index
        self.focused_textfield = e.control

    def on_field_blur(self, e, section_key, index):
        """Handle field blur - auto-delete empty rows (except first)"""
        # Save current text
        text = e.control.value.strip()
        self.data[section_key][index]["text"] = text
        self.save_data()

        # Auto-delete empty rows (but not the first row)
        if index > 0 and text == "":
            self.snapshot_for_undo()
            self.data[section_key].pop(index)
            self.save_data()
            self.rebuild_ui()

    def on_checkbox_change(self, e, section_key, index):
        """Handle checkbox toggle"""
        self.snapshot_for_undo()
        self.data[section_key][index]["done"] = e.control.value
        self.save_data()
        self.rebuild_ui()

    def on_text_change(self, e, section_key, index):
        """Handle text change (no save yet, just update in memory)"""
        self.data[section_key][index]["text"] = e.control.value

    def on_score_change(self, e):
        """Handle score change"""
        self.data["task_score"] = e.control.value

    def on_score_blur(self, e):
        """Save score when leaving field"""
        self.snapshot_for_undo()
        self.data["task_score"] = e.control.value
        self.save_data()

    # --- Actions ---

    def add_row(self):
        """Add a new row to the currently focused section"""
        if self.focused_section is None:
            self.show_snackbar("Click in a section first")
            return

        self.snapshot_for_undo()
        today = datetime.now().strftime("%Y-%m-%d")

        if self.focused_section in CHECKBOX_SECTIONS:
            new_item = {"text": "", "done": False, "dateAdded": today}
        else:
            new_item = {"text": "", "dateAdded": today}

        # Insert after current index
        insert_at = (self.focused_index or 0) + 1
        self.data[self.focused_section].insert(insert_at, new_item)
        self.save_data()

        # Set pending focus to the new row
        self.pending_focus_section = self.focused_section
        self.pending_focus_index = insert_at

        self.rebuild_ui()
        self.show_snackbar("Row added")

    def archive_row(self):
        """Archive the currently focused row"""
        if self.focused_section is None or self.focused_index is None:
            self.show_snackbar("Click in a row first")
            return

        section = self.focused_section
        index = self.focused_index
        items = self.data.get(section, [])

        if index >= len(items):
            return

        # Sync current text from focused textfield before archiving
        if self.focused_textfield:
            self.data[section][index]["text"] = self.focused_textfield.value

        item = items[index]
        text = item.get("text", "").strip()

        # Don't archive empty rows
        if not text:
            self.show_snackbar("Cannot archive empty row")
            return

        # First row special handling
        if index == 0:
            # For checkbox sections, must be completed to archive first row
            if section in CHECKBOX_SECTIONS and not item.get("done", False):
                self.show_snackbar("Complete the task first (check the box)")
                return

        self.snapshot_for_undo()

        # Calculate days to complete
        date_added = item.get("dateAdded", datetime.now().strftime("%Y-%m-%d"))
        date_completed = datetime.now().strftime("%Y-%m-%d")

        try:
            added_dt = datetime.strptime(date_added, "%Y-%m-%d")
            completed_dt = datetime.strptime(date_completed, "%Y-%m-%d")
            days_to_complete = (completed_dt - added_dt).days
        except:
            days_to_complete = 0

        # Create archive entry
        archive_entry = {
            "text": text,
            "section": section,
            "dateAdded": date_added,
            "dateCompleted": date_completed,
            "daysToComplete": days_to_complete,
        }

        if section in CHECKBOX_SECTIONS:
            archive_entry["wasCompleted"] = item.get("done", False)

        self.data["archive"].append(archive_entry)

        # Remove from section
        items.pop(index)

        # If first row was archived, add a new empty row
        if index == 0 and len(items) == 0:
            today = datetime.now().strftime("%Y-%m-%d")
            if section in CHECKBOX_SECTIONS:
                items.append({"text": "", "done": False, "dateAdded": today})
            else:
                items.append({"text": "", "dateAdded": today})

        self.save_data()

        # Set focus to the row above (or row 0 if we archived the first row)
        self.pending_focus_section = section
        if index > 0:
            self.pending_focus_index = index - 1
        else:
            self.pending_focus_index = 0

        # Clear old textfield reference before rebuild
        self.focused_textfield = None

        self.rebuild_ui()
        self.show_snackbar(f"Archived! ({days_to_complete} days)")

    # --- Tab Methods ---

    def switch_tab(self, tab_id):
        """Switch to a different tab"""
        if tab_id == self.all_data.get("activeTab"):
            return

        self.all_data["activeTab"] = tab_id
        self.data = self.get_active_tab_data()
        self.save_data()

        # Clear focus tracking
        self.focused_section = None
        self.focused_index = None
        self.focused_textfield = None

        self.rebuild_ui()

    def show_tab_menu(self, e, tab_id):
        """Show right-click context menu for a tab"""
        def close_menu(e):
            self.page.pop_dialog()

        def on_add(e):
            self.page.pop_dialog()
            self.add_tab()

        def on_rename(e):
            self.page.pop_dialog()
            self.rename_tab_dialog(tab_id)

        def on_close(e):
            self.page.pop_dialog()
            self.close_tab(tab_id)

        menu_dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text("Tab Options", size=14, color=self.theme["text"], font_family=self.font_family),
            bgcolor=self.theme["panel"],
            content=ft.Column([
                ft.TextButton("Add Tab", on_click=on_add,
                    style=ft.ButtonStyle(color=self.theme["text"])),
                ft.TextButton("Rename", on_click=on_rename,
                    style=ft.ButtonStyle(color=self.theme["text"])),
                ft.TextButton("Close", on_click=on_close,
                    style=ft.ButtonStyle(color=self.theme["red"])),
            ], spacing=0, tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=close_menu),
            ],
        )
        self.page.show_dialog(menu_dialog)

    def add_tab(self):
        """Add a new tab"""
        today = datetime.now().strftime("%Y-%m-%d")
        new_id = str(uuid.uuid4())[:8]
        new_tab = {
            "id": new_id,
            "name": today,
            "data": get_default_planner()
        }
        self.all_data["tabs"].append(new_tab)
        self.all_data["activeTab"] = new_id
        self.data = new_tab["data"]
        self.save_data()

        # Clear focus tracking
        self.focused_section = None
        self.focused_index = None
        self.focused_textfield = None

        self.rebuild_ui()
        self.show_snackbar("New tab created")

    def rename_tab_dialog(self, tab_id):
        """Show dialog to rename a tab"""
        tab = None
        for t in self.all_data.get("tabs", []):
            if t["id"] == tab_id:
                tab = t
                break
        if not tab:
            return

        name_field = ft.TextField(
            value=tab["name"],
            border_color=self.theme["border"],
            focused_border_color=self.theme["accent"],
            bgcolor=self.theme["bg"],
            color=self.theme["text"],
            autofocus=True,
        )

        def close_dialog(e):
            self.page.pop_dialog()

        def save_name(e):
            new_name = name_field.value.strip()
            if new_name:
                tab["name"] = new_name
                self.save_data()
            self.page.pop_dialog()
            if new_name:
                self.rebuild_ui()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Rename Tab", size=14, color=self.theme["text"], font_family=self.font_family),
            bgcolor=self.theme["panel"],
            content=name_field,
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.TextButton("Save", on_click=save_name),
            ],
        )
        self.page.show_dialog(dialog)

    def close_tab(self, tab_id):
        """Close a tab"""
        tabs = self.all_data.get("tabs", [])

        # Don't allow closing the last tab
        if len(tabs) <= 1:
            self.show_snackbar("Cannot close the last tab")
            return

        # Find the tab
        tab_to_close = None
        tab_index = -1
        for i, t in enumerate(tabs):
            if t["id"] == tab_id:
                tab_to_close = t
                tab_index = i
                break

        if not tab_to_close:
            return

        # Check if tab has content
        has_content = False
        for section in ALL_SECTIONS:
            items = tab_to_close["data"].get(section, [])
            for item in items:
                if item.get("text", "").strip():
                    has_content = True
                    break
            if has_content:
                break

        def do_close(e=None):
            if hasattr(self, '_confirm_dialog'):
                self._confirm_dialog.open = False
                self.page.update()

            tabs.pop(tab_index)

            # If we closed the active tab, switch to another
            if self.all_data.get("activeTab") == tab_id:
                new_index = min(tab_index, len(tabs) - 1)
                self.all_data["activeTab"] = tabs[new_index]["id"]
                self.data = tabs[new_index]["data"]

            self.save_data()

            # Clear focus tracking
            self.focused_section = None
            self.focused_index = None
            self.focused_textfield = None

            self.rebuild_ui()
            self.show_snackbar("Tab closed")

        do_close()

    def on_keyboard(self, e: ft.KeyboardEvent):
        """Handle keyboard events"""
        if e.ctrl and e.key == "Z":
            if e.shift:
                self.redo()
            else:
                self.undo()
            self.page.update()
        elif e.ctrl and e.key == "Y":
            self.redo()
            self.page.update()
        elif e.ctrl and e.key == "Enter":
            self.add_row()
            self.page.update()
        elif e.ctrl and e.key == "Backspace":
            self.archive_row()
            self.page.update()
        elif e.ctrl and e.key.lower() == "t":
            self.add_tab()
            self.page.update()
        elif e.ctrl and e.key.lower() == "w":
            # Close current tab
            active_id = self.all_data.get("activeTab")
            if active_id:
                self.close_tab(active_id)
            self.page.update()
        elif e.ctrl and e.key.lower() == "r":
            # Rename current tab
            active_id = self.all_data.get("activeTab")
            if active_id:
                self.rename_tab_dialog(active_id)
        elif e.ctrl and e.key == ",":
            self.open_settings()


def main(page: ft.Page):
    DailyPlanner(page)


if __name__ == "__main__":
    ft.run(main)
