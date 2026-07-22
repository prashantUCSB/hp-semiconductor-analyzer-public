"""
Generic 4-port measurement panel.

Each SMU is configured in its own compact QGroupBox (role + relevant fields).
Hiding both the label and field widget of a QFormLayout row collapses it in
Qt 5.15, so only the relevant fields are shown for the selected role.

Four SMU boxes are stacked in a QScrollArea so the left panel never overflows.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout,
    QLabel, QComboBox, QScrollArea, QSizePolicy,
)
from PyQt5.QtCore import Qt

from .base_panel import BasePanel
from .form_helpers import make_dspin, make_combo, form_group
from ..dpi import dp
from ...measurements.generic_4port import (
    Generic4PortMeasurement,
    ROLE_SWEEP_V, ROLE_STEP_V, ROLE_CONST_V, ROLE_CONST_I,
    ROLE_GROUND, ROLE_FLOAT,
)

ROLES = [ROLE_SWEEP_V, ROLE_STEP_V, ROLE_CONST_V, ROLE_CONST_I, ROLE_GROUND, ROLE_FLOAT]


class SMUConfigBox(QGroupBox):
    """
    Compact per-SMU configuration widget.

    Layout (vertical QFormLayout inside a QGroupBox):
      Role:        [COMBO]
      Start:       [spin V]   ← sweep / step only
      Stop:        [spin V]   ← sweep / step only
      Step/NStep:  [spin   ]  ← sweep / step only
      Value:       [spin V]   ← const only
      Compliance:  [spin  ]   ← all except GROUND / FLOAT
    """

    def __init__(self, ch: int, parent=None):
        super().__init__(f"SMU {ch}", parent)
        self.ch = ch
        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        form = QFormLayout(self)
        form.setContentsMargins(dp(6), dp(2), dp(6), dp(4))
        form.setSpacing(dp(3))
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # ── Role ──────────────────────────────────────────────────────
        self.role_combo = QComboBox()
        self.role_combo.addItems(ROLES)
        self._add_row(form, "Role:", self.role_combo)

        # ── Sweep fields (SWEEP_V / STEP_V) ───────────────────────────
        self.start = make_dspin(0.0,  -200, 200, suffix="V")
        self.stop  = make_dspin(1.0,  -200, 200, suffix="V")
        self.step  = make_dspin(0.05, 0.001, 100, 3, suffix="V")

        self._lbl_start, _ = self._add_row(form, "Start:", self.start)
        self._lbl_stop,  _ = self._add_row(form, "Stop:",  self.stop)
        self._lbl_step,  _ = self._add_row(form, "Step:",  self.step)

        # ── Constant field (CONST_V / CONST_I) ────────────────────────
        self.value = make_dspin(0.0, -200, 200, suffix="V")
        self._lbl_value, _ = self._add_row(form, "Value:", self.value)

        # ── Compliance (all except GROUND / FLOAT) ────────────────────
        self.comp = make_dspin(0.1, 1e-12, 1.0, 6, suffix="A")
        self._lbl_comp, _ = self._add_row(form, "Compliance:", self.comp)

        self.role_combo.currentTextChanged.connect(self._update_visibility)
        self._update_visibility(self.role_combo.currentText())

    def _add_row(self, form: QFormLayout, label: str, widget: QWidget):
        """Add a form row and return (label_widget, field_widget)."""
        lbl = QLabel(label)
        form.addRow(lbl, widget)
        return lbl, widget

    # ------------------------------------------------------------------
    def _update_visibility(self, role: str):
        is_sweep     = role in (ROLE_SWEEP_V, ROLE_STEP_V)
        is_const     = role in (ROLE_CONST_V, ROLE_CONST_I)
        show_comp    = role not in (ROLE_GROUND, ROLE_FLOAT)

        for lbl, w in [
            (self._lbl_start, self.start),
            (self._lbl_stop,  self.stop),
            (self._lbl_step,  self.step),
        ]:
            lbl.setVisible(is_sweep)
            w.setVisible(is_sweep)

        self._lbl_value.setVisible(is_const)
        self.value.setVisible(is_const)

        self._lbl_comp.setVisible(show_comp)
        self.comp.setVisible(show_comp)

    # ------------------------------------------------------------------
    def get_config(self) -> dict:
        role = self.role_combo.currentText()
        d = {
            "ch":         self.ch,
            "role":       role,
            "v_name":     f"V{self.ch}",
            "i_name":     f"I{self.ch}",
            "compliance": self.comp.value(),
        }
        if role in (ROLE_SWEEP_V, ROLE_STEP_V):
            start = self.start.value()
            stop  = self.stop.value()
            step  = self.step.value()
            d.update({
                "start": start,
                "stop":  stop,
                "step":  step,
                "nstep": max(1, round(abs(stop - start) / step)) if step else 10,
            })
        elif role in (ROLE_CONST_V, ROLE_CONST_I):
            d["value"] = self.value.value()
        return d


# ── Panel ─────────────────────────────────────────────────────────────────────

class GenericPanel(BasePanel):
    plot_xlabel = "X"
    plot_ylabel = "Y"
    plot_title  = "Generic 4-Port"

    def build_params_widget(self) -> QWidget:
        # ── Outer container ────────────────────────────────────────────
        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(dp(4))

        # ── Scroll area for 4 SMU boxes ────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(scroll.NoFrame)

        smu_container = QWidget()
        smu_layout = QVBoxLayout(smu_container)
        smu_layout.setContentsMargins(0, 0, dp(4), 0)  # right margin for scrollbar
        smu_layout.setSpacing(dp(4))

        self.smu_boxes = []
        for ch in range(1, 5):
            box = SMUConfigBox(ch)
            smu_layout.addWidget(box)
            self.smu_boxes.append(box)

        smu_layout.addStretch()
        scroll.setWidget(smu_container)
        outer_layout.addWidget(scroll, stretch=1)

        # ── Plot axis selectors ────────────────────────────────────────
        vars_list = ["V1", "V2", "V3", "V4", "I1", "I2", "I3", "I4"]
        self.out_x = make_combo(vars_list, "V1")
        self.out_y = make_combo(vars_list, "I1")
        outer_layout.addWidget(form_group("Plot Axes", [
            ("X axis:", self.out_x),
            ("Y axis:", self.out_y),
        ]))

        return outer

    # ------------------------------------------------------------------
    def get_measurement_params(self) -> dict:
        channels   = [box.get_config() for box in self.smu_boxes]
        x_var      = self.out_x.currentText()
        y_var      = self.out_y.currentText()
        output_vars = list(dict.fromkeys([x_var, y_var]))   # ordered, deduplicated
        return {
            "channels":    channels,
            "output_vars": output_vars,
        }

    def make_measurement(self):
        return Generic4PortMeasurement(
            self._instrument_provider(),
            self.get_measurement_params(),
        )
