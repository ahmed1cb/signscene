import os
import sys

from core import api_client, session
from PySide6.QtWidgets import QApplication
from ui import styles
from ui.main_window import MainWindow

_devnull = os.open(os.devnull, os.O_WRONLY)
os.dup2(_devnull, 2)


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(styles.APP_STYLESHEET)
    app.setApplicationName("SignScene")

    window = MainWindow()
    window.show()

    saved = session.load()
    if saved and saved.get("token"):
        try:
            user = api_client.me(saved["token"])
            window._enter_home(user)
        except Exception:
            session.clear()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
