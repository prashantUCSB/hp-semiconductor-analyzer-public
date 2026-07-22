"""
Driver for HP / Agilent 4156A / 4156B Precision Semiconductor Parameter Analyzer.

The 4156 uses a hierarchical SCPI-like command set built around "pages"
(MEAS, DISP, CALC, etc.).  Unlike the 4145, all setup is done before
measurement execution.

Reference: HP 4156A/B User's Guide (HP P/N 04156-90030)
"""

import time
import logging
import numpy as np
from typing import List, Tuple, Dict, Optional

from .base_instrument import GPIBInstrument

logger = logging.getLogger(__name__)

# ── Channel numbers ──────────────────────────────────────────────────────────
SMU1, SMU2, SMU3, SMU4 = 1, 2, 3, 4
VSU1, VSU2 = 5, 6
VMU1, VMU2 = 7, 8

# ── Integration time ─────────────────────────────────────────────────────────
INTEG_SHORT  = "SHORT"
INTEG_MEDIUM = "MED"
INTEG_LONG   = "LONG"


class HP4156(GPIBInstrument):
    """
    HP/Agilent 4156A / 4156B driver.

    The 4156 uses :PAGE:MEAS:* commands for sweep setup and :MEAS:EXEC
    to trigger measurement.  Data is retrieved with :DATA:VAR?.
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
        self.write(":PAGE:REST")          # reset measurement page
        time.sleep(0.3)

    # ------------------------------------------------------------------
    # Channel definition  (:PAGE:CHAN)
    # ------------------------------------------------------------------

    def define_smu(self, ch: int, v_name: str, i_name: str,
                   v_range: float = 0, i_range: float = 0,
                   mode: str = "COMM"):
        """
        Define SMU channel.
          ch      : 1–4
          v_name  : voltage variable name
          i_name  : current variable name
          v_range : 0 = auto
          i_range : 0 = auto
          mode    : 'COMM'|'V'|'I'|'VPULSE'|'IPULSE'|'COMMON'
        """
        self.write(f":PAGE:CHAN:SMU{ch}:VNAM '{v_name}'")
        self.write(f":PAGE:CHAN:SMU{ch}:INAM '{i_name}'")
        self.write(f":PAGE:CHAN:SMU{ch}:MODE {mode}")
        if v_range:
            self.write(f":PAGE:CHAN:SMU{ch}:VRANGE {v_range}")
        if i_range:
            self.write(f":PAGE:CHAN:SMU{ch}:IRANGE {i_range}")

    def define_vsu(self, ch: int, v_name: str):
        """Define VSU channel (ch=5 or 6)."""
        vsu = ch - 4
        self.write(f":PAGE:CHAN:VSU{vsu}:VNAM '{v_name}'")

    def define_vmu(self, ch: int, v_name: str):
        """Define VMU channel (ch=7 or 8)."""
        vmu = ch - 6
        self.write(f":PAGE:CHAN:VMU{vmu}:VNAM '{v_name}'")

    # ------------------------------------------------------------------
    # Measurement setup  (:PAGE:MEAS)
    # ------------------------------------------------------------------

    def setup_var1_v(self, ch: int, start: float, stop: float, step: float,
                     compliance: float = 0.1):
        """Primary sweep – voltage."""
        self.write(f":PAGE:MEAS:VAR1:MODE VOLTAGE")
        self.write(f":PAGE:MEAS:VAR1:START {start}")
        self.write(f":PAGE:MEAS:VAR1:STOP {stop}")
        self.write(f":PAGE:MEAS:VAR1:STEP {step}")
        self.write(f":PAGE:MEAS:VAR1:COMP {compliance}")
        self.write(f":PAGE:MEAS:VAR1:SOUR SMU{ch}")

    def setup_var1_i(self, ch: int, start: float, stop: float, step: float,
                     compliance: float = 10.0):
        """Primary sweep – current."""
        self.write(f":PAGE:MEAS:VAR1:MODE CURRENT")
        self.write(f":PAGE:MEAS:VAR1:START {start}")
        self.write(f":PAGE:MEAS:VAR1:STOP {stop}")
        self.write(f":PAGE:MEAS:VAR1:STEP {step}")
        self.write(f":PAGE:MEAS:VAR1:COMP {compliance}")
        self.write(f":PAGE:MEAS:VAR1:SOUR SMU{ch}")

    def setup_var2_v(self, ch: int, start: float, stop: float, nstep: int,
                     compliance: float = 0.1):
        """Secondary step – voltage (family of curves)."""
        self.write(f":PAGE:MEAS:VAR2:MODE VOLTAGE")
        self.write(f":PAGE:MEAS:VAR2:START {start}")
        self.write(f":PAGE:MEAS:VAR2:STOP {stop}")
        self.write(f":PAGE:MEAS:VAR2:STEP {nstep}")
        self.write(f":PAGE:MEAS:VAR2:COMP {compliance}")
        self.write(f":PAGE:MEAS:VAR2:SOUR SMU{ch}")

    def setup_const_v(self, ch: int, voltage: float, compliance: float = 0.1):
        """Force constant voltage on SMU channel."""
        self.write(f":PAGE:MEAS:CONS:SMU{ch}:FUNC VOLTAGE")
        self.write(f":PAGE:MEAS:CONS:SMU{ch}:VALUE {voltage}")
        self.write(f":PAGE:MEAS:CONS:SMU{ch}:COMP {compliance}")

    def setup_const_i(self, ch: int, current: float, compliance: float = 10.0):
        """Force constant current on SMU channel."""
        self.write(f":PAGE:MEAS:CONS:SMU{ch}:FUNC CURRENT")
        self.write(f":PAGE:MEAS:CONS:SMU{ch}:VALUE {current}")
        self.write(f":PAGE:MEAS:CONS:SMU{ch}:COMP {compliance}")

    def set_integration_time(self, integ: str = INTEG_MEDIUM):
        """Set integration time: SHORT, MED, or LONG."""
        self.write(f":PAGE:MEAS:MSET:INTEG {integ}")

    def set_hold_delay(self, hold: float = 0.0, delay: float = 0.0):
        """Set hold and delay times (seconds) before/between points."""
        self.write(f":PAGE:MEAS:MSET:HTIM {hold}")
        self.write(f":PAGE:MEAS:MSET:DTIM {delay}")

    def enable_smu_output(self, *channels: int):
        """Enable measurement output for specified SMU channels."""
        for ch in channels:
            self.write(f":PAGE:MEAS:MSET:SMU{ch}:DIS ON")

    # ------------------------------------------------------------------
    # Execute and fetch
    # ------------------------------------------------------------------

    def measure(self) -> bool:
        """Execute measurement and wait for completion."""
        self.write(":MEAS:EXEC")
        return self._wait_complete(timeout=300)

    def _wait_complete(self, timeout: int = 300) -> bool:
        """Poll *STB? until measurement is done."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                stb = int(self.query("*STB?"))
                if stb & 0x10:   # data ready
                    return True
                if stb & 0x20:   # hardware error
                    logger.warning("Instrument error bit set")
                    return False
            except Exception:
                pass
            time.sleep(0.2)
        logger.warning("Measurement timeout")
        return False

    def fetch_data(self, var_name: str) -> np.ndarray:
        """Retrieve data array for a named variable."""
        raw = self.query(f":DATA:VAR? '{var_name}'")
        values = []
        for tok in raw.strip().split(","):
            tok = tok.strip()
            if not tok:
                continue
            try:
                if tok[0].isalpha():
                    tok = tok[1:]
                values.append(float(tok))
            except ValueError:
                logger.debug("Skipping token: %r", tok)
        return np.array(values, dtype=float)

    def fetch_all(self, var_names: List[str]) -> Dict[str, np.ndarray]:
        return {name: self.fetch_data(name) for name in var_names}

    # ------------------------------------------------------------------
    # Convenience: full measurement sequences
    # ------------------------------------------------------------------

    def run_iv_sweep(
        self,
        sweep_ch: int,
        v_start: float, v_stop: float, v_step: float,
        sense_channels: List[int],
        const_channels: Optional[Dict[int, float]] = None,
        compliance: float = 0.1,
        integration: str = INTEG_MEDIUM,
        v_name: str = "VGS", i_name: str = "ID",
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generic single-sweep I-V.  Returns (voltage, current) arrays.
        """
        self.initialize()

        # Define all channels
        self.define_smu(sweep_ch, v_name, i_name, mode="COMM")
        for ch in sense_channels:
            if ch != sweep_ch:
                self.define_smu(ch, f"V{ch}", f"I{ch}", mode="COMM")

        # Sweep setup
        self.setup_var1_v(sweep_ch, v_start, v_stop, v_step, compliance)
        self.set_integration_time(integration)

        # Constant bias channels
        if const_channels:
            for ch, val in const_channels.items():
                self.define_smu(ch, f"V{ch}", f"I{ch}", mode="COMM")
                self.setup_const_v(ch, val, compliance)

        if not self.measure():
            raise RuntimeError("4156 measurement failed")

        return self.fetch_data(v_name), self.fetch_data(i_name)

    def run_family_of_curves(
        self,
        drain_ch: int, gate_ch: int,
        vd_start: float, vd_stop: float, vd_step: float,
        vg_start: float, vg_stop: float, vg_nstep: int,
        vd_compliance: float = 0.1, vg_compliance: float = 0.1,
        integration: str = INTEG_MEDIUM,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        MOSFET output curve family (Id–Vds for multiple Vgs steps).
        Returns (Vds_2D, Vgs_steps, Id_2D) where rows = Vgs step.
        """
        self.initialize()
        self.define_smu(drain_ch, "VDS", "ID", mode="COMM")
        self.define_smu(gate_ch,  "VGS", "IG", mode="COMM")

        self.setup_var1_v(drain_ch, vd_start, vd_stop, vd_step, vd_compliance)
        self.setup_var2_v(gate_ch,  vg_start, vg_stop, vg_nstep, vg_compliance)
        self.set_integration_time(integration)

        if not self.measure():
            raise RuntimeError("Family-of-curves measurement failed")

        vds = self.fetch_data("VDS")
        ids = self.fetch_data("ID")
        vgs = self.fetch_data("VGS")

        # Reshape into 2-D arrays (Vgs_step × Vds_points)
        n_vds = round((vd_stop - vd_start) / vd_step) + 1
        n_vgs = vg_nstep + 1
        try:
            vds_2d = vds.reshape(n_vgs, n_vds)
            ids_2d = ids.reshape(n_vgs, n_vds)
            vgs_steps = np.linspace(vg_start, vg_stop, n_vgs)
        except Exception:
            logger.warning("Could not reshape arrays; returning flat")
            vds_2d, ids_2d, vgs_steps = vds, ids, vgs
        return vds_2d, vgs_steps, ids_2d
