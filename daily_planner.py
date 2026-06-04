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
import uuid
from datetime import datetime

# Data file
DATA_FILE = r"C:\Users\Cmcna\daily_planner.json"

# Dark theme colors
DARK_THEME = {
    "bg": "#0d1117",
    "panel": "#161b22",
    "border": "#30363d",
    "text": "#c9d1d9",
    "text_dim": "#484f58",
    "accent": "#58a6ff",
    "green": "#238636",
    "red": "#f85149",
    "header": "#58a6ff",
    "divider": "#30363d",
}

# Light theme colors
LIGHT_THEME = {
    "bg": "#ffffff",
    "panel": "#f6f8fa",
    "border": "#d0d7de",
    "text": "#1f2328",
    "text_dim": "#656d76",
    "accent": "#0969da",
    "green": "#1a7f37",
    "red": "#cf222e",
    "header": "#0969da",
    "divider": "#d0d7de",
}

# Current theme (will be set dynamically)
THEME = DARK_THEME

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
        "theme": "dark"
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


class DailyPlanner:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Daily Planner"
        self.page.bgcolor = DARK_THEME["bg"]  # Default, will be updated after theme loads
        self.page.padding = 20
        self.page.window.width = 700
        self.page.window.height = 900
        self.page.window.icon = r"C:\Users\Cmcna\Documents\To Do List\planner_icon.ico"
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

        # Load theme
        self.theme = DARK_THEME if self.all_data.get("theme", "dark") == "dark" else LIGHT_THEME
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

    def apply_theme(self):
        """Apply current theme to page"""
        self.page.bgcolor = self.theme["bg"]

    def toggle_theme(self, e=None):
        """Toggle between light and dark theme"""
        if self.all_data.get("theme", "dark") == "dark":
            self.all_data["theme"] = "light"
            self.theme = LIGHT_THEME
        else:
            self.all_data["theme"] = "dark"
            self.theme = DARK_THEME
        self.apply_theme()
        self.save_data()
        self.rebuild_ui()

    def load_data(self):
        """Load data from JSON file"""
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                return migrate_data(data)
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
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=self.theme["text"]),
            bgcolor=self.theme["panel"],
            duration=1500,
        )
        self.page.snack_bar.open = True
        self.page.update()

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
                    size=13,
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
            content=ft.Text("✕", size=11, color=self.theme["text_dim"]),
            padding=ft.Padding(6, 8, 6, 8),
            on_click=lambda e: self.close_tab(self.all_data.get("activeTab")),
        )
        tabs.append(close_tab_btn)

        # Theme toggle button
        is_dark = self.all_data.get("theme", "dark") == "dark"
        theme_btn = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE if is_dark else ft.Icons.DARK_MODE,
            icon_color=self.theme["text_dim"],
            tooltip="Toggle light/dark mode",
            on_click=self.toggle_theme,
        )

        return ft.Container(
            content=ft.Row(
                [ft.Row(tabs, spacing=2), theme_btn],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.Padding(0, 0, 0, 10),
        )

    def build_ui(self):
        """Build the main UI"""
        content = ft.Column(
            controls=[
                self.build_tab_bar(),
                self.build_header("TOP PRIORITIES - NON-NEGOTIABLES (DO FIRST)"),
                self.build_section("top_priorities", has_checkbox=True),

                self.build_divider(),
                self.build_subheader("IMPORTANT / IN PROGRESS"),
                self.build_section("important", has_checkbox=True),

                self.build_divider(),
                self.build_subheader("LOW PRIORITY / PARKING LOT"),
                self.build_section("low_priority", has_checkbox=True),

                ft.Container(height=10),
                self.build_subheader("ONE WIN TODAY (EVEN SMALL):"),
                self.build_section("one_win"),

                ft.Container(height=10),
                self.build_score_row(),

                self.build_header("GRATITUDE - WHAT WENT RIGHT TODAY?"),
                self.build_section("gratitude", bullet=True),

                self.build_divider(),
                self.build_subheader("LESSON / AWARENESS"),
                self.build_subheader("WHAT I LEARNED OR NOTICED TODAY:"),
                self.build_section("lesson"),

                self.build_divider(),
                self.build_subheader("TOMORROW SETUP"),
                self.build_subheader("TOMORROW'S TOP 1:"),
                self.build_section("tomorrow_top"),

                ft.Container(height=10),
                self.build_subheader("FIRST ACTION TOMORROW MORNING:"),
                self.build_section("first_action"),

                ft.Container(height=20),
                ft.Text(
                    "Ctrl+T: New tab | Ctrl+R: Rename tab | Ctrl+W: Close tab | Ctrl+Enter: Add row",
                    size=11,
                    color=self.theme["text_dim"],
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        self.page.add(content)

    def build_header(self, text):
        """Build a major section header with lines above and below"""
        line = "=" * 60
        return ft.Column([
            ft.Container(height=15),
            ft.Text(line, size=12, color=self.theme["divider"], font_family="Consolas"),
            ft.Text(text, size=14, color=self.theme["header"], weight=ft.FontWeight.BOLD),
            ft.Text(line, size=12, color=self.theme["divider"], font_family="Consolas"),
        ], spacing=2)

    def build_divider(self):
        """Build a simple divider"""
        return ft.Column([
            ft.Container(height=10),
            ft.Text("-" * 60, size=12, color=self.theme["divider"], font_family="Consolas"),
        ], spacing=2)

    def build_subheader(self, text):
        """Build a sub-section header"""
        return ft.Text(text, size=13, color=self.theme["header"], weight=ft.FontWeight.W_500)

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
            controls.append(ft.Text("*", size=16, color=self.theme["accent"]))

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
            text_size=14,
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
            textfield.text_style = ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH)

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
            text_size=14,
            width=60,
            text_align=ft.TextAlign.CENTER,
            content_padding=ft.Padding(10, 8, 10, 8),
            on_change=self.on_score_change,
            on_blur=self.on_score_blur,
        )

        return ft.Row([
            ft.Text("AVERAGE TASK SCORE TODAY (1-10):", size=13, color=self.theme["header"], weight=ft.FontWeight.W_500),
            score_field,
        ], spacing=10)

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
            menu_dialog.open = False
            self.page.update()

        def on_add(e):
            menu_dialog.open = False
            self.page.update()
            self.add_tab()

        def on_rename(e):
            menu_dialog.open = False
            self.page.update()
            self.rename_tab_dialog(tab_id)

        def on_close(e):
            menu_dialog.open = False
            self.page.update()
            self.close_tab(tab_id)

        menu_dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text("Tab Options", size=14, color=self.theme["text"]),
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
        self.page.dialog = menu_dialog
        menu_dialog.open = True
        self.page.update()

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
            dialog.open = False
            self.page.update()

        def save_name(e):
            new_name = name_field.value.strip()
            if new_name:
                tab["name"] = new_name
                self.save_data()
            dialog.open = False
            self.page.update()
            if new_name:
                self.rebuild_ui()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Rename Tab", size=14, color=self.theme["text"]),
            bgcolor=self.theme["panel"],
            content=name_field,
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.TextButton("Save", on_click=save_name),
            ],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

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


def main(page: ft.Page):
    DailyPlanner(page)


if __name__ == "__main__":
    ft.run(main)
