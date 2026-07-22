# Changelog

All notable changes to the HP Semiconductor Analyzer Controller are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html):
`MAJOR.MINOR.PATCH` — breaking . feature . bugfix

---

## [Unreleased]

> Changes staged but not yet versioned.

- Nothing pending.

---

## [1.1.2] — 2026-05-29

### Fixed — VISA Scan Subprocess Isolation

- **Root cause:** `agvisa32.dll` (Keysight IO Libraries Suite) could trigger a
  native Windows access violation during `viFindRsrc` or `viOpen` on the
  Keysight 82351B PCIe GPIB card, killing the entire Python process with a
  silent crash-to-desktop. No Python exception handler survives a kernel-mode
  DLL fault.

- **Fix:** VISA scan now runs in a completely isolated `multiprocessing.Process`
  (`src/instruments/visa_manager.py` — `_scan_in_process()`). A DLL crash kills
  only the subprocess; the main GUI process waits up to 30 s, reads the exit
  code, and either displays the results or shows a meaningful error message
  (`"VISA scan process crashed (exit …)"`) instead of disappearing.

- **`main.py`** — added `multiprocessing.freeze_support()` before `main()`;
  required for PyInstaller frozen EXEs on Windows so that spawned worker
  subprocesses do not re-launch the GUI.

- **`src/gui/connection_panel.py`** — `_ScanWorker.run()` replaced with
  subprocess launcher: spawns `_scan_in_process` via `multiprocessing.Process`,
  joins with 30 s timeout, checks `p.exitcode`, recovers gracefully on crash
  or timeout.

- **`src/instruments/visa_manager.py`** — `_call_with_timeout()` helper retained
  (still provides per-resource 5 s and per-`viFindRsrc` 10 s timeouts for
  non-crashing hangs); `_scan_in_process()` module-level function added as the
  subprocess entry point.

### Fixed — Build Script PS5.1 Compatibility

- **`build_exe.ps1`** — changed `$ErrorActionPreference = "Stop"` to `"Continue"`.
  In PowerShell 5.1, any native executable that writes to stderr (pip notices,
  PyInstaller INFO logs, ISCC progress) triggers a `NativeCommandError` under
  `Stop` mode and, when caught with `try/catch`, resets `$LASTEXITCODE` to a
  non-zero value even if the process exited successfully. All native exe failures
  are now detected exclusively via `$LASTEXITCODE` checks; PS cmdlet failures
  still bubble up naturally. Also added `--disable-pip-version-check` to pip
  calls to suppress the "new version available" stderr notice.

---

## [1.1.1] — 2026-05-29

### Fixed — Installer

- **`installer.iss`** — removed the `InitializeSetup()` pre-install check that
  looked for `dist\HP_Analyzer\HP_Analyzer.exe` relative to `{src}` (the Inno
  Setup source-directory constant, which resolves to the installer EXE's own
  directory at install time on the end-user machine). The dist folder is baked
  into the installer binary during compilation; Inno Setup would have already
  failed to compile if the folder were missing, making the runtime check both
  incorrect and redundant. The check caused every clean install to abort with
  "the application bundle was not found." Installer rebuilt as
  `release\HP_Analyzer_v1.1.0_Setup.exe`.

---

## [1.1.0] — 2026-05-28

### Added — HP 4155A/B/C Instrument Support

- **`src/instruments/hp4155.py`** — new driver for the HP 4155A / 4155B / 4155C
  Semiconductor Parameter Analyzer. Inherits HP4156 command set; enforces 2-SMU
  limit (4155 has no SMU3/SMU4) and disables VMU channels (absent on 4155).
  Model variant detected from `*IDN?` response on connect.

### Added — Robust GPIB Connectivity

- **`src/instruments/visa_manager.py`** — `VISAManager` class:
  auto-detects NI-VISA → Keysight IO Libraries Suite → pyvisa-py (fallback),
  USB deduplication by (vendor, product, serial) key, IDN-based deduplication
  across interfaces, NCIC error skipping (already-held resources), HP-model
  detection from IDN strings.

- **`src/instruments/base_instrument.py`** rewritten with:
  - `viClear()` (SDC) before every `*IDN?` to flush stale buffer data
  - Retry `open_resource()` once on VisaIOError (bus briefly busy after scan)
  - Retry `*IDN?` once with pause (slow instruments post-device-clear)
  - `_idn_fallback()` hook — HP 4145A predates IEEE 488.2 and doesn't respond
    to `*IDN?`; the hook sends `BC` as a liveness probe and returns a synthetic
    IDN string so the 4145A now connects reliably
  - `bus_reset()` helper — sends SDC + IFC + `*CLS`; call after any timeout
  - `interface_clear()` — asserts the GPIB IFC line via `visalib.send_ifc()`

