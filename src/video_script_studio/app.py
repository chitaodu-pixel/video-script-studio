from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from video_script_studio.ui.main_window import MainWindow


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("VideoScript Studio")
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())

