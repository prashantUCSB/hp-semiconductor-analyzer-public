"""
Diode I-V Measurement.

Sweeps voltage across anode–cathode, measures current.
Extracts: ideality factor (n), saturation current (I0), series resistance.
"""

import numpy as np
import logging
from typing import Dict, Any

from .base_measurement import BaseMeasurement, MeasurementResult

logger = logging.getLogger(__name__)

kT_q = 0.02585  # kT/q at 300 K in volts


def extract_diode_parameters(v: np.ndarray, i: np.ndarray):
    """
    Fit diode equation:  I = I0 * (exp(V / (n * kT/q)) - 1)

    Returns dict with I0, n, and estimated series resistance.
    Fit is done in the log domain on the forward-bias exponential region.
    """
    # Forward region: I > 0 and V > 0
    mask = (i > 1e-15) & (v > 0)
    if mask.sum() < 4:
        return {"I0 (A)": "N/A", "n": "N/A", "Rs (Ω)": "N/A"}

    v_f = v[mask]
    i_f = i[mask]
    log_i = np.log(i_f)

    # Linear fit log(I) vs V  →  slope = 1/(n·kT/q),  intercept = log(I0)
    coeffs = np.polyfit(v_f, log_i, 1)
    slope, intercept = coeffs
    if slope <= 0:
        return {"I0 (A)": "N/A", "n": "N/A", "Rs (Ω)": "N/A"}

    n  = 1.0 / (slope * kT_q)
    I0 = np.exp(intercept)

    # Estimate series resistance from deviation at high current
    high_mask = i_f > 0.5 * i_f.max()
    if high_mask.sum() > 2:
        v_excess = v_f[high_mask] - n * kT_q * np.log(i_f[high_mask] / I0 + 1)
        Rs = float(np.mean(v_excess / i_f[high_mask]))
    else:
        Rs = float("nan")

    return {
        "I0 (A)":  f"{I0:.4e}",
        "n":       round(n, 3),
        "Rs (Ω)":  round(Rs, 2) if not np.isnan(Rs) else "N/A",
    }


class DiodeIVMeasurement(BaseMeasurement):
    """
    Diode I-V measurement.

    Expected params:
      anode_ch   : int  – SMU for anode (swept)
      cathode_ch : int  – SMU for cathode (ground / compliance)
      v_start    : float
      v_stop     : float
      v_step     : float
      compliance : float
      log_points : bool – if True, use log-spaced points
      n_points   : int  – number of points (used if log_points=True)
    """

    NAME = "Diode I-V"

    def run(self):
        try:
            self._run_impl()
        except Exception as exc:
            self.emit_error(str(exc))

    def _run_impl(self):
        p    = self.params
        inst = self.instrument

        self.emit_status("Setting up diode I-V…")

        anode_ch   = p["anode_ch"]
        cathode_ch = p["cathode_ch"]
        v_start    = p["v_start"]
        v_stop     = p["v_stop"]
        v_step     = p["v_step"]
        compliance = p.get("compliance", 0.1)

        const = {cathode_ch: 0.0}

        instr_type = type(inst).__name__
        if instr_type == "HP4156":
            inst.initialize()
            inst.define_smu(anode_ch,   "VA", "IA", mode="COMM")
            inst.define_smu(cathode_ch, "VC", "IC", mode="COMM")
            inst.setup_var1_v(anode_ch, v_start, v_stop, v_step, compliance)
            inst.setup_const_v(cathode_ch, 0.0, compliance)
            inst.measure()
            v_arr = inst.fetch_data("VA")
            i_arr = inst.fetch_data("IA")
        else:  # HP4145
            v_arr, i_arr = inst.run_iv_sweep(
                anode_ch, v_start, v_stop, v_step,
                cathode_ch, const_channels=const,
                compliance=compliance,
                v_name="VA", i_name="IA",
            )

        for i, (v, i_d) in enumerate(zip(v_arr, i_arr)):
            self.emit_point(x=float(v), y=float(i_d), series="I")
            self.emit_progress(int(100 * i / len(v_arr)))
            if self._abort:
                break

        analysis = extract_diode_parameters(v_arr, i_arr)

        result = MeasurementResult(self.NAME)
        result.data     = {"V (V)": v_arr, "I (A)": i_arr}
        result.metadata = dict(p)
        result.analysis = analysis

        self.emit_status("Done.")
        self.emit_progress(100)
        self.emit_result(result)
