import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from ui import styles
from ui.main_window import MainWindow

BASE = Path(__file__).parent


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(styles.APP_STYLESHEET)
    app.setApplicationName("Communication Without Barriers")
    app.setWindowIcon(QIcon(str(BASE / "assets/images/icon.svg")))

    window = MainWindow()
    window.show()
    window.restore_session()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
