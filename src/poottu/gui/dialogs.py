# src/poottu/gui/dialogs.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLineEdit, QTextEdit, QComboBox, QMessageBox, QInputDialog,
    QDateTimeEdit, QCheckBox, QSpinBox
)
from PySide6.QtCore import Qt, QDateTime
from datetime import datetime
import secrets
import string

class GroupDialog(QDialog):
    def __init__(self, groups):
        super().__init__()
        self.setWindowTitle("Manage Groups")
        self.setModal(True)
        self.groups = groups.copy()
        self.edited_groups = None

        layout = QVBoxLayout(self)

        self.group_list = QTreeWidget()
        self.group_list.setHeaderLabel("Groups")
        for group in self.groups:
            QTreeWidgetItem(self.group_list, [group])
        layout.addWidget(self.group_list)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add")
        edit_btn = QPushButton("Edit")
        delete_btn = QPushButton("Delete")
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        layout.addLayout(btn_layout)

        add_btn.clicked.connect(self.add_group)
        edit_btn.clicked.connect(self.edit_group)
        delete_btn.clicked.connect(self.delete_group)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

    def add_group(self):
        text, ok = QInputDialog.getText(self, "Add Group", "Group Name:")
        if ok and text and text not in self.groups:
            self.groups.append(text)
            QTreeWidgetItem(self.group_list, [text])

    def edit_group(self):
        item = self.group_list.currentItem()
        if not item:
            return
        old_name = item.text(0)
        text, ok = QInputDialog.getText(self, "Edit Group", "Group Name:", text=old_name)
        if ok and text and text != old_name:
            item.setText(0, text)
            idx = self.groups.index(old_name)
            self.groups[idx] = text

    def delete_group(self):
        item = self.group_list.currentItem()
        if not item:
            return
        name = item.text(0)
        reply = QMessageBox.question(
            self, "Delete Group",
            f"Are you sure you want to delete '{name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            idx = self.groups.index(name)
            self.groups.pop(idx)
            root = self.group_list.invisibleRootItem()
            root.removeChild(item)

    def accept(self):
        self.edited_groups = self.groups
        super().accept()


class PasswordGeneratorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Password Generator")
        self.setModal(True)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Password Length [1-20]:"))
        self.len_spin = QSpinBox()
        self.len_spin.setRange(1, 20)
        self.len_spin.setValue(12)
        layout.addWidget(self.len_spin)

        self.chk_upper = QCheckBox("Uppercase [A-Z]")
        self.chk_upper.setChecked(True)
        layout.addWidget(self.chk_upper)

        self.chk_lower = QCheckBox("Lowercase [a-z]")
        self.chk_lower.setChecked(True)
        layout.addWidget(self.chk_lower)

        self.chk_digit = QCheckBox("Number [0-9]")
        self.chk_digit.setChecked(True)
        layout.addWidget(self.chk_digit)

        self.chk_special = QCheckBox("Special Characters")
        self.chk_special.setChecked(True)
        layout.addWidget(self.chk_special)

        layout.addWidget(QLabel("Generated Password:"))
        self.out_edit = QLineEdit()
        self.out_edit.setReadOnly(False)
        layout.addWidget(self.out_edit)

        btn_row = QHBoxLayout()
        self.btn_generate = QPushButton("Generate")
        self.btn_ok = QPushButton("Use Password")
        self.btn_cancel = QPushButton("Cancel")
        btn_row.addWidget(self.btn_generate)
        btn_row.addWidget(self.btn_ok)
        btn_row.addWidget(self.btn_cancel)
        layout.addLayout(btn_row)

        self.btn_generate.clicked.connect(self.generate_password)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        self.generate_password()

    def generate_password(self):
        length = self.len_spin.value()
        pools = []
        if self.chk_upper.isChecked():
            pools.append(string.ascii_uppercase)
        if self.chk_lower.isChecked():
            pools.append(string.ascii_lowercase)
        if self.chk_digit.isChecked():
            pools.append(string.digits)
        if self.chk_special.isChecked():
            pools.append("!@#$%^&*()-_=+[]{};:,.?/\\|~")

        if not pools:
            pools = [string.ascii_lowercase]

        password_chars = []
        for pool in pools:
            if len(password_chars) < length:
                password_chars.append(secrets.choice(pool))

        all_chars = "".join(pools)
        for _ in range(length - len(password_chars)):
            password_chars.append(secrets.choice(all_chars))

        secrets.SystemRandom().shuffle(password_chars)
        self.out_edit.setText("".join(password_chars))

    def get_password(self):
        return self.out_edit.text()


class EntryDialog(QDialog):
    def __init__(self, groups, entry=None):
        super().__init__()
        self.setWindowTitle("Add / Edit Entry")

        layout = QVBoxLayout(self)

        self.group_combo = QComboBox()
        self.group_combo.addItems(groups)
        layout.addWidget(QLabel("Group:"))
        layout.addWidget(self.group_combo)

        self.title_edit = QLineEdit()
        layout.addWidget(QLabel("Title:"))
        layout.addWidget(self.title_edit)

        self.username_edit = QLineEdit()
        layout.addWidget(QLabel("Username:"))
        layout.addWidget(self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Normal)  # show while typing
        layout.addWidget(QLabel("Password:"))
        layout.addWidget(self.password_edit)

        gen_row = QHBoxLayout()
        self.btn_generate_pw = QPushButton("Generate…")
        gen_row.addStretch()
        gen_row.addWidget(self.btn_generate_pw)
        layout.addLayout(gen_row)
        self.btn_generate_pw.clicked.connect(self._open_generator)

        self.old_password_edit = QLineEdit()
        self.old_password_edit.setEchoMode(QLineEdit.Normal)  # show while typing
        layout.addWidget(QLabel("Old Password:"))
        layout.addWidget(self.old_password_edit)

        self.url_edit = QLineEdit()
        layout.addWidget(QLabel("URL:"))
        layout.addWidget(self.url_edit)

        self.notes_edit = QTextEdit()
        layout.addWidget(QLabel("Notes:"))
        layout.addWidget(self.notes_edit)

        self.expires_checkbox = QCheckBox("Enable Expiry")
        layout.addWidget(self.expires_checkbox)

        self.expires_edit = QDateTimeEdit()
        self.expires_edit.setCalendarPopup(True)
        self._make_blank()
        self.expires_edit.setEnabled(False)

        layout.addWidget(QLabel("Expires:"))
        layout.addWidget(self.expires_edit)

        self.expires_checkbox.toggled.connect(self._on_expires_toggled)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        # Hook Save through validation
        save_btn.clicked.connect(self._on_save)
        cancel_btn.clicked.connect(self.reject)

        self.setLayout(layout)

        if entry:
            self.group_combo.setCurrentText(entry.get("group", "General"))
            self.title_edit.setText(entry.get("title", ""))
            self.username_edit.setText(entry.get("username", ""))
            self.password_edit.setText(entry.get("password", ""))
            self.old_password_edit.setText(entry.get("old_password", ""))
            self.url_edit.setText(entry.get("url", ""))
            self.notes_edit.setPlainText(entry.get("notes", ""))

            dt = entry.get("expires", None)
            if dt:
                self.expires_checkbox.setChecked(True)
                if isinstance(dt, QDateTime):
                    self.expires_edit.setDateTime(dt)
                else:
                    if isinstance(dt, str):
                        try:
                            parsed = datetime.strptime(dt, "%d-%m-%Y")
                            self.expires_edit.setDateTime(QDateTime.fromSecsSinceEpoch(int(parsed.timestamp())))
                        except Exception:
                            try:
                                parsed = datetime.fromisoformat(dt)
                                self.expires_edit.setDateTime(QDateTime.fromSecsSinceEpoch(int(parsed.timestamp())))
                            except Exception:
                                pass
                    else:
                        self.expires_edit.setDateTime(QDateTime.fromSecsSinceEpoch(int(dt.timestamp())))
            else:
                self.expires_checkbox.setChecked(False)
                self._make_blank()
                self.expires_edit.setEnabled(False)

    def _open_generator(self):
        dlg = PasswordGeneratorDialog(self)
        if dlg.exec() == QDialog.Accepted:
            pw = dlg.get_password()
            if pw:
                self.password_edit.setText(pw)

    def _make_blank(self):
        self.expires_edit.setDisplayFormat("")
        self.expires_edit.clear()
        self.expires_edit.setDateTime(QDateTime())

    def _make_visible_format(self):
        self.expires_edit.setDisplayFormat("dd-MM-yyyy")

    def _on_expires_toggled(self, checked: bool):
        if checked:
            self.expires_edit.setEnabled(True)
            self._make_visible_format()
            self.expires_edit.setDateTime(QDateTime.currentDateTime())
        else:
            self.expires_edit.setEnabled(False)
            self._make_blank()

    def _validate(self):
        # Reset any prior error styles
        for w in (self.title_edit, self.username_edit, self.password_edit):
            w.setStyleSheet("")
        # Check mandatory fields
        group_ok = bool(self.group_combo.currentText().strip())
        title_ok = bool(self.title_edit.text().strip())
        user_ok = bool(self.username_edit.text().strip())
        pass_ok = bool(self.password_edit.text().strip())

        missing = []
        if not group_ok:
            missing.append("Group")
        if not title_ok:
            missing.append("Title")
            self.title_edit.setStyleSheet("border: 1px solid red;")
        if not user_ok:
            missing.append("Username")
            self.username_edit.setStyleSheet("border: 1px solid red;")
        if not pass_ok:
            missing.append("Password")
            self.password_edit.setStyleSheet("border: 1px solid red;")

        if missing:
            QMessageBox.warning(self, "Missing Fields", "Please fill: " + ", ".join(missing))
            return False
        return True

    def _on_save(self):
        if not self._validate():
            return
        self.accept()

    def get_data(self):
        if self.expires_checkbox.isChecked():
            py_dt = self.expires_edit.dateTime().toPython().replace(microsecond=0)
            expires_str = py_dt.date().strftime("%d-%m-%Y")
        else:
            expires_str = None
        return {
            "group": self.group_combo.currentText(),
            "title": self.title_edit.text().strip(),
            "username": self.username_edit.text().strip(),
            "password": self.password_edit.text().strip(),
            "old_password": self.old_password_edit.text().strip(),
            "url": self.url_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
            "expires": expires_str,
        }
