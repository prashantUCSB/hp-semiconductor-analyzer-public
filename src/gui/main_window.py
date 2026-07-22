"""
Main application window.

Layout
------
  ┌─────────────────────────────────────────────────┐
  │  Menu bar                                        │
  ├─────────────────────────────────────────────────┤
  │  Connection panel (top bar)                      │
  ├──────────────────────────┬──────────────────────┤
  │                          │  Queue dock (right)  │
  │  Measurement tabs        │  (can be hidden /    │
  │                          │   detached)          │
  ├─────────────────────────────────────────────────┤
  │ [status message]              Built by …  v1.x  │
  └─────────────────────────────────────────────────┘
"""

import logging
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QTabWidget, QStatusBar, QFrame, QLabel,
    QDockWidget, QAction, QMenuBar,
)
from PyQt5.QtCore import Qt

from .dpi import dp
from .connection_panel import ConnectionPanel
from .panels.mosfet_panel     import MOSFETPanel
from .panels.diode_panel      import DiodePanel
from .panels.resistor_panel   import ResistorPanel
from .panels.cv_panel         import CVPanel
from .panels.van_der_pauw_panel import VanDerPauwPanel
from .panels.kelvin_panel     import KelvinPanel
from .panels.hall_bar_panel   import HallBarPanel
from .panels.generic_panel    import GenericPanel
from .panels.queue_panel      import QueuePanel
from ..measurements.queue_manager import MeasurementQueue

logger = logging.getLogger(__name__)

APP_TITLE = "HP Semiconductor Analyzer Controller"

try:
    from src.version import __version__, CREDIT
except ImportError:
    try:
        from version import __version__, CREDIT
    except ImportError:
        __version__ = "dev"
        CREDIT = "Built by Prashant Srinivasan  |  dev"


