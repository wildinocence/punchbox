import os
import sys

from PySide6.QtWidgets import QApplication

from punchbox_gui.main_window import MainWindow


def _default_config_path():
    # A frozen (PyInstaller) exe isn't necessarily launched with the repo as
    # cwd (double-clicking it from the Start Menu/Desktop won't be) - locate
    # the bundled punchbox.yaml relative to the bundle itself instead. In a
    # normal (non-frozen) dev run, this keeps the existing cwd-relative
    # behavior (run from the repo root).
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.getcwd()
    return os.path.join(base, "punchbox.yaml")


def main():
    app = QApplication(sys.argv)
    window = MainWindow(_default_config_path())
    window.resize(1100, 700)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
