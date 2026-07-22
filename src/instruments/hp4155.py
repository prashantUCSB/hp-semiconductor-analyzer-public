"""
Driver for HP 4155A / 4155B Semiconductor Parameter Analyzer.

The HP 4155 is a 2-SMU / 2-VSU variant of the HP 4156 family.
It uses the same hierarchical page-based SCPI-like command set as the 4156
but supports only SMU1 and SMU2 (no SMU3/SMU4), plus VSU1/VSU2.
The 4155 has no VMU channels.

Reference: HP 4155A/B Operating Manual (HP P/N 04155-90030)
"""

import time
import logging
from typing import Optional

from .hp4156 import HP4156, INTEG_SHORT, INTEG_MEDIUM, INTEG_LONG  # noqa: F401

logger = logging.getLogger(__name__)


class HP4155(HP4156):
    """
    HP 4155A / 4155B driver.

    Hardware differences from HP 4156:
      • 2 SMUs only (SMU1, SMU2)       — SMU3/SMU4 are absent
      • 2 VSUs  (VSU1, VSU2)           — same as 4156
      • No VMUs                         — 4156 has VMU1/VMU2
      • Max output voltage ±40 V        — same as 4156A

    Everything else (page-based command structure, sweep commands,
    data retrieval, integration times) is identical to HP4156.
    The driver simply validates channel numbers and updates the model string.
    """

    MAX_SMU = 2   # 4155 has only SMU1 and SMU2

    MODEL_A = "4155A"
    MODEL_B = "4155B"
    MODEL_C = "4155C"

    def __init__(self, resource_string: str = ""):
        super().__init__(resource_string)
        self.model = self.MODEL_A  # updated after IDN on connect

    # ------------------------------------------------------------------
    # Connection / identification
    # ------------------------------------------------------------------

    def connect(self, resource_string: Optional[str] = None) -> bool:
        ok = super().connect(resource_string)
        if ok:
            idn_upper = self.idn.upper()
            if "4155C" in idn_upper:
                self.model = self.MODEL_C
            elif "4155B" in idn_upper:
                self.model = self.MODEL_B
            else:
                self.model = self.MODEL_A
        return ok

    # ------------------------------------------------------------------
    # Channel validation
    # ------------------------------------------------------------------

    def _validate_smu(self, ch: int):
        """Raise ValueError if ch exceeds this instrument's SMU count."""
        if ch < 1 or ch > self.MAX_SMU:
            raise ValueError(
                f"HP {self.model} has {self.MAX_SMU} SMUs (1–{self.MAX_SMU}); "
                f"requested SMU{ch}"
            )

    def define_smu(self, ch: int, v_name: str, i_name: str,
                   v_range: float = 0, i_range: float = 0,
                   mode: str = "COMM"):
        self._validate_smu(ch)
        super().define_smu(ch, v_name, i_name, v_range, i_range, mode)

    def setup_var1_v(self, ch: int, start: float, stop: float, step: float,
                     compliance: float = 0.1):
        self._validate_smu(ch)
        super().setup_var1_v(ch, start, stop, step, compliance)

    def setup_var1_i(self, ch: int, start: float, stop: float, step: float,
                     compliance: float = 10.0):
        self._validate_smu(ch)
        super().setup_var1_i(ch, start, stop, step, compliance)

    def setup_var2_v(self, ch: int, start: float, stop: float, nstep: int,
                     compliance: float = 0.1):
        self._validate_smu(ch)
        super().setup_var2_v(ch, start, stop, nstep, compliance)

    def setup_const_v(self, ch: int, voltage: float, compliance: float = 0.1):
        self._validate_smu(ch)
        super().setup_const_v(ch, voltage, compliance)

    def setup_const_i(self, ch: int, current: float, compliance: float = 10.0):
        self._validate_smu(ch)
        super().setup_const_i(ch, current, compliance)

    def define_vmu(self, ch: int, v_name: str):
        raise AttributeError(
            f"HP {self.model} does not have Voltage Monitor Units (VMUs)"
        )

    # ------------------------------------------------------------------
    # Convenience: 4155-specific info
    # ------------------------------------------------------------------

    def __repr__(self) -> str:  # noqa: D105
        status = "connected" if self.connected else "disconnected"
        return f"<HP4155 model={self.model} {self.resource_string} {status}>"
