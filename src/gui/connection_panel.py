"""
Connection Panel — VISA scan, per-instrument rows, and manual GPIB entry.

Mirrors the Keithley-IV suite's InstrumentPanel design adapted for HP
semiconductor analyzers (4145A/B, 4155A/B/C, 4156A/B/C, 4280A).

Architecture
------------
• VISAManager scan runs in a background QThread so the GUI stays responsive.
• Each discovered / manually-added resource gets its own InstrumentRow widget.
• Connecting is also threaded; the row shows a "Connecting…" state while busy.
• Manual entry accepts any VISA resource string and instrument type.

Signals emitted to MainWindow
------------------------------
instrument_connected(instrument_instance)
instrument_disconnected()
"""

import logging
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QPushButton,
    QFrame, QSizePolicy, QGroupBox, QFormLayout, QLineEdit, QScrollArea,
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QPainter

from .dpi import dp
from ..instruments.base_instrument import GPIBInstrument

logger = logging.getLogger(__name__)

# ── Instrument catalogue ────────────────────────────────────────────────────────
# Maps display name → driver class name (resolved at connect time)
INSTRUMENTS = {
    "HP 4145A": "HP4145",
    "HP 4145B": "HP4145",
    "HP 4155A": "HP4155",
    "HP 4155B": "HP4155",
    "HP 4155C": "HP4155",
    "HP 4156A": "HP4156",
    "HP 4156B": "HP4156",
    "HP 4156C": "HP4156",
    "HP 4280A": "HP4280",
}

# Map driver class name → import helper
def _load_driver_class(class_name: str):
    from src.instruments import HP4145, HP4155, HP4156, HP4280
    return {"HP4145": HP4145, "HP4155": HP4155, "HP4156": HP4156, "HP4280": HP4280}[class_name]


# ── Background scan thread ──────────────────────────────────────────────────────

class _ScanWorker(QThread):
    done  = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, skip_resources: "set | None" = None):
        super().__init__()
        self._skip = skip_resources or set()

    def run(self):
        import multiprocessing
        from ..instruments.visa_manager import _scan_in_process

        q = multiprocessing.Queue()
        p = multiprocessing.Process(
            target=_scan_in_process,
            args=(q, list(self._skip)),
            daemon=True,
        )
        p.start()
        p.join(timeout=30)

        if p.is_alive():
            p.terminate()
            p.join(2)
            self.error.emit(
                "VISA scan timed out after 30 s.\n"
                "Check that the GPIB adapter is connected and the driver is installed."
            )
            self.done.emit([])
            return

        if p.exitcode != 0:
            # Subprocess crashed — most likely a native DLL fault (agvisa32.dll).
            self.error.emit(
                f"VISA scan process crashed (exit {p.exitcode}).\n"
                "This usually means the Keysight GPIB driver faulted.\n"
                "Try opening Keysight Connection Expert and scanning for instruments first,\n"
                "then retry the scan here."
            )
            self.done.emit([])
            return

        if q.empty():
            self.done.emit([])
            return

        tag, val = q.get_nowait()
        if tag == "ok":
            self.done.emit(val)
        else:
            logger.error("VISA scan failed: %s", val)
            self.error.emit(val)
            self.done.emit([])


# ── Background connect thread ───────────────────────────────────────────────────

class _ConnectWorker(QThread):
    connected = pyqtSignal(object)   # instrument instance on success
    failed    = pyqtSignal(str)      # error message on failure

    def __init__(self, driver_class_name: str, resource: str, parent=None):
        super().__init__(parent)
        self._driver_class_name = driver_class_name
        self._resource           = resource

    def run(self):
        try:
            cls  = _load_driver_class(self._driver_class_name)
            inst = cls()
            if inst.connect(self._resource):
                self.connected.emit(inst)
            else:
                self.failed.emit(f"connect() returned False for {self._resource}")
        except Exception as exc:
            self.failed.emit(str(exc))


# ── Status LED ──────────────────────────────────────────────────────────────────

class _StatusDot(QLabel):
    """Small coloured circle: grey = idle, green = connected, amber = busy, red = error."""

    _COLORS = {
        "idle":       "#555577",
        "connected":  "#4CAF50",
        "busy":       "#FF9800",
        "error":      "#F44336",
    }

    def __init__(self, parent=None):
        super().__init__("●", parent)
        self.setFixedWidth(dp(16))
        self._set("idle")

    def _set(self, state: str):
        color = self._COLORS.get(state, self._COLORS["idle"])
        self.setStyleSheet(f"color:{color}; font-size:14pt;")

    def set_idle(self):        self._set("idle")
    def set_connected(self):   self._set("connected")
    def set_busy(self):        self._set("busy")
    def set_error(self):       self._set("error")


