import re
from pathlib import Path

import numpy as np
from core import speaker
from core.asl.templates import TemplateStore
from core.camera import CameraWorker
from core.message import Message
from core.speaker import Speaker
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.screens.teach_dialog import TeachDialog
from ui.widgets.message_panel import MessagePanel

COM_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]{1,10}-\d{4}$")
ICON_PATH = Path(__file__).resolve().parents[2] / "assets/images/icon.svg"


class VideoLabel(QLabel):
    """QLabel with fixed layout hints so placeholder text/pixmap never resizes it."""

    def sizeHint(self) -> QSize:
        return QSize(480, 360)

    def minimumSizeHint(self) -> QSize:
        return QSize(320, 240)


class HomeScreen(QWidget):
    def __init__(self, on_sign_out, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_sign_out = on_sign_out
        self._camera_worker: CameraWorker | None = None
        self._last_frame: np.ndarray | None = None
        self._templates = TemplateStore()
        self._recording_word: str | None = None
        speaker.apply_saved()
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        root.addLayout(self._build_top_bar())
        root.addLayout(self._build_call_bar())
        root.addLayout(self._build_main_area(), stretch=1)

    # ---------- top bar ----------
    def _build_top_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()

        title = QLabel("SignScene")
        title.setObjectName("Title")

        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("StatusDot")
        self.own_id = QLabel("")
        self.own_id.setObjectName("Hint")

        identity = QHBoxLayout()
        identity.setSpacing(6)
        identity.addWidget(self.status_dot)
        identity.addWidget(self.own_id)

        self.teach_button = QPushButton("Teach signs")
        self.teach_button.setObjectName("GhostButton")
        self.teach_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.teach_button.setFixedWidth(120)
        self.teach_button.clicked.connect(self._show_teach)

        sign_out = QPushButton("Sign out")
        sign_out.setObjectName("GhostButton")
        sign_out.setCursor(Qt.CursorShape.PointingHandCursor)
        sign_out.setFixedWidth(110)
        sign_out.clicked.connect(self._on_sign_out)

        logo = QLabel()
        logo.setPixmap(QIcon(str(ICON_PATH)).pixmap(30, 30))
        logo.setFixedSize(30, 30)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        bar.addWidget(logo)
        bar.addWidget(title)
        bar.addStretch(1)
        bar.addSpacing(8)
        bar.addWidget(self.teach_button)
        bar.addSpacing(8)
        bar.addLayout(identity)
        bar.addSpacing(12)
        bar.addWidget(sign_out)
        return bar

    # ---------- call bar ----------
    def _build_call_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(10)

        self.peer_edit = QLineEdit()
        self.peer_edit.setPlaceholderText("Enter com_id to call — e.g. JOHN-7290")
        self.peer_edit.setMinimumHeight(42)
        self.peer_edit.setMaxLength(16)
        self.peer_edit.textChanged.connect(self._on_peer_changed)
        self.peer_edit.returnPressed.connect(self._try_call)

        self.call_button = QPushButton("Connect")
        self.call_button.setMinimumHeight(42)
        self.call_button.setMinimumWidth(110)
        self.call_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.call_button.setEnabled(False)
        self.call_button.clicked.connect(self._try_call)

        self.call_status = QLabel("")
        self.call_status.setObjectName("Hint")

        bar.addWidget(self.peer_edit, 1)
        bar.addWidget(self.call_button)
        bar.addWidget(self.call_status)
        return bar

    # ---------- camera + side panels ----------
    def _build_main_area(self) -> QHBoxLayout:
        area = QHBoxLayout()
        area.setSpacing(14)

        camera_card = QFrame()
        camera_card.setObjectName("Card")
        camera_layout = QVBoxLayout(camera_card)
        camera_layout.setContentsMargins(10, 10, 10, 10)
        camera_layout.setSpacing(12)

        camera_title = QLabel("Camera")
        camera_title.setObjectName("Subtitle")

        self.camera_video = VideoLabel()
        self.camera_video.setObjectName("CameraVideo")
        self.camera_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_video.setText("Camera feed will appear here")

        self.gesture_label = QLabel("")
        self.gesture_label.setObjectName("GestureLabel")
        self.gesture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.composing_label = QLabel("—")
        self.composing_label.setObjectName("ComposingLabel")
        self.composing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.composing_label.setWordWrap(True)

        self.camera_hud = QLabel("Hand tracking is off")
        self.camera_hud.setObjectName("CameraHud")
        self.camera_hud.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.fps_label = QLabel("")
        self.fps_label.setObjectName("CameraHud")

        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        status_row.addWidget(self.camera_hud)
        status_row.addStretch(1)
        status_row.addWidget(self.fps_label)

        self.camera_button = QPushButton("Open Camera")
        self.camera_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.camera_button.setFixedWidth(160)
        self.camera_button.clicked.connect(self._open_camera)

        self.clear_button = QPushButton("Clear")
        self.clear_button.setObjectName("GhostButton")
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.setFixedWidth(90)
        self.clear_button.setEnabled(False)
        self.clear_button.clicked.connect(self._clear_composing)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.camera_button)
        button_row.addWidget(self.clear_button)
        button_row.addStretch(1)

        camera_layout.addWidget(camera_title, alignment=Qt.AlignmentFlag.AlignLeft)
        camera_layout.addWidget(self.camera_video, stretch=1)
        camera_layout.addWidget(self.gesture_label)
        camera_layout.addWidget(self.composing_label)
        camera_layout.addLayout(status_row)
        camera_layout.addLayout(button_row)

        # side panels: messages (default) or the teach panel
        self.messages_area = MessagePanel("Messages", "The Chat Messages")

        messages_page = QWidget()
        messages_layout = QVBoxLayout(messages_page)
        messages_layout.setContentsMargins(0, 0, 0, 0)
        messages_layout.setSpacing(14)
        messages_layout.addWidget(self.messages_area, stretch=1)

        self._messages_page = messages_page

        self._teach = TeachDialog(
            templates=self._templates,
            on_record=self._start_record,
            on_clear=self._clear_word,
            on_close=self._show_messages,
        )

        self.side_stack = QStackedWidget()
        self.side_stack.addWidget(self._messages_page)
        self.side_stack.addWidget(self._teach)
        self.side_stack.setCurrentWidget(self._messages_page)

        area.addWidget(camera_card, 62)
        area.addWidget(self.side_stack, 38)
        return area

    # ---------- teach panel wiring ----------
    def _show_teach(self) -> None:
        self._teach.refresh()
        self.side_stack.setCurrentWidget(self._teach)

    def _show_messages(self) -> None:
        self.side_stack.setCurrentWidget(self._messages_page)

    def _start_record(self, word: str) -> None:
        if self._camera_worker is None:
            self._teach.status.setText("Open the camera first.")
            return
        self._recording_word = word
        self._camera_worker.request_record(word)

    def _clear_word(self, word: str) -> None:
        self._templates.clear_word(word)

    # ---------- behavior ----------
    def set_user(self, full_name: str, com_id: str) -> None:
        self.own_id.setText(com_id)
        self.setToolTip(full_name)

    def _on_peer_changed(self, text: str) -> None:
        upper = text.upper()
        if text != upper:
            self.peer_edit.blockSignals(True)
            self.peer_edit.setText(upper)
            self.peer_edit.blockSignals(False)

        valid = bool(COM_ID_PATTERN.match(self.peer_edit.text().strip()))
        self.call_button.setEnabled(valid)

        self.peer_edit.setProperty("invalid", bool(upper) and not valid)
        self.peer_edit.setProperty("valid", valid)
        self.peer_edit.style().unpolish(self.peer_edit)
        self.peer_edit.style().polish(self.peer_edit)

    def _try_call(self) -> None:
        peer = self.peer_edit.text().strip()
        self.call_status.setText(f"Call request to {peer} — not wired yet")

    def _open_camera(self) -> None:
        if self._camera_worker is not None:
            self._camera_worker.stop()
            self.camera_button.setEnabled(False)
            self.camera_hud.setText("Stopping camera…")
            return

        self.camera_button.setText("Stop Camera")
        self.camera_hud.setText("Starting camera…")

        worker = CameraWorker(templates=self._templates, parent=self)
        worker.frame_ready.connect(self._on_frame)
        worker.status_changed.connect(self.camera_hud.setText)
        worker.sentence_changed.connect(self._on_sentence_changed)
        worker.sentence_ready.connect(self._on_sentence_ready)
        worker.gesture_detected.connect(self._on_gesture)
        worker.gesture_recorded.connect(self._on_gesture_recorded)
        worker.record_progress.connect(self._on_record_progress)
        worker.fps_changed.connect(self._on_fps)
        worker.stopped.connect(self._on_camera_stopped)
        self._camera_worker = worker
        self.clear_button.setEnabled(True)
        worker.start()

    def _on_frame(self, rgb: np.ndarray) -> None:
        if rgb is None or rgb.size == 0:
            return
        self._last_frame = rgb
        self._render_frame()

    def _render_frame(self) -> None:
        if self._last_frame is None:
            return
        h, w, _ = self._last_frame.shape
        qimage = QImage(self._last_frame.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        target = self.camera_video.size()
        if target.width() < 1 or target.height() < 1:
            return
        pixmap = QPixmap.fromImage(qimage).scaled(
            target,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = max(0, (pixmap.width() - target.width()) // 2)
        y = max(0, (pixmap.height() - target.height()) // 2)
        self.camera_video.setPixmap(pixmap.copy(x, y, target.width(), target.height()))

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._render_frame()

    def _on_sentence_changed(self, text: str) -> None:
        self.composing_label.setText(text if text else "—")

    def _on_sentence_ready(self, text: str) -> None:
        if text:
            msg = Message("txt", text)

            self.messages_area.add_message(msg)
            # Here Convert the text to the audio (on the sender screen)
            try:
                Speaker.say(msg)
            except Exception as e:
                print(e)
            self.camera_hud.setText("Sentence sent to My messages")
        self.composing_label.setText("—")

    def _on_gesture(self, word: str, confidence: float) -> None:
        self.gesture_label.setText(f"Sign: {word}  ({confidence * 100:.0f}%)")
        QTimer.singleShot(2500, lambda: self.gesture_label.setText(""))

    def _on_gesture_recorded(self, word: str, total: int) -> None:
        self._recording_word = None
        self._teach.on_recorded(word, total)

    def _on_record_progress(self, remaining_ms: int) -> None:
        if self._recording_word:
            self._teach.on_record_progress(self._recording_word, remaining_ms)

    def _on_fps(self, fps: float) -> None:
        self.fps_label.setText(f"{fps:.0f} fps")

    def _clear_composing(self) -> None:
        if self._camera_worker is not None:
            self._camera_worker.request_clear()
        self.composing_label.setText("—")

    def _on_camera_stopped(self) -> None:
        worker = self._camera_worker
        self._camera_worker = None
        self._last_frame = None
        self.camera_button.setText("Open Camera")
        self.camera_button.setEnabled(True)
        self.clear_button.setEnabled(False)
        self.camera_hud.setText("Hand tracking is off")
        self.fps_label.setText("")
        self.gesture_label.setText("")
        self.composing_label.setText("—")
        self.camera_video.clear()
        self.camera_video.setText("Camera feed will appear here")
        if worker is not None:
            worker.deleteLater()

    def shutdown_camera(self) -> None:
        if self._camera_worker is not None:
            self._camera_worker.stop()
            self._camera_worker.wait(3000)
            self._camera_worker = None
