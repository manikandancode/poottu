# src/poottu/utils/backup.py

import json
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple

from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QWidget, QLineEdit, QApplication

from poottu.utils.paths import get_header_path, get_db_path
from poottu.core.vault import Vault
from poottu.core.database import Database
from nacl.bindings import (
    crypto_aead_xchacha20poly1305_ietf_encrypt,
    crypto_aead_xchacha20poly1305_ietf_decrypt,
)
import os as _os
import base64
from argon2 import low_level as argon2
import re


@dataclass
class BackupMeta:
    version: str = "1.0"
    aead: str = "xchacha20poly1305-ietf"
    kdf: str = "argon2id"


def _argon2_derive_key(password: str, salt: bytes, params: dict) -> bytes:
    return argon2.hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=params.get("time_cost", 4),
        memory_cost=params.get("memory_cost", 65536),
        parallelism=params.get("parallelism", 1),
        hash_len=params.get("hash_len", 32),
        type=argon2.Type.ID,
    )


def _pack_payload(files: dict) -> bytes:
    manifest = {name: base64.b64encode(data).decode("utf-8") for name, data in files.items()}
    return json.dumps({"manifest": manifest}, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _unpack_payload(data: bytes) -> dict:
    obj = json.loads(data.decode("utf-8"))
    manifest = obj.get("manifest", {})
    return {name: base64.b64decode(b64) for name, b64 in manifest.items()}


def _validate_backup_passphrase(p1: str, p2: str) -> Tuple[bool, str]:
    if not p1 or not p2:
        return False, "Backup passphrase cannot be empty."
    if p1 != p2:
        return False, "Backup passphrases do not match."
    if len(p1) < 12:
        return False, "Backup passphrase must be at least 12 characters."
    has_lower = re.search(r"[a-z]", p1) is not None
    has_upper = re.search(r"[A-Z]", p1) is not None
    has_digit = re.search(r"\d", p1) is not None
    has_special = re.search(r"[^A-Za-z0-9]", p1) is not None
    if not (has_lower and has_upper and has_digit and has_special):
        return False, "Backup passphrase must include lowercase, uppercase, number, and special character."
    return True, ""


def export_encrypted_backup(parent: QWidget):
    path, _ = QFileDialog.getSaveFileName(parent, "Export Encrypted Backup", "poottu-backup.pbak", "Poottu Backup (*.pbak)")
    if not path:
        return

    rules = "Minimum 12 characters with at least one lowercase, uppercase, number, and special character."
    pwd, ok = QInputDialog.getText(
        parent,
        "Backup Passphrase",
        f"Enter a backup passphrase:\n\n{rules}",
        echo=QLineEdit.Normal
    )
    if not ok:
        return
    pwd2, ok = QInputDialog.getText(
        parent,
        "Confirm Passphrase",
        f"Re-enter backup passphrase:\n\n{rules}",
        echo=QLineEdit.Normal
    )
    if not ok:
        return

    ok_valid, msg = _validate_backup_passphrase(pwd, pwd2)
    if not ok_valid:
        QMessageBox.warning(parent, "Backup", msg)
        return

    header_path = get_header_path()
    db_path = get_db_path()
    if not header_path.exists() or not db_path.exists():
        QMessageBox.warning(parent, "Backup", "Vault header or database not found.")
        return

    files = {
        "vault.header": header_path.read_bytes(),
        "poottu.db": db_path.read_bytes(),
    }
    plaintext = _pack_payload(files)

    salt = _os.urandom(16)
    kdf_params = Vault.DEFAULT_PARAMS
    key = _argon2_derive_key(pwd, salt, kdf_params)

    nonce = _os.urandom(24)
    ciphertext = crypto_aead_xchacha20poly1305_ietf_encrypt(plaintext, aad=None, nonce=nonce, key=key)

    meta = BackupMeta()
    envelope = {
        "meta": {
            "version": meta.version,
            "aead": meta.aead,
            "kdf": meta.kdf,
            "params": kdf_params,
            "salt": base64.b64encode(salt).decode("utf-8"),
            "nonce": base64.b64encode(nonce).decode("utf-8"),
        },
        "data": base64.b64encode(ciphertext).decode("utf-8"),
    }

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(envelope, f, separators=(",", ":"), sort_keys=True)
        QMessageBox.information(
            parent,
            "Backup",
            "Encrypted backup exported successfully.\n\nYou need the backup passphrase and your current master password to restore and unlock."
        )
    except Exception as e:
        QMessageBox.critical(parent, "Backup", f"Failed to write backup: {e}")


def import_encrypted_backup(parent: QWidget, db_obj: Optional[Database] = None):
    path, _ = QFileDialog.getOpenFileName(parent, "Import Encrypted Backup", "", "Poottu Backup (*.pbak)")
    if not path:
        return

    pwd, ok = QInputDialog.getText(parent, "Backup Passphrase", "Enter the backup passphrase:", echo=QLineEdit.Normal)
    if not ok:
        return
    if not pwd or not pwd.strip():
        QMessageBox.warning(parent, "Restore", "Backup passphrase cannot be empty.")
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            envelope = json.load(f)
        meta = envelope.get("meta", {})
        if meta.get("aead") != "xchacha20poly1305-ietf" or meta.get("kdf") != "argon2id":
            QMessageBox.critical(parent, "Restore", "Unsupported backup format.")
            return

        salt = base64.b64decode(meta["salt"])
        nonce = base64.b64decode(meta["nonce"])
        kdf_params = meta.get("params", Vault.DEFAULT_PARAMS)
        ciphertext = base64.b64decode(envelope.get("data"))

        key = _argon2_derive_key(pwd, salt, kdf_params)
        plaintext = crypto_aead_xchacha20poly1305_ietf_decrypt(ciphertext, aad=None, nonce=nonce, key=key)
        files = _unpack_payload(plaintext)

        if "vault.header" not in files or "poottu.db" not in files:
            QMessageBox.critical(parent, "Restore", "Backup is missing required files.")
            return

        header_path = get_header_path()
        db_path = get_db_path()
        app_dir = header_path.parent
        app_dir.mkdir(parents=True, exist_ok=True)

        tmp_header = app_dir / "vault.header.tmp"
        tmp_db = app_dir / "poottu.db.tmp"

        tmp_header.write_bytes(files["vault.header"])
        tmp_db.write_bytes(files["poottu.db"])

        _fsync_file(tmp_header)
        _fsync_file(tmp_db)

        if db_obj is not None and hasattr(db_obj, "close"):
            try:
                db_obj.close()
            except Exception:
                pass

        try:
            if db_path.exists():
                db_path.unlink()
        except Exception:
            pass
        try:
            if header_path.exists():
                header_path.unlink()
        except Exception:
            pass

        tmp_header.rename(header_path)
        tmp_db.rename(db_path)

        msg = QMessageBox(parent)
        msg.setWindowTitle("Restore")
        msg.setIcon(QMessageBox.Information)
        msg.setText("Backup restored successfully.\n\nPlease close the app and reopen, then unlock with the backup device's master password.")
        msg.addButton("Close App", QMessageBox.AcceptRole)
        msg.exec()

        QApplication.quit()
    except Exception as e:
        QMessageBox.critical(parent, "Restore", f"Import failed: {e}")


def _fsync_file(path: Path):
    try:
        with open(path, "rb") as f:
            os.fsync(f.fileno())
    except Exception:
        pass
