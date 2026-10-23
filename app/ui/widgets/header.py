from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

ICON_PATH = Path(__file__).resolve().parents[2] / "assets/images/icon.svg"


class Header(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TopBar")
        self.setFixedHeight(60)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(QIcon(str(ICON_PATH)).pixmap(30, 30))
        logo.setFixedSize(30, 30)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        name = QLabel("SignScene")
        name.setObjectName("Brand")

        layout.addWidget(logo)
        layout.addWidget(name)
        layout.addStretch(1)