### Added — Measurement Queue

- **`src/measurements/queue_manager.py`** — `MeasurementQueue` with per-item
  status tracking (PENDING / RUNNING / DONE / ABORTED / ERROR), add/remove/
  reorder operations, and auto-export callback.
- **`src/gui/panels/queue_panel.py`** — dockable queue management widget with
  Run Queue / Stop buttons, per-item export checkboxes, CSV/Excel/Both format
  selector, and live status icons.

### Added — Wiring Guide (F1)

- **`src/gui/dialogs/wiring_guide_dialog.py`** — dark-themed HTML wiring guide
  covering GPIB setup for Keysight 82351B and NI USB-GPIB, channel maps for all
  four instruments, and connection diagrams for every measurement type.
  Opens from **Help → Wiring Guide…** or press **F1**.

### Changed — Connection Panel

- **`src/gui/connection_panel.py`** completely redesigned:
  - Per-instrument rows with colored status dots (grey / amber / green / red)
  - Background `QThread` VISA scan (GUI stays responsive during scan)
  - **Manual entry** — type any VISA resource string + pick instrument model
  - **Bus Reset** button (active while connected) — sends SDC + IFC + `*CLS`
  - Auto-detects driver class (HP4145/HP4155/HP4156/HP4280) from IDN string

### Changed — Main Window

- Added Measurement Queue as a `QDockWidget` on the right (dockable, floatable,
  closable via **View → Measurement Queue**).
- Added **Help** menu with Wiring Guide (F1) and About dialog.
- `_on_connected()` now handles HP4155 in addition to HP4145/HP4156/HP4280.

### Changed — One-Click Installer

