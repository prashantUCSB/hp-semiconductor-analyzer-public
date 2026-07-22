"""Hall bar measurement panel."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from .base_panel import BasePanel
from .form_helpers import make_dspin, make_spin, ch_combo, form_group
from ...measurements.hall_bar import HallBarMeasurement


class HallBarPanel(BasePanel):
    plot_xlabel = "Measurement"
    plot_ylabel = "Resistance (Ω)"
    plot_title  = "Hall Bar"

    def build_params_widget(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.force_hi = ch_combo(1)
        self.force_lo = ch_combo(2)
        self.long_hi  = ch_combo(3)
        self.long_lo  = ch_combo(4)
        layout.addWidget(form_group("Current Contacts", [
            ("I+ (SMU):", self.force_hi),
            ("I- (SMU):", self.force_lo),
        ]))

        self.hall_hi = ch_combo(3)
        self.hall_lo = ch_combo(4)
        # Reuse long_hi/lo for longitudinal, hall_hi/lo for transverse
        layout.addWidget(form_group("Voltage Contacts", [
            ("Longitudinal V+ (SMU):", self.long_hi),
            ("Longitudinal V- (SMU):", self.long_lo),
            ("Hall V+ (SMU):",         self.hall_hi),
            ("Hall V- (SMU):",         self.hall_lo),
        ]))

        self.current  = make_dspin(1e-4, 1e-9, 0.1, 9, suffix="A")
        self.comp_v   = make_dspin(10.0, 0.01, 200, suffix="V")
        self.b_field  = make_dspin(0.1, -20, 20, 4, suffix="T")
        self.n_avg    = make_spin(5, 1, 50)
        layout.addWidget(form_group("Measurement Settings", [
            ("Source current:", self.current),
            ("Compliance V:",   self.comp_v),
            ("B-field:",        self.b_field),
            ("# Averages:",     self.n_avg),
        ]))

        self.bar_length = make_dspin(100.0, 1, 10000, 1, suffix="µm")
        self.bar_width  = make_dspin(20.0,  1, 10000, 1, suffix="µm")
        self.thickness  = make_dspin(0.0,   0, 10000, 1, suffix="nm")
        layout.addWidget(form_group("Geometry", [
            ("Bar length (L):", self.bar_length),
            ("Bar width (W):",  self.bar_width),
            ("Thickness (0=2D):", self.thickness),
        ]))

        return w

    def get_measurement_params(self) -> dict:
        return {
            "force_hi_ch":       int(self.force_hi.currentText()),
            "force_lo_ch":       int(self.force_lo.currentText()),
            "long_hi_ch":        int(self.long_hi.currentText()),
            "long_lo_ch":        int(self.long_lo.currentText()),
            "hall_hi_ch":        int(self.hall_hi.currentText()),
            "hall_lo_ch":        int(self.hall_lo.currentText()),
            "current":           self.current.value(),
            "compliance_v":      self.comp_v.value(),
            "magnetic_field_T":  self.b_field.value(),
            "n_averages":        self.n_avg.value(),
            "bar_length_um":     self.bar_length.value(),
            "bar_width_um":      self.bar_width.value(),
            "thickness_nm":      self.thickness.value(),
        }

    def make_measurement(self):
        return HallBarMeasurement(
            self._instrument_provider(),
            self.get_measurement_params(),
        )
