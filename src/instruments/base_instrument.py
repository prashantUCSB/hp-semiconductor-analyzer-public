"""
Base class for all HP GPIB instruments.

Handles VISA resource management via VISAManager and adds GPIB-specific
robustness: viClear, interface-clear, retry on IDN, 4145A pre-IEEE-488.2
fallback, and a bus-reset helper.

Supported adapters
------------------
Keysight 82351B  — PCIe/PCI GPIB card; uses NI-VISA or Keysight IO Libraries
NI GPIB-USB-HS   — USB-to-GPIB adapter; uses NI-VISA
Both present GPIB resources as  GPIB<board>::<addr>::INSTR  to PyVISA.
"""

import time
import logging
from typing import Optional

import pyvisa
import pyvisa.errors

from .visa_manager import VISAManager

logger = logging.getLogger(__name__)

# Shared manager so all instruments on one PC reuse the same RM instance.
_shared_vm: Optional[VISAManager] = None


def _get_shared_vm() -> VISAManager:
    global _shared_vm
    if _shared_vm is None:
        _shared_vm = VISAManager()
    return _shared_vm


class GPIBInstrument:
    """
    Base class for HP GPIB instruments.

    Subclasses should override `initialize()` to put the instrument in a
    known state after connection, and optionally `_idn_fallback()` for
    instruments that predate IEEE 488.2 (e.g. HP 4145A).
    """

    # ── Timing constants ─────────────────────────────────────────────────────
    GPIB_OPEN_TIMEOUT_MS = 5_000    # time allowed to open the resource
    GPIB_TIMEOUT_MS      = 30_000   # per-command timeout (instruments can be slow)
    IDN_RETRY_DELAY_S    = 0.3      # pause before retrying *IDN?
    CONNECT_RETRY_DELAY_S = 0.5     # pause before retrying open_resource

    def __init__(self, resource_string: str = "", timeout_ms: int = 0):
        self.resource_string = resource_string
        self.timeout_ms = timeout_ms or self.GPIB_TIMEOUT_MS
        self._vm  = _get_shared_vm()
        self._res: Optional[pyvisa.resources.Resource] = None
        self.connected = False
        self.idn = ""

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self, resource_string: Optional[str] = None) -> bool:
        """
        Open the VISA resource and identify the instrument.

        Retries once on a VISA I/O error (common after a prior scan or
        disconnect leaves the bus briefly busy).  Calls viClear() before
        querying *IDN? to flush any stale measurement data.

        Returns True on success.
        """
        if resource_string:
            self.resource_string = resource_string

        for attempt in range(2):
            try:
                self._res = self._vm.open_resource(
                    self.resource_string,
                    open_timeout=self.GPIB_OPEN_TIMEOUT_MS,
                    timeout_ms=self.timeout_ms,
                )
                break
            except pyvisa.errors.VisaIOError as exc:
                if attempt == 0:
                    logger.warning(
                        "open_resource failed (attempt 1, retrying): %s", exc
                    )
                    time.sleep(self.CONNECT_RETRY_DELAY_S)
                else:
                    logger.error("Connection failed (%s): %s", self.resource_string, exc)
                    return False
            except Exception as exc:
                logger.error("Connection failed (%s): %s", self.resource_string, exc)
                return False

        # Device clear — flushes instrument output buffer and resets parser.
        # viClear() is a no-op on GPIB if the board doesn't support SDC;
        # ignore any error rather than aborting the connect sequence.
        try:
            self._res.clear()
            time.sleep(0.05)
        except Exception as exc:
            logger.debug("viClear() skipped: %s", exc)

        # Query *IDN? with one retry.  Some instruments (HP 4145B, 4156) take
        # ~200 ms to respond after a device clear.
        self.idn = ""
        for attempt in range(2):
            try:
                self.idn = self._res.query("*IDN?").strip()
                break
            except Exception as exc:
                if attempt == 0:
                    logger.debug("*IDN? failed (attempt 1): %s — retrying", exc)
                    time.sleep(self.IDN_RETRY_DELAY_S)
                else:
                    # Last resort: instrument may predate IEEE 488.2 (HP 4145A).
                    logger.debug("*IDN? gave no response — trying instrument fallback")
                    self.idn = self._idn_fallback()

        self.connected = True
        logger.info("Connected: %s  IDN: %s", self.resource_string, self.idn or "<none>")
        return True

    def disconnect(self):
        """Close the VISA resource gracefully."""
        if self._res:
            try:
                self._res.close()
            except Exception:
                pass
            self._res = None
        self.connected = False
        logger.info("Disconnected: %s", self.resource_string)

    # ------------------------------------------------------------------
    # Instrument lifecycle hooks (override in subclasses)
    # ------------------------------------------------------------------

    def initialize(self):
        """Put the instrument in a known state.  Called after connect()."""

    def _idn_fallback(self) -> str:
        """
        Called when *IDN? fails — used for pre-IEEE 488.2 instruments.
        Subclasses may send a benign command and return a static model string.
        Returns "" if the instrument cannot be identified.
        """
        return ""

    # ------------------------------------------------------------------
    # Low-level I/O
    # ------------------------------------------------------------------

    def write(self, cmd: str):
        if not self.connected or self._res is None:
            raise RuntimeError(f"Not connected to {self.resource_string}")
        logger.debug("WRITE >> %s", cmd)
        self._res.write(cmd)

    def query(self, cmd: str) -> str:
        if not self.connected or self._res is None:
            raise RuntimeError(f"Not connected to {self.resource_string}")
        logger.debug("QUERY >> %s", cmd)
        resp = self._res.query(cmd)
        logger.debug("       << %s", resp.strip())
        return resp

    def read(self) -> str:
        if not self.connected or self._res is None:
            raise RuntimeError(f"Not connected to {self.resource_string}")
        resp = self._res.read()
        logger.debug("READ  << %s", resp.strip())
        return resp

    def read_raw(self) -> bytes:
        if self._res is None:
            raise RuntimeError(f"Not connected to {self.resource_string}")
        return self._res.read_raw()

    # ------------------------------------------------------------------
    # VISA resource listing helpers (class-level, uses shared VM)
    # ------------------------------------------------------------------

    @staticmethod
    def list_resources() -> list:
        """Return all available VISA resource strings."""
        return _get_shared_vm().list_resources()

    @staticmethod
    def list_resources_with_info(skip: "set | None" = None) -> list:
        """Return probed resources with IDN metadata (for the connection panel scan)."""
        return _get_shared_vm().list_resources_with_info(skip=skip)

    # ------------------------------------------------------------------
    # Standard IEEE 488.2 helpers
    # ------------------------------------------------------------------

    def reset(self):
        """*RST — reset instrument to factory defaults."""
        self.write("*RST")
        time.sleep(0.5)

    def clear(self):
        """*CLS — clear status registers and event queues."""
        self.write("*CLS")

    def wait_complete(self):
        """*OPC? — block until all pending operations finish."""
        self.query("*OPC?")

    def get_errors(self) -> str:
        """Query SCPI error queue (:SYST:ERR?)."""
        try:
            return self.query(":SYST:ERR?").strip()
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # GPIB bus-management helpers
    # ------------------------------------------------------------------

    def device_clear(self):
        """
        Send Selected Device Clear (SDC) to flush the instrument's input and
        output buffers.  Equivalent to pressing the instrument front-panel
        RESET/LOCAL key without changing settings.
        """
        if self._res is None:
            return
        try:
            self._res.clear()
            time.sleep(0.05)
            logger.debug("Device Clear sent to %s", self.resource_string)
        except Exception as exc:
            logger.debug("Device Clear failed: %s", exc)

    def interface_clear(self):
        """
        Assert the GPIB IFC (Interface Clear) line.  Resets all bus devices
        to their idle state and makes the controller CIC (Controller-In-Charge).

        Requires that the VISA resource manager supports the viGpibSendIFC()
        operation (available in NI-VISA and Keysight IO Libraries).
        """
        if self._res is None:
            return
        try:
            # viGpibSendIFC is exposed as visalib.send_ifc on pyvisa ≥ 1.12
            self._res.visalib.send_ifc(self._res.session)
            time.sleep(0.05)
            logger.info("IFC (Interface Clear) asserted on %s", self.resource_string)
        except AttributeError:
            logger.debug("visalib.send_ifc not available on this backend")
        except Exception as exc:
            logger.debug("IFC failed: %s", exc)

    def bus_reset(self):
        """
        Full GPIB bus recovery sequence:
          1. Device Clear (SDC)    — flush instrument buffers
          2. Interface Clear (IFC) — reset bus to idle
          3. *CLS                  — clear status registers
        Use after a measurement error or timeout.
        """
        logger.info("GPIB bus reset on %s", self.resource_string)
        self.device_clear()
        self.interface_clear()
        try:
            self.clear()
        except Exception:
            pass
        time.sleep(0.2)
