"""
Kelvin (4-wire) Resistance Measurement.

Forces current through outer probes, measures voltage on inner probes
to eliminate contact resistance.  Can sweep current to get R vs I.
"""

import numpy as np
import logging
from .base_measurement import BaseMeasurement, MeasurementResult

logger = logging.getLogger(__name__)


class Kelvin4ProbeMeasurement(BaseMeasurement):
    """
    4-wire (Kelvin) resistance measurement.

    Probe assignments:
      force_hi_ch  : SMU forcing positive current
      force_lo_ch  : SMU sinking current (return)
      sense_hi_ch  : SMU measuring high-voltage terminal (high-impedance)
      sense_lo_ch  : SMU measuring low-voltage terminal (high-impedance)

    Expected params:
      force_hi_ch  : int
      force_lo_ch  : int
      sense_hi_ch  : int
      sense_lo_ch  : int
      i_start      : float – start current (A)
      i_stop       : float – stop current (A)
      i_step       : float – step current (A)  (0 for single point)
      compliance_v : float
      n_averages   : int
    """

    NAME = "Kelvin 4-Probe Resistance"

    def run(self):
        try:
            self._run_impl()
        except Exception as exc:
            self.emit_error(str(exc))

    def _run_impl(self):
        p    = self.params
        inst = self.instrument

        self.emit_status("Kelvin 4-probe measurement…")

        fhi = p["force_hi_ch"]
        flo = p["force_lo_ch"]
        shi = p["sense_hi_ch"]
        slo = p["sense_lo_ch"]
        i_start    = p.get("i_start", 1e-4)
        i_stop     = p.get("i_stop",  1e-4)
        i_step     = p.get("i_step",  0)
        V_comp     = p.get("compliance_v", 10.0)
        n_avg      = p.get("n_averages", 3)

        if i_step == 0 or i_start == i_stop:
            currents = np.array([i_start])
        else:
            currents = np.arange(i_start, i_stop + i_step / 2, i_step)

        v_arr, r_arr = [], []

        for idx, I in enumerate(currents):
            if self._abort:
                break

            readings = []
            for _ in range(n_avg):
                V_meas = self._force_and_sense(inst, fhi, flo, shi, slo,
                                               float(I), V_comp)
                readings.append(V_meas)

            V_avg = float(np.mean(readings))
            R_val = V_avg / I if I != 0 else float("nan")
            v_arr.append(V_avg)
            r_arr.append(R_val)

            self.emit_point(x=float(I) * 1e3, y=R_val, series="R")   # mA vs Ω
            self.emit_progress(int(100 * (idx + 1) / len(currents)))
            self.emit_status(f"I = {I*1e3:.4f} mA  →  R = {R_val:.4e} Ω")

        v_arr = np.array(v_arr)
        r_arr = np.array(r_arr)

        # Linear fit V vs I → slope = R
        if len(currents) > 2 and not np.any(np.isnan(r_arr)):
            coeffs = np.polyfit(currents, v_arr, 1)
            R_lin  = coeffs[0]
        else:
            R_lin  = float(np.nanmean(r_arr))

        result = MeasurementResult(self.NAME)
        result.data     = {
            "I (A)":  currents,
            "V (V)":  v_arr,
            "R (Ω)":  r_arr,
        }
        result.metadata = dict(p)
        result.analysis = {
            "R_mean (Ω)":  f"{R_lin:.6e}",
            "R_std (Ω)":   f"{float(np.nanstd(r_arr)):.6e}",
        }

        self.emit_status("Done.")
        self.emit_progress(100)
        self.emit_result(result)

    # ------------------------------------------------------------------

    def _force_and_sense(self, inst, fhi, flo, shi, slo,
                         I: float, V_comp: float) -> float:
        """Force I on (fhi, flo), measure V on (shi, slo)."""
        instr_type = type(inst).__name__
        if instr_type == "HP4156":
            inst.initialize()
            inst.define_smu(fhi, "VFH", "IFH", mode="COMM")
            inst.define_smu(flo, "VFL", "IFL", mode="COMM")
            inst.define_smu(shi, "VSH", "ISH", mode="COMM")
            inst.define_smu(slo, "VSL", "ISL", mode="COMM")
            inst.setup_const_i(fhi,  I,  V_comp)
            inst.setup_const_i(flo, -I,  V_comp)
            inst.setup_const_v(shi, 0.0, I * 10)
            inst.setup_const_v(slo, 0.0, I * 10)
            inst.measure()
            v_hi = inst.fetch_data("VSH")
            v_lo = inst.fetch_data("VSL")
            return float(v_hi[0] - v_lo[0]) if len(v_hi) and len(v_lo) else 0.0
        else:
            # HP4145: single-point current sweep
            v_arr, _ = inst.run_iv_sweep(
                fhi, I, I, I, shi,
                const_channels={flo: 0.0, slo: 0.0},
                compliance=V_comp,
                v_name="VFH", i_name="IFH",
            )
            return float(v_arr[0]) if len(v_arr) else 0.0
