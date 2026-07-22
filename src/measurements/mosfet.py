"""
MOSFET Measurements
  - Transfer curve (Id–Vgs at fixed Vds)
  - Output curve (Id–Vds for multiple Vgs steps)
  - Subthreshold slope, gm, Vth extraction
"""

import numpy as np
import logging
from typing import Dict, Any

from .base_measurement import BaseMeasurement, MeasurementResult

logger = logging.getLogger(__name__)


# ── Analysis helpers ─────────────────────────────────────────────────────────

def extract_threshold_voltage(vgs: np.ndarray, ids: np.ndarray,
                               method: str = "linear") -> float:
    """
    Extract threshold voltage from Id–Vgs transfer curve.

    Methods:
      'linear'    – linear extrapolation of max-gm tangent
      'sqrt'      – √Id extrapolation (for long-channel MOSFET)
      'constant'  – Vgs at Id = W/L × 100 nA (simple heuristic)
    """
    if len(vgs) < 4:
        return float("nan")

    if method == "sqrt":
        sqrt_ids = np.sqrt(np.abs(ids))
        idx_max  = np.argmax(np.gradient(sqrt_ids, vgs))
        slope    = np.gradient(sqrt_ids, vgs)[idx_max]
        if slope <= 0:
            return float("nan")
        return vgs[idx_max] - sqrt_ids[idx_max] / slope

    elif method == "constant":
        threshold_current = 100e-9
        idx = np.searchsorted(np.abs(ids), threshold_current)
        return vgs[min(idx, len(vgs) - 1)]

    else:  # linear extrapolation
        gm   = np.gradient(ids, vgs)
        idx  = np.argmax(np.abs(gm))
        slope = gm[idx]
        if slope == 0:
            return float("nan")
        return vgs[idx] - ids[idx] / slope


def extract_subthreshold_slope(vgs: np.ndarray, ids: np.ndarray) -> float:
    """
    Extract subthreshold slope S (mV/dec).
    Finds the region below threshold where log10(Id) vs Vgs is most linear.
    """
    mask = ids > 0
    if mask.sum() < 4:
        return float("nan")
    log_ids = np.log10(ids[mask])
    vgs_sub = vgs[mask]

    # Find min-slope (subthreshold region)
    slopes = np.gradient(log_ids, vgs_sub)
    # Take average of bottom 20% of current range
    thresh = np.percentile(log_ids, 30)
    sub_mask = log_ids < thresh
    if sub_mask.sum() < 2:
        return float("nan")
    s = np.mean(np.abs(1.0 / slopes[sub_mask])) * 1000  # V/dec → mV/dec
    return s


def extract_gm(vgs: np.ndarray, ids: np.ndarray) -> np.ndarray:
    """Transconductance gm = dId/dVgs."""
    return np.gradient(ids, vgs)


# ── MOSFET Transfer Curve ────────────────────────────────────────────────────

class MOSFETTransferMeasurement(BaseMeasurement):
    """
    Id–Vgs transfer curve at fixed Vds.

    Expected params keys:
      gate_ch   : int  – SMU channel for gate
      drain_ch  : int  – SMU channel for drain
      source_ch : int  – SMU channel for source (connected to ground)
      body_ch   : int or None – SMU channel for body (or None)
      vgs_start : float
      vgs_stop  : float
      vgs_step  : float
      vds       : float – fixed drain–source bias
      vgs_compliance : float
      vds_compliance : float
      log_scale : bool – measure in log-spaced Vgs
      double_sweep : bool – sweep forward then back
    """

    NAME = "MOSFET Transfer Curve"

    def run(self):
        try:
            self._run_impl()
        except Exception as exc:
            self.emit_error(str(exc))
            logger.exception("Transfer curve error")

    def _run_impl(self):
        p = self.params
        inst = self.instrument
        instr_type = type(inst).__name__

        self.emit_status("Setting up transfer curve measurement…")

        gate_ch   = p["gate_ch"]
        drain_ch  = p["drain_ch"]
        source_ch = p.get("source_ch", None)
        vgs_start = p["vgs_start"]
        vgs_stop  = p["vgs_stop"]
        vgs_step  = p["vgs_step"]
        vds       = p.get("vds", 0.05)
        vgs_comp  = p.get("vgs_compliance", 10e-3)
        vds_comp  = p.get("vds_compliance", 0.1)
        double_sw = p.get("double_sweep", False)

        const = {drain_ch: vds}
        if source_ch:
            const[source_ch] = 0.0

        if instr_type == "HP4145":
            from ..instruments.hp4145 import HP4145
            vgs, ids = inst.run_iv_sweep(
                gate_ch, vgs_start, vgs_stop, vgs_step,
                drain_ch, const_channels=const,
                compliance=vds_comp,
                v_name="VGS", i_name="ID",
            )
        else:  # HP4156
            inst.initialize()
            inst.define_smu(gate_ch,  "VGS", "IG", mode="COMM")
            inst.define_smu(drain_ch, "VDS", "ID", mode="COMM")
            if source_ch:
                inst.define_smu(source_ch, "VS", "IS", mode="COMM")
            inst.setup_var1_v(gate_ch, vgs_start, vgs_stop, vgs_step, vgs_comp)
            inst.setup_const_v(drain_ch, vds, vds_comp)
            if source_ch:
                inst.setup_const_v(source_ch, 0.0, vds_comp)
            inst.measure()
            vgs = inst.fetch_data("VGS")
            ids = inst.fetch_data("ID")

        if self._abort:
            return

        # Emit real-time points for live plot
        for i, (v, i_d) in enumerate(zip(vgs, ids)):
            self.emit_point(x=float(v), y=float(i_d), series="Id")
            self.emit_progress(int(100 * i / len(vgs)))
            if self._abort:
                break

        # Analysis
        gm       = extract_gm(vgs, ids)
        vth      = extract_threshold_voltage(vgs, ids, method=p.get("vth_method", "linear"))
        ss       = extract_subthreshold_slope(vgs, np.abs(ids))
        gm_max   = float(np.max(np.abs(gm)))

        result = MeasurementResult(self.NAME)
        result.data     = {"Vgs (V)": vgs, "Id (A)": ids, "gm (S)": gm}
        result.metadata = dict(p)
        result.analysis = {
            "Vth (V)":              round(vth, 4),
            "gm_max (S)":           f"{gm_max:.4e}",
            "SS (mV/dec)":          round(ss, 1) if not np.isnan(ss) else "N/A",
            "Ion (A)":              f"{float(ids[-1]):.4e}",
            "Ion/Ioff":             f"{float(abs(ids[-1]) / max(abs(ids[0]), 1e-15)):.2e}",
        }

        self.emit_status("Done.")
        self.emit_progress(100)
        self.emit_result(result)


