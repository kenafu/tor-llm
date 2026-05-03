from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(object)
    finished = Signal()


class FunctionWorker(QRunnable):
    def __init__(self, fn, *args, **kwargs) -> None:  # noqa: ANN001
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(exc)
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


class StreamWorker(QRunnable):
    def __init__(self, iterable_factory, *args, **kwargs) -> None:  # noqa: ANN001
        super().__init__()
        self.iterable_factory = iterable_factory
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True

    @Slot()
    def run(self) -> None:
        try:
            for chunk in self.iterable_factory(*self.args, **self.kwargs):
                if self.cancelled:
                    break
                self.signals.result.emit(str(chunk))
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(exc)
        finally:
            self.signals.finished.emit()
