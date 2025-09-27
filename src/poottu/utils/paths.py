# src/poottu/utils/paths.py
import platformdirs
from pathlib import Path

APP_NAME = "Poottu"

def get_app_dir():
    return Path(platformdirs.user_data_dir(APP_NAME))

def get_header_path():
    return get_app_dir() / "vault.header"

def get_db_path():
    return get_app_dir() / "poottu.db"