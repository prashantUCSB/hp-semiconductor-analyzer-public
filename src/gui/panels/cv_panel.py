"""C-V measurement panel (HP 4280A)."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from .base_panel import BasePanel
from .form_helpers import make_dspin, make_combo, make_spin, form_group
from ...measurements.capacitance_cv import CapacitanceCVMeasurement


class CVPanel(BasePanel):
    plot_xlabel = "V_bias (V)"
    plot_ylabel = "C (F)"
    plot_title  = "Capacitance C-V"

    def build_params_widget(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.v_start = make_dspin(-5.0, -100, 100, suffix="V")
        self.v_stop  = make_dspin( 5.0, -100, 100, suffix="V")
        self.v_step  = make_dspin( 0.1,   0.01, 10, 3, suffix="V")
        layout.addWidget(form_group("Bias Sweep", [
            ("Start:", self.v_start),
            ("Stop:",  self.v_stop),
            ("Step:",  self.v_step),
        ]))

        self.mode = make_combo(["CPGP", "CPRP", "CSRS", "CSGS"], "CPGP")
        self.integ = make_combo(["1 (Fast)", "2 (Medium)", "3 (Slow)"], "2 (Medium)")
        self.delay = make_dspin(0.05, 0.0, 10.0, 3, suffix="s")
        layout.addWidget(form_group("Measurement Settings", [
            ("Mode:",        self.mode),
            ("Integration:", self.integ),
            ("Delay/pt:",    self.delay),
        ]))

        self.area = make_dspin(1e-4, 1e-8, 1.0, 8, suffix="cm²")
        layout.addWidget(form_group("Device Parameters", [
            ("Area:", self.area),
        ]))

        return w

    def get_measurement_params(self) -> dict:
        integ_map = {"1 (Fast)": 1, "2 (Medium)": 2, "3 (Slow)": 3}
        return {
            "v_start":     self.v_start.value(),
            "v_stop":      self.v_stop.value(),
            "v_step":      self.v_step.value(),
            "mode":        self.mode.currentText(),
            "integration": integ_map.get(self.integ.currentText(), 2),
            "delay":       self.delay.value(),
            "area_cm2":    self.area.value(),
        }

    def make_measurement(self):
        return CapacitanceCVMeasurement(
            self._instrument_provider(),
            self.get_measurement_params(),
        )
