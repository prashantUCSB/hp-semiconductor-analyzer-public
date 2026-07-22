"""Kelvin 4-probe resistance panel."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from .base_panel import BasePanel
from .form_helpers import make_dspin, make_spin, ch_combo, form_group
from ...measurements.kelvin_4probe import Kelvin4ProbeMeasurement


class KelvinPanel(BasePanel):
    plot_xlabel = "I (mA)"
    plot_ylabel = "R (Ω)"
    plot_title  = "Kelvin 4-Probe Resistance"

    def build_params_widget(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.force_hi  = ch_combo(1)
        self.force_lo  = ch_combo(2)
        self.sense_hi  = ch_combo(3)
        self.sense_lo  = ch_combo(4)
        layout.addWidget(form_group("Probe Assignment", [
            ("Force I+ (SMU):", self.force_hi),
            ("Force I- (SMU):", self.force_lo),
            ("Sense V+ (SMU):", self.sense_hi),
            ("Sense V- (SMU):", self.sense_lo),
        ]))

        self.i_start  = make_dspin(1e-4, -0.1, 0.1, 9, suffix="A")
        self.i_stop   = make_dspin(1e-3, -0.1, 0.1, 9, suffix="A")
        self.i_step   = make_dspin(1e-4, 0, 0.1, 9, suffix="A")
        layout.addWidget(form_group("Current Sweep", [
            ("I start:",  self.i_start),
            ("I stop:",   self.i_stop),
            ("I step (0=single):", self.i_step),
        ]))

        self.comp_v    = make_dspin(10.0, 0.01, 200, suffix="V")
        self.n_avg     = make_spin(3, 1, 20)
        layout.addWidget(form_group("Settings", [
            ("Compliance V:", self.comp_v),
            ("# Averages:",   self.n_avg),
        ]))

        return w

    def get_measurement_params(self) -> dict:
        return {
            "force_hi_ch": int(self.force_hi.currentText()),
            "force_lo_ch": int(self.force_lo.currentText()),
            "sense_hi_ch": int(self.sense_hi.currentText()),
            "sense_lo_ch": int(self.sense_lo.currentText()),
            "i_start":     self.i_start.value(),
            "i_stop":      self.i_stop.value(),
            "i_step":      self.i_step.value(),
            "compliance_v": self.comp_v.value(),
            "n_averages":   self.n_avg.value(),
        }

    def make_measurement(self):
        return Kelvin4ProbeMeasurement(
            self._instrument_provider(),
            self.get_measurement_params(),
        )
