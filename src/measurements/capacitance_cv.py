"""
Capacitance C-V Measurement using HP 4280A.

Sweeps DC bias, measures C and G at 1 MHz.
Extracts: Cox, tox, Vfb, Vth (from MOS C-V), doping, Dit.
"""

import numpy as np
import logging
from scipy.signal import savgol_filter
from .base_measurement import BaseMeasurement, MeasurementResult

logger = logging.getLogger(__name__)

eps0    = 8.854e-12   # F/m
eps_SiO2 = 3.9
eps_Si   = 11.7
q       = 1.602e-19
ni_Si   = 1.45e16     # m^-3 at 300 K
kT      = 0.02585     # eV at 300 K


def extract_mosc_parameters(v_bias: np.ndarray, c_farad: np.ndarray,
                             area_cm2: float = 1e-4):
    """
    Extract key MOS capacitor parameters from C-V data.

    Returns a dict with Cox, tox, Vfb, Vth (approx), doping, and Dit (approx).
    """
    result = {}
    area_m2 = area_cm2 * 1e-4   # cm² → m²

    # Cox = max capacitance (accumulation)
    Cox = float(np.max(c_farad)) / area_m2
    result["Cox (F/m²)"] = f"{Cox:.4e}"
    if Cox > 0:
        tox = eps0 * eps_SiO2 / Cox
        result["tox (nm)"] = round(tox * 1e9, 2)
    else:
        result["tox (nm)"] = "N/A"

    # Cmin = min capacitance (deep depletion or inversion)
    Cmin = float(np.min(c_farad)) / area_m2
    result["Cmin (F/m²)"] = f"{Cmin:.4e}"

    # Vfb estimate: where C = Cox * (1 + tox/Wdmax)^-1 … simplified:
    # midgap capacitance method: Cfb ≈ midpoint of accumulation & depletion
    if Cox > 0 and Cmin > 0:
        # Cfb heuristic (Berglund)
        Cfb = Cox / (1 + Cox * np.sqrt(2 * eps0 * eps_Si / (q * ni_Si)) / (eps0 * eps_SiO2)) \
              if tox > 0 else Cox * 0.7
        c_norm = c_farad / area_m2
        idx_vfb = np.argmin(np.abs(c_norm - Cfb))
        Vfb = float(v_bias[idx_vfb])
        result["Vfb (V)"] = round(Vfb, 3)

        # Vth ~ Vfb ± 2*phi_f (rough estimate; sign depends on device type)
        # Assume p-type Si, NMOS: Vth = Vfb + 2*phi_f + Qd/Cox
        # Without knowing Na, approximate from Cmin
        # NA approx from depletion width at Cmin
        Cmin_val = Cmin
        if Cox > Cmin_val > 0:
            Wd = eps0 * eps_Si * (1.0/Cmin_val - 1.0/Cox)
            NA = 2 * eps0 * eps_Si / (q * Wd**2) if Wd > 0 else float("nan")
            if not np.isnan(NA) and NA > 0:
                phi_f = kT * np.log(NA / ni_Si)
                Vth_approx = Vfb + 2 * phi_f + np.sqrt(4 * q * eps0 * eps_Si * NA * phi_f) / Cox
                result["Vth approx (V)"] = round(Vth_approx, 3)
                result["NA (cm⁻³)"]      = f"{NA * 1e-6:.3e}"  # m^-3 → cm^-3
    return result


class CapacitanceCVMeasurement(BaseMeasurement):
    """
    C-V measurement using HP 4280A C-V plotter.

    Expected params:
      v_start    : float  – start bias (V)
      v_stop     : float  – stop bias (V)
      v_step     : float  – step size (V)
      mode       : str    – 'CPRP' | 'CPGP' | 'CSRS' | 'CSGS'
      integration: int    – 1=FAST, 2=MED, 3=SLOW
      delay      : float  – settling delay (s)
      area_cm2   : float  – device area for parameter extraction
    """

    NAME = "Capacitance C-V"

    def run(self):
        try:
            self._run_impl()
        except Exception as exc:
            self.emit_error(str(exc))

    def _run_impl(self):
        p    = self.params
        inst = self.instrument

        self.emit_status("Starting C-V sweep…")

        v_start    = p["v_start"]
        v_stop     = p["v_stop"]
        v_step     = p.get("v_step", 0.1)
        mode       = p.get("mode", "CPGP")
        integration = p.get("integration", 2)
        delay      = p.get("delay", 0.05)
        area_cm2   = p.get("area_cm2", 1e-4)

        from ..instruments.hp4280 import HP4280
        if not isinstance(inst, HP4280):
            self.emit_error("C-V measurement requires HP 4280A instrument")
            return

        voltages, c_vals, g_vals = inst.cv_sweep(
            v_start, v_stop, v_step,
            mode=mode,
            integration=integration,
            delay=delay,
        )

        for i, (v, c, g) in enumerate(zip(voltages, c_vals, g_vals)):
            if self._abort:
                break
            self.emit_point(x=float(v), y=float(c), series="C", y2=float(g))
            self.emit_progress(int(100 * i / max(len(voltages), 1)))

        analysis = extract_mosc_parameters(voltages, c_vals, area_cm2)

        result = MeasurementResult(self.NAME)
        result.data     = {
            "V_bias (V)": voltages,
            "C (F)":      c_vals,
            "G (S)":      g_vals,
        }
        result.metadata = dict(p)
        result.analysis = analysis

        self.emit_status("Done.")
        self.emit_progress(100)
        self.emit_result(result)
