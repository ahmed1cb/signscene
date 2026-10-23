import base64
import binascii
from pathlib import Path

from core.message import Message
from core.speaker import Speaker
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


class _SectionPanel(QFrame):
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
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
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

    def _show_content(self) -> None:
        self._empty.setVisible(False)
        self._scroll.setVisible(True)

    def _add_layout(self, layout: QHBoxLayout) -> None:
        self._list_layout.addLayout(layout)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def _add_widget(self, widget: QWidget) -> None:
        self._list_layout.addWidget(widget)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())


class MessagePanel(_SectionPanel):
    """Chat-style message list. Bubbles stack bottom-up; empty until add_message()"""

    def add_message(self, msg: Message) -> None:
        self._show_content()

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

        self._add_layout(row)


class ScenePreview(QLabel):
    MAX_HEIGHT = 220

    def __init__(self, pixmap: QPixmap, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ScenePreview")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.setMinimumHeight(80)
        self._source = pixmap
        self._last_width = 0
        self._rescale()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self.width() != self._last_width:
            self._rescale()

    def _rescale(self) -> None:
        width = max(1, self.width() - 10)
        self._last_width = self.width()
        scaled = self._source.scaledToWidth(
            width, Qt.TransformationMode.SmoothTransformation
        )
        if scaled.height() > self.MAX_HEIGHT:
            scaled = scaled.scaledToHeight(
                self.MAX_HEIGHT, Qt.TransformationMode.SmoothTransformation
            )
        self.setPixmap(scaled)
        self.setFixedHeight(scaled.height() + 10)


class ScenePanel(_SectionPanel):
    def add_scene(self, content, mine: bool = True) -> None:
        self._show_content()

        pixmap = _load_pixmap(content)
        if pixmap is None:
            label = QLabel("Scene image unavailable")
            label.setObjectName("Hint")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)
            self._add_widget(label)
            return

        preview = ScenePreview(pixmap)
        preview.setToolTip("Scene")
        self._add_widget(preview)


class MessagesArea(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scene_split = QSplitter(Qt.Orientation.Horizontal)
        self.scene_split.setObjectName("SceneSplitter")
        self.scene_split.setChildrenCollapsible(False)
        self.scene_split.setHandleWidth(8)

        self.scenes_mine = ScenePanel("My Scenes", "Your generated scenes appear here")
        self.scenes_peer = ScenePanel("Other Scenes", "Peer's scenes appear here")

        self.scene_split.addWidget(self.scenes_mine)
        self.scene_split.addWidget(self.scenes_peer)
        self.scene_split.setStretchFactor(0, 1)
        self.scene_split.setStretchFactor(1, 1)
        self.scene_split.setSizes([200, 200])

        self.main_split = QSplitter(Qt.Orientation.Vertical)
        self.main_split.setObjectName("MainMessagesSplitter")
        self.main_split.setChildrenCollapsible(False)
        self.main_split.setHandleWidth(8)

        self.messages = MessagePanel("Messages", "The Chat Messages")

        self.main_split.addWidget(self.scene_split)
        self.main_split.addWidget(self.messages)
        self.main_split.setStretchFactor(0, 2)
        self.main_split.setStretchFactor(1, 3)
        self.main_split.setSizes([300, 420])

        layout.addWidget(self.main_split)

    def add_message(self, msg: Message) -> None:
        if msg.type == "scene":
            if getattr(msg, "mine", True):
                self.scenes_mine.add_scene(msg.content, True)
            else:
                self.scenes_peer.add_scene(msg.content, False)
        else:
            self.messages.add_message(msg)


def _load_pixmap(content) -> QPixmap | None:
    if isinstance(content, QPixmap):
        return content if not content.isNull() else None
    if isinstance(content, QImage):
        return QPixmap.fromImage(content) if not content.isNull() else None
    if isinstance(content, (bytes, bytearray)):
        pixmap = QPixmap()
        if pixmap.loadFromData(bytes(content)):
            return pixmap
        return None
    if isinstance(content, (str, Path)):
        text = str(content)
        if text.startswith("data:image/"):
            _, _, data = text.partition(",")
            try:
                raw = base64.b64decode(data)
            except (ValueError, binascii.Error):
                return None
            return _load_pixmap(raw)
        pixmap = QPixmap(text)
        return pixmap if not pixmap.isNull() else None
    return None
