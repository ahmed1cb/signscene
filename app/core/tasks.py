"""Run blocking work off the GUI thread and deliver results via Qt signals."""
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class _TaskSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()


class _Task(QRunnable):
    def __init__(self, fn: Callable[[], object], signals: _TaskSignals) -> None:
        super().__init__()
        self._fn = fn
        self._signals = signals

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as exc:
            self._signals.failed.emit(str(exc))
        else:
            self._signals.succeeded.emit(result)
        finally:
            self._signals.finished.emit()


_pending: set[_TaskSignals] = set()


def run_async(
    fn: Callable[[], object],
    on_success: Callable[[object], None] | None = None,
    on_error: Callable[[str], None] | None = None,
    on_finished: Callable[[], None] | None = None,
) -> None:
    """Run `fn` on a worker thread; callbacks are invoked on the GUI thread."""
    signals = _TaskSignals()
    if on_success:
        signals.succeeded.connect(on_success)
    if on_error:
        signals.failed.connect(on_error)
    if on_finished:
        signals.finished.connect(on_finished)
    signals.finished.connect(lambda: _pending.discard(signals))
    _pending.add(signals)
    QThreadPool.globalInstance().start(_Task(fn, signals))
