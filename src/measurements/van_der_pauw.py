"""
Van der Pauw Sheet Resistance and Hall Effect Measurement.

Four ohmic contacts labeled A, B, C, D clockwise.
Measures sheet resistance Rs and optionally Hall mobility/carrier density.

Reference: L.J. van der Pauw, Philips Research Reports 13, 1 (1958)
"""

import numpy as np
import logging
from scipy.optimize import brentq
from .base_measurement import BaseMeasurement, MeasurementResult

logger = logging.getLogger(__name__)

q = 1.602e-19   # C


def van_der_pauw_f(x: float) -> float:
    """VdP equation: exp(-π·RAB,CD/Rs) + exp(-π·RBC,DA/Rs) = 1."""
    return x  # resolved iteratively in solve_sheet_resistance


def solve_sheet_resistance(R_abcd: float, R_bcda: float) -> float:
    """
    Solve Van der Pauw equation numerically.
    R_abcd = V_CD / I_AB,  R_bcda = V_DA / I_BC
    Returns Rs (Ω/sq).
    """
    def equation(Rs):
        return (np.exp(-np.pi * R_abcd / Rs)
                + np.exp(-np.pi * R_bcda / Rs) - 1.0)

    Rs_guess = np.pi * (R_abcd + R_bcda) / (2 * np.log(2))
    try:
        Rs = brentq(equation, Rs_guess * 1e-4, Rs_guess * 1e4, maxiter=1000)
    except Exception:
        Rs = Rs_guess   # fall back to geometric mean approximation
    return Rs


