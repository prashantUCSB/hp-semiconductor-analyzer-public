"""
Generic 4-Port Measurement.

Freely assigns each SMU as either:
  - Voltage sweep source (VAR1 / VAR2)
  - Constant voltage / current source
  - Measurement-only (floating, high-Z)
  - Ground (0 V)

Useful for custom device characterisation that doesn't fit a named topology.
"""

import numpy as np
import logging
from typing import List, Dict, Any
from .base_measurement import BaseMeasurement, MeasurementResult

logger = logging.getLogger(__name__)

# SMU role constants
ROLE_SWEEP_V  = "SWEEP_V"
ROLE_STEP_V   = "STEP_V"
ROLE_CONST_V  = "CONST_V"
ROLE_CONST_I  = "CONST_I"
ROLE_GROUND   = "GROUND"
ROLE_FLOAT    = "FLOAT"


class Generic4PortMeasurement(BaseMeasurement):
    """
    Generic 4-SMU measurement with flexible role assignment.

    Expected params:
      channels : list of dicts, one per SMU, e.g.:
        [
          {"ch": 1, "role": "SWEEP_V", "start": -2, "stop": 2,
           "step": 0.1, "compliance": 0.1, "v_name": "V1", "i_name": "I1"},
          {"ch": 2, "role": "CONST_V", "value": 1.0, "compliance": 0.1,
           "v_name": "V2", "i_name": "I2"},
          {"ch": 3, "role": "GROUND",  "v_name": "V3", "i_name": "I3"},
          {"ch": 4, "role": "FLOAT",   "v_name": "V4", "i_name": "I4"},
        ]
      output_vars : list of variable names to plot/save (e.g. ["V1", "I1", "I2"])
      integration : str (4156 only)
    """

    NAME = "Generic 4-Port"

    def run(self):
        try:
            self._run_impl()
        except Exception as exc:
            self.emit_error(str(exc))

    def _run_impl(self):
        p      = self.params
        inst   = self.instrument
        chconf = p.get("channels", [])
        out_vars = p.get("output_vars", [])

        self.emit_status("Configuring 4-port measurement…")

        instr_type = type(inst).__name__

        if instr_type == "HP4156":
            self._run_4156(inst, chconf, out_vars, p)
        else:
            self._run_4145(inst, chconf, out_vars, p)

    def _run_4156(self, inst, chconf, out_vars, p):
        from ..instruments.hp4156 import INTEG_MEDIUM
        inst.initialize()
        integration = p.get("integration", INTEG_MEDIUM)

        sweep_ch = None
        for cfg in chconf:
            ch   = cfg["ch"]
            role = cfg["role"]
            vn   = cfg.get("v_name", f"V{ch}")
            fn   = cfg.get("i_name", f"I{ch}")
            inst.define_smu(ch, vn, fn, mode="COMM")

            if role == ROLE_SWEEP_V:
                sweep_ch = ch
                inst.setup_var1_v(ch, cfg["start"], cfg["stop"], cfg["step"],
                                  cfg.get("compliance", 0.1))
            elif role == ROLE_STEP_V:
                inst.setup_var2_v(ch, cfg["start"], cfg["stop"],
                                  int(cfg.get("nstep", 5)),
                                  cfg.get("compliance", 0.1))
            elif role == ROLE_CONST_V:
                inst.setup_const_v(ch, cfg["value"], cfg.get("compliance", 0.1))
            elif role == ROLE_CONST_I:
                inst.setup_const_i(ch, cfg["value"], cfg.get("compliance", 10.0))
            elif role in (ROLE_GROUND, ROLE_FLOAT):
                inst.setup_const_v(ch, 0.0, cfg.get("compliance", 0.1))

        inst.set_integration_time(integration)
        if not inst.measure():
            self.emit_error("Measurement failed")
            return

        data = inst.fetch_all(out_vars)

        # Emit points for live plot
        x_key = out_vars[0] if out_vars else list(data.keys())[0]
        y_key = out_vars[1] if len(out_vars) > 1 else x_key
        x_arr = data.get(x_key, np.array([]))
        y_arr = data.get(y_key, np.array([]))
        for i, (x, y) in enumerate(zip(x_arr, y_arr)):
            self.emit_point(x=float(x), y=float(y), series=y_key)
            self.emit_progress(int(100 * i / max(len(x_arr), 1)))

        result = MeasurementResult(self.NAME)
        result.data     = data
        result.metadata = dict(p)
        self.emit_result(result)

    def _run_4145(self, inst, chconf, out_vars, p):
        # Find the sweep channel
        sweep_cfg = next((c for c in chconf if c["role"] == ROLE_SWEEP_V), None)
        if sweep_cfg is None:
            self.emit_error("No SWEEP_V channel configured")
            return

        sweep_ch = sweep_cfg["ch"]
        vn = sweep_cfg.get("v_name", f"V{sweep_ch}")
        fn = sweep_cfg.get("i_name", f"I{sweep_ch}")

        const_channels = {}
        for cfg in chconf:
            ch = cfg["ch"]
            if ch == sweep_ch:
                continue
            if cfg["role"] in (ROLE_CONST_V, ROLE_GROUND):
                const_channels[ch] = cfg.get("value", 0.0)

        v_arr, i_arr = inst.run_iv_sweep(
            sweep_ch,
            sweep_cfg["start"], sweep_cfg["stop"], sweep_cfg["step"],
            sweep_ch,
            const_channels=const_channels,
            compliance=sweep_cfg.get("compliance", 0.1),
            v_name=vn, i_name=fn,
        )

        for i, (v, curr) in enumerate(zip(v_arr, i_arr)):
            self.emit_point(x=float(v), y=float(curr), series=fn)
            self.emit_progress(int(100 * i / max(len(v_arr), 1)))

        result = MeasurementResult(self.NAME)
        result.data = {vn: v_arr, fn: i_arr}
        result.metadata = dict(p)
        self.emit_result(result)
