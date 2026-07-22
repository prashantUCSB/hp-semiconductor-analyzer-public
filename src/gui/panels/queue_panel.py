"""
Measurement Queue Panel.

Displays the queue as a table, lets the user add/remove/reorder items,
choose an export format, and launch the queue via the Run button.

PyQt5 port of the Keithley-IV suite's QueuePanel.
"""
from __future__ import annotations

import logging

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from PyQt5.QtGui import QColor

from ...measurements.queue_manager import MeasurementQueue, QueueItem, QueueItemStatus

log = logging.getLogger(__name__)

_COL_STATUS = 0
_COL_TYPE   = 1
_COL_LABEL  = 2
_COL_NPTS   = 3
_COL_EXPORT = 4

_STATUS_COLORS = {
    QueueItemStatus.PENDING: "#888888",
    QueueItemStatus.RUNNING: "#FF9800",
    QueueItemStatus.DONE:    "#4CAF50",
    QueueItemStatus.ABORTED: "#FFC107",
    QueueItemStatus.ERROR:   "#F44336",
}


class QueuePanel(QWidget):
    """
    Queue management widget — intended for use in a QDockWidget.

    Signals
    -------
    run_queue_requested()   — user clicked Run Queue
    stop_queue_requested()  — user clicked Stop
    item_removed(str)       — an item was deleted; carries its display label
    """

    run_queue_requested  = pyqtSignal()
    stop_queue_requested = pyqtSignal()
    item_removed         = pyqtSignal(str)

    def __init__(self, queue: MeasurementQueue, parent=None):
        super().__init__(parent)
        self._queue = queue
        self._build_ui()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setMinimumWidth(dp_fallback(220))

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        title = QLabel("MEASUREMENT QUEUE")
        title.setStyleSheet("font-weight:700; font-size:9pt; color:#aaa;")
        root.addWidget(title)

        # Table
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["", "Type", "Label", "Pts", "Save"])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.setColumnWidth(_COL_STATUS, 20)
        self._table.setColumnWidth(_COL_TYPE,   82)
        self._table.setColumnWidth(_COL_LABEL,  84)
        self._table.setColumnWidth(_COL_NPTS,   36)
        self._table.setColumnWidth(_COL_EXPORT, 36)
        self._table.setAlternatingRowColors(True)
        self._table.itemChanged.connect(self._on_item_changed)
        root.addWidget(self._table, stretch=1)

        # Row controls
        row_ctrl = QHBoxLayout()
        self._del_btn = QPushButton("Remove")
        self._del_btn.setToolTip("Remove selected item from queue")
        self._del_btn.clicked.connect(self._remove_selected)
        self._up_btn = QPushButton("▲")
        self._up_btn.setFixedWidth(dp_fallback(28))
        self._up_btn.setToolTip("Move selected item up")
        self._up_btn.clicked.connect(self._move_up)
        self._dn_btn = QPushButton("▼")
        self._dn_btn.setFixedWidth(dp_fallback(28))
        self._dn_btn.setToolTip("Move selected item down")
        self._dn_btn.clicked.connect(self._move_down)
        row_ctrl.addWidget(self._del_btn)
        row_ctrl.addStretch()
        row_ctrl.addWidget(self._up_btn)
        row_ctrl.addWidget(self._dn_btn)
        root.addLayout(row_ctrl)

        # Clear / Check All
        misc_row = QHBoxLayout()
        self._clear_btn = QPushButton("Clear All")
        self._clear_btn.clicked.connect(self._clear_queue)
        self._check_all_btn = QPushButton("Check All")
        self._check_all_btn.setToolTip("Mark all items for export")
        self._check_all_btn.clicked.connect(self._check_all_export)
        misc_row.addWidget(self._clear_btn)
        misc_row.addWidget(self._check_all_btn)
        root.addLayout(misc_row)

        # Export format
        fmt_row = QHBoxLayout()
        fmt_lbl = QLabel("Export:")
        fmt_lbl.setStyleSheet("color:#888;")
        self._format_combo = QComboBox()
        self._format_combo.addItem("CSV",   userData="csv")
        self._format_combo.addItem("Excel", userData="excel")
        self._format_combo.addItem("Both",  userData="both")
        self._format_combo.setToolTip(
            "CSV:   one .csv per measurement in a date-time subfolder\n"
            "Excel: one .xlsx workbook, one sheet per measurement\n"
            "Both:  CSV and Excel"
        )
        fmt_row.addWidget(fmt_lbl)
        fmt_row.addWidget(self._format_combo, stretch=1)
        root.addLayout(fmt_row)

        # Run / Stop
        self._run_btn = QPushButton("▶▶  Run Queue")
        self._run_btn.setStyleSheet(
            "QPushButton { background-color:#1565C0; color:white; font-weight:700; padding:4px 8px; }"
            "QPushButton:disabled { background-color:#444; color:#888; }"
        )
        self._run_btn.clicked.connect(self.run_queue_requested.emit)
        root.addWidget(self._run_btn)

        self._stop_btn = QPushButton("■  Stop")
        self._stop_btn.setStyleSheet(
            "QPushButton { background-color:#B71C1C; color:white; font-weight:700; padding:4px 8px; }"
            "QPushButton:disabled { background-color:#444; color:#888; }"
        )
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self.stop_queue_requested.emit)
        root.addWidget(self._stop_btn)

        self._count_lbl = QLabel("Queue empty")
        self._count_lbl.setStyleSheet("color:#888; font-size:8pt;")
        root.addWidget(self._count_lbl)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_item(self, measurement_class, params: dict, label: str = ""):
        """Add a measurement to the queue and refresh the table."""
        item = self._queue.add(measurement_class, params, label)
        self._append_row(item)
        self._refresh_count()

    def refresh(self):
        """Rebuild the table from the current queue state."""
        self._table.setRowCount(0)
        for item in self._queue:
            self._append_row(item)
        self._refresh_count()

    def update_item_status(self, uid: str, status: QueueItemStatus):
        """Update the status symbol/color for a single row by UID."""
        for row in range(self._table.rowCount()):
            cell = self._table.item(row, _COL_STATUS)
            if cell and cell.data(Qt.UserRole) == uid:
                symbol = _STATUS_SYMBOLS_DICT.get(status, "?")
                color  = _STATUS_COLORS.get(status, "#888")
                cell.setText(symbol)
                cell.setForeground(QColor(color))
                break

    def set_running(self, running: bool):
        self._run_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)
        self._clear_btn.setEnabled(not running)
        self._del_btn.setEnabled(not running)

    def is_export_checked(self, uid: str) -> bool:
        for row in range(self._table.rowCount()):
            cell = self._table.item(row, _COL_STATUS)
            if cell and cell.data(Qt.UserRole) == uid:
                exp_cell = self._table.item(row, _COL_EXPORT)
                if exp_cell:
                    return exp_cell.checkState() == Qt.Checked
        return False

    @property
    def export_format(self) -> str:
        return self._format_combo.currentData()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append_row(self, item: QueueItem):
        self._table.blockSignals(True)
        row = self._table.rowCount()
        self._table.insertRow(row)

        status_cell = QTableWidgetItem(item.status_symbol)
        status_cell.setData(Qt.UserRole, item.uid)
        status_cell.setTextAlignment(Qt.AlignCenter)
        color = _STATUS_COLORS.get(item.status, "#888")
        status_cell.setForeground(QColor(color))

        n_pts = self._estimate_pts(item)
        self._table.setItem(row, _COL_STATUS, status_cell)
        self._table.setItem(row, _COL_TYPE,   QTableWidgetItem(item.display_type[:12]))
        self._table.setItem(row, _COL_LABEL,  QTableWidgetItem(item.display_label[:14]))
        self._table.setItem(row, _COL_NPTS,   QTableWidgetItem(str(n_pts)))

        export_cell = QTableWidgetItem()
        export_cell.setCheckState(Qt.Checked)
        export_cell.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        export_cell.setTextAlignment(Qt.AlignCenter)
        self._table.setItem(row, _COL_EXPORT, export_cell)
        self._table.blockSignals(False)

    @staticmethod
    def _estimate_pts(item: QueueItem) -> int:
        p = item.params
        try:
            if "vgs_start" in p and "vgs_stop" in p and "vgs_step" in p:
                step = abs(p.get("vgs_step", 0.1))
                if step:
                    return int(abs(p["vgs_stop"] - p["vgs_start"]) / step) + 1
        except Exception:
            pass
        return p.get("n_points", 0)

    def _selected_uid(self) -> Optional[str]:
        row = self._table.currentRow()
        if row < 0:
            return None
        cell = self._table.item(row, _COL_STATUS)
        return cell.data(Qt.UserRole) if cell else None

    def _remove_selected(self):
        row = self._table.currentRow()
        if row < 0:
            return
        status_cell = self._table.item(row, _COL_STATUS)
        label_cell  = self._table.item(row, _COL_LABEL)
        if not status_cell:
            return
        uid     = status_cell.data(Qt.UserRole)
        display = label_cell.text() if label_cell else "item"
        self._queue.remove(uid)
        self.refresh()
        self.item_removed.emit(display)

    def _move_up(self):
        uid = self._selected_uid()
        if uid:
            self._queue.move_up(uid)
            self.refresh()

    def _move_down(self):
        uid = self._selected_uid()
        if uid:
            self._queue.move_down(uid)
            self.refresh()

    def _clear_queue(self):
        self._queue.clear()
        self._table.setRowCount(0)
        self._refresh_count()

    def _check_all_export(self):
        self._table.blockSignals(True)
        for row in range(self._table.rowCount()):
            cell = self._table.item(row, _COL_EXPORT)
            if cell:
                cell.setCheckState(Qt.Checked)
        self._table.blockSignals(False)

    def _on_item_changed(self, item: QTableWidgetItem):
        pass   # no live action needed; export state is read at run time

    def _refresh_count(self):
        n = len(self._queue)
        self._count_lbl.setText(
            f"{n} item{'s' if n != 1 else ''} in queue" if n else "Queue empty"
        )


# ── Helpers ─────────────────────────────────────────────────────────────────────

_STATUS_SYMBOLS_DICT = {
    QueueItemStatus.PENDING: "⏳",
    QueueItemStatus.RUNNING: "▶",
    QueueItemStatus.DONE:    "✓",
    QueueItemStatus.ABORTED: "⊘",
    QueueItemStatus.ERROR:   "✗",
}


def dp_fallback(px: int) -> int:
    """DPI-scaled pixel size; falls back to identity if dpi module unavailable."""
    try:
        from ..dpi import dp
        return dp(px)
    except Exception:
        return px


try:
    from typing import Optional
except ImportError:
    Optional = None  # type: ignore[assignment]