- **`installer.iss`** — new Inno Setup 6 script that packages
  `dist\HP_Analyzer\` into a single `HP_Analyzer_v<ver>_Setup.exe`:
  - Installs to `%ProgramFiles%\HP Semiconductor Analyzer\`
  - Start Menu group + optional Desktop shortcut
  - Add/Remove Programs registration with uninstaller
  - Post-install VISA-driver note if NI-VISA / Keysight IO are not detected
- **`build_exe.ps1`** — new `-Installer` flag runs Inno Setup automatically;
  `-ZipOutput` zips the portable folder; version kept in sync with git tag.
- **`build_exe.bat`** — same flags: `/installer` and `/clean`.
- **`hp_analyzer.spec`** — updated with all new modules; removed deprecated
  `cipher=block_cipher` for PyInstaller 6 compatibility.

---

## [1.0.2] — 2026-04-11

### Fixed — Generic 4-Port SMU Layout Overflow

- **`src/gui/panels/generic_panel.py`** — complete layout redesign:
  - **Problem:** `SMUConfigRow` used a single `QHBoxLayout` with 5 labeled
    spinboxes side-by-side. At any normal panel width (240–360 px) this
    overflowed the tab, pushing widgets off-screen at all resolutions.
  - **Fix:** Replaced with `SMUConfigBox` — a `QGroupBox` per SMU containing
    a vertical `QFormLayout`. Only the fields relevant to the selected role
    are shown; hiding both the label and field widget collapses the row in
    Qt 5.15's `QFormLayout`.
  - Four `SMUConfigBox` widgets sit inside a `QScrollArea` (horizontal
    scrollbar disabled) so the left panel never overflows regardless of
    DPI or window size.
  - Role visibility:
    - `SWEEP_V` / `STEP_V` → Start, Stop, Step, Compliance
    - `CONST_V` / `CONST_I` → Value, Compliance
    - `GROUND` / `FLOAT`   → no fields
  - Fixed `nstep` calculation: `round(abs(stop-start)/step)` with zero-step
    guard replaces the bare `int()` cast that could produce 0.

### Changed — EXE Rebuilt

- `dist/HP_Analyzer/` rebuilt with PyInstaller to include all v1.0.1 and
  v1.0.2 fixes (DPI scaling, button text clipping, Generic panel overflow).
  Previous v1.0.0 EXE did not include any of these fixes.

---

## [1.0.1] — 2026-04-11

### Fixed — DPI Scaling & Button Text Clipping

- **`src/gui/dpi.py`** *(new file)* — DPI utility module:
  - `dp(n)` scales any pixel value by the screen's logical DPI factor; use for
    minimum widths, icon sizes, margins, and fixed-size widgets
  - `em(n)` returns `n × QFontMetrics.height()` — sizes relative to text height
  - `scale_factor()` returns logical DPI ÷ 96 (e.g. 1.5 at 144 DPI / 1440p @ 150 %)
  - `base_font_pt()` returns a DPI-scaled point size clamped to 9–18 pt

- **`main.py`** — HiDPI setup hardened:
  - `Qt.HighDpiScaleFactorRoundingPolicy.PassThrough` now set before
    `QApplication` is constructed; without this Qt rounded fractional DPI
    factors (1.25×, 1.5×, 1.75×) down to 1× causing tiny UI on 1440p/5K2K
    monitors set to 125 % or 150 % in Windows Display Settings
  - Base font size now derived from `base_font_pt()` (live DPI) instead of
    hardcoded `9`
  - Stylesheet built by `build_stylesheet()` after font is set so all em-based
    sizes are computed against the correct font metrics

- **`src/gui/styles.py`** — full rewrite of size constants:
  - All `px` hardcodes replaced with expressions derived from `_em()` and
    `QFontMetrics` at call time — every padding, radius, tab height, scrollbar
    width, checkbox size, and minimum button width now scales with DPI
  - `QPushButton` given `min-width: 4em` so text never overflows regardless of
    locale or font size
  - `QTabBar::tab` given `min-width: 4em` so tab labels never clip
  - Spinner up/down arrow width scales with font
  - `build_stylesheet()` factory function replaces module-level `STYLESHEET`
    constant; legacy `STYLESHEET = ""` stub kept for import compatibility

- **`src/gui/connection_panel.py`**:
  - All `setFixedWidth` calls replaced with `setMinimumWidth(dp(n))` —
    instrument model combo, VISA resource combo, Scan, and Connect buttons
    now grow if the DPI-scaled text exceeds the old fixed cap
  - VISA resource combo given `stretch=1` so it fills available space
  - `StatusLED.setFixedSize` uses `dp(14)` and `border-radius` derived from
    the scaled diameter

- **`src/gui/plot_canvas.py`**:
  - Removed `setFixedWidth(60)` from **Clear** button and `setFixedWidth(80)`
    from **Save PNG** button — these were the primary clipping sites
  - Canvas `setMinimumHeight` uses `dp(280)`

- **`src/gui/results_table.py`**:
  - Removed `setFixedWidth(60)` from **CSV** and **Excel** export buttons
  - Button labels clarified: "CSV" → "Save CSV", "Excel" → "Save Excel"
  - Minimum widths set via `dp()`

- **`src/gui/panels/base_panel.py`**:
  - Progress bar changed from `setFixedWidth(160)` to
    `setMinimumWidth(dp(160))` + `setMaximumWidth(dp(260))`
  - Left parameter panel uses `setMinimumWidth(dp(240))` +
    `setMaximumWidth(dp(360))` instead of a single fixed maximum
  - Results panel min/max height uses `dp()`

- **`src/gui/panels/generic_panel.py`**:
  - Role combo `setFixedWidth(110)` → `setMinimumWidth(dp(110))`
  - All five spinbox widgets `setFixedWidth(90)` → `setMinimumWidth(dp(80))`

### Resolution Coverage

| Resolution | Typical Windows DPI % | scale_factor() | Notes |
| --- | --- | --- | --- |
| 1280×720 (720p) | 100 % | 1.00 | Baseline, 9 pt font |
| 1920×1080 (1080p) | 100 % | 1.00 | Standard lab workstation |
| 2560×1440 (1440p) | 125 % | 1.25 | Fractional — PassThrough required |
| 3840×2160 (4K UHD) | 150–200 % | 1.50–2.00 | Common on high-DPI displays |
| 5120×2160 (5K2K) | 175–200 % | 1.75–2.00 | Fractional — PassThrough required |

---

## [1.0.0] — 2026-04-11

### Added — Instruments

- **HP 4145A/B driver** (`src/instruments/hp4145.py`)
  - Full token-based command set: `DE`, `SS`, `MM`, `ME1`, `DO`, `BC`
  - SMU channel definition (`define_smu`), VSU/VMU channel support
  - VAR1/VAR2 voltage and current sweep setup
  - Constant voltage/current source methods
  - STB polling for measurement completion
  - ASCII data parser with status-character stripping
  - `run_iv_sweep()` convenience method

- **HP 4156A/B driver** (`src/instruments/hp4156.py`)
  - `:PAGE:MEAS:*` SCPI-like command set
  - Primary sweep (VAR1), secondary step (VAR2), constant sources
  - Integration time: SHORT / MED / LONG
  - Hold and delay time configuration
  - `run_iv_sweep()` and `run_family_of_curves()` convenience methods
  - STB polling for completion

- **HP 4280A driver** (`src/instruments/hp4280.py`)
  - 1 MHz C-V plotter support
  - Measurement modes: CPGP, CPRP, CSRS, CSGS
  - Bias voltage sweep with per-point settling delay
  - Integration time: FAST / MEDIUM / SLOW
  - Cable length compensation (0, 1, 2 m)
  - `cv_sweep()` returns (V_bias, C, G) NumPy arrays

- **Base instrument** (`src/instruments/base_instrument.py`)
  - PyVISA resource manager with NI-VISA, Keysight IO, and `@py` fallback
  - `list_resources()` static method for VISA resource discovery
  - IEEE 488.2 helpers: `*RST`, `*CLS`, `*OPC?`, `SYST:ERR?`

### Added — Measurements

- **MOSFET Transfer Curve** (`src/measurements/mosfet.py`)
  - Id–Vgs sweep at fixed Vds
  - Threshold voltage extraction: linear extrapolation, √Id, and constant-current methods
  - Transconductance gm = dId/dVgs (numerical gradient)
  - Subthreshold slope S (mV/dec)
  - Ion, Ioff, Ion/Ioff ratio

- **MOSFET Output Curve** (`src/measurements/mosfet.py`)
  - Id–Vds family of curves for configurable Vgs steps
  - HP4156: uses native `VAR2` step; HP4145: sequential single sweeps

- **Diode I-V** (`src/measurements/diode_iv.py`)
  - Anode–cathode voltage sweep
  - Log-domain fit: saturation current I₀, ideality factor n
  - Series resistance Rₛ from high-current deviation

- **Resistor I-V** (`src/measurements/resistor_iv.py`)
  - Two-terminal voltage sweep
  - Linear fit R = V/I

- **Capacitance C-V** (`src/measurements/capacitance_cv.py`)
  - HP 4280A bias sweep via per-point `set_bias_voltage` + `measure_single`
  - Extracts: Cox, tox, Vfb (Berglund midgap method), Vth (approx), Nₐ, Cmin
  - MOS capacitor parameter extraction (area-normalized)

- **Van der Pauw** (`src/measurements/van_der_pauw.py`)
  - 8-configuration resistance measurement (4 configurations × 2 directions)
  - Numerical Van der Pauw equation solve via `scipy.optimize.brentq`
  - Optional Hall measurement: R_Hall, ns (sheet carrier density), µH, carrier type

- **Kelvin 4-Probe** (`src/measurements/kelvin_4probe.py`)
  - Force current on outer probes, measure voltage on inner probes
  - Optional current sweep for R vs I characterization
  - R_mean and R_std over configurable averages

- **Hall Bar** (`src/measurements/hall_bar.py`)
  - Longitudinal resistance Rxx and transverse Hall resistance Rxy
  - Derived: sheet resistance Rs = Rxx × (W/L), sheet carrier density ns, Hall mobility µH
  - Optional 3D carrier density n₃D (requires film thickness)
  - Carrier type determination from sign of Rxy

- **Generic 4-Port** (`src/measurements/generic_4port.py`)
  - Per-SMU role assignment: SWEEP_V, STEP_V, CONST_V, CONST_I, GROUND, FLOAT
  - Dynamic parameter visibility in GUI
  - Works with both HP4145 and HP4156

- **Base measurement worker** (`src/measurements/base_measurement.py`)
  - `QThread` subclass with `progress`, `point_ready`, `result_ready`, `error`, `status` signals
  - `MeasurementResult` container with `to_dataframe()`, `save_csv()`, `save_excel()`
  - `abort()` cooperative cancellation

### Added — GUI

- **Main window** (`src/gui/main_window.py`)
  - 8-tab measurement area (MOSFET, Diode, Resistor, C-V, Van der Pauw, Kelvin, Hall Bar, Generic)
  - C-V tab automatically disabled when non-4280A instrument connected
  - Qt status bar with live connection and measurement status

- **Connection panel** (`src/gui/connection_panel.py`)
  - Instrument model dropdown (4145A, 4145B, 4156A, 4156B, 4280A)
  - VISA resource editable combobox with **Scan** button
  - Background `_ConnectThread` prevents GUI freeze during connect
  - `StatusLED` widget: grey = disconnected, orange = connecting, green = connected
  - IDN string display

- **Plot canvas** (`src/gui/plot_canvas.py`)
  - Matplotlib `FigureCanvasQTAgg` with dark theme matching Qt stylesheet
  - Multiple named series with automatic color cycling (8 colors)
  - Log-X and Log-Y axis toggles (checkboxes)
  - NavigationToolbar2QT for zoom/pan/home
  - Mouse coordinate readout
  - **Save PNG** button
  - `add_point()` for live streaming; `set_data()` for batch update; `clear()`

- **Results panel** (`src/gui/results_table.py`)
  - **Analysis** tab: key–value table of extracted parameters
  - **Raw Data** tab: scrollable DataFrame preview (up to 500 rows)
  - **CSV** and **Excel** export buttons

- **Base panel** (`src/gui/panels/base_panel.py`)
  - Standard layout: Run / Abort buttons, progress bar, status label
  - Horizontal splitter: parameter form (left, fixed 340 px) | plot (right, expanding)
  - Results panel below (max 200 px)
  - Connects worker signals to plot, results, and status automatically

- **Dark stylesheet** (`src/gui/styles.py`)
  - Background `#1E1E2E`, panel `#2A2A3E`, accent `#2196F3`
  - Styled: QPushButton (normal / hover / pressed / disabled / danger / success),
    QGroupBox, QLineEdit, QDoubleSpinBox, QComboBox, QTabWidget, QTableWidget,
    QProgressBar, QCheckBox, QRadioButton, QScrollBar, QStatusBar

