"""
Base class for all measurement routines.

All measurements run in a QThread subclass and emit progress/data signals
so that the GUI can update plots in real time without blocking.
"""

import logging
import numpy as np
import pandas as pd
from typing import Any, Dict, Optional
from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class MeasurementResult:
    """Container for a completed measurement."""

    def __init__(self, name: str):
        self.name = name
        self.data: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Any] = {}
        self.analysis: Dict[str, Any] = {}

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.data)

    def save_csv(self, path: str):
        self.to_dataframe().to_csv(path, index=False)
        logger.info("Saved: %s", path)

    def save_excel(self, path: str):
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            self.to_dataframe().to_excel(writer, sheet_name="Data", index=False)
            if self.analysis:
                pd.DataFrame([self.analysis]).to_excel(
                    writer, sheet_name="Analysis", index=False
                )
        logger.info("Saved: %s", path)


class BaseMeasurement(QThread):
    """
    QThread-based measurement worker.

    Subclasses override `run()` and call `self.emit_point()` or
    `self.emit_result()` to push data back to the GUI.

    Signals
    -------
    progress    (int 0–100)
    point_ready (dict)   – single data point for real-time plotting
    result_ready(MeasurementResult)
    error       (str)
    status      (str)
    """

    progress     = pyqtSignal(int)
    point_ready  = pyqtSignal(dict)
    result_ready = pyqtSignal(object)
    error        = pyqtSignal(str)
    status       = pyqtSignal(str)

    def __init__(self, instrument, params: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.instrument = instrument
        self.params = params
        self._abort = False
        self.result: Optional[MeasurementResult] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def abort(self):
        """Request abort. The run() loop checks self._abort periodically."""
        self._abort = True
        logger.info("Abort requested")

    def run(self):
        """Override in subclass."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Helpers for subclasses
    # ------------------------------------------------------------------

    def emit_point(self, **kwargs):
        """Emit a single (x, y) or multi-channel data point dict."""
        self.point_ready.emit(kwargs)

    def emit_result(self, result: MeasurementResult):
        self.result = result
        self.result_ready.emit(result)

    def emit_status(self, msg: str):
        self.status.emit(msg)
        logger.info("[%s] %s", self.__class__.__name__, msg)

    def emit_error(self, msg: str):
        self.error.emit(msg)
        logger.error("[%s] %s", self.__class__.__name__, msg)

    def emit_progress(self, pct: int):
        self.progress.emit(max(0, min(100, pct)))
