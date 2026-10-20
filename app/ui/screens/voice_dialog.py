from core import speaker
from core.speaker import Speaker
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class VoiceDialog(QDialog):
    """Popup to pick the TTS voice, rate and volume."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Voice settings")
        self.setModal(True)
        self.setMinimumWidth(440)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Voice settings")
        title.setObjectName("Title")
        done = QPushButton("Done")
        done.setObjectName("GhostButton")
        done.setCursor(Qt.CursorShape.PointingHandCursor)
        done.clicked.connect(self.accept)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(done)

        hint = QLabel(
            "Choose the voice used to speak recognized sentences. "
            "Adjust rate and volume, then press Test to preview."
        )
        hint.setObjectName("Hint")
        hint.setWordWrap(True)

        voice_row = QHBoxLayout()
        voice_row.setSpacing(10)
        self.voice_combo = QComboBox()
        self.voice_combo.setObjectName("VoiceCombo")
        self.voice_combo.setMinimumHeight(40)
        self.voice_combo.setToolTip("Voice used to speak recognized sentences")
        self.voice_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.voice_combo.setMinimumContentsLength(24)
        for voice_id, voice_name in speaker.list_voices():
            self.voice_combo.addItem(voice_name, voice_id)

        test_button = QPushButton("Test")
        test_button.setCursor(Qt.CursorShape.PointingHandCursor)
        test_button.setFixedWidth(80)
        test_button.setToolTip("Speak a sample with the current settings")
        test_button.clicked.connect(self._on_test)

        voice_row.addWidget(self.voice_combo, 1)
        voice_row.addWidget(test_button)

        self.rate_value = QLabel()
        self.rate_value.setObjectName("Subtitle")
        self.rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.rate_slider.setObjectName("RateSlider")
        self.rate_slider.setRange(50, 200)
        self.rate_slider.setToolTip("Speech rate")
        self.rate_slider.valueChanged.connect(self._on_rate_changed)

        self.volume_value = QLabel()
        self.volume_value.setObjectName("Subtitle")
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("VolumeSlider")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setToolTip("Speech volume")
        self.volume_slider.valueChanged.connect(self._on_volume_changed)

        root.addLayout(header)
        root.addWidget(hint)
        root.addLayout(voice_row)
        root.addWidget(self._labeled_row("Rate", self.rate_slider, self.rate_value))
        root.addWidget(
            self._labeled_row("Volume", self.volume_slider, self.volume_value)
        )

        self._load_current()

    def _labeled_row(
        self, caption: str, slider: QSlider, value_label: QLabel
    ) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        label = QLabel(caption)
        label.setFixedWidth(60)
        value_label.setFixedWidth(36)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(label)
        layout.addWidget(slider, 1)
        layout.addWidget(value_label)
        return row

    def _load_current(self) -> None:
        current = speaker.current()

        wanted = current.get("voice_id")
        if wanted is not None:
            for i in range(self.voice_combo.count()):
                if str(self.voice_combo.itemData(i)) == str(wanted):
                    self.voice_combo.setCurrentIndex(i)
                    break
        self.voice_combo.currentIndexChanged.connect(self._on_voice_changed)

        self.rate_slider.setValue(int(current["rate"]))
        self._on_rate_changed(self.rate_slider.value())

        self.volume_slider.setValue(int(float(current["volume"]) * 100))
        self._on_volume_changed(self.volume_slider.value())

    def _on_voice_changed(self, index: int) -> None:
        voice_id = self.voice_combo.itemData(index)
        if voice_id is None:
            return
        speaker.set_voice(str(voice_id), self.voice_combo.itemText(index))

    def _on_rate_changed(self, value: int) -> None:
        self.rate_value.setText(str(value))
        speaker.set_rate(value)

    def _on_volume_changed(self, value: int) -> None:
        self.volume_value.setText(str(value))
        speaker.set_volume(value / 100.0)

    def _on_test(self) -> None:
        try:
            Speaker.say("This is how SignScene will sound.")
        except Exception as e:
            print(e)
