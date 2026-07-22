"""Diode I-V panel."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from .base_panel import BasePanel
from .form_helpers import make_dspin, ch_combo, form_group
from ...measurements.diode_iv import DiodeIVMeasurement


class DiodePanel(BasePanel):
    plot_xlabel = "V (V)"
    plot_ylabel = "I (A)"
    plot_title  = "Diode I-V"

    def build_params_widget(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.anode_ch   = ch_combo(1)
        self.cathode_ch = ch_combo(2)
        layout.addWidget(form_group("Channel Assignment", [
            ("Anode SMU:",   self.anode_ch),
            ("Cathode SMU:", self.cathode_ch),
        ]))

        self.v_start    = make_dspin(-1.0, -40, 40, suffix="V")
        self.v_stop     = make_dspin( 1.2, -40, 40, suffix="V")
        self.v_step     = make_dspin( 0.02, 0.001, 10, 3, suffix="V")
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
            "anode_ch":   int(self.anode_ch.currentText()),
            "cathode_ch": int(self.cathode_ch.currentText()),
            "v_start":    self.v_start.value(),
            "v_stop":     self.v_stop.value(),
            "v_step":     self.v_step.value(),
            "compliance": self.compliance.value(),
        }

    def make_measurement(self):
        return DiodeIVMeasurement(
            self._instrument_provider(),
            self.get_measurement_params(),
        )
