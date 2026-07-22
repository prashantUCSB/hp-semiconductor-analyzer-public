"""Resistor I-V panel."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from .base_panel import BasePanel
from .form_helpers import make_dspin, ch_combo, form_group
from ...measurements.resistor_iv import ResistorIVMeasurement


class ResistorPanel(BasePanel):
    plot_xlabel = "V (V)"
    plot_ylabel = "I (A)"
    plot_title  = "Resistor I-V"

    def build_params_widget(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.hi_ch = ch_combo(1)
        self.lo_ch = ch_combo(2)
        layout.addWidget(form_group("Channel Assignment", [
            ("High SMU:", self.hi_ch),
            ("Low SMU:",  self.lo_ch),
        ]))

        self.v_start    = make_dspin(-1.0, -40, 40, suffix="V")
        self.v_stop     = make_dspin( 1.0, -40, 40, suffix="V")
        self.v_step     = make_dspin( 0.05, 0.001, 10, 3, suffix="V")
        layout.addWidget(form_group("Voltage Sweep", [
            ("Start:", self.v_start),
            ("Stop:",  self.v_stop),
            ("Step:",  self.v_step),
        ]))

        self.compliance = make_dspin(0.1, 1e-6, 1.0, 4, suffix="A")
        layout.addWidget(form_group("Compliance", [
            ("Compliance:", self.compliance),
        ]))

        return w

    def get_measurement_params(self) -> dict:
        return {
            "hi_ch":      int(self.hi_ch.currentText()),
            "lo_ch":      int(self.lo_ch.currentText()),
            "v_start":    self.v_start.value(),
            "v_stop":     self.v_stop.value(),
            "v_step":     self.v_step.value(),
            "compliance": self.compliance.value(),
        }

    def make_measurement(self):
        return ResistorIVMeasurement(
            self._instrument_provider(),
            self.get_measurement_params(),
        )
