from core.message import Message
from core.speaker import Speaker
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class MessagePanel(QFrame):
    """Chat-style message list. Bubbles stack bottom-up; empty until add_message()."""

    def __init__(
        self, title: str, empty_text: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        header = QLabel(title)
        header.setObjectName("Subtitle")
        layout.addWidget(header)

        self._empty = QLabel(empty_text)
        self._empty.setObjectName("Hint")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setWordWrap(True)
        layout.addWidget(self._empty, stretch=1)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("MessageScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setVisible(False)

        self._list = QWidget()
        self._list.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch(1)

        self._scroll.setWidget(self._list)
        layout.addWidget(self._scroll, stretch=1)

    def add_message(self, msg: Message) -> None:
        self._empty.setVisible(False)
        self._scroll.setVisible(True)

        bubble = QPushButton(msg.content)
        bubble.setObjectName("BubbleMine" if msg.mine else "BubbleTheirs")
        bubble.clicked.connect(lambda x=0: Speaker.say(msg))
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if msg.mine:
            row.addStretch(1)
            row.addWidget(bubble, stretch=0)
        else:
            row.addWidget(bubble, stretch=0)
            row.addStretch(1)

        self._list_layout.addLayout(row)
        self._scroll.ensureWidgetVisible(self._list)