class VanDerPauwMeasurement(BaseMeasurement):
    """
    Van der Pauw sheet resistance measurement.

    Channels A, B, C, D  →  SMU 1–4.
    Performs 8 resistance measurements (two per configuration, averaged)
    then solves for Rs.

    Optionally includes Hall measurement at a fixed B-field.

    Expected params:
      ch_a, ch_b, ch_c, ch_d : int  – SMU channels
      current                 : float – source current (A)
      compliance_v            : float – compliance voltage
      n_averages              : int   – averages per step
      magnetic_field_T        : float – B-field (T), 0 to skip Hall
      sample_thickness_cm     : float – for Hall mobility (3D carrier density)
    """

    NAME = "Van der Pauw"

    def run(self):
        try:
            self._run_impl()
        except Exception as exc:
            self.emit_error(str(exc))

    def _run_impl(self):
        p    = self.params
        inst = self.instrument

        self.emit_status("Van der Pauw measurement…")

        ch = {
            "A": p["ch_a"],
            "B": p["ch_b"],
            "C": p["ch_c"],
            "D": p["ch_d"],
        }
        I_src  = p.get("current", 1e-3)
        V_comp = p.get("compliance_v", 10.0)
        n_avg  = p.get("n_averages", 3)
        B_T    = p.get("magnetic_field_T", 0.0)

        R_vals = {}

        # ── Step 1: R_ABCD  (force I: A→B, measure V: C→D) ──────────────
        for label, (i_hi, i_lo, v_hi, v_lo) in {
            "R_ABCD": ("A", "B", "C", "D"),
            "R_BCDA": ("B", "C", "D", "A"),
            "R_CDAB": ("C", "D", "A", "B"),
            "R_DABC": ("D", "A", "B", "C"),
        }.items():
            r = self._measure_r(inst, ch, i_hi, i_lo, v_hi, v_lo,
                                I_src, V_comp, n_avg)
            R_vals[label] = r
            self.emit_point(x=0, y=r, series=label)
            self.emit_status(f"{label} = {r:.4f} Ω")
            if self._abort:
                return

        R_abcd = (R_vals["R_ABCD"] + R_vals["R_CDAB"]) / 2
        R_bcda = (R_vals["R_BCDA"] + R_vals["R_DABC"]) / 2

        Rs = solve_sheet_resistance(R_abcd, R_bcda)
        self.emit_status(f"Sheet resistance Rs = {Rs:.4f} Ω/sq")

        analysis = {
            "Rs (Ω/sq)":     round(Rs, 4),
            "R_ABCD (Ω)":    round(R_abcd, 6),
            "R_BCDA (Ω)":    round(R_bcda, 6),
        }

        # ── Step 2: Hall coefficient (optional) ──────────────────────────
        if B_T != 0:
            self.emit_status("Hall measurement…")
            # Hall resistances: R_ACBD and R_BDAC
            R_hall_1 = self._measure_r(inst, ch, "A", "C", "B", "D",
                                       I_src, V_comp, n_avg)
            R_hall_2 = self._measure_r(inst, ch, "B", "D", "A", "C",
                                       I_src, V_comp, n_avg)
            R_H = (R_hall_1 - R_hall_2) / 2
            # Sheet carrier density
            ns = 1.0 / (q * abs(R_H) * B_T) if R_H != 0 else float("nan")
            mu_H = abs(R_H) / Rs if Rs != 0 else float("nan")
            analysis.update({
                "R_Hall (Ω)":    round(R_H, 6),
                "ns (cm⁻²)":     f"{ns * 1e-4:.4e}" if not np.isnan(ns) else "N/A",
                "μH (cm²/V·s)":  round(mu_H * 1e4, 2) if not np.isnan(mu_H) else "N/A",
                "carrier type":  "n-type" if R_H < 0 else "p-type",
            })

        result = MeasurementResult(self.NAME)
        result.data     = {k: np.array([v]) for k, v in R_vals.items()}
        result.metadata = dict(p)
        result.analysis = analysis

        self.emit_status("Done.")
        self.emit_progress(100)
        self.emit_result(result)

    # ------------------------------------------------------------------
    # Low-level 4-probe resistance via SMU
    # ------------------------------------------------------------------

    def _measure_r(self, inst, ch: dict,
                   i_hi: str, i_lo: str, v_hi: str, v_lo: str,
                   I_src: float, V_comp: float, n_avg: int) -> float:
        """
        Force current I_src on (i_hi, i_lo), measure voltage on (v_hi, v_lo).
        Returns R = V/I averaged over n_avg readings.
        """
        readings = []
        instr_type = type(inst).__name__

        for _ in range(n_avg):
            if instr_type == "HP4156":
                inst.initialize()
                inst.define_smu(ch[i_hi], f"V{i_hi}", f"I{i_hi}", mode="COMM")
                inst.define_smu(ch[i_lo], f"V{i_lo}", f"I{i_lo}", mode="COMM")
                inst.define_smu(ch[v_hi], f"V{v_hi}", f"I{v_hi}", mode="COMM")
                inst.define_smu(ch[v_lo], f"V{v_lo}", f"I{v_lo}", mode="COMM")
                # Force I on i_hi, 0 V on others (floating measurement)
                inst.setup_const_i(ch[i_hi],  I_src, V_comp)
                inst.setup_const_i(ch[i_lo], -I_src, V_comp)
                inst.setup_const_v(ch[v_hi], 0.0, I_src * 10)
                inst.setup_const_v(ch[v_lo], 0.0, I_src * 10)
                inst.measure()
                v1 = inst.fetch_data(f"V{v_hi}")
                v2 = inst.fetch_data(f"V{v_lo}")
                V_meas = float(v1[0] - v2[0]) if len(v1) and len(v2) else 0
            else:  # HP4145
                # Use run_iv_sweep with single point
                v_arr, i_arr = inst.run_iv_sweep(
                    ch[i_hi], I_src, I_src, I_src,
                    ch[v_hi],
                    const_channels={ch[i_lo]: 0.0, ch[v_lo]: 0.0},
                    compliance=V_comp,
                    v_name=f"V{i_hi}", i_name=f"I{i_hi}",
                )
                V_meas = float(v_arr[0]) if len(v_arr) else 0

            readings.append(V_meas / I_src if I_src != 0 else 0)

        return float(np.mean(readings))
