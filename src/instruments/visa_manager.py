"""
VISA resource manager for HP semiconductor analyzers.

Auto-detects NI-VISA, Keysight IO Libraries Suite, or pyvisa-py as fallback.
Handles GPIB (Keysight 82351B, NI GPIB-USB), USB-TMC, and LAN interfaces.
Includes IDN-based deduplication, NCIC error skipping, and HP model detection.
"""
from __future__ import annotations

import concurrent.futures
import logging
import re
from typing import Optional

import pyvisa
import pyvisa.errors

log = logging.getLogger(__name__)

# HP/Agilent/Keysight GPIB addresses typical for these instruments
# (reference only — the scan probes whatever VISA reports)
_HP_TYPICAL_ADDRESSES = {
    "HP4145": [17],
    "HP4155": [17],
    "HP4156": [17],
    "HP4280": [22],
}

# Keywords that identify an HP semiconductor analyzer in the IDN response
_HP_IDN_KEYS = (
    "4145", "4155", "4156", "4280",
    "HEWLETT-PACKARD", "AGILENT", "KEYSIGHT",
)

_BACKEND_CANDIDATES = [
    "",      # default: NI-VISA or Keysight IO (whichever is on PATH)
    "@py",   # pyvisa-py pure-Python fallback
]

# Pre-compiled USB resource-string patterns (for deduplication on USB-GPIB adapters)
_USB_SERIAL_RE = re.compile(
    r"USB\d*::0x([0-9A-Fa-f]+)::0x([0-9A-Fa-f]+)::([^:]+)",
    re.IGNORECASE,
)
_USB_RE = re.compile(
    r"USB\d*::0x([0-9A-Fa-f]+)::0x([0-9A-Fa-f]+)::",
    re.IGNORECASE,
)


