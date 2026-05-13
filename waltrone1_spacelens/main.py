from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from .app.main_window import MainWindow
from .app.theme import LIGHT_THEME


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("waltrone1-SpaceLens")
    app.setStyleSheet(LIGHT_THEME)
    window = MainWindow()
    window.show()
    return app.exec()