- **Form helpers** (`src/gui/panels/form_helpers.py`)
  - `make_dspin()`, `make_spin()`, `make_combo()`, `ch_combo()`, `form_group()`, `group()`

- **Measurement panels** (all in `src/gui/panels/`)
  - `mosfet_panel.py`: TransferCurvePanel + OutputCurvePanel in sub-tabs
  - `diode_panel.py`, `resistor_panel.py`, `cv_panel.py`
  - `van_der_pauw_panel.py`, `kelvin_panel.py`, `hall_bar_panel.py`
  - `generic_panel.py`: `SMUConfigRow` with dynamic role-based field visibility

### Added — Build & Distribution

- **`hp_analyzer.spec`** — PyInstaller spec (folder mode, `console=False`,
  all hidden imports, `config/` data bundle)
- **`build_exe.ps1`** — PowerShell build script (auto-venv, `-ZipOutput`, `-Clean`)
- **`build_exe.bat`** — CMD batch fallback

### Added — Documentation

- **`README.md`** — project overview, instrument table, measurement table,
  install commands, project structure tree
- **`INSTALL.md`** — step-by-step installation guide (3 options: EXE, source, build)
- **`PROMPT_ENGINEERING.md`** — full record of AI prompts and actions
- **`CHANGELOG.md`** — this file

### Added — Repository

- Git repository initialized
- `.gitignore` (Python standard + data files)
- `setup.py` with entry point `hp-analyzer`
- `requirements.txt`
- Repository pushed to `https://github.com/prashantUCSB/hp-semiconductor-analyzer`

---

## Planned — Future Versions

### [1.1.0] — Planned

- [ ] Auto-save measurements to timestamped CSV on Run completion
- [ ] Measurement sequence editor (run multiple measurements in order)
- [ ] Dark/light theme toggle in menu bar
- [ ] Keithley 4200-SCS support (same panel framework)
- [ ] Log panel showing all GPIB traffic in real time
- [ ] MOSFET: body effect measurement (Vth vs Vsb)

### [1.2.0] — Planned

- [ ] Open/short/load compensation for C-V (4280A)
- [ ] Frequency-dependent C-V (requires HP 4284A or equivalent)
- [ ] Noise measurement tab (if supported by instrument)
- [ ] Python scripting console tab (call measurement objects directly)
- [ ] HDF5 data export

### [2.0.0] — Planned

- [ ] Wafer mapping: grid of devices, automated measurement at each site
- [ ] Database backend (SQLite) for measurement storage and retrieval
- [ ] Plugin API for third-party instrument drivers
