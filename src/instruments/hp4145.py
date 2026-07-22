"""
Driver for HP 4145A / 4145B Semiconductor Parameter Analyzer.

The 4145 uses a token-based command language (not SCPI). Channel assignments:
  SMU1–SMU4  : Source/Measure Units  (channels 1–4)
  VSU1–VSU2  : Voltage Source Units  (channels 5–6)
  VMU1–VMU2  : Voltage Monitor Units (channels 7–8)

Reference: HP 4145A/B Operating and Programming Manual (HP P/N 04145-90040)
"""

import time
import logging
import numpy as np
from typing import List, Tuple, Optional, Dict

from .base_instrument import GPIBInstrument

logger = logging.getLogger(__name__)

# ── Channel constants ────────────────────────────────────────────────────────
CH1, CH2, CH3, CH4 = 1, 2, 3, 4
VSU1, VSU2 = 5, 6
VMU1, VMU2 = 7, 8

# ── Mode constants ───────────────────────────────────────────────────────────
MODE_SWEEP_V = "VAR1"   # primary sweep variable (voltage)
MODE_SWEEP_I = "VAR1"   # primary sweep variable (current)
MODE_STEP_V  = "VAR2"   # step variable (voltage)
MODE_STEP_I  = "VAR2"   # step variable (current)
MODE_CONST_V = "VARD"   # constant voltage
MODE_CONST_I = "VARD"   # constant current (use CONS mode)

# ── Measurement mode codes for MM command ───────────────────────────────────
MM_SWEEP   = 1   # sweep measurement
MM_SAMPLE  = 2   # sampling
MM_QUASI   = 3   # quasi-static C-V (4145B only)