class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._instrument = None
        self._queue      = MeasurementQueue()

        self.setWindowTitle(f"{APP_TITLE}  v{__version__}")
        self.resize(dp(1400), dp(860))

        self._build_ui()
        self._build_menu()
        self._connect_signals()

        logging.basicConfig(level=logging.INFO)

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Connection panel (top bar) ─────────────────────────────────
        self.conn_panel = ConnectionPanel()
        conn_frame = QFrame()
        conn_frame.setFrameShape(QFrame.StyledPanel)
        conn_frame.setStyleSheet(
            "QFrame { background-color: #12121E; "
            "border-bottom: 1px solid #3A3A5E; }"
        )
        cf_layout = QVBoxLayout(conn_frame)
        cf_layout.setContentsMargins(4, 2, 4, 2)
        cf_layout.addWidget(self.conn_panel)
        root.addWidget(conn_frame)

        # ── Measurement tabs ───────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        def inst():
            return self._instrument

        self.panel_mosfet  = MOSFETPanel(inst)
        self.panel_diode   = DiodePanel(inst)
        self.panel_res     = ResistorPanel(inst)
        self.panel_cv      = CVPanel(inst)
        self.panel_vdp     = VanDerPauwPanel(inst)
        self.panel_kelvin  = KelvinPanel(inst)
        self.panel_hall    = HallBarPanel(inst)
        self.panel_generic = GenericPanel(inst)

        self.tabs.addTab(self.panel_mosfet,  "MOSFET")
        self.tabs.addTab(self.panel_diode,   "Diode I-V")
        self.tabs.addTab(self.panel_res,     "Resistor")
        self.tabs.addTab(self.panel_cv,      "C-V (4280A)")
        self.tabs.addTab(self.panel_vdp,     "Van der Pauw")
        self.tabs.addTab(self.panel_kelvin,  "Kelvin 4-Probe")
        self.tabs.addTab(self.panel_hall,    "Hall Bar")
        self.tabs.addTab(self.panel_generic, "Generic 4-Port")

        root.addWidget(self.tabs, stretch=1)

        # ── Status bar ─────────────────────────────────────────────────
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready — connect an instrument to begin.")

        self._credit_label = QLabel(CREDIT)
        self._credit_label.setObjectName("subtext")
        self._credit_label.setContentsMargins(0, 0, dp(8), 0)
        self.status_bar.addPermanentWidget(self._credit_label)

        # ── Queue dock widget (right side, dockable/hideable) ──────────
        self.queue_panel = QueuePanel(self._queue)
        self.queue_dock  = QDockWidget("Measurement Queue", self)
        self.queue_dock.setWidget(self.queue_panel)
        self.queue_dock.setFeatures(
            QDockWidget.DockWidgetMovable |
            QDockWidget.DockWidgetFloatable |
            QDockWidget.DockWidgetClosable
        )
        self.addDockWidget(Qt.RightDockWidgetArea, self.queue_dock)

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu(self):
        mb = self.menuBar()

        # View menu
        view_menu = mb.addMenu("&View")
        toggle_queue = self.queue_dock.toggleViewAction()
        toggle_queue.setText("Measurement &Queue")
        view_menu.addAction(toggle_queue)

        # Help menu
        help_menu = mb.addMenu("&Help")
        wiring_act = QAction("&Wiring Guide…", self)
        wiring_act.setShortcut("F1")
        wiring_act.triggered.connect(self._show_wiring_guide)
        help_menu.addAction(wiring_act)

        about_act = QAction("&About", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self):
        self.conn_panel.instrument_connected.connect(self._on_connected)
        self.conn_panel.instrument_disconnected.connect(self._on_disconnected)
        self.queue_panel.run_queue_requested.connect(self._on_run_queue)
        self.queue_panel.stop_queue_requested.connect(self._on_stop_queue)

    def _on_connected(self, inst):
        self._instrument = inst
        model_str = inst.idn[:100] if inst.idn else inst.resource_string
        self.status_bar.showMessage(f"Connected: {model_str}")

        # Enable / disable the C-V tab based on instrument type
        from ..instruments.hp4280 import HP4280
        from ..instruments.hp4155 import HP4155
        from ..instruments.hp4156 import HP4156

        cv_idx = self.tabs.indexOf(self.panel_cv)
        if isinstance(inst, HP4280):
            self.tabs.setTabEnabled(cv_idx, True)
            self.tabs.setTabToolTip(cv_idx, "")
        else:
            self.tabs.setTabEnabled(cv_idx, False)
            self.tabs.setTabToolTip(cv_idx, "C-V sweep requires HP 4280A")

    def _on_disconnected(self):
        self._instrument = None
        self.status_bar.showMessage("Disconnected.")

    # ------------------------------------------------------------------
    # Queue run/stop
    # ------------------------------------------------------------------

    def _on_run_queue(self):
        if not self._instrument:
            self.status_bar.showMessage("Connect an instrument before running the queue.")
            return
        pending = self._queue.pending_items()
        if not pending:
            self.status_bar.showMessage("Queue is empty — add measurements first.")
            return
        self.queue_panel.set_running(True)
        self._run_next_queued()

    def _run_next_queued(self):
        pending = self._queue.pending_items()
        if not pending:
            self.queue_panel.set_running(False)
            self.status_bar.showMessage("Queue complete.")
            return

        item = pending[0]
        from ..measurements.queue_manager import QueueItemStatus
        item.status = QueueItemStatus.RUNNING
        self.queue_panel.update_item_status(item.uid, QueueItemStatus.RUNNING)
        self.status_bar.showMessage(f"Running: {item.display_label}…")

        worker = item.measurement_class(self._instrument, item.params)
        worker.status.connect(self.status_bar.showMessage)
        worker.result_ready.connect(lambda result, i=item: self._on_item_done(i, result))
        worker.error.connect(lambda msg, i=item: self._on_item_error(i, msg))
        worker.start()
        # Keep a reference so the thread isn't GC'd
        self._current_worker = worker

    def _on_item_done(self, item, result):
        from ..measurements.queue_manager import QueueItemStatus
        item.status = QueueItemStatus.DONE
        item.result = result
        self.queue_panel.update_item_status(item.uid, QueueItemStatus.DONE)

        # Auto-export if checked
        if self.queue_panel.is_export_checked(item.uid):
            self._auto_export(item, result)

        self._run_next_queued()

    def _on_item_error(self, item, msg: str):
        from ..measurements.queue_manager import QueueItemStatus
        item.status    = QueueItemStatus.ERROR
        item.error_msg = msg
        self.queue_panel.update_item_status(item.uid, QueueItemStatus.ERROR)
        self.status_bar.showMessage(f"Error in '{item.display_label}': {msg}")
        self.queue_panel.set_running(False)

    def _on_stop_queue(self):
        if hasattr(self, "_current_worker") and self._current_worker:
            self._current_worker.abort()
        self.queue_panel.set_running(False)
        self.status_bar.showMessage("Queue stopped by user.")

    @staticmethod
    def _auto_export(item, result):
        """Save result to CSV/Excel in a timestamped subdirectory."""
        import os, datetime
        from ..measurements.queue_manager import QueueItemStatus
        if result is None:
            return
        try:
            ts     = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            folder = os.path.join("exports", ts)
            os.makedirs(folder, exist_ok=True)
            name   = item.display_label.replace(" ", "_").replace("/", "-")
            path   = os.path.join(folder, f"{name}.csv")
            result.save_csv(path)
            logger.info("Auto-exported: %s", path)
        except Exception as exc:
            logger.warning("Auto-export failed for %s: %s", item.display_label, exc)

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def _show_wiring_guide(self):
        try:
            from .dialogs.wiring_guide_dialog import WiringGuideDialog
            dlg = WiringGuideDialog(self)
            dlg.show()
        except Exception as exc:
            self.status_bar.showMessage(f"Could not open wiring guide: {exc}")

    def _show_about(self):
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.about(
            self,
            f"About {APP_TITLE}",
            f"<b>{APP_TITLE}</b><br>"
            f"Version {__version__}<br><br>"
            "Supports HP/Agilent 4145A/B, 4155A/B/C, 4156A/B/C, 4280A<br>"
            "GPIB via Keysight 82351B and NI GPIB-USB adapters.<br><br>"
            "Built by Prashant Srinivasan · UCSB TCR"
        )
