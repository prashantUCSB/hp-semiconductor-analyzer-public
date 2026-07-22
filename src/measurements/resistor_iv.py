"""
Resistor I-V Measurement.

Sweeps voltage, measures current.  Fits R = V/I (linear region).
"""

import numpy as np
import logging
from .base_measurement import BaseMeasurement, MeasurementResult

logger = logging.getLogger(__name__)


class ResistorIVMeasurement(BaseMeasurement):
    """
    Two-terminal resistor I-V.

    Expected params:
      hi_ch      : int  – high-potential SMU channel
      lo_ch      : int  – low-potential SMU channel (ground)
      v_start    : float
      v_stop     : float
      v_step     : float
      compliance : float
    """

    NAME = "Resistor I-V"

    def run(self):
        try:
            self._run_impl()
        except Exception as exc:
            self.emit_error(str(exc))

    def _run_impl(self):
        p    = self.params
        inst = self.instrument

        self.emit_status("Resistor I-V…")

        hi_ch      = p["hi_ch"]
        lo_ch      = p["lo_ch"]
        v_start    = p["v_start"]
        v_stop     = p["v_stop"]
        v_step     = p["v_step"]
        compliance = p.get("compliance", 0.1)

        instr_type = type(inst).__name__
        if instr_type == "HP4156":
            inst.initialize()
            inst.define_smu(hi_ch, "VHI", "IHI", mode="COMM")
            inst.define_smu(lo_ch, "VLO", "ILO", mode="COMM")
            inst.setup_var1_v(hi_ch, v_start, v_stop, v_step, compliance)
            inst.setup_const_v(lo_ch, 0.0, compliance)
            inst.measure()
            v_arr = inst.fetch_data("VHI")
            i_arr = inst.fetch_data("IHI")
        else:
            v_arr, i_arr = inst.run_iv_sweep(
                hi_ch, v_start, v_stop, v_step,
                lo_ch, const_channels={lo_ch: 0.0},
                compliance=compliance,
                v_name="VHI", i_name="IHI",
            )

        for idx, (v, i) in enumerate(zip(v_arr, i_arr)):
            self.emit_point(x=float(v), y=float(i), series="I")
            self.emit_progress(int(100 * idx / max(len(v_arr), 1)))

        # Fit resistance
        mask = np.abs(i_arr) > 0
        if mask.sum() > 2:
            coeffs    = np.polyfit(v_arr[mask], i_arr[mask], 1)
            r_fit     = 1.0 / coeffs[0] if coeffs[0] != 0 else float("nan")
            r_intercept = coeffs[1]
        else:
            r_fit = float("nan")
            r_intercept = float("nan")

        result = MeasurementResult(self.NAME)
        result.data     = {"V (V)": v_arr, "I (A)": i_arr}
        result.metadata = dict(p)
        result.analysis = {
            "R_fit (Ω)":    f"{r_fit:.4e}" if not np.isnan(r_fit) else "N/A",
            "Intercept (A)": f"{r_intercept:.4e}",
        }

        self.emit_status("Done.")
        self.emit_progress(100)
        self.emit_result(result)
