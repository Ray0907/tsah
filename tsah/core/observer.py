from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Callable, ClassVar

from tsah.core import ax_raw
from tsah.core.ax import AXElement


@dataclass(slots=True)
class AXEvent:
    pid: int
    notification: str
    element: AXElement
    timestamp: float


class AXObserver:
    _instances: ClassVar[dict[int, "AXObserver"]] = {}
    _callback: ClassVar[ax_raw.AXObserverCallback]

    def __init__(
        self,
        pid: int,
        *,
        callback: Callable[[AXEvent], None],
        element: AXElement | None = None,
        notifications: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        self.pid = pid
        self._callback_fn = callback
        self._element = element or AXElement.application(pid)
        self._notifications = list(notifications or [ax_raw.NOTIFICATION_NAMES["focused_ui_changed"]])
        self._observer = ax_raw.create_observer(pid, self._callback)
        self._run_loop = None
        self._source = ax_raw.observer_source(self._observer)
        self._closed = False
        self._thread: threading.Thread | None = None

        self._instances[int(self._observer.value)] = self
        for notification in self._notifications:
            ax_raw.add_notification(self._observer, self._element.ref, notification)

    @classmethod
    def for_focused_application(
        cls,
        *,
        callback: Callable[[AXEvent], None],
        notifications: list[str] | tuple[str, ...] | None = None,
    ) -> "AXObserver":
        element = AXElement.focused_application()
        pid = element.pid()
        if pid is None:
            raise RuntimeError("Focused application does not report a pid")
        return cls(pid, callback=callback, element=element, notifications=notifications)

    def run(self) -> None:
        if self._closed:
            raise RuntimeError("Observer is closed")
        self._run_loop = ax_raw.current_run_loop()
        ax_raw.add_run_loop_source(self._run_loop, self._source)
        try:
            ax_raw.run_loop_run()
        finally:
            ax_raw.remove_run_loop_source(self._run_loop, self._source)
            self._run_loop = None

    def run_in_thread(self, *, name: str | None = None, daemon: bool = True) -> threading.Thread:
        if self._thread is not None and self._thread.is_alive():
            return self._thread

        thread = threading.Thread(target=self.run, name=name or f"AXObserver-{self.pid}", daemon=daemon)
        thread.start()
        self._thread = thread
        return thread

    def stop(self) -> None:
        if self._run_loop is not None:
            ax_raw.run_loop_stop(self._run_loop)

    def close(self) -> None:
        if self._closed:
            return
        self.stop()
        for notification in self._notifications:
            ax_raw.remove_notification(self._observer, self._element.ref, notification)
        self._instances.pop(int(self._observer.value), None)
        ax_raw.release(self._observer)
        self._element.close()
        self._closed = True

    def __enter__(self) -> "AXObserver":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @staticmethod
    def _dispatch(observer_ref, element_ref, notification_ref, _refcon) -> None:
        instance = AXObserver._instances.get(int(observer_ref))
        if instance is None or instance._closed:
            return

        event = AXEvent(
            pid=instance.pid,
            notification=ax_raw.string_to_python(notification_ref),
            element=AXElement(element_ref),
            timestamp=time.time(),
        )
        instance._callback_fn(event)
        event.element.close()


AXObserver._callback = ax_raw.AXObserverCallback(AXObserver._dispatch)