class VISAManager:
    """
    Manages PyVISA resource manager lifecycle and provides HP-aware scanning.

    Usage
    -----
    vm = VISAManager()
    results = vm.list_resources_with_info()
    res = vm.open_resource("GPIB0::17::INSTR", open_timeout=5000)
    """

    def __init__(self, backend: str = "") -> None:
        self._rm: Optional[pyvisa.ResourceManager] = None
        self._preferred_backend = backend
        self._open()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _open(self) -> None:
        candidates = [self._preferred_backend] if self._preferred_backend else _BACKEND_CANDIDATES
        for backend in candidates:
            try:
                self._rm = pyvisa.ResourceManager(backend) if backend else pyvisa.ResourceManager()
                log.info("VISA backend: %s", self._rm.visalib)
                return
            except Exception as exc:
                log.debug("Backend '%s' unavailable: %s", backend, exc)
        raise RuntimeError(
            "No VISA backend found.\n"
            "Install one of:\n"
            "  • NI-VISA (https://www.ni.com/visa)\n"
            "  • Keysight IO Libraries Suite (Keysight 82351B users)\n"
            "  • pip install pyvisa-py  (software-only fallback)"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def resource_manager(self) -> pyvisa.ResourceManager:
        if self._rm is None:
            self._open()
        return self._rm  # type: ignore[return-value]

    def list_resources(self) -> list[str]:
        """Raw list of all VISA resource strings."""
        try:
            return list(self._rm.list_resources())  # type: ignore[union-attr]
        except Exception as exc:
            log.error("list_resources failed: %s", exc)
            return []

    def list_resources_with_info(
        self, skip: "set[str] | None" = None
    ) -> list[dict]:
        """
        Probe each VISA resource and return only reachable instruments with IDN data.

        Parameters
        ----------
        skip : resource strings already held open by connected drivers — re-opening
               them causes VI_ERROR_NCIC; they are excluded from the probe but their
               rows are already in the UI.

        Serial (ASRL) ports are always skipped — they time out on *IDN? and are
        not used by any HP semiconductor analyzer.
        """
        skip = skip or set()

        # list_resources() calls viFindRsrc() which on some Keysight GPIB setups
        # can also block. Run it in a thread with a hard 10 s wall-clock timeout.
        all_resources = self._call_with_timeout(self.list_resources, timeout=10.0) or []
        log.info("VISA scan: %d resource(s) found", len(all_resources))

        # Deduplicate USB resources by (vendor, product, serial)
        seen_usb_keys: set[tuple] = set()
        deduped: list[str] = []
        for rstr in all_resources:
            key = self._usb_device_key(rstr)
            if key is not None:
                if key in seen_usb_keys:
                    log.debug("Skipping duplicate USB resource: %s", rstr)
                    continue
                seen_usb_keys.add(key)
            deduped.append(rstr)

        # Build skip-by-USB-key set so both variant strings of a connected device
        # are excluded even when NI-VISA returns a different variant string.
        skip_usb_keys: set[tuple] = set()
        for s in skip:
            k = self._usb_device_key(s)
            if k is not None:
                skip_usb_keys.add(k)

        seen_idns: set[str] = set()
        results: list[dict] = []

        for rstr in deduped:
            if rstr.upper().startswith("ASRL"):
                log.debug("Skipping serial port: %s", rstr)
                continue

            if rstr in skip:
                log.debug("Skipping already-connected resource: %s", rstr)
                continue

            rstr_key = self._usb_device_key(rstr)
            if rstr_key is not None and rstr_key in skip_usb_keys:
                log.debug("Skipping USB variant of connected resource: %s", rstr)
                continue

            # Run the probe in a thread with a hard 5 s wall-clock timeout.
            # IMPORTANT: do NOT use `with ThreadPoolExecutor() as ex:` -- the
            # context manager calls shutdown(wait=True) on exit, which blocks
            # forever if the worker thread is hung in the VISA DLL.
            # Use shutdown(wait=False) so we abandon the thread and move on.
            info = self._call_with_timeout(self._probe_one, timeout=5.0, args=(rstr,))

            if info is None:
                log.warning("Scan probe timed out or failed for %s -- skipping", rstr)
                continue

            idn = info["idn"]
            # IDN-based deduplication
            if idn and idn in seen_idns:
                log.info("Skipping %s -- duplicate IDN already seen", rstr)
                continue
            if idn:
                seen_idns.add(idn)

            log.info("Found: %s  IDN=%r", rstr, idn)
            results.append(info)

        log.info("VISA scan complete: %d instrument(s) found", len(results))
        return results

    @staticmethod
    def _call_with_timeout(fn, timeout: float, args: tuple = ()) -> object:
        """Call fn(*args) in a daemon thread; return None if it exceeds timeout.

        Uses shutdown(wait=False) so a hung VISA thread is abandoned rather than
        blocking the caller.  The leaked thread keeps running in the background
        but causes no further harm once its VISA call finally returns or crashes.
        """
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = ex.submit(fn, *args)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return None
        except Exception as exc:
            log.debug("_call_with_timeout error: %s", exc)
            return None
        finally:
            # wait=False: do NOT block if the thread is stuck in the VISA DLL
            ex.shutdown(wait=False)

    def _probe_one(self, rstr: str) -> "dict | None":
        """Open one VISA resource, query *IDN?, return info dict or None.

        Called from a ThreadPoolExecutor thread so the caller can enforce a
        hard wall-clock timeout independent of VI_ATTR_TMO_VALUE.
        Never calls res.clear() / SDC -- that is reserved for actual connect.
        """
        try:
            res = self._rm.open_resource(rstr)  # type: ignore[union-attr]
            res.timeout = 3000
            res.read_termination  = "\n"
            res.write_termination = "\n"
            idn = ""
            try:
                idn = res.query("*IDN?").strip()
            except pyvisa.errors.VisaIOError as exc:
                log.debug("*IDN? failed for %s: %s -- trying *STB?", rstr, exc)
                try:
                    res.query("*STB?")
                    idn = ""   # alive but no IDN (e.g. HP 4145A)
                except Exception:
                    idn = ""
            except Exception as exc:
                log.debug("IDN error for %s: %s", rstr, exc)
                idn = ""
            finally:
                try:
                    res.close()
                except Exception:
                    pass
        except pyvisa.errors.VisaIOError as exc:
            if "NCIC" in str(exc):
                log.info("Resource %s held open (NCIC) -- skipping scan probe", rstr)
            else:
                log.debug("Cannot open %s: %s", rstr, exc)
            return None
        except Exception as exc:
            log.debug("Skipping unreachable resource %s: %s", rstr, exc)
            return None

        info = self._parse_resource_string(rstr)
        info["idn"]            = idn
        info["friendly"]       = self._friendly_name(rstr, idn)
        info["is_hp_analyzer"] = self._is_hp_analyzer(rstr, idn)
        return info

    def open_resource(
        self,
        resource_string: str,
        open_timeout: int = 5000,
        timeout_ms: int = 30000,
        read_termination: str = "\n",
        write_termination: str = "\n",
    ) -> pyvisa.resources.Resource:
        """Open a VISA resource with HP-appropriate settings."""
        res = self._rm.open_resource(resource_string, open_timeout=open_timeout)  # type: ignore[union-attr]
        res.timeout = timeout_ms
        res.read_termination  = read_termination
        res.write_termination = write_termination
        return res

    def close(self) -> None:
        if self._rm:
            try:
                self._rm.close()
            except Exception:
                pass
            self._rm = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _usb_device_key(rstr: str) -> "tuple[int, int, str] | None":
        m = _USB_SERIAL_RE.match(rstr)
        if m:
            try:
                return (int(m.group(1), 16), int(m.group(2), 16), m.group(3).upper())
            except ValueError:
                pass
        return None

    @staticmethod
    def _parse_resource_string(rstr: str) -> dict:
        upper = rstr.upper()
        if upper.startswith("GPIB"):
            parts = rstr.split("::")
            addr = parts[1] if len(parts) > 1 else "?"
            return {"resource_string": rstr, "interface": "GPIB",
                    "address": f"GPIB · addr {addr}"}
        if upper.startswith("USB"):
            m = _USB_RE.match(rstr)
            short = f"USB · 0x{m.group(2).upper()}" if m else "USB"
            return {"resource_string": rstr, "interface": "USB", "address": short}
        if upper.startswith("TCPIP"):
            parts = rstr.split("::")
            ip = parts[1] if len(parts) > 1 else "?"
            return {"resource_string": rstr, "interface": "LAN",
                    "address": f"LAN · {ip}"}
        return {"resource_string": rstr, "interface": "Unknown", "address": rstr}

    @staticmethod
    def _is_hp_analyzer(rstr: str, idn: str) -> bool:
        """Return True if the IDN or address suggests an HP/Agilent semiconductor analyzer."""
        combined = (idn + " " + rstr).upper()
        return any(k in combined for k in _HP_IDN_KEYS)

    @staticmethod
    def _friendly_name(rstr: str, idn: str) -> str:
        """Build a human-readable label from IDN or resource string."""
        if idn:
            parts = [p.strip() for p in idn.split(",")]
            # IDN format: MANUFACTURER,MODEL,SERIAL,FIRMWARE
            mfr   = parts[0].upper() if parts else ""
            model = parts[1].upper() if len(parts) > 1 else ""
            model = model.replace("MODEL", "").strip()
            mfr_short = (
                "HP"       if "HEWLETT" in mfr
                else "Agilent" if "AGILENT" in mfr
                else "Keysight" if "KEYSIGHT" in mfr
                else mfr
            )
            if model:
                return f"{mfr_short} {model}"
        # Fall back to GPIB address in resource string
        if rstr.upper().startswith("GPIB"):
            parts = rstr.split("::")
            addr = parts[1] if len(parts) > 1 else "?"
            return f"GPIB instrument at addr {addr}"
        return rstr

    @staticmethod
    def _guess_hp_model(idn: str) -> str:
        """Return the most likely HP model string from IDN content."""
        for key in ("4145B", "4145A", "4155C", "4155B", "4155A",
                    "4156C", "4156B", "4156A", "4280A"):
            if key in idn.upper():
                return key
        return ""


def _scan_in_process(result_queue, skip_list: list) -> None:
    """Entry point for the isolated VISA-scan subprocess.

    Runs in a separate OS process so a native DLL crash (e.g. agvisa32.dll
    access violation) kills only this subprocess, not the main GUI process.
    Must be a module-level function (not a method) so multiprocessing can pickle it.
    """
    try:
        vm = VISAManager()
        results = vm.list_resources_with_info(skip=set(skip_list))
        result_queue.put(("ok", results))
    except Exception as exc:
        result_queue.put(("error", str(exc)))
