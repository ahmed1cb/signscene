"""Sentence builder: accumulates recognized gesture words and auto-sends on idle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

SEND_AFTER_NO_HAND_MS = 4000  # hand away this long → auto-send sentence


@dataclass
class SentenceBuilder:
    on_sentence_changed: Callable[[str], None] = lambda text: None
    on_sentence_ready: Callable[[str], None] = lambda text: None

    sentence: str = ""
    _no_hand_since_ms: int = -1

    def add_word(self, word: str) -> None:
        word = " ".join(word.strip().split())
        if not word:
            return
        self.sentence = f"{self.sentence} {word}".strip() if self.sentence else word
        self.on_sentence_changed(self.sentence)

    def tick(self, ts_ms: int, has_hand: bool) -> None:
        if has_hand:
            self._no_hand_since_ms = -1
            return

        if self._no_hand_since_ms < 0:
            self._no_hand_since_ms = ts_ms
            return

        if ts_ms - self._no_hand_since_ms >= SEND_AFTER_NO_HAND_MS and self.sentence:
            text = self.sentence
            self.clear_sentence()
            self.on_sentence_ready(text)

    def clear_sentence(self) -> None:
        self.sentence = ""
        self._no_hand_since_ms = -1
        self.on_sentence_changed("")
