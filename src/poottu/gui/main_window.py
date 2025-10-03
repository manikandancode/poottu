# src/poottu/gui/main_window.py

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                               QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem,
                               QLabel, QLineEdit, QPushButton, QTextEdit, QMenuBar, QMessageBox,
                               QApplication, QDialog, QMenu, QSpacerItem, QSizePolicy, QInputDialog)
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QAction, QClipboard
from poottu.gui.dialogs import GroupDialog, EntryDialog
from poottu.core.database import Database
from poottu.utils.backup import export_encrypted_backup, import_encrypted_backup

APP_VERSION = "1.0.0"
PROJECT_URL = "https://due.im/poottu/"

class MainWindow(QMainWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("Poottu Password Manager")
        self.resize(900, 600)

        self.clipboard_clear_secs = 30
        self.clipboard_timer = QTimer(self)
        self.clipboard_timer.setSingleShot(True)
        self.clipboard_timer.timeout.connect(self.clear_clipboard_safely)

        
        self.clipboard_hud = QLabel("", self)
        self.clipboard_hud.setObjectName("clipboardHud")
        self.clipboard_hud.setAlignment(Qt.AlignCenter)
        self.clipboard_hud.setVisible(False)
        self.clipboard_hud_timer = QTimer(self)
        self.clipboard_hud_timer.setSingleShot(True)
        self.clipboard_hud_timer.timeout.connect(lambda: self.clipboard_hud.setVisible(False))
        self._install_hud_styles()

        self.current_entries = []

        
        self.create_menu_bar()

        
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(8, 4, 8, 4)
        top_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search…")
        self.search_edit.textChanged.connect(self.apply_search_filter)
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setFixedWidth(260)
        top_layout.addWidget(QLabel("Search:"))
        top_layout.addWidget(self.search_edit)

        central_container = QWidget()
        central_v = QVBoxLayout(central_container)
        central_v.setContentsMargins(0, 0, 0, 0)
        central_v.addWidget(top_widget)

        central_splitter = QSplitter(Qt.Horizontal)
        central_splitter.setChildrenCollapsible(False)
        central_v.addWidget(central_splitter)

        # Groups
        self.groups_tree = QTreeWidget()
        self.groups_tree.setHeaderLabel("Groups")
        central_splitter.addWidget(self.groups_tree)

        # Right side splitter
        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.setChildrenCollapsible(False)

        # Entry list
        self.entry_table = QTableWidget()
        self.entry_table.setColumnCount(7)
        self.entry_table.setHorizontalHeaderLabels(["Title", "Username", "Password", "Old Password", "URL", "Notes", "Expires"])
        self.entry_table.horizontalHeader().setStretchLastSection(True)
        self.entry_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.entry_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.entry_table.customContextMenuRequested.connect(self.show_entry_context_menu)
        right_splitter.addWidget(self.entry_table)

        # Preview
        self.preview_widget = QWidget()
        preview_layout = QVBoxLayout(self.preview_widget)
        self.preview_title = QLabel("Title: N/A")
        self.preview_username = QLabel("Username: N/A")
        self.preview_password = QLineEdit()
        self.preview_password.setEchoMode(QLineEdit.Password)
        self.preview_password.setReadOnly(True)
        self.show_password_btn = QPushButton("Show Password")
        self.preview_url = QLabel("URL: N/A")
        self.preview_expires = QLabel("Expires: N/A")
        self.preview_notes = QTextEdit()
        self.preview_notes.setReadOnly(True)
        self.preview_created = QLabel("Created: N/A")
        self.preview_modified = QLabel("Modified: N/A")

        preview_layout.addWidget(self.preview_title)
        preview_layout.addWidget(self.preview_username)
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Password:"))
        password_layout.addWidget(self.preview_password)
        password_layout.addWidget(self.show_password_btn)
        preview_layout.addLayout(password_layout)
        preview_layout.addWidget(self.preview_url)
        preview_layout.addWidget(self.preview_expires)
        preview_layout.addWidget(QLabel("Notes:"))
        preview_layout.addWidget(self.preview_notes)
        preview_layout.addWidget(self.preview_created)
        preview_layout.addWidget(self.preview_modified)

        right_splitter.addWidget(self.preview_widget)

        central_splitter.addWidget(self.groups_tree)
        central_splitter.addWidget(right_splitter)
        self.setCentralWidget(central_container)

        central_splitter.setSizes([150, 750])
        right_splitter.setSizes([400, 200])

        # Signals
        self.groups_tree.currentItemChanged.connect(self.group_changed)
        self.entry_table.itemSelectionChanged.connect(self.entry_selected)
        self.show_password_btn.clicked.connect(self.toggle_password_visibility)

        # Keyboard shortcuts (window-level)
        edit_shortcut = QAction(self)
        edit_shortcut.setShortcut("F2")
        edit_shortcut.triggered.connect(self._edit_current_row)
        self.addAction(edit_shortcut)

        delete_shortcut = QAction(self)
        delete_shortcut.setShortcut("Delete")
        delete_shortcut.triggered.connect(self._delete_current_row)
        self.addAction(delete_shortcut)

        self.load_groups()
        general_item = None
        for i in range(self.groups_tree.topLevelItemCount()):
            it = self.groups_tree.topLevelItem(i)
            if it.text(0) == "General":
                general_item = it
                break
        if general_item is not None:
            self.groups_tree.setCurrentItem(general_item)
        else:
            if self.groups_tree.topLevelItemCount() > 0:
                self.groups_tree.setCurrentItem(self.groups_tree.topLevelItem(0))

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        add_entry_action = QAction("Add Entry", self)
        add_entry_action.setShortcut("Ctrl+N")
        add_entry_action.triggered.connect(self.add_entry)
        file_menu.addAction(add_entry_action)

        manage_groups_action = QAction("Edit Groups", self)
        manage_groups_action.setShortcut("Ctrl+G")
        manage_groups_action.triggered.connect(self.manage_groups)
        file_menu.addAction(manage_groups_action)

        backup_action = QAction("Backup", self)
        backup_action.setShortcut("Ctrl+B")
        backup_action.triggered.connect(lambda: export_encrypted_backup(self))
        file_menu.addAction(backup_action)

        restore_action = QAction("Restore", self)
        restore_action.setShortcut("Ctrl+R")
        restore_action.triggered.connect(lambda: import_encrypted_backup(self, self.db))
        file_menu.addAction(restore_action)

        clipboard_menu = file_menu.addMenu("Clipboard")
        cfg_clip_action = QAction("Configure Clear Timer…", self)
        cfg_clip_action.triggered.connect(self.configure_clipboard_timer)
        clipboard_menu.addAction(cfg_clip_action)

        file_menu.addSeparator()
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        file_menu.addAction(about_action)

        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def show_about_dialog(self):
        text = (
            "<b>Poottu Password Manager</b><br>"
            f"Version: {APP_VERSION}<br>"
            "Author: Manikandan D<br>"
            f'Project: <a href="{PROJECT_URL}">{PROJECT_URL}</a><br><br>'
            "<b>License</b>: MIT License<br><br>"
            "Copyright (c) 2025 Manikandan D<br><br>"
            "Permission is hereby granted, free of charge, to any person obtaining a copy "
            'of this software and associated documentation files (the "Software"), to deal '
            "in the Software without restriction, including without limitation the rights "
            "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell "
            "copies of the Software, and to permit persons to whom the Software is "
            "furnished to do so, subject to the following conditions:<br><br>"
            "The above copyright notice and this permission notice shall be included in all "
            "copies or substantial portions of the Software.<br><br>"
            "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR "
            "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, "
            "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE "
            "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER "
            "LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, "
            "OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE "
            "SOFTWARE."
        )
        box = QMessageBox(self)
        box.setWindowTitle("About")
        box.setTextFormat(Qt.RichText)
        box.setTextInteractionFlags(Qt.TextBrowserInteraction)
        box.setStandardButtons(QMessageBox.Ok)
        box.setText(text)
        box.exec()

    # ---------- Clipboard ----------
    def configure_clipboard_timer(self):
        secs, ok = QInputDialog.getInt(self, "Clipboard Clear Timer",
                                       "Seconds before clipboard is cleared (0 disables):",
                                       value=self.clipboard_clear_secs,
                                       minValue=0, maxValue=3600, step=1)
        if ok:
            self.clipboard_clear_secs = int(secs)
            if self.clipboard_timer.isActive():
                self.clipboard_timer.stop()

    def clear_clipboard_safely(self):
        QApplication.clipboard().clear(QClipboard.Mode.Clipboard)

    def _install_hud_styles(self):
        self.clipboard_hud.setStyleSheet("""
            #clipboardHud {
                background: rgba(30, 30, 30, 180);
                color: white;
                padding: 8px 12px;
                border-radius: 10px;
                font-size: 12px;
                border: 1px solid rgba(0,0,0,120);
            }
        """)

    def _show_clipboard_hud(self, seconds: int):
        msg = f"Copied. Will clear in {seconds}s" if seconds > 0 else "Copied."
        self.clipboard_hud.setText(msg)
        self.clipboard_hud.adjustSize()
        margin = 18
        w = self.clipboard_hud.width()
        h = self.clipboard_hud.height()
        area_w = self.width()
        area_h = self.height()
        self.clipboard_hud.move((area_w - w) // 2, area_h - h - margin)
        self.clipboard_hud.setVisible(True)
        self.clipboard_hud_timer.start(2500)

    # ---------- Groups ----------
    def manage_groups(self):
        current_groups_dicts = self.db.get_groups()
        current_groups = [g['name'] for g in current_groups_dicts]
        dlg = GroupDialog(current_groups)
        if dlg.exec() == QDialog.Accepted:
            new_groups = dlg.edited_groups

            for group in set(new_groups) - set(current_groups):
                self.db.add_group(group)

            for old, new in zip(current_groups, new_groups):
                if old != new:
                    self.db.edit_group(old, new)

            for group in set(current_groups) - set(new_groups):
                self.db.delete_group(group)

            self.load_groups()

    def add_entry(self):
        groups = [g['name'] for g in self.db.get_groups()]
        dlg = EntryDialog(groups)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            if data["title"] and data["password"]:
                self.db.add_entry(**data)
                target = data["group"]
                for i in range(self.groups_tree.topLevelItemCount()):
                    it = self.groups_tree.topLevelItem(i)
                    if it.text(0) == target:
                        self.groups_tree.setCurrentItem(it)
                        break
                self.load_entries(target)
                self.apply_search_filter()

    def load_groups(self):
        self.groups_tree.clear()
        groups = self.db.get_groups()
        for group in groups:
            item = QTreeWidgetItem([group['name']])
            item.setData(0, Qt.UserRole, group['id'])
            self.groups_tree.addTopLevelItem(item)

    def current_group_name(self):
        item = self.groups_tree.currentItem()
        return item.text(0) if item else "General"

    def load_entries(self, group_name):
        self.current_entries = self.db.get_entries_by_group(group_name)
        self.apply_search_filter()

    def populate_table(self, entries):
        self.entry_table.clearContents()
        self.entry_table.setRowCount(len(entries))
        for i, entry in enumerate(entries):
            title_item = QTableWidgetItem(entry["title"])
            title_item.setData(Qt.UserRole, entry["id"])
            self.entry_table.setItem(i, 0, title_item)
            self.entry_table.setItem(i, 1, QTableWidgetItem(entry["username"]))
            self.entry_table.setItem(i, 2, QTableWidgetItem("*****"))
            self.entry_table.setItem(i, 3, QTableWidgetItem("*****"))
            self.entry_table.setItem(i, 4, QTableWidgetItem(entry.get("url", "")))
            note_preview = entry["notes"][:50] + "..." if len(entry["notes"]) > 50 else entry["notes"]
            self.entry_table.setItem(i, 5, QTableWidgetItem(note_preview))
            expires_str = str(entry.get("expires", "")) if entry.get("expires") else ""
            self.entry_table.setItem(i, 6, QTableWidgetItem(expires_str))
        self.entry_table.resizeColumnsToContents()

    def apply_search_filter(self):
        text = (self.search_edit.text() or "").strip().lower()
        if not text:
            filtered = self.current_entries
        else:
            def match(entry):
                return any((
                    text in (entry.get("title", "") or "").lower(),
                    text in (entry.get("username", "") or "").lower(),
                    text in (entry.get("url", "") or "").lower(),
                    text in (entry.get("notes", "") or "").lower(),
                ))
            filtered = [e for e in self.current_entries if match(e)]
        self.populate_table(filtered)

    def group_changed(self, current, previous):
        if current:
            group_name = current.text(0)
            self.load_entries(group_name)
            self.clear_preview()

    def entry_selected(self):
        selected = self.entry_table.selectedItems()
        if selected:
            row = selected[0].row()
            entry_id = self.entry_table.item(row, 0).data(Qt.UserRole)
            entry = self.db.get_entry(entry_id)
            if entry:
                self.preview_title.setText(f"Title: {entry.get('title', 'N/A')}")
                self.preview_username.setText(f"Username: {entry.get('username', 'N/A')}")
                self.preview_password.setText(entry.get('password', ''))
                self.preview_url.setText(f"URL: {entry.get('url', 'N/A')}")
                self.preview_expires.setText(f"Expires: {entry.get('expires', 'N/A')}")
                self.preview_notes.setPlainText(entry.get('notes', ''))
                self.preview_created.setText(f"Created: {entry.get('created', 'N/A')}")
                self.preview_modified.setText(f"Modified: {entry.get('modified', 'N/A')}")
            else:
                self.clear_preview()
        else:
            self.clear_preview()

    def clear_preview(self):
        self.preview_title.setText("Title: N/A")
        self.preview_username.setText("Username: N/A")
        self.preview_password.clear()
        self.preview_url.setText("URL: N/A")
        self.preview_expires.setText("Expires: N/A")
        self.preview_notes.clear()
        self.preview_created.setText("Created: N/A")
        self.preview_modified.setText("Modified: N/A")

    def toggle_password_visibility(self):
        if self.preview_password.echoMode() == QLineEdit.Password:
            self.preview_password.setEchoMode(QLineEdit.Normal)
            self.show_password_btn.setText("Hide Password")
        else:
            self.preview_password.setEchoMode(QLineEdit.Password)
            self.show_password_btn.setText("Show Password")

    # -------- Context menu for entries --------
    def show_entry_context_menu(self, pos: QPoint):
        row = self.entry_table.rowAt(pos.y())
        if row < 0:
            return
        entry_id = self.entry_table.item(row, 0).data(Qt.UserRole)
        menu = QMenu(self)

        act_edit = menu.addAction("Edit Entry")
        act_delete = menu.addAction("Delete Entry")
        menu.addSeparator()
        act_copy_user = menu.addAction("Copy Username")
        act_copy_pass = menu.addAction("Copy Password")
        act_copy_url = menu.addAction("Copy URL")
        act_copy_old = menu.addAction("Copy Old Password")
        act_copy_notes = menu.addAction("Copy Notes")

        action = menu.exec(self.entry_table.viewport().mapToGlobal(pos))
        if action == act_edit:
            self.edit_selected_entry(entry_id)
        elif action == act_delete:
            self.delete_selected_entry(entry_id)
        elif action == act_copy_user:
            self.copy_field(entry_id, "username")
        elif action == act_copy_pass:
            self.copy_field(entry_id, "password")
        elif action == act_copy_url:
            self.copy_field(entry_id, "url")
        elif action == act_copy_old:
            self.copy_field(entry_id, "old_password")
        elif action == act_copy_notes:
            self.copy_field(entry_id, "notes")

    # -------- Shortcut helpers--------
    def _current_selected_entry_id(self):
        selected = self.entry_table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        item = self.entry_table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _edit_current_row(self):
        entry_id = self._current_selected_entry_id()
        if entry_id is not None:
            self.edit_selected_entry(entry_id)

    def _delete_current_row(self):
        entry_id = self._current_selected_entry_id()
        if entry_id is not None:
            self.delete_selected_entry(entry_id)

    def copy_field(self, entry_id: int, field: str):
        entry = self.db.get_entry(entry_id)
        if not entry:
            QMessageBox.warning(self, "Copy", "Entry not found.")
            return
        value = entry.get(field, "") or ""
        QApplication.clipboard().setText(value)
        secs = getattr(self, "clipboard_clear_secs", 0) or 0
        if secs > 0:
            if self.clipboard_timer.isActive():
                self.clipboard_timer.stop()
            self.clipboard_timer.start(secs * 1000)
        self._show_clipboard_hud(secs)

    def edit_selected_entry(self, entry_id: int):
        entry = self.db.get_entry(entry_id)
        if not entry:
            QMessageBox.warning(self, "Edit Entry", "Entry not found.")
            return

        groups = [g['name'] for g in self.db.get_groups()]
        entry_data = {
            "group": self.current_group_name(),
            "title": entry.get("title", ""),
            "username": entry.get("username", ""),
            "password": entry.get("password", ""),
            "old_password": entry.get("old_password", ""),
            "url": entry.get("url", ""),
            "notes": entry.get("notes", ""),
            "expires": entry.get("expires", None),
        }

        dlg = EntryDialog(groups, entry=entry_data)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            self.db.update_entry(entry_id, **data)
            self.load_entries(data["group"])
            self.apply_search_filter()

    def delete_selected_entry(self, entry_id: int):
        reply = QMessageBox.question(
            self, "Delete Entry",
            "Are you sure you want to delete this entry?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_entry(entry_id)
            self.load_entries(self.current_group_name())
            self.apply_search_filter()
            self.clear_preview()
