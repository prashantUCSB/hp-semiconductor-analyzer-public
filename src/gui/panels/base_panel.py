"""
Base class for all measurement panels.

Layout:
  ┌──────────────────────────────────────────────────────┐
  │  [Run]  [Abort]   ████████░░  50%   status text      │  ← control bar
  ├────────────────────────┬─────────────────────────────┤
  │                        │                             │
  │  parameter inputs      │      plot canvas            │
  │  (left panel)          │                             │
  │                        │                             │
  ├────────────────────────┴─────────────────────────────┤
  │  results / export                                     │
  └──────────────────────────────────────────────────────┘
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QProgressBar, QLabel,
)
from PyQt5.QtCore import Qt
from ..dpi import dp

from ..plot_canvas import PlotCanvas
from ..results_table import ResultsPanel

logger = logging.getLogger(__name__)


class BasePanel(QWidget):
    """
    Subclasses must implement:
      - build_params_widget() → QWidget   (parameter input form)
      - get_measurement_params() → dict   (read form values)
      - make_measurement()     → BaseMeasurement instance
      - plot_xlabel, plot_ylabel, plot_title class attributes
    """

    plot_xlabel = "X"
    plot_ylabel = "Y"
    plot_title  = "Measurement"

    def __init__(self, instrument_provider, parent=None):
        """
        instrument_provider : callable returning the current instrument (or None)
        """
        super().__init__(parent)
        self._instrument_provider = instrument_provider
        self._worker = None
        self._build_base_ui()

    # ------------------------------------------------------------------
    # Build base layout
    # ------------------------------------------------------------------

    def _build_base_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)

        # ── Control bar ────────────────────────────────────────────────
        ctrl = QHBoxLayout()
        self.btn_run   = QPushButton("Run")
        self.btn_abort = QPushButton("Abort")
        self.btn_abort.setObjectName("danger")
        self.btn_abort.setEnabled(False)
        self.btn_run.clicked.connect(self._start_measurement)
        self.btn_abort.clicked.connect(self._abort_measurement)
        ctrl.addWidget(self.btn_run)
        ctrl.addWidget(self.btn_abort)

        self.progress = QProgressBar()
        self.progress.setMinimumWidth(dp(160))
        self.progress.setMaximumWidth(dp(260))
        self.progress.setRange(0, 100)
        ctrl.addWidget(self.progress)

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("subtext")
        ctrl.addWidget(self.lbl_status, stretch=1)
        root.addLayout(ctrl)

        # ── Main splitter (params | plot) ──────────────────────────────
        h_split = QSplitter(Qt.Horizontal)
        h_split.setHandleWidth(4)

        # Left: parameter widget (to be created by subclass)
        self._params_widget = self.build_params_widget()
        left_scroll = QWidget()
        left_layout = QVBoxLayout(left_scroll)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self._params_widget)
        left_layout.addStretch()
        left_scroll.setMinimumWidth(dp(240))
        left_scroll.setMaximumWidth(dp(360))
        h_split.addWidget(left_scroll)

        # Right: plot
        self.plot = PlotCanvas(
            xlabel=self.plot_xlabel,
            ylabel=self.plot_ylabel,
            title=self.plot_title,
        )
        h_split.addWidget(self.plot)
        h_split.setStretchFactor(0, 0)
        h_split.setStretchFactor(1, 1)
        root.addWidget(h_split, stretch=1)

        # ── Results panel ──────────────────────────────────────────────
        self.results = ResultsPanel()
        self.results.setMinimumHeight(dp(140))
        self.results.setMaximumHeight(dp(220))
        root.addWidget(self.results)

    # ------------------------------------------------------------------
    # Subclass interface
    # ------------------------------------------------------------------

    def build_params_widget(self) -> QWidget:
        """Return the parameter input widget."""
        raise NotImplementedError

    def get_measurement_params(self) -> dict:
        """Read form values and return params dict."""
        raise NotImplementedError

    def make_measurement(self):
        """Return a configured BaseMeasurement instance."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Measurement control
    # ------------------------------------------------------------------

    def _start_measurement(self):
        inst = self._instrument_provider()
        if inst is None:
            self.lbl_status.setText("No instrument connected!")
            return

        self.plot.clear()
        self.progress.setValue(0)
        self.btn_run.setEnabled(False)
        self.btn_abort.setEnabled(True)

        try:
            worker = self.make_measurement()
        except Exception as exc:
            self.lbl_status.setText(f"Config error: {exc}")
            self.btn_run.setEnabled(True)
            self.btn_abort.setEnabled(False)
            return

        self._worker = worker
        worker.progress.connect(self.progress.setValue)
        worker.status.connect(self.lbl_status.setText)
        worker.error.connect(self._on_error)
        worker.point_ready.connect(self._on_point)
        worker.result_ready.connect(self._on_result)
        worker.finished.connect(self._on_finished)
        worker.start()

    def _abort_measurement(self):
        if self._worker:
            self._worker.abort()
            self.lbl_status.setText("Aborting…")

    def _on_point(self, data: dict):
        """Live data update – add one point to the plot."""
        x = data.get("x", 0)
        y = data.get("y", 0)
        series = data.get("series", "data")
        self.plot.add_point(series, x, y)

    def _on_result(self, result):
        self.results.display_result(result)

    def _on_error(self, msg: str):
        self.lbl_status.setText(f"Error: {msg}")
        logger.error(msg)

    def _on_finished(self):
        self.btn_run.setEnabled(True)
        self.btn_abort.setEnabled(False)
        self._worker = None
