from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QStackedWidget

from core import session
from ui.screens.home_screen import HomeScreen
from ui.screens.login_screen import LoginScreen
from ui.screens.register_screen import RegisterScreen


class MainWindow(QStackedWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SignScene")
        self.setMinimumSize(1100, 720)

        self.login = LoginScreen(
            on_login_success=self._enter_home,
            on_go_register=self.show_register,
        )
        self.register = RegisterScreen(
            on_registered=self._go_to_login_after_register,
            on_go_login=self.show_login,
        )
        self.home = HomeScreen(on_sign_out=self.show_login)

        self.addWidget(self.login)
        self.addWidget(self.register)
        self.addWidget(self.home)
        self.setCurrentWidget(self.login)

    def show_login(self) -> None:
        session.clear()
        self.login.reset()
        self.home.peer_edit.clear()
        self.home.call_status.setText("")
        self.setCurrentWidget(self.login)

    def show_register(self) -> None:
        self.register.reset()
        self.setCurrentWidget(self.register)

    def _enter_home(self, user: dict) -> None:
        self.home.set_user(user.get("full_name", ""), user.get("com_id", ""))
        self.setCurrentWidget(self.home)
    def _go_to_login_after_register(self, user: dict) -> None:
        self.login.com_id_edit.setText((user.get("com_id") or "").upper())
        self.login.password.edit.clear()
        self.login.clear_messages()
        self.login.show_info("Account created. Please sign in.")
        self.setCurrentWidget(self.login)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.home.shutdown_camera()
        super().closeEvent(event)

