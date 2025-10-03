import sys
import os
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtGui import QIcon
from poottu.gui.create_window import CreateWindow
from poottu.gui.unlock_window import UnlockWindow
from poottu.gui.main_window import MainWindow
from poottu.utils.paths import get_header_path
from poottu.core.database import Database

if sys.platform == 'win32':
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('poottu.app.1.0')

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Poottu")
    
    base_dir = os.path.dirname(__file__)
    icon_png = os.path.join(base_dir, 'resources', 'icon.png')
    icon_ico = os.path.join(base_dir, 'resources', 'icon.ico')

    
    if sys.platform == 'win32' and os.path.exists(icon_ico):
        app.setWindowIcon(QIcon(icon_ico))
    elif os.path.exists(icon_png):
        app.setWindowIcon(QIcon(icon_png))

    header_path = get_header_path()
    if not header_path.exists():
        create_win = CreateWindow()
        if create_win.exec() != QDialog.Accepted:
            sys.exit(0)
        key = create_win.master_key
    else:
        unlock_win = UnlockWindow()
        if unlock_win.exec() != QDialog.Accepted:
            sys.exit(0)
        key = unlock_win.master_key

    db_path = get_header_path().parent / "poottu.db"
    db = Database(db_path, key)
    main_win = MainWindow(db)
    main_win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
