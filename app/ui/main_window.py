from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QCloseEvent, QResizeEvent
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from core import session
from ui.screens.home_screen import HomeScreen
from ui.screens.login_screen import LoginScreen
from ui.screens.register_screen import RegisterScreen
from ui.widgets.titlebar import TitleBar

RESIZE_MARGIN = 6


class _ResizeHandle(QWidget):
    def __init__(
        self, edges: Qt.Edge, cursor: Qt.CursorShape, parent: QWidget
    ) -> None:
        super().__init__(parent)
        self._edges = edges
        self.setObjectName("ResizeHandle")
        self.setCursor(cursor)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None and handle.startSystemResize(self._edges):
                event.accept()
                return
        super().mousePressEvent(event)


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.FramelessWindowHint
        )
        self.setWindowTitle("SignScene")
        self.setMinimumSize(1100, 720)

        screen = Qt.CursorShape
        edge = Qt.Edge

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.titlebar = TitleBar()
        root.addWidget(self.titlebar)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.login = LoginScreen(
            on_login_success=self._enter_home,
            on_go_register=self.show_register,
        )
        self.register = RegisterScreen(
            on_registered=self._go_to_login_after_register,
            on_go_login=self.show_login,
        )
        self.home = HomeScreen(on_sign_out=self.show_login)

        self.stack.addWidget(self.login)
        self.stack.addWidget(self.register)
        self.stack.addWidget(self.home)
        self.stack.setCurrentWidget(self.login)

        self._handles = [
            self._make_handle(edge.TopEdge, screen.SizeVerCursor),
            self._make_handle(edge.BottomEdge, screen.SizeVerCursor),
            self._make_handle(edge.LeftEdge, screen.SizeHorCursor),
            self._make_handle(edge.RightEdge, screen.SizeHorCursor),
            self._make_handle(
                edge.TopEdge | edge.LeftEdge, screen.SizeFDiagCursor
            ),
            self._make_handle(
                edge.TopEdge | edge.RightEdge, screen.SizeBDiagCursor
            ),
            self._make_handle(
                edge.BottomEdge | edge.LeftEdge, screen.SizeBDiagCursor
            ),
            self._make_handle(
                edge.BottomEdge | edge.RightEdge, screen.SizeFDiagCursor
            ),
        ]
        self._layout_handles()
        self._update_handle_visibility()

    def _make_handle(
        self, edges: Qt.Edge, cursor: Qt.CursorShape
    ) -> _ResizeHandle:
        handle = _ResizeHandle(edges, cursor, self)
        handle.raise_()
        return handle

    def _layout_handles(self) -> None:
        width, height = self.width(), self.height()
        margin = RESIZE_MARGIN
        inner_width = max(0, width - 2 * margin)
        inner_height = max(0, height - 2 * margin)

        self._handles[0].setGeometry(margin, 0, inner_width, margin)
        self._handles[1].setGeometry(
            margin, height - margin, inner_width, margin
        )
        self._handles[2].setGeometry(0, margin, margin, inner_height)
        self._handles[3].setGeometry(
            width - margin, margin, margin, inner_height
        )
        self._handles[4].setGeometry(0, 0, margin, margin)
        self._handles[5].setGeometry(width - margin, 0, margin, margin)
        self._handles[6].setGeometry(0, height - margin, margin, margin)
        self._handles[7].setGeometry(
            width - margin, height - margin, margin, margin
        )

    def _update_handle_visibility(self) -> None:
        visible = not (self.isMaximized() or self.isFullScreen())
        for handle in self._handles:
            handle.setVisible(visible)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_handles"):
            self._layout_handles()

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if (
            event.type() == QEvent.Type.WindowStateChange
            and hasattr(self, "_handles")
        ):
            self.titlebar.sync_maximize()
            self._update_handle_visibility()

    def show_login(self) -> None:
        self.home.shutdown_realtime()
        session.clear()
        self.login.reset()
        self.home.peer_edit.clear()
        self.home.call_status.setText("")
        self.stack.setCurrentWidget(self.login)

    def show_register(self) -> None:
        self.register.reset()
        self.stack.setCurrentWidget(self.register)

    def _enter_home(self, user: dict) -> None:
        self.home.set_user(
            user.get("full_name", ""),
            user.get("com_id", ""),
        )
        saved = session.load() or {}
        token = saved.get("token")
        if token:
            self.home.start_realtime(token)
        self.stack.setCurrentWidget(self.home)

    def _go_to_login_after_register(self, user: dict) -> None:
        self.login.com_id_edit.setText((user.get("com_id") or "").upper())
        self.login.password.edit.clear()
        self.login.clear_messages()
        self.login.show_info("Account created. Please sign in.")
        self.stack.setCurrentWidget(self.login)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.home.shutdown_camera()
        self.home.shutdown_realtime()
        super().closeEvent(event)