class HP4145(GPIBInstrument):
    """
    HP 4145A / 4145B driver.

    The 4145 command set mirrors the front-panel softkey structure:
      DE  – Define channels (name, variable assignment, unit type)
      SS  – Source Setup (sweep params, step params, constants)
      MD  – Measurement Data (select what to display/return)
      MM  – Measurement Mode
      ME  – Measurement Execute
      DO  – Data Output
      BC  – Binary/BCD Clear (clear data buffer)
      DP  – Display Plotting
      GP  – Graphics Plot
    """

    MODEL_A = "4145A"
    MODEL_B = "4145B"

    def __init__(self, resource_string: str = ""):
        super().__init__(resource_string)
        self.model = self.MODEL_A   # updated after connect/IDN check

    # ------------------------------------------------------------------
    # Identification / initialisation
    # ------------------------------------------------------------------

    def connect(self, resource_string: Optional[str] = None) -> bool:
        ok = super().connect(resource_string)
        if ok:
            if "4145B" in self.idn.upper():
                self.model = self.MODEL_B
            # self.idn may be empty for 4145A (pre-IEEE 488.2); model stays MODEL_A
            self.initialize()
        return ok

    def _idn_fallback(self) -> str:
        """
        The HP 4145A predates IEEE 488.2 and does not implement *IDN?.
        Send a harmless 'BC' (buffer clear) command as a liveness check.
        If it doesn't throw, the instrument is alive; return a static model string.
        """
        try:
            self.write("BC")
            import time as _t; _t.sleep(0.1)
            return "HEWLETT-PACKARD,4145A,0,0"
        except Exception:
            return ""

    def initialize(self):
        """Put instrument in a known state."""
        self.write("BC")      # clear data buffer
        self.write("DR1")     # data ready flag enable
        time.sleep(0.2)

    # ------------------------------------------------------------------
    # DE – Define channel setup
    # ------------------------------------------------------------------

    def define_smu(self, ch: int, v_name: str, i_name: str, mode: str, func: int = 1):
        """
        Define an SMU channel.
          ch      : 1–4
          v_name  : voltage variable name (up to 6 chars)
          i_name  : current variable name (up to 6 chars)
          mode    : 'VAR1'|'VAR2'|'VARD'|'CONS'
          func    : 1=FORCE/MEASURE V+I, 2=FORCE V, 3=FORCE I, 4=COMMON
        """
        self.write(f"DE CH{ch},'{v_name}','{i_name}',{mode},{func}")

    def define_vsu(self, ch: int, v_name: str, mode: str = "CONS"):
        """Define a Voltage Source Unit (ch=5 or 6)."""
        vsu = ch - 4   # 5→VSU1, 6→VSU2
        self.write(f"DE VS{vsu},'{v_name}',{mode}")

    def define_vmu(self, ch: int, v_name: str, mode: str = "CONS"):
        """Define a Voltage Monitor Unit (ch=7 or 8)."""
        vmu = ch - 6   # 7→VMU1, 8→VMU2
        self.write(f"DE VM{vmu},'{v_name}',{mode}")

    # ------------------------------------------------------------------
    # SS – Source Setup
    # ------------------------------------------------------------------

    def setup_var1_v(self, start: float, stop: float, step: float,
                     compliance: float = 0.1):
        """Set up VAR1 voltage sweep (primary sweep)."""
        self.write(f"SS VR1,{start},{stop},{step},{compliance}")

    def setup_var1_i(self, start: float, stop: float, step: float,
                     compliance: float = 10.0):
        """Set up VAR1 current sweep."""
        self.write(f"SS IR1,{start},{stop},{step},{compliance}")

    def setup_var2_v(self, start: float, stop: float, step: float,
                     compliance: float = 0.1):
        """Set up VAR2 voltage step (secondary sweep)."""
        self.write(f"SS VR2,{start},{stop},{step},{compliance}")

    def setup_var2_i(self, start: float, stop: float, step: float,
                     compliance: float = 0.1):
        """Set up VAR2 current step."""
        self.write(f"SS IR2,{start},{stop},{step},{compliance}")

    def setup_const_v(self, ch: int, voltage: float, compliance: float = 0.1):
        """Set a constant voltage on an SMU/VSU channel."""
        self.write(f"SS VC{ch},{voltage},{compliance}")

    def setup_const_i(self, ch: int, current: float, compliance: float = 10.0):
        """Set a constant current on an SMU channel."""
        self.write(f"SS IC{ch},{current},{compliance}")

    # ------------------------------------------------------------------
    # MD / MM – Measurement Data / Mode
    # ------------------------------------------------------------------

    def set_measurement_mode(self, mode: int = MM_SWEEP):
        """
        Set measurement mode.
          1 = sweep, 2 = sampling, 3 = quasi-static C-V
        """
        self.write(f"MM {mode},1")   # mode, display channel

    def select_display(self, *vars_: str):
        """Select up to 4 variables for display/data output."""
        var_str = ",".join(f"'{v}'" for v in vars_[:4])
        self.write(f"MD {var_str}")

    # ------------------------------------------------------------------
    # ME / DO – Execute and fetch data
    # ------------------------------------------------------------------

    def measure(self) -> bool:
        """Trigger measurement and wait for completion. Returns True on success."""
        self.write("BC")     # clear buffer
        self.write("ME1")    # execute single measurement
        return self._wait_srq(timeout=120)

    def _wait_srq(self, timeout: int = 120) -> bool:
        """Poll STB until measurement complete bit (bit 4) is set."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                stb = int(self.query("*STB?"))
                if stb & 0x10:   # bit 4 = data ready
                    return True
                if stb & 0x20:   # bit 5 = error
                    logger.warning("Instrument error during measurement")
                    return False
            except Exception:
                pass
            time.sleep(0.1)
        logger.warning("Measurement timeout after %d s", timeout)
        return False

    def fetch_data(self, var_name: str) -> np.ndarray:
        """
        Retrieve ASCII data for a named variable.
        Returns a 1-D numpy array of float values.
        """
        raw = self.query(f"DO '{var_name}'")
        values = []
        for token in raw.strip().split(","):
            token = token.strip()
            if not token:
                continue
            try:
                # 4145 prefixes each value with a status char, e.g. "N1.234E-3"
                if token[0].isalpha():
                    token = token[1:]
                values.append(float(token))
            except ValueError:
                logger.debug("Skipping token: %r", token)
        return np.array(values, dtype=float)

    def fetch_all(self, var_names: List[str]) -> Dict[str, np.ndarray]:
        """Fetch data for a list of variable names."""
        return {name: self.fetch_data(name) for name in var_names}

    # ------------------------------------------------------------------
    # Convenience: full measurement sequences
    # ------------------------------------------------------------------

    def run_iv_sweep(
        self,
        sweep_ch: int,
        v_start: float, v_stop: float, v_step: float,
        sense_ch: int,
        const_channels: Optional[Dict[int, float]] = None,
        compliance: float = 0.1,
        v_name: str = "VGS", i_name: str = "ID",
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generic single-sweep I-V.
        Returns (voltage_array, current_array).
        """
        # Reset channel definitions
        self.write("BC")

        # Define sweep channel (VAR1)
        self.define_smu(sweep_ch, v_name, i_name, "VAR1", func=1)

        # Define constant channels
        if const_channels:
            for ch, val in const_channels.items():
                v_n = f"V{ch}"
                i_n = f"I{ch}"
                self.define_smu(ch, v_n, i_n, "VARD", func=1)
                self.setup_const_v(ch, val, compliance)

        # Source setup
        self.setup_var1_v(v_start, v_stop, v_step, compliance)

        # Select output variables
        self.select_display(v_name, i_name)
        self.set_measurement_mode(MM_SWEEP)

        # Execute
        if not self.measure():
            raise RuntimeError("Measurement failed or timed out")

        v_arr = self.fetch_data(v_name)
        i_arr = self.fetch_data(i_name)
        return v_arr, i_arr
