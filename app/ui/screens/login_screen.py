from core import api_client
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class _PasswordLineEdit(QWidget):
    def __init__(self, placeholder: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit.setPlaceholderText(placeholder)
        self.edit.setMinimumHeight(42)

        self.toggle = QPushButton("Show")
        self.toggle.setObjectName("TogglePassword")
        self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle.setCheckable(True)
        self.toggle.setFixedWidth(64)
        self.toggle.toggled.connect(self._on_toggle)

        layout.addWidget(self.edit, 1)
        layout.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignVCenter)

    def _on_toggle(self, checked: bool) -> None:
        self.edit.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self.toggle.setText("Hide" if checked else "Show")

    def text(self) -> str:
        return self.edit.text()


class LoginScreen(QWidget):
    def __init__(
        self, on_login_success, on_go_register, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._on_login_success = on_login_success
        self._on_go_register = on_go_register
        self._build_ui()
        self.reset()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("Card")
        card.setFixedWidth(420)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.setSpacing(14)

        title = QLabel("Welcome back")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Sign in to continue to SignScene")
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.com_id_edit = QLineEdit()
        self.com_id_edit.setPlaceholderText("com_id (e.g. ALICE-4821)")
        self.com_id_edit.setMinimumHeight(42)
        self.com_id_edit.returnPressed.connect(self._try_login)

        self.password = _PasswordLineEdit("Password")
        self.password.edit.returnPressed.connect(self._try_login)

        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.info_label = QLabel("")
        self.info_label.setObjectName("SuccessLabel")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setWordWrap(True)
        self.info_label.hide()

        self.login_button = QPushButton("Sign in")
        self.login_button.setMinimumHeight(44)
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.clicked.connect(self._try_login)

        register_row = QHBoxLayout()
        register_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        no_account = QLabel("Don't have an account?")
        no_account.setObjectName("Hint")
        register_link = QPushButton("Create one")
        register_link.setObjectName("LinkButton")
        register_link.setCursor(Qt.CursorShape.PointingHandCursor)
        register_link.clicked.connect(self._on_go_register)
        register_row.addWidget(no_account)
        register_row.addWidget(register_link)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(8)
        card_layout.addWidget(self.com_id_edit)
        card_layout.addWidget(self.password)
        card_layout.addWidget(self.info_label)
        card_layout.addWidget(self.error_label)
        card_layout.addWidget(self.login_button)
        card_layout.addLayout(register_row)

        root.addWidget(card)

    def _try_login(self) -> None:
        self.clear_messages()
        com_id = self.com_id_edit.text().strip()
        password = self.password.text()

        if not com_id or not password:
            self._show_error("Please fill in all fields.")
            return

        try:
            user = api_client.login(com_id, password)
        except api_client.AuthError as exc:
            print(str(exec))
            self._show_error(
                "Something Went Wrong, Please Check the connection and try again"
            )
            return

        self._on_login_success(user)

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()

    def clear_messages(self) -> None:
        self.error_label.hide()
        self.error_label.setText("")
        self.info_label.hide()
        self.info_label.setText("")

    def reset(self) -> None:
        self.com_id_edit.setText("ALICE-4821")
        self.password.edit.setText("123456")
        self.clear_messages()

    def show_info(self, text: str) -> None:
        self.clear_messages()
        self.info_label.setText(text)
        self.info_label.show()