# ── MOSFET Output Curve ──────────────────────────────────────────────────────

class MOSFETOutputMeasurement(BaseMeasurement):
    """
    Id–Vds family of curves for multiple Vgs steps.

    Expected params keys:
      drain_ch  : int
      gate_ch   : int
      source_ch : int or None
      vds_start : float
      vds_stop  : float
      vds_step  : float
      vgs_start : float
      vgs_stop  : float
      vgs_nstep : int   – number of Vgs steps (0 = single curve)
      vds_compliance : float
      vgs_compliance : float
    """

    NAME = "MOSFET Output Curve"

    def run(self):
        try:
            self._run_impl()
        except Exception as exc:
            self.emit_error(str(exc))
            logger.exception("Output curve error")

    def _run_impl(self):
        p    = self.params
        inst = self.instrument

        self.emit_status("Setting up output curve measurement…")

        drain_ch  = p["drain_ch"]
        gate_ch   = p["gate_ch"]
        source_ch = p.get("source_ch", None)
        vds_start = p["vds_start"]
        vds_stop  = p["vds_stop"]
        vds_step  = p["vds_step"]
        vgs_start = p["vgs_start"]
        vgs_stop  = p["vgs_stop"]
        vgs_nstep = p.get("vgs_nstep", 5)
        vds_comp  = p.get("vds_compliance", 0.1)
        vgs_comp  = p.get("vgs_compliance", 10e-3)

        instr_type = type(inst).__name__

        if instr_type == "HP4156":
            vds_2d, vgs_steps, ids_2d = inst.run_family_of_curves(
                drain_ch, gate_ch,
                vds_start, vds_stop, vds_step,
                vgs_start, vgs_stop, vgs_nstep,
                vds_comp, vgs_comp,
            )
        else:
            # HP4145: run one Vgs at a time
            vgs_steps = np.linspace(vgs_start, vgs_stop, vgs_nstep + 1)
            vds_2d, ids_2d = [], []
            for i, vgs_val in enumerate(vgs_steps):
                if self._abort:
                    break
                self.emit_status(f"Vgs = {vgs_val:.3f} V …")
                const = {gate_ch: vgs_val}
                if source_ch:
                    const[source_ch] = 0.0
                vds, ids = inst.run_iv_sweep(
                    drain_ch, vds_start, vds_stop, vds_step,
                    gate_ch, const_channels=const,
                    compliance=vds_comp,
                    v_name="VDS", i_name="ID",
                )
                vds_2d.append(vds)
                ids_2d.append(ids)
                self.emit_progress(int(100 * (i + 1) / len(vgs_steps)))
                for v, i_d in zip(vds, ids):
                    self.emit_point(x=float(v), y=float(i_d),
                                    series=f"Vgs={vgs_val:.2f}V")
            vds_2d  = np.array(vds_2d)
            ids_2d  = np.array(ids_2d)

        result = MeasurementResult(self.NAME)
        result.data = {}
        for idx, vgs_v in enumerate(vgs_steps):
            sfx = f"_Vgs{vgs_v:.2f}V"
            result.data[f"Vds (V){sfx}"]  = vds_2d[idx]
            result.data[f"Id (A){sfx}"]   = ids_2d[idx]
        result.metadata = dict(p)

        self.emit_status("Done.")
        self.emit_progress(100)
        self.emit_result(result)
