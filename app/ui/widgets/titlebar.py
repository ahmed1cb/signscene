from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QIcon, QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

ICON_PATH = Path(__file__).resolve().parents[2] / "assets/images/icon.svg"


class _WindowButton(QPushButton):
    def __init__(
        self,
        text: str,
        tooltip: str,
        object_name: str = "WindowButton",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName(object_name)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(36, 28)


class TitleBar(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(46)
        self.setMouseTracking(True)
        self._press_pos: QPoint | None = None
        self._dragging = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 8, 0)
        layout.setSpacing(9)

        logo = QLabel()
        logo.setPixmap(QIcon(str(ICON_PATH)).pixmap(22, 22))
        logo.setFixedSize(22, 22)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        name = QLabel("Communication without Barriers")
        name.setObjectName("Brand")
        name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.minimize_button = _WindowButton("−", "Minimize")
        self.maximize_button = _WindowButton("□", "Maximize")
        self.close_button = _WindowButton("×", "Close", "WindowCloseButton")

        self.minimize_button.clicked.connect(lambda: self.window().showMinimized())
        self.maximize_button.clicked.connect(self._toggle_maximize)
        self.close_button.clicked.connect(lambda: self.window().close())

        layout.addWidget(logo)
        layout.addWidget(name)
        layout.addStretch(1)
        layout.addWidget(self.minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(self.close_button)

    def _toggle_maximize(self) -> None:
        window = self.window()
        if window.isMaximized():
            window.showNormal()
        else:
            window.showMaximized()
        self.sync_maximize()

    def sync_maximize(self) -> None:
        maximized = self.window().isMaximized()
        self.maximize_button.setText("▣" if maximized else "□")
        self.maximize_button.setToolTip("Restore" if maximized else "Maximize")

    def _start_drag(self) -> bool:
        handle = self.window().windowHandle()
        return handle is not None and handle.startSystemMove()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._dragging = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._press_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            current = event.globalPosition().toPoint()
            if not self._dragging:
                if (current - self._press_pos).manhattanLength() < 4:
                    return
                self._dragging = True
                if self._start_drag():
                    self._press_pos = None
                    event.accept()
                    return

            if self._press_pos is not None:
                window = self.window()
                delta = current - self._press_pos
                if not window.isMaximized():
                    window.move(window.pos() + delta)
                self._press_pos = current
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._press_pos = None
        self._dragging = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = None
            self._dragging = False
            self._toggle_maximize()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
