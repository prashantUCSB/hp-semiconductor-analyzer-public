"""
Hall Bar Measurement.

Hall bar geometry: 6 contacts (2 current, 4 voltage) or standard 8-contact bar.
Measures Hall resistance, longitudinal resistance, carrier density, and mobility.
Requires an external magnet — user enters B-field value manually.

Contact labeling (standard Hall bar):
  I+  I-      : current source contacts (force_hi, force_lo)
  V1+ V1-    : longitudinal voltage pair 1
  V2+ V2-    : transverse (Hall) voltage pair
"""

import numpy as np
import logging
from .base_measurement import BaseMeasurement, MeasurementResult

logger = logging.getLogger(__name__)

q = 1.602e-19


class HallBarMeasurement(BaseMeasurement):
    """
    Hall bar resistance / Hall effect measurement.

    Expected params:
      force_hi_ch   : int  – I+ terminal SMU
      force_lo_ch   : int  – I- terminal SMU
      long_hi_ch    : int  – longitudinal V+ SMU (high-Z)
      long_lo_ch    : int  – longitudinal V- SMU (high-Z)
      hall_hi_ch    : int  – transverse V+ SMU (high-Z)
      hall_lo_ch    : int  – transverse V- SMU (high-Z)
      current       : float – source current (A)
      compliance_v  : float
      magnetic_field_T : float – applied B-field (T), entered by user
      bar_length_um : float – distance between longitudinal voltage probes (µm)
      bar_width_um  : float – Hall bar width (µm)
      thickness_nm  : float – film thickness (nm), 0 for 2D sheet
      n_averages    : int
    """

    NAME = "Hall Bar"

    def run(self):
        try:
            self._run_impl()
        except Exception as exc:
            self.emit_error(str(exc))

    def _run_impl(self):
        p    = self.params
        inst = self.instrument

        self.emit_status("Hall bar measurement…")

        fhi  = p["force_hi_ch"]
        flo  = p["force_lo_ch"]
        lhi  = p["long_hi_ch"]
        llo  = p["long_lo_ch"]
        hhi  = p["hall_hi_ch"]
        hlo  = p["hall_lo_ch"]

        I_src   = p.get("current", 1e-4)
        V_comp  = p.get("compliance_v", 10.0)
        B_T     = p.get("magnetic_field_T", 0.1)
        L_um    = p.get("bar_length_um", 100.0)
        W_um    = p.get("bar_width_um",  20.0)
        t_nm    = p.get("thickness_nm",   0.0)
        n_avg   = p.get("n_averages",     5)

        # ── Longitudinal resistance ───────────────────────────────────────
        self.emit_status("Measuring longitudinal resistance Rxx…")
        rxx_readings = []
        for _ in range(n_avg):
            V_long = self._kelvin(inst, fhi, flo, lhi, llo, I_src, V_comp)
            rxx_readings.append(V_long / I_src if I_src != 0 else 0)
        R_xx = float(np.mean(rxx_readings))
        self.emit_point(x=0, y=R_xx, series="Rxx")
        self.emit_status(f"Rxx = {R_xx:.4e} Ω")

        # ── Hall resistance ───────────────────────────────────────────────
        self.emit_status("Measuring Hall resistance Rxy…")
        hall_readings = []
        for _ in range(n_avg):
            V_hall = self._kelvin(inst, fhi, flo, hhi, hlo, I_src, V_comp)
            hall_readings.append(V_hall / I_src if I_src != 0 else 0)
        R_xy = float(np.mean(hall_readings))
        self.emit_point(x=1, y=R_xy, series="Rxy")
        self.emit_status(f"Rxy = {R_xy:.4e} Ω")

        # ── Derived quantities ────────────────────────────────────────────
        # Sheet resistance: Rs = Rxx * (W/L)
        L_m = L_um * 1e-6
        W_m = W_um * 1e-6
        Rs  = R_xx * (W_m / L_m) if L_m > 0 else float("nan")

        # Hall carrier density (sheet): ns = B / (q * |Rxy|)
        ns = abs(B_T) / (q * abs(R_xy)) if R_xy != 0 else float("nan")

        # Hall mobility: mu = |Rxy| / (Rs * B)
        mu_H = abs(R_xy) / (Rs * abs(B_T)) if (Rs != 0 and B_T != 0) else float("nan")

        # 3D carrier density (if thickness given)
        if t_nm > 0:
            t_m  = t_nm * 1e-9
            n3d  = ns / t_m if not np.isnan(ns) else float("nan")
        else:
            n3d = float("nan")

        carrier_type = "n-type" if R_xy < 0 else "p-type"

        analysis = {
            "Rxx (Ω)":        f"{R_xx:.6e}",
            "Rxy (Ω)":        f"{R_xy:.6e}",
            "Rs (Ω/sq)":      f"{Rs:.4e}" if not np.isnan(Rs) else "N/A",
            "ns (cm⁻²)":      f"{ns * 1e-4:.4e}" if not np.isnan(ns) else "N/A",
            "μH (cm²/V·s)":   f"{mu_H * 1e4:.2f}" if not np.isnan(mu_H) else "N/A",
            "n3D (cm⁻³)":     f"{n3d * 1e-6:.4e}" if not np.isnan(n3d) else "N/A",
            "Carrier type":   carrier_type,
            "B-field (T)":    B_T,
        }

        result = MeasurementResult(self.NAME)
        result.data     = {
            "Rxx (Ω)": np.array([R_xx]),
            "Rxy (Ω)": np.array([R_xy]),
        }
        result.metadata = dict(p)
        result.analysis = analysis

        self.emit_status("Done.")
        self.emit_progress(100)
        self.emit_result(result)

    # ------------------------------------------------------------------

    def _kelvin(self, inst, fhi, flo, vhi, vlo, I_src, V_comp) -> float:
        """Force I, measure V differentially."""
        instr_type = type(inst).__name__
        if instr_type == "HP4156":
            inst.initialize()
            for ch, vn, fn in [
                (fhi, "VFH", "IFH"), (flo, "VFL", "IFL"),
                (vhi, "VVH", "IVH"), (vlo, "VVL", "IVL"),
            ]:
                inst.define_smu(ch, vn, fn, mode="COMM")
            inst.setup_const_i(fhi,  I_src, V_comp)
            inst.setup_const_i(flo, -I_src, V_comp)
            inst.setup_const_v(vhi, 0.0, I_src * 100)
            inst.setup_const_v(vlo, 0.0, I_src * 100)
            inst.measure()
            v_hi_arr = inst.fetch_data("VVH")
            v_lo_arr = inst.fetch_data("VVL")
            return float(v_hi_arr[0] - v_lo_arr[0]) if (len(v_hi_arr) and len(v_lo_arr)) else 0.0
        else:
            v_arr, _ = inst.run_iv_sweep(
                fhi, I_src, I_src, I_src, vhi,
                const_channels={flo: 0.0, vlo: 0.0},
                compliance=V_comp,
                v_name="VFH", i_name="IFH",
            )
            return float(v_arr[0]) if len(v_arr) else 0.0