class _ElidedLabel(QLabel):
    """QLabel that truncates overflowing text with '…'."""

    def paintEvent(self, event):
        painter = QPainter(self)
        metrics = self.fontMetrics()
        elided  = metrics.elidedText(self.text(), Qt.ElideRight, self.width())
        painter.drawText(self.rect(), int(self.alignment()), elided)


# ── Per-instrument row ──────────────────────────────────────────────────────────

class InstrumentRow(QWidget):
    """One row in the instrument list: dot · name · address · Connect button."""

    connect_requested    = pyqtSignal(str, str)   # resource_string, driver_class_name
    disconnect_requested = pyqtSignal(str)         # resource_string

    def __init__(
        self,
        resource_string: str,
        friendly: str,
        driver_class_name: str,
        idn: str = "",
        is_hp: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.resource_string  = resource_string
        self.driver_class_name = driver_class_name
        self.idn              = idn
        self.is_hp            = is_hp
        self._connected       = False
        self._thread: Optional[_ConnectWorker] = None
        self._build_ui(friendly)

    def _build_ui(self, friendly: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        self._dot = _StatusDot()
        layout.addWidget(self._dot)

        info = QVBoxLayout()
        info.setSpacing(0)
        self._name_lbl = _ElidedLabel(friendly)
        self._name_lbl.setStyleSheet("font-weight:600;")
        addr_text = self.idn[:48] if self.idn else self.resource_string
        self._addr_lbl = _ElidedLabel(addr_text)
        self._addr_lbl.setStyleSheet("font-size:8pt; color:#888;")
        info.addWidget(self._name_lbl)
        info.addWidget(self._addr_lbl)
        layout.addLayout(info, stretch=1)

        self._btn = QPushButton("Connect" if self.is_hp else "—")
        self._btn.setMinimumWidth(dp(90))
        if self.is_hp:
            self._btn.clicked.connect(self._on_button)
        else:
            self._btn.setEnabled(False)
        layout.addWidget(self._btn)

    # ------------------------------------------------------------------
    # Connect / disconnect
    # ------------------------------------------------------------------

    def _on_button(self):
        if self._connected:
            self.disconnect_requested.emit(self.resource_string)
        else:
            self._start_connect()

    def _start_connect(self):
        if not self.driver_class_name:
            return
        self._dot.set_busy()
        self._btn.setEnabled(False)
        self._name_lbl.setText("Connecting…")

        self._thread = _ConnectWorker(self.driver_class_name, self.resource_string, self)
        self._thread.connected.connect(self._on_connected)
        self._thread.failed.connect(self._on_failed)
        self._thread.start()

    def _on_connected(self, inst):
        self._connected = True
        self._dot.set_connected()
        self._btn.setText("Disconnect")
        self._btn.setEnabled(True)
        label = inst.idn[:60] if inst.idn else self.resource_string
        self._name_lbl.setText(label)
        self._addr_lbl.setText(self.resource_string)
        # Bubble up to ConnectionPanel via the signal
        self.connect_requested.emit(self.resource_string, self.driver_class_name)

    def _on_failed(self, msg: str):
        self._dot.set_error()
        self._btn.setText("Retry")
        self._btn.setEnabled(True)
        self._name_lbl.setText("Connection failed")
        self._addr_lbl.setText(msg[:72])

    def set_disconnected(self):
        self._connected = False
        self._dot.set_idle()
        self._btn.setText("Connect")
        self._btn.setEnabled(True)
        self._name_lbl.setText(self.resource_string)
        self._addr_lbl.setText(self.idn[:48] if self.idn else self.resource_string)

    # ------------------------------------------------------------------
    # The _on_connected signal is re-emitted by ConnectionPanel after it
    # actually connects the instrument; this row just owns the thread.
    # We need to pass the instrument instance back to the panel via a different path.
    # Use a private callback instead.
    # ------------------------------------------------------------------

    def start_connect_with_callback(self, on_connected, on_failed):
        """Start the connect thread; call on_connected(inst) or on_failed(msg) on completion."""
        self._dot.set_busy()
        self._btn.setEnabled(False)
        self._name_lbl.setText("Connecting…")

        self._thread = _ConnectWorker(self.driver_class_name, self.resource_string, self)
        self._thread.connected.connect(lambda inst: self._connected_cb(inst, on_connected))
        self._thread.failed.connect(lambda msg: self._failed_cb(msg, on_failed))
        self._thread.start()

    def _connected_cb(self, inst, callback):
        self._connected = True
        self._dot.set_connected()
        self._btn.setText("Disconnect")
        self._btn.setEnabled(True)
        label = inst.idn[:60] if inst.idn else self.resource_string
        self._name_lbl.setText(label)
        self._addr_lbl.setText(self.resource_string)
        callback(inst)

    def _failed_cb(self, msg: str, callback):
        self._dot.set_error()
        self._btn.setText("Retry")
        self._btn.setEnabled(True)
        self._name_lbl.setText("Connection failed")
        self._addr_lbl.setText(msg[:72])
        callback(msg)


# ── Main ConnectionPanel widget ─────────────────────────────────────────────────

class ConnectionPanel(QWidget):
    """
    Top-bar / side-panel for VISA instrument management.

    Signals
    -------
    instrument_connected(instrument_instance)
    instrument_disconnected()
    """

    instrument_connected    = pyqtSignal(object)
    instrument_disconnected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._instrument   = None
        self._rows: dict[str, InstrumentRow] = {}
        self._resources: dict[str, dict]     = {}
        self._scan_worker: Optional[_ScanWorker] = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 4, 6, 4)
        root.setSpacing(6)

        # ── Scan row ──────────────────────────────────────────────────
        scan_row = QHBoxLayout()
        self.btn_scan = QPushButton("⟳  Scan VISA")
        self.btn_scan.setMinimumWidth(dp(100))
        self.btn_scan.clicked.connect(self._on_scan)
        scan_row.addWidget(self.btn_scan)

        self.btn_bus_reset = QPushButton("Bus Reset")
        self.btn_bus_reset.setMinimumWidth(dp(90))
        self.btn_bus_reset.setToolTip(
            "Send GPIB Device Clear + Interface Clear to the connected instrument.\n"
            "Use after a measurement timeout or communication error."
        )
        self.btn_bus_reset.clicked.connect(self._on_bus_reset)
        self.btn_bus_reset.setEnabled(False)
        scan_row.addWidget(self.btn_bus_reset)
        scan_row.addStretch()
        root.addLayout(scan_row)

        # ── Manual entry ───────────────────────────────────────────────
        manual_box = QGroupBox("Manual Entry")
        mf = QFormLayout(manual_box)
        mf.setSpacing(4)
        mf.setContentsMargins(6, 6, 6, 6)

        self._manual_addr = QLineEdit()
        self._manual_addr.setPlaceholderText("GPIB0::17::INSTR")
        mf.addRow("VISA resource:", self._manual_addr)

        self._manual_model = QComboBox()
        self._manual_model.addItems(list(INSTRUMENTS.keys()))
        mf.addRow("Instrument:", self._manual_model)

        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._on_manual_add)
        mf.addRow("", add_btn)

        root.addWidget(manual_box)

        # ── Instrument list ────────────────────────────────────────────
        list_box = QGroupBox("Discovered / Added Instruments")
        lb_layout = QVBoxLayout(list_box)
        lb_layout.setContentsMargins(4, 4, 4, 4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self._list_container = QWidget()
        self._list_layout    = QVBoxLayout(self._list_container)
        self._list_layout.setAlignment(Qt.AlignTop)
        self._list_layout.setSpacing(2)
        self._list_layout.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self._list_container)
        lb_layout.addWidget(scroll)
        root.addWidget(list_box, stretch=1)

        # ── Status / IDN ───────────────────────────────────────────────
        status_row = QHBoxLayout()
        self._dot = _StatusDot()
        status_row.addWidget(self._dot)
        self._lbl_status = QLabel("Not connected — click Scan VISA or add manually.")
        self._lbl_status.setObjectName("subtext")
        self._lbl_status.setWordWrap(True)
        status_row.addWidget(self._lbl_status, stretch=1)
        root.addLayout(status_row)

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------

    def _on_scan(self):
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("Scanning…")
        self._lbl_status.setText("Scanning VISA bus for HP instruments…")

        connected_rstrings: set = set()
        if self._instrument and hasattr(self._instrument, "_res") and self._instrument._res:
            try:
                connected_rstrings.add(str(self._instrument._res.resource_name))
            except Exception:
                pass

        self._scan_worker = _ScanWorker(skip_resources=connected_rstrings)
        self._scan_worker.done.connect(self._on_scan_done)
        self._scan_worker.error.connect(lambda msg: self._lbl_status.setText(f"Scan error: {msg}"))
        self._scan_worker.start()

    def _on_scan_done(self, results: list):
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("⟳  Scan VISA")

        new_count = 0
        for info in results:
            rstr = info["resource_string"]
            if rstr in self._rows:
                continue
            self._resources[rstr] = info
            # Auto-detect driver class from IDN; fall back to first HP instrument
            driver = self._driver_from_info(info)
            if driver is None:
                driver = "HP4156"   # sensible default for unknown HP GPIB device
            self._add_row(
                rstr,
                info.get("friendly", rstr),
                driver,
                idn=info.get("idn", ""),
                is_hp=info.get("is_hp_analyzer", True),
            )
            new_count += 1

        total = len(self._rows)
        if total == 0:
            self._lbl_status.setText(
                "No VISA instruments found.\n"
                "Verify NI-VISA or Keysight IO Libraries are installed,\n"
                "the GPIB adapter is connected, and the instrument is powered on."
            )
        else:
            added = f" ({new_count} new)" if new_count else " (already listed)"
            self._lbl_status.setText(f"{total} instrument(s) found{added}.")

    @staticmethod
    def _driver_from_info(info: dict) -> Optional[str]:
        idn = info.get("idn", "").upper()
        for key, cls in (
            ("4145B", "HP4145"), ("4145A", "HP4145"),
            ("4155", "HP4155"),
            ("4156", "HP4156"),
            ("4280", "HP4280"),
        ):
            if key in idn:
                return cls
        return None

    # ------------------------------------------------------------------
    # Manual add
    # ------------------------------------------------------------------

    def _on_manual_add(self):
        rstr = self._manual_addr.text().strip()
        if not rstr:
            return
        model_name   = self._manual_model.currentText()
        driver_class = INSTRUMENTS.get(model_name, "HP4156")
        info = {
            "resource_string": rstr,
            "interface": "Manual",
            "friendly": model_name,
            "idn": "",
            "is_hp_analyzer": True,
        }
        self._resources[rstr] = info
        if rstr not in self._rows:
            self._add_row(rstr, model_name, driver_class, idn="", is_hp=True)
        self._manual_addr.clear()

    # ------------------------------------------------------------------
    # Row management
    # ------------------------------------------------------------------

    def _add_row(
        self,
        resource_string: str,
        friendly: str,
        driver_class_name: str,
        idn: str = "",
        is_hp: bool = True,
    ):
        row = InstrumentRow(
            resource_string, friendly, driver_class_name,
            idn=idn, is_hp=is_hp
        )
        row.start_connect_with_callback(
            lambda inst: self._on_row_connected(inst),
            lambda msg:  self._on_row_failed(msg),
        )
        # Disconnect button connects back here
        self._rows[resource_string] = row
        self._list_layout.addWidget(row)

        # Wire the actual connect via direct button signal
        # (InstrumentRow._btn click → start_connect_with_callback was set above,
        # but _on_button doesn't know about the callback — need to rewire)
        # Override the button click:
        btn = row._btn
        btn.clicked.disconnect()
        btn.clicked.connect(
            lambda checked=False, r=row: self._row_button_clicked(r)
        )

    def _row_button_clicked(self, row: InstrumentRow):
        if row._connected:
            self._disconnect_row(row)
        else:
            row.start_connect_with_callback(
                lambda inst: self._on_row_connected(inst),
                lambda msg:  self._on_row_failed(msg),
            )

    def _on_row_connected(self, inst):
        self._instrument = inst
        self._dot.set_connected()
        self._lbl_status.setText(f"Connected: {inst.idn[:100] if inst.idn else inst.resource_string}")
        self.btn_bus_reset.setEnabled(True)
        self.instrument_connected.emit(inst)

    def _on_row_failed(self, msg: str):
        self._lbl_status.setText(f"Connection error: {msg}")

    def _disconnect_row(self, row: InstrumentRow):
        if self._instrument:
            try:
                self._instrument.disconnect()
            except Exception:
                pass
            self._instrument = None
        row.set_disconnected()
        self._dot.set_idle()
        self._lbl_status.setText("Disconnected.")
        self.btn_bus_reset.setEnabled(False)
        self.instrument_disconnected.emit()

    # ------------------------------------------------------------------
    # Bus reset
    # ------------------------------------------------------------------

    def _on_bus_reset(self):
        if self._instrument and self._instrument.connected:
            try:
                self._instrument.bus_reset()
                self._lbl_status.setText("GPIB bus reset sent (SDC + IFC + *CLS).")
            except Exception as exc:
                self._lbl_status.setText(f"Bus reset failed: {exc}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def instrument(self):
        return self._instrument
