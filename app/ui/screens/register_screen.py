import re

from core import api_client
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.screens.login_screen import _PasswordLineEdit
from ui.widgets.header import Header

COM_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]{1,10}-\d{4}$")


class RegisterScreen(QWidget):
    def __init__(
        self, on_registered, on_go_login, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._on_registered = on_registered
        self._on_go_login = on_go_login
        self._build_ui()
        self._connect_validation()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        card = QFrame()
        card.setObjectName("Card")
        card.setFixedWidth(460)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.setSpacing(12)

        title = QLabel("Create your account")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel(
            "Your com_id is how others reach you — share it with people you call."
        )
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Full name")
        self.name_edit.setMinimumHeight(42)

        self.com_id_edit = QLineEdit()
        self.com_id_edit.setPlaceholderText("com_id — e.g. ALICE-4821")
        self.com_id_edit.setMinimumHeight(42)
        self.com_id_edit.setMaxLength(16)

        self.com_id_hint = QLabel("Letters, then a dash and 4 digits.")
        self.com_id_hint.setObjectName("Hint")

        self.password = _PasswordLineEdit("Password")

        self.confirm = _PasswordLineEdit("Confirm password")

        content_label = QLabel("Content you want to receive")
        content_label.setObjectName("Hint")

        content_row = QHBoxLayout()
        self.check_text = QCheckBox("Text")
        self.check_audio = QCheckBox("Audio")
        self.check_scene = QCheckBox("Scene")
        for check in (self.check_text, self.check_audio, self.check_scene):
            check.setChecked(True)
            content_row.addWidget(check)
        content_row.addStretch(1)

        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.register_button = QPushButton("Create account")
        self.register_button.setMinimumHeight(44)
        self.register_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.register_button.setEnabled(False)
        self.register_button.clicked.connect(self._try_register)

        back_row = QHBoxLayout()
        back_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        have_account = QLabel("Already have an account?")
        have_account.setObjectName("Hint")
        back_link = QPushButton("Sign in")
        back_link.setObjectName("LinkButton")
        back_link.setCursor(Qt.CursorShape.PointingHandCursor)
        back_link.clicked.connect(self._on_go_login)
        back_row.addWidget(have_account)
        back_row.addWidget(back_link)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(4)
        card_layout.addWidget(self.name_edit)
        card_layout.addWidget(self.com_id_edit)
        card_layout.addWidget(self.com_id_hint)
        card_layout.addWidget(self.password)
        card_layout.addWidget(self.confirm)
        card_layout.addWidget(content_label)
        card_layout.addLayout(content_row)
        card_layout.addWidget(self.error_label)
        card_layout.addWidget(self.register_button)
        card_layout.addLayout(back_row)

        root.addWidget(Header())
        root.addStretch(1)
        root.addWidget(card, 0, Qt.AlignmentFlag.AlignCenter)
        root.addStretch(1)

    def _connect_validation(self) -> None:
        self.name_edit.textChanged.connect(self._revalidate)
        self.com_id_edit.textChanged.connect(self._on_com_id_changed)
        self.password.edit.textChanged.connect(self._revalidate)
        self.confirm.edit.textChanged.connect(self._revalidate)
        self.confirm.edit.returnPressed.connect(self._try_register)

    def _on_com_id_changed(self, text: str) -> None:
        upper = text.upper()
        if text != upper:
            self.com_id_edit.blockSignals(True)
            self.com_id_edit.setText(upper)
            self.com_id_edit.blockSignals(False)

        if not upper:
            self._set_com_id_state(None, "Letters, then a dash and 4 digits.")
        elif COM_ID_PATTERN.match(upper):
            self._set_com_id_state(True, "Looks good.")
        else:
            self._set_com_id_state(False, "Use the format ALICE-4821.")
        self._revalidate()

    def _set_com_id_state(self, valid: bool | None, hint: str) -> None:
        self.com_id_hint.setText(hint)
        self.com_id_hint.setObjectName(
            "SuccessLabel" if valid else ("ErrorLabel" if valid is False else "Hint")
        )
        self.com_id_hint.style().unpolish(self.com_id_hint)
        self.com_id_hint.style().polish(self.com_id_hint)
        if valid is None:
            self.com_id_edit.setProperty("invalid", False)
            self.com_id_edit.setProperty("valid", False)
        else:
            self.com_id_edit.setProperty("invalid", not valid)
            self.com_id_edit.setProperty("valid", valid)
        self.com_id_edit.style().unpolish(self.com_id_edit)
        self.com_id_edit.style().polish(self.com_id_edit)

    def _form_valid(self) -> bool:
        if not self.name_edit.text().strip():
            return False
        if not COM_ID_PATTERN.match(self.com_id_edit.text().strip()):
            return False
        if len(self.password.text()) < 6:
            return False
        if self.password.text() != self.confirm.text():
            return False
        if not (
            self.check_text.isChecked()
            or self.check_audio.isChecked()
            or self.check_scene.isChecked()
        ):
            return False
        return True

    def _revalidate(self) -> None:
        self.register_button.setEnabled(self._form_valid())

    def _try_register(self) -> None:
        self._hide_error()
        if not self._form_valid():
            self._show_error("Please fix the highlighted fields.")
            return

        preferred = []
        if self.check_text.isChecked():
            preferred.append("text")
        if self.check_audio.isChecked():
            preferred.append("audio")
        if self.check_scene.isChecked():
            preferred.append("scene")

        try:
            user = api_client.register(
                full_name=self.name_edit.text().strip(),
                com_id=self.com_id_edit.text().strip(),
                password=self.password.text(),
                preferred=preferred,
            )
        except api_client.AuthError as exc:
            self._show_error(
                "Something went wrong, Please check the connection and try again"
            )
            return

        self._on_registered(user)

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()

    def _hide_error(self) -> None:
        self.error_label.hide()
        self.error_label.setText("")

    def reset(self) -> None:
        self.name_edit.clear()
        self.com_id_edit.clear()
        self.password.edit.clear()
        self.confirm.edit.clear()
        for check in (self.check_text, self.check_audio, self.check_scene):
            check.setChecked(True)
        self._set_com_id_state(None, "Letters, then a dash and 4 digits.")
        self._hide_error()
        self._revalidate()
