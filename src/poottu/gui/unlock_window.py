# src/poottu/gui/unlock_window.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from poottu.core.vault import Vault
from poottu.utils.paths import get_header_path


class UnlockWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unlock Poottu")
        self.setModal(True)
        self.setMinimumWidth(440)
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
        title = QLabel("Welcome back")
        tfont = QFont()
        tfont.setPointSize(16)
        tfont.setWeight(QFont.Weight.DemiBold)
        title.setFont(tfont)
        title.setAlignment(Qt.AlignHCenter)

        subtitle = QLabel("Enter the master password to unlock your vault")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignHCenter)

        # Password label + field with show/hide
        pwd_label = QLabel("Master password")
        self.pass_field = QLineEdit()
        self.pass_field.setEchoMode(QLineEdit.Password)
        self.pass_field.setPlaceholderText("Enter master password")
        self.pass_field.returnPressed.connect(self.accept)

        self.show_chk = QCheckBox("Show")
        self.show_chk.toggled.connect(
            lambda checked: self.pass_field.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        )

        pwd_row = QHBoxLayout()
        pwd_row.setSpacing(8)
        pwd_row.addWidget(self.pass_field)
        pwd_row.addWidget(self.show_chk)

        # Error label
        self.error = QLabel("")
        self.error.setObjectName("error")
        self.error.setWordWrap(True)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_unlock = QPushButton("Unlock")
        btn_unlock.setObjectName("primary")
        btn_unlock.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_unlock)

        # Assemble card
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(8)
        card_layout.addWidget(pwd_label)
        card_layout.addLayout(pwd_row)
        card_layout.addWidget(self.error)
        card_layout.addLayout(btn_row)

        # Center the card
        root.addStretch(1)
        root.addWidget(card, 0, Qt.AlignHCenter)
        root.addStretch(1)

        # Apply stylesheet
        self.setStyleSheet(self._modern_style())

    def accept(self):
        p = self.pass_field.text()
        if not p:
            self.error.setText("Please enter password")
            return
        try:
            self.master_key = Vault.load(p, get_header_path())
            self.error.setText("")
            super().accept()
        except ValueError:
            self.error.setText("Invalid master password")
            self.pass_field.clear()
            self.pass_field.setFocus()
        except Exception as e:
            self.error.setText(f"Error: {e}")

    def _modern_style(self) -> str:
        # Force subtitle to a visible neutral color for both themes.
        # Using explicit hex avoids palette(mid) pitfalls on some styles.
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
            /* Larger and clearly visible in both themes */
            font-size: 13px;
            margin-top: 2px;
            margin-bottom: 6px;
            /* Use a neutral gray that contrasts on light, while still readable on dark */
            color: #6B6F76;
        }
        /* If running under a very dark palette, boost contrast slightly via a shadow-like outline */
        #subtitle:disabled { color: #6B6F76; }  /* no-op, ensures style block is valid everywhere */

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
