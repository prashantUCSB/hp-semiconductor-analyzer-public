"""
MOSFET measurement panel.
Tabs: Transfer Curve | Output Curve
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget,
)

from .base_panel import BasePanel
from .form_helpers import (
    make_dspin, make_spin, make_combo, ch_combo, form_group,
)
from ...measurements.mosfet import MOSFETTransferMeasurement, MOSFETOutputMeasurement


# ── Transfer Curve Panel ──────────────────────────────────────────────────────

class TransferCurvePanel(BasePanel):
    plot_xlabel = "Vgs (V)"
    plot_ylabel = "Id (A)"
    plot_title  = "MOSFET Transfer Curve"

    def build_params_widget(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Channel assignment
        self.gate_ch   = ch_combo(1)
        self.drain_ch  = ch_combo(2)
        self.source_ch = ch_combo(3)
        gb_ch = form_group("Channel Assignment", [
            ("Gate SMU:",   self.gate_ch),
            ("Drain SMU:",  self.drain_ch),
            ("Source SMU:", self.source_ch),
        ])
        layout.addWidget(gb_ch)

        # Vgs sweep
        self.vgs_start = make_dspin(-2.0, -40, 40, suffix="V")
        self.vgs_stop  = make_dspin( 2.0, -40, 40, suffix="V")
        self.vgs_step  = make_dspin( 0.05, 0.001, 10, 3, suffix="V")
        gb_vgs = form_group("Vgs Sweep", [
            ("Start:", self.vgs_start),
            ("Stop:",  self.vgs_stop),
            ("Step:",  self.vgs_step),
        ])
        layout.addWidget(gb_vgs)

        # Bias
        self.vds_bias = make_dspin(0.05, -40, 40, suffix="V")
        self.vgs_comp = make_dspin(0.01, 1e-6, 1.0, 6, suffix="A")
        self.vds_comp = make_dspin(0.1, 1e-6, 1.0, 4, suffix="A")
        gb_bias = form_group("Bias / Compliance", [
            ("Vds (fixed):",  self.vds_bias),
            ("Vgs compliance:", self.vgs_comp),
            ("Vds compliance:", self.vds_comp),
        ])
        layout.addWidget(gb_bias)

        # Options
        self.vth_method = make_combo(["linear", "sqrt", "constant"], "linear")
        gb_opt = form_group("Analysis Options", [
            ("Vth method:", self.vth_method),
        ])
        layout.addWidget(gb_opt)

        return w

    def get_measurement_params(self) -> dict:
        return {
            "gate_ch":       int(self.gate_ch.currentText()),
            "drain_ch":      int(self.drain_ch.currentText()),
            "source_ch":     int(self.source_ch.currentText()),
            "vgs_start":     self.vgs_start.value(),
            "vgs_stop":      self.vgs_stop.value(),
            "vgs_step":      self.vgs_step.value(),
            "vds":           self.vds_bias.value(),
            "vgs_compliance": self.vgs_comp.value(),
            "vds_compliance": self.vds_comp.value(),
            "vth_method":    self.vth_method.currentText(),
        }

    def make_measurement(self):
        return MOSFETTransferMeasurement(
            self._instrument_provider(),
            self.get_measurement_params(),
        )


# ── Output Curve Panel ────────────────────────────────────────────────────────

class OutputCurvePanel(BasePanel):
    plot_xlabel = "Vds (V)"
    plot_ylabel = "Id (A)"
    plot_title  = "MOSFET Output Curve"

    def build_params_widget(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.gate_ch   = ch_combo(1)
        self.drain_ch  = ch_combo(2)
        self.source_ch = ch_combo(3)
        layout.addWidget(form_group("Channel Assignment", [
            ("Gate SMU:",   self.gate_ch),
            ("Drain SMU:",  self.drain_ch),
            ("Source SMU:", self.source_ch),
        ]))

        self.vds_start = make_dspin(0.0, -40, 40, suffix="V")
        self.vds_stop  = make_dspin(2.0, -40, 40, suffix="V")
        self.vds_step  = make_dspin(0.05, 0.001, 10, 3, suffix="V")
        layout.addWidget(form_group("Vds Sweep", [
            ("Start:", self.vds_start),
            ("Stop:",  self.vds_stop),
            ("Step:",  self.vds_step),
        ]))

        self.vgs_start  = make_dspin(0.5, -40, 40, suffix="V")
        self.vgs_stop   = make_dspin(2.0, -40, 40, suffix="V")
        self.vgs_nstep  = make_spin(5, 1, 99)
        layout.addWidget(form_group("Vgs Steps", [
            ("Vgs start:", self.vgs_start),
            ("Vgs stop:",  self.vgs_stop),
            ("# steps:",   self.vgs_nstep),
        ]))

        self.vds_comp = make_dspin(0.1, 1e-6, 1.0, 4, suffix="A")
        self.vgs_comp = make_dspin(0.01, 1e-6, 1.0, 6, suffix="A")
        layout.addWidget(form_group("Compliance", [
            ("Vds compliance:", self.vds_comp),
            ("Vgs compliance:", self.vgs_comp),
        ]))

        return w

    def get_measurement_params(self) -> dict:
        return {
            "drain_ch":      int(self.drain_ch.currentText()),
            "gate_ch":       int(self.gate_ch.currentText()),
            "source_ch":     int(self.source_ch.currentText()),
            "vds_start":     self.vds_start.value(),
            "vds_stop":      self.vds_stop.value(),
            "vds_step":      self.vds_step.value(),
            "vgs_start":     self.vgs_start.value(),
            "vgs_stop":      self.vgs_stop.value(),
            "vgs_nstep":     self.vgs_nstep.value(),
            "vds_compliance": self.vds_comp.value(),
            "vgs_compliance": self.vgs_comp.value(),
        }

    def make_measurement(self):
        return MOSFETOutputMeasurement(
            self._instrument_provider(),
            self.get_measurement_params(),
        )


# ── Combined MOSFET tab widget ────────────────────────────────────────────────

class MOSFETPanel(QWidget):
    """Container with Transfer and Output sub-tabs."""

    def __init__(self, instrument_provider, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        tabs.addTab(TransferCurvePanel(instrument_provider), "Transfer Curve")
        tabs.addTab(OutputCurvePanel(instrument_provider),   "Output Curve")
        layout.addWidget(tabs)
