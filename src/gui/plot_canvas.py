"""
Matplotlib canvas embedded in a QWidget.

Supports:
  - Multiple series with auto-color cycling
  - Linear / log Y-axis toggle
  - Cursor crosshair with coordinate readout
  - Export to PNG
"""

import numpy as np
import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib import rcParams

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QLabel
from PyQt5.QtCore import Qt

# Match plot style to the dark UI
rcParams.update({
    "figure.facecolor":  "#1E1E2E",
    "axes.facecolor":    "#12121E",
    "axes.edgecolor":    "#3A3A5E",
    "axes.labelcolor":   "#CDD6F4",
    "text.color":        "#CDD6F4",
    "xtick.color":       "#CDD6F4",
    "ytick.color":       "#CDD6F4",
    "grid.color":        "#2A2A4A",
    "grid.linestyle":    "--",
    "grid.alpha":        0.5,
    "legend.facecolor":  "#2A2A3E",
    "legend.edgecolor":  "#3A3A5E",
    "legend.labelcolor": "#CDD6F4",
    "lines.linewidth":   1.5,
})

COLORS = [
    "#2196F3", "#F44336", "#4CAF50", "#FF9800",
    "#9C27B0", "#00BCD4", "#FFEB3B", "#E91E63",
]


class PlotCanvas(QWidget):
    """
    A Matplotlib figure embedded in a Qt widget.

    Usage:
        canvas = PlotCanvas()
        canvas.add_point("Id", x=0.1, y=1e-6)
        canvas.add_point("Id", x=0.2, y=2e-6)
        canvas.set_labels("Vgs (V)", "Id (A)")
        canvas.draw()
    """

    def __init__(self, parent=None, xlabel="X", ylabel="Y", title=""):
        super().__init__(parent)
        self._series: dict = {}          # name → (x_list, y_list, color)
        self._color_idx = 0
        self._log_y = False
        self._xlabel = xlabel
        self._ylabel = ylabel
        self._title  = title

        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_point(self, series: str, x: float, y: float, **kwargs):
        """Append a single point to a named series and refresh the plot."""
        if series not in self._series:
            color = COLORS[self._color_idx % len(COLORS)]
            self._color_idx += 1
            self._series[series] = {"x": [], "y": [], "color": color}
        self._series[series]["x"].append(x)
        self._series[series]["y"].append(y)
        self._refresh()

    def set_data(self, series: str, x: np.ndarray, y: np.ndarray):
        """Replace data for a named series."""
        if series not in self._series:
            color = COLORS[self._color_idx % len(COLORS)]
            self._color_idx += 1
            self._series[series] = {"x": [], "y": [], "color": color}
        self._series[series]["x"] = list(x)
        self._series[series]["y"] = list(y)
        self._refresh()

    def clear(self):
        self._series.clear()
        self._color_idx = 0
        self._refresh()

    def set_labels(self, xlabel: str = "", ylabel: str = "", title: str = ""):
        self._xlabel = xlabel or self._xlabel
        self._ylabel = ylabel or self._ylabel
        self._title  = title  or self._title
        self._refresh()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Toolbar row
        toolbar_row = QHBoxLayout()

        self.chk_logy = QCheckBox("Log Y")
        self.chk_logy.setChecked(False)
        self.chk_logy.stateChanged.connect(self._toggle_logy)
        toolbar_row.addWidget(self.chk_logy)

        self.chk_logx = QCheckBox("Log X")
        self.chk_logx.setChecked(False)
        self.chk_logx.stateChanged.connect(self._refresh)
        toolbar_row.addWidget(self.chk_logx)

        toolbar_row.addStretch()

        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self.clear)
        toolbar_row.addWidget(btn_clear)

        btn_save = QPushButton("Save PNG")
        btn_save.clicked.connect(self._save_png)
        toolbar_row.addWidget(btn_save)

        layout.addLayout(toolbar_row)

        # Matplotlib figure
        self.fig = Figure(figsize=(6, 4), tight_layout=True)
        self.ax  = self.fig.add_subplot(111)
        self.canvas = FigureCanvasQTAgg(self.fig)
        from .dpi import dp
        self.canvas.setMinimumHeight(dp(280))
        layout.addWidget(self.canvas)

        # Nav toolbar
        self.nav = NavigationToolbar2QT(self.canvas, self)
        self.nav.setStyleSheet("background: transparent; color: #CDD6F4;")
        layout.addWidget(self.nav)

        # Coordinate label
        self.coord_label = QLabel("")
        self.coord_label.setObjectName("subtext")
        layout.addWidget(self.coord_label)
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)

    # ------------------------------------------------------------------

    def _toggle_logy(self):
        self._log_y = self.chk_logy.isChecked()
        self._refresh()

    def _refresh(self):
        self.ax.cla()
        self.ax.set_facecolor("#12121E")
        self.ax.grid(True)

        for name, s in self._series.items():
            x = np.array(s["x"])
            y = np.array(s["y"])
            if len(x) == 0:
                continue
            if self._log_y and self.chk_logy.isChecked():
                mask = np.abs(y) > 0
                if mask.any():
                    self.ax.semilogy(x[mask], np.abs(y[mask]),
                                     color=s["color"], label=name)
            elif self.chk_logx.isChecked():
                mask = x > 0
                if mask.any():
                    self.ax.semilogx(x[mask], y[mask],
                                     color=s["color"], label=name)
            else:
                self.ax.plot(x, y, color=s["color"], label=name)

        if self._xlabel:
            self.ax.set_xlabel(self._xlabel)
        if self._ylabel:
            self.ax.set_ylabel(self._ylabel)
        if self._title:
            self.ax.set_title(self._title, fontsize=10, fontweight="bold")
        if self._series:
            self.ax.legend(fontsize=8, loc="best")

        self.canvas.draw_idle()

    def _on_mouse_move(self, event):
        if event.inaxes:
            self.coord_label.setText(
                f"  x = {event.xdata:.5g}   y = {event.ydata:.5g}"
            )

    def _save_png(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", "plot.png", "PNG files (*.png)"
        )
        if path:
            self.fig.savefig(path, dpi=150, bbox_inches="tight",
                             facecolor=self.fig.get_facecolor())
