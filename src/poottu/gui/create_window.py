# src/poottu/gui/create_window.py

import re
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from poottu.core.vault import Vault
from poottu.utils.paths import get_header_path
import zxcvbn


class CreateWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Create Poottu Master Password")
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Card container
        card = QWidget()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)

        # Header
        title = QLabel("Create your vault")
        tfont = QFont()
        tfont.setPointSize(16)
        tfont.setWeight(QFont.Weight.DemiBold)
        title.setFont(tfont)
        title.setAlignment(Qt.AlignHCenter)

        subtitle = QLabel("Choose a strong master password to protect your data")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignHCenter)

        hint = QLabel("Hint: Minimum 12 characters with uppercase, lowercase, number, and special character.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)

        # Password 1
        p1_label = QLabel("Enter master password")
        self.pass1 = QLineEdit()
        self.pass1.setEchoMode(QLineEdit.Password)
        self.pass1.setPlaceholderText("Enter master password")
        self.show1 = QCheckBox("Show")
        self.show1.toggled.connect(lambda c: self.pass1.setEchoMode(QLineEdit.Normal if c else QLineEdit.Password))
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.addWidget(self.pass1)
        row1.addWidget(self.show1)

        # Password 2
        p2_label = QLabel("Confirm master password")
        self.pass2 = QLineEdit()
        self.pass2.setEchoMode(QLineEdit.Password)
        self.pass2.setPlaceholderText("Re-enter master password")
        self.pass2.returnPressed.connect(self.accept)
        self.show2 = QCheckBox("Show")
        self.show2.toggled.connect(lambda c: self.pass2.setEchoMode(QLineEdit.Normal if c else QLineEdit.Password))
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.addWidget(self.pass2)
        row2.addWidget(self.show2)

        # Error label
        self.error = QLabel("")
        self.error.setObjectName("error")
        self.error.setWordWrap(True)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_create = QPushButton("Create")
        btn_create.setObjectName("primary")
        btn_create.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_create)

        # Assemble
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(6)
        card_layout.addWidget(hint)
        card_layout.addSpacing(10)
        card_layout.addWidget(p1_label)
        card_layout.addLayout(row1)
        card_layout.addWidget(p2_label)
        card_layout.addLayout(row2)
        card_layout.addWidget(self.error)
        card_layout.addLayout(btn_row)

        root.addStretch(1)
        root.addWidget(card, 0, Qt.AlignHCenter)
        root.addStretch(1)

        self.setStyleSheet(self._modern_style())

    def validate_password(self, password):
        if len(password) < 12:
            return "Password must be at least 12 characters long"
        if not re.search(r"[a-z]", password):
            return "Password must contain at least one lowercase letter"
        if not re.search(r"[A-Z]", password):
            return "Password must contain at least one uppercase letter"
        if not re.search(r"\d", password):
            return "Password must contain at least one number"
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return "Password must contain at least one special character"
        strength = zxcvbn.zxcvbn(password)
        if strength["score"] < 4:
            return "Password is too weak. Try creating a stronger password."
        return None

    def accept(self):
        p1 = self.pass1.text()
        p2 = self.pass2.text()
        if not p1 or not p2:
            self.error.setText("Please enter passwords")
            return
        if p1 != p2:
            self.error.setText("Passwords do not match")
            return
        validation_error = self.validate_password(p1)
        if validation_error:
            self.error.setText(validation_error)
            return
        try:
            self.master_key = Vault.create(p1, get_header_path())
            self.error.setText("")
            super().accept()
        except Exception as e:
            self.error.setText(f"Error creating vault: {e}")

    def _modern_style(self) -> str:
        # Use explicit neutral colors for subtitle and hint to ensure readability in both themes
        return """
        QDialog {
            background: palette(window);
        }
        #card {
            background: palette(base);
            border: 1px solid rgba(0,0,0,20%);
            border-radius: 12px;
        }
        QLabel {
            color: palette(text);
        }
        #subtitle {
            font-size: 13px;
            margin-top: 2px;
            margin-bottom: 6px;
            color: #6B6F76; /* neutral gray visible on light and acceptable on dark */
        }
        #hint {
            font-size: 12px;
            color: #7A8088; /* slightly lighter for secondary text */
        }
        #error {
            color: rgb(200, 55, 55);
            font-size: 12px;
            min-height: 18px;
        }
        QLineEdit {
            padding: 10px 12px;
            border-radius: 8px;
            border: 1px solid rgba(0,0,0,28%);
            background: palette(base);
            selection-background-color: palette(highlight);
            selection-color: palette(highlighted-text);
        }
        QLineEdit:focus {
            border: 1px solid palette(highlight);
            outline: none;
        }
        QCheckBox {
            padding-left: 6px;
            color: palette(text);
        }
        QPushButton {
            padding: 8px 14px;
            border-radius: 8px;
            border: 1px solid rgba(0,0,0,20%);
            background: palette(button);
            color: palette(button-text);
        }
        QPushButton:hover {
            background: palette(light);
        }
        QPushButton:pressed {
            background: palette(midlight);
        }
        QPushButton#primary {
            background: palette(highlight);
            color: palette(highlighted-text);
            border: 1px solid palette(highlight);
        }
        """
