"""Van der Pauw sheet resistance + Hall panel."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from .base_panel import BasePanel
from .form_helpers import make_dspin, make_spin, ch_combo, form_group
from ...measurements.van_der_pauw import VanDerPauwMeasurement


class VanDerPauwPanel(BasePanel):
    plot_xlabel = "Configuration"
    plot_ylabel = "Resistance (Ω)"
    plot_title  = "Van der Pauw"

    def build_params_widget(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.ch_a = ch_combo(1)
        self.ch_b = ch_combo(2)
        self.ch_c = ch_combo(3)
        self.ch_d = ch_combo(4)
        layout.addWidget(form_group("Contacts (clockwise)", [
            ("Contact A (SMU):", self.ch_a),
            ("Contact B (SMU):", self.ch_b),
            ("Contact C (SMU):", self.ch_c),
            ("Contact D (SMU):", self.ch_d),
        ]))

        self.current    = make_dspin(1e-3, 1e-9, 0.1, 9, suffix="A")
        self.comp_v     = make_dspin(10.0, 0.01, 200, suffix="V")
        self.n_averages = make_spin(3, 1, 20)
        layout.addWidget(form_group("Measurement Settings", [
            ("Source current:", self.current),
            ("Compliance V:",   self.comp_v),
            ("# Averages:",     self.n_averages),
        ]))

        self.b_field    = make_dspin(0.0, -10, 10, 4, suffix="T")
        layout.addWidget(form_group("Hall (optional)", [
            ("B-field:", self.b_field),
        ]))

        return w

    def get_measurement_params(self) -> dict:
        return {
            "ch_a":              int(self.ch_a.currentText()),
            "ch_b":              int(self.ch_b.currentText()),
            "ch_c":              int(self.ch_c.currentText()),
            "ch_d":              int(self.ch_d.currentText()),
            "current":           self.current.value(),
            "compliance_v":      self.comp_v.value(),
            "n_averages":        self.n_averages.value(),
            "magnetic_field_T":  self.b_field.value(),
        }

    def make_measurement(self):
        return VanDerPauwMeasurement(
            self._instrument_provider(),
            self.get_measurement_params(),
        )
