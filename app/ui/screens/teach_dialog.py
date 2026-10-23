from core.asl.templates import GestureTemplate, TemplateStore
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class TeachDialog(QWidget):
    """Inline teach panel: record landmark samples for each sign."""

    def __init__(self, templates: TemplateStore, on_record, on_clear, on_close) -> None:
        super().__init__()
        self._templates = templates
        self._on_record = on_record
        self._on_clear = on_clear
        self._on_close = on_close
        self._rows: dict[str, QLabel] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Teach signs")
        title.setObjectName("Title")
        close = QPushButton("Done")
        close.setObjectName("GhostButton")
        close.setCursor(self.cursor())
        close.clicked.connect(self._on_close)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(close)

        hint = QLabel(
            "Press Record on a word, then perform the sign clearly for 2 seconds "
            "after the countdown. Record 3–5 times per word for best accuracy. "
            "The camera must be running."
        )
        hint.setObjectName("Hint")
        hint.setWordWrap(True)

        add_row = QHBoxLayout()
        self.custom_edit = QLineEdit()
        self.custom_edit.setPlaceholderText("Add a custom word — e.g. water")
        self.custom_edit.setMinimumHeight(40)
        add_button = QPushButton("Add")
        add_button.setFixedWidth(90)
        add_button.clicked.connect(self._add_custom)
        add_row.addWidget(self.custom_edit, 1)
        add_row.addWidget(add_button)

        self.status = QLabel("")
        self.status.setObjectName("Hint")

        self._list = QWidget()
        self._list.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName("MessageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self._list)

        root.addLayout(header)
        root.addWidget(hint)
        root.addLayout(add_row)
        root.addWidget(self.status)
        root.addWidget(scroll, stretch=1)

        self._populate()

    def _words(self) -> list[str]:
        return list(self._templates.templates)

    def _populate(self) -> None:
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._rows.clear()
        for word in self._words():
            self._list_layout.insertWidget(
                self._list_layout.count() - 1, self._row(word)
            )

    def _row(self, word: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        name = QLabel(word)
        count = QLabel(self._count_text(word))
        self._rows[word] = count

        record = QPushButton("Record")
        record.setFixedWidth(100)
        record.clicked.connect(lambda _=False, w=word: self._record(word))

        clear = QPushButton("Clear")
        clear.setObjectName("GhostButton")
        clear.setFixedWidth(80)
        clear.clicked.connect(lambda _, w=word: self._clear(word))

        layout.addWidget(name, 1)
        layout.addWidget(count)
        layout.addWidget(record)
        layout.addWidget(clear)
        return row

    def _count_text(self, word: str) -> str:
        count = self._templates.sample_count(word)
        return f"{count} sample{'s' if count != 1 else ''}"

    def _add_custom(self) -> None:
        word = self.custom_edit.text().strip().lower()
        if not word:
            return
        self.custom_edit.clear()
        self._templates.templates.setdefault(word, GestureTemplate(word=word))
        self._populate()

    def _record(self, word: str) -> None:
        self._on_record(word)

    def _clear(self, word: str) -> None:
        self._on_clear(word)
        self._populate()

    # ---- external updates ----
    def refresh(self) -> None:
        for word, label in self._rows.items():
            label.setText(self._count_of(word))

    def _count_of(self, word: str) -> str:
        count = self._templates.sample_count(word)
        return f"{count} sample{'s' if count != 1 else ''}"

    def on_recorded(self, word: str, total: int) -> None:
        label = self._rows.get(word)
        if label is not None:
            label.setText(f"{total} sample{'s' if total != 1 else ''}")
        self.status.setText(f"Saved sample for “{word}” ({total} total)")
        if word not in self._rows:
            self._populate()

    def on_record_progress(self, word: str, remaining_ms: int) -> None:
        self.status.setText(f"Recording “{word}”… {remaining_ms / 1000:.1f}s")
