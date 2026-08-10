from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(int)


class TaskWorker(QRunnable):
    def __init__(self, task: Callable[[Callable[[int], None]], Any]) -> None:
        super().__init__()
        self.task = task
        self.signals = WorkerSignals()
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True

    def report_progress(self, value: int) -> None:
        if self.cancelled:
            raise InterruptedError("任务已取消")
        self.signals.progress.emit(max(0, min(100, value)))

    @Slot()
    def run(self) -> None:
        try:
            result = self.task(self.report_progress)
        except Exception as exc:  # UI boundary: convert failure to a signal
            self.signals.failed.emit(str(exc))
        else:
            self.signals.finished.emit(result)

