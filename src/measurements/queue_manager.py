"""
Measurement queue — ordered list of pending measurement runs.

Each QueueItem wraps a measurement class and its parameters so the user can
set up multiple sweeps and run them back-to-back without clicking between tabs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional, Type
from uuid import uuid4


class QueueItemStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    DONE    = auto()
    ABORTED = auto()
    ERROR   = auto()


_STATUS_SYMBOLS = {
    QueueItemStatus.PENDING: "⏳",
    QueueItemStatus.RUNNING: "▶",
    QueueItemStatus.DONE:    "✓",
    QueueItemStatus.ABORTED: "⊘",
    QueueItemStatus.ERROR:   "✗",
}


@dataclass
class QueueItem:
    measurement_class: Type   # BaseMeasurement subclass
    params:            Dict[str, Any]
    label:             str = ""
    uid:               str = field(default_factory=lambda: str(uuid4())[:8])
    status:            QueueItemStatus = QueueItemStatus.PENDING
    result:            Optional[object] = None
    error_msg:         str = ""

    @property
    def display_type(self) -> str:
        return getattr(self.measurement_class, "NAME", self.measurement_class.__name__)

    @property
    def display_label(self) -> str:
        return self.label or self.display_type

    @property
    def status_symbol(self) -> str:
        return _STATUS_SYMBOLS[self.status]


class MeasurementQueue:
    """Ordered list of QueueItems with add / remove / reorder helpers."""

    def __init__(self) -> None:
        self._items: list[QueueItem] = []

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    @property
    def items(self) -> list[QueueItem]:
        return list(self._items)

    def add(self, measurement_class, params: dict, label: str = "") -> QueueItem:
        item = QueueItem(measurement_class=measurement_class, params=params, label=label)
        self._items.append(item)
        return item

    def remove(self, uid: str) -> None:
        self._items = [i for i in self._items if i.uid != uid]

    def move_up(self, uid: str) -> None:
        idx = self._find(uid)
        if idx > 0:
            self._items[idx - 1], self._items[idx] = self._items[idx], self._items[idx - 1]

    def move_down(self, uid: str) -> None:
        idx = self._find(uid)
        if idx < len(self._items) - 1:
            self._items[idx + 1], self._items[idx] = self._items[idx], self._items[idx + 1]

    def clear(self) -> None:
        self._items.clear()

    def reset_statuses(self) -> None:
        for item in self._items:
            item.status   = QueueItemStatus.PENDING
            item.result   = None
            item.error_msg = ""

    def pending_items(self) -> list[QueueItem]:
        return [i for i in self._items if i.status == QueueItemStatus.PENDING]

    def _find(self, uid: str) -> int:
        for i, item in enumerate(self._items):
            if item.uid == uid:
                return i
        raise KeyError(f"UID {uid!r} not in queue")
