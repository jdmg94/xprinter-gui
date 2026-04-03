"""Shared application state passed to every panel."""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from xprinter import XPrinter


class AppContext:
    """Holds the live XPrinter instance and notifies panels on connect/disconnect."""

    def __init__(self) -> None:
        self.printer: XPrinter | None = None
        self._on_connect: list[Callable[[XPrinter], None]] = []
        self._on_disconnect: list[Callable[[], None]] = []
        self._on_status: list[Callable[[str], None]] = []

    # ------------------------------------------------------------------
    # Subscription helpers
    # ------------------------------------------------------------------

    def on_connect(self, cb: Callable[[XPrinter], None]) -> None:
        self._on_connect.append(cb)

    def on_disconnect(self, cb: Callable[[], None]) -> None:
        self._on_disconnect.append(cb)

    def on_status(self, cb: Callable[[str], None]) -> None:
        self._on_status.append(cb)

    # ------------------------------------------------------------------
    # State changes
    # ------------------------------------------------------------------

    def connect(self, printer: XPrinter) -> None:
        self.printer = printer
        for cb in self._on_connect:
            cb(printer)

    def disconnect(self) -> None:
        if self.printer is not None:
            try:
                self.printer.close()
            except Exception:
                pass
        self.printer = None
        for cb in self._on_disconnect:
            cb()

    def set_status(self, msg: str) -> None:
        for cb in self._on_status:
            cb(msg)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def connected(self) -> bool:
        return self.printer is not None
