"""
Driver for HP 4280A 1 MHz C-V Plotter.

The 4280A measures capacitance (and conductance) as a function of DC bias.
It operates at 1 MHz with a 30 mVrms AC signal.

Reference: HP 4280A Operating and Service Manual (HP P/N 04280-90012)
"""

import time
import logging
import numpy as np
from typing import Tuple, Optional

from .base_instrument import GPIBInstrument

logger = logging.getLogger(__name__)

# ── Measurement modes ────────────────────────────────────────────────────────
MODE_CS_RS  = "CSRS"   # series C and R
MODE_CS_GS  = "CSGS"   # series C and G
MODE_CP_RP  = "CPRP"   # parallel C and R
MODE_CP_GP  = "CPGP"   # parallel C and G

# ── Frequency ────────────────────────────────────────────────────────────────
FREQ_1MHZ = "1E6"

# ── Integration ──────────────────────────────────────────────────────────────
INTEG_FAST   = 1
INTEG_MEDIUM = 2
INTEG_SLOW   = 3


class HP4280(GPIBInstrument):
    """
    HP 4280A 1 MHz C-V Plotter driver.

    The 4280A supports a single DC bias terminal and measures C (or G) vs.
    bias voltage.  AC test signal is fixed at 1 MHz, 30 mVrms.
    """

    def __init__(self, resource_string: str = ""):
        super().__init__(resource_string)

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def connect(self, resource_string: Optional[str] = None) -> bool:
        ok = super().connect(resource_string)
        if ok:
            self.initialize()
        return ok

    def initialize(self):
        """Reset to factory defaults."""
        self.reset()
        time.sleep(0.5)

    # ------------------------------------------------------------------
    # Instrument setup
    # ------------------------------------------------------------------

    def set_mode(self, mode: str = MODE_CP_GP):
        """Set measurement mode (CSRS, CSGS, CPRP, CPGP)."""
        self.write(f"MD{mode}")

    def set_bias_voltage(self, voltage: float):
        """Set DC bias voltage (V). Range: -100 V to +100 V."""
        if not (-100 <= voltage <= 100):
            raise ValueError(f"Bias voltage {voltage} V out of range ±100 V")
        self.write(f"BI{voltage:.4f}")

    def set_bias_enable(self, enable: bool = True):
        """Enable/disable DC bias output."""
        self.write("BIA ON" if enable else "BIA OFF")

    def set_integration(self, level: int = INTEG_MEDIUM):
        """Set integration time: 1=FAST, 2=MEDIUM, 3=SLOW."""
        self.write(f"IT{level}")

    def set_cable_length(self, length_m: int = 0):
        """Set cable length for compensation (0, 1, or 2 meters)."""
        if length_m not in (0, 1, 2):
            raise ValueError("Cable length must be 0, 1, or 2 m")
        self.write(f"CL{length_m}")

    # ------------------------------------------------------------------
    # Single-point measurement
    # ------------------------------------------------------------------

    def measure_single(self) -> Tuple[float, float]:
        """
        Trigger a single measurement.
        Returns (C_or_primary, G_or_secondary) as floats.
        """
        self.write("TR1")    # trigger
        raw = self.read()
        return self._parse_cv_response(raw)

    # ------------------------------------------------------------------
    # C-V sweep
    # ------------------------------------------------------------------

    def cv_sweep(
        self,
        v_start: float, v_stop: float, v_step: float,
        mode: str = MODE_CP_GP,
        integration: int = INTEG_MEDIUM,
        delay: float = 0.05,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Perform a C-V sweep.

        Args:
            v_start   : start bias voltage (V)
            v_stop    : stop bias voltage (V)
            v_step    : step size (V, sign taken from direction)
            mode      : measurement mode string
            integration: 1/2/3
            delay     : settling delay between points (s)

        Returns:
            (bias_V, C_F, G_S)  – voltage, capacitance, conductance arrays
        """
        self.set_mode(mode)
        self.set_integration(integration)
        self.set_bias_enable(True)

        voltages = np.arange(v_start, v_stop + v_step / 2, v_step)
        c_vals, g_vals = [], []

        for v in voltages:
            self.set_bias_voltage(float(v))
            time.sleep(delay)
            c, g = self.measure_single()
            c_vals.append(c)
            g_vals.append(g)

        self.set_bias_enable(False)
        return voltages, np.array(c_vals), np.array(g_vals)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_cv_response(self, raw: str) -> Tuple[float, float]:
        """Parse 4280A response string into (primary, secondary) floats."""
        tokens = raw.strip().split(",")
        if len(tokens) >= 2:
            try:
                return float(tokens[0]), float(tokens[1])
            except ValueError:
                pass
        # Try removing status characters
        try:
            p = float(tokens[0].lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
            s = float(tokens[1].lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")) if len(tokens) > 1 else 0.0
            return p, s
        except (ValueError, IndexError):
            logger.warning("Could not parse 4280A response: %r", raw)
            return 0.0, 0.0
