# HP Semiconductor Parameter Analyzer Controller

A Python/PyQt5 GUI for controlling HP/Agilent 4145A, 4145B, 4156A, 4156B
Semiconductor Parameter Analyzers and the HP 4280A 1 MHz C-V Plotter via GPIB.

**Current version: 1.0.1** — see [CHANGELOG.md](CHANGELOG.md)

## Supported Instruments

| Instrument | Interface | Notes |
|---|---|---|
| HP 4145A | GPIB | 4 SMU, 2 VSU, 2 VMU |
| HP 4145B | GPIB | Same as A + quasi-static C-V |
| HP 4156A | GPIB | Precision, 4 SMU |
| HP 4156B | GPIB | Same as A, extended ranges |
| HP 4280A | GPIB | 1 MHz C-V plotter |

## GPIB Adapters

- NI USB-GPIB (requires NI-VISA)
- Keysight 82357B USB-GPIB (requires Keysight IO Libraries or NI-VISA)
- Keysight 82351A/B PCIe-GPIB (requires Keysight IO Libraries)
- Pure-Python fallback via `pyvisa-py` + `gpib-ctypes`

## Measurements

| Panel | Measurement | Extracted Parameters |
|---|---|---|
| **MOSFET** | Transfer curve Id–Vgs | Vth, gm_max, SS, Ion/Ioff |
| **MOSFET** | Output curve Id–Vds | Family of curves |
| **Diode I-V** | Forward/reverse I-V | I₀, ideality n, Rs |
| **Resistor** | Two-terminal I-V | R (fitted) |
| **C-V (4280A)** | C-V @ 1 MHz | Cox, tox, Vfb, Vth, NA |
| **Van der Pauw** | Sheet resistance + Hall | Rs, ns, µH, carrier type |
| **Kelvin 4-Probe** | 4-wire R vs I | R_mean, R_std |
| **Hall Bar** | Rxx, Rxy, Hall effect | Rs, ns, µH, n3D, carrier type |
| **Generic 4-Port** | Custom SMU assignment | — |

## Display Resolution Support

The app scales correctly on all standard resolutions and Windows DPI settings:

| Resolution | Windows DPI % | Notes |
|---|---|---|
| 1280×720 | 100 % | Baseline |
| 1920×1080 | 100 % | Standard lab workstation |
| 2560×1440 | 125 % | Fractional scaling — fully supported |
| 3840×2160 | 150–200 % | 4K UHD |
| 5120×2160 | 175–200 % | 5K2K — fractional scaling supported |

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/prashantUCSB/hp-semiconductor-analyzer.git
cd hp-semiconductor-analyzer

# 2. Create a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 3. Install dependencies  ← required before first run
pip install -r requirements.txt

# 4. (Optional) Install NI-VISA or Keysight IO Libraries
#    for hardware GPIB adapter support.
#    PyVISA-py works without these for some adapters.

# 5. Run
python main.py
```

> **Note:** Step 3 is required. The app will not start without the dependencies.
> See [INSTALL.md](INSTALL.md) for the full guide including EXE build instructions.

## Building a Portable EXE (Windows)

```powershell
# Allow scripts (one-time)
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# Build standalone folder → dist\HP_Analyzer\
.\build_exe.ps1

# Build + create distributable ZIP
.\build_exe.ps1 -ZipOutput
```

Copy the entire `dist\HP_Analyzer\` folder to any Windows 10/11 machine.
No Python installation required on the target — only a VISA runtime (NI-VISA
or Keysight IO Libraries).

## Usage

1. **Connect** — select instrument model, click **Scan** to discover VISA
   resources, select `GPIB0::17::INSTR` (or type it), click **Connect**.
2. **Select tab** — MOSFET, Diode, Resistor, C-V, Van der Pauw, Kelvin,
   Hall Bar, or Generic 4-Port.
3. **Assign channels** — match SMU numbers to your physical wiring.
4. **Set parameters** — sweep range, compliance, step count.
5. **Run** — plot updates live as data arrives.
6. **Export** — **Save CSV** or **Save Excel** in the Results panel.

## Project Structure

```
hp-semiconductor-analyzer/
├── main.py                      # Entry point + HiDPI setup
├── requirements.txt
├── setup.py
├── build_exe.ps1                # PowerShell EXE build script
├── build_exe.bat                # CMD batch fallback
├── hp_analyzer.spec             # PyInstaller spec
├── src/
│   ├── instruments/
│   │   ├── base_instrument.py   # PyVISA base class
│   │   ├── hp4145.py            # HP 4145A/B driver
│   │   ├── hp4156.py            # HP 4156A/B driver
│   │   └── hp4280.py            # HP 4280A driver
│   ├── measurements/
│   │   ├── base_measurement.py  # QThread worker base
│   │   ├── mosfet.py            # Transfer + output curves
│   │   ├── diode_iv.py
│   │   ├── resistor_iv.py
│   │   ├── capacitance_cv.py
│   │   ├── van_der_pauw.py
│   │   ├── kelvin_4probe.py
│   │   ├── hall_bar.py
│   │   └── generic_4port.py
│   └── gui/
│       ├── dpi.py               # DPI scaling utilities (dp, em, scale_factor)
│       ├── main_window.py
│       ├── connection_panel.py
│       ├── plot_canvas.py
│       ├── results_table.py
│       ├── styles.py            # Dynamic stylesheet (em-based sizing)
│       └── panels/
│           ├── base_panel.py
│           ├── form_helpers.py
│           ├── mosfet_panel.py
│           ├── diode_panel.py
│           ├── resistor_panel.py
│           ├── cv_panel.py
│           ├── van_der_pauw_panel.py
│           ├── kelvin_panel.py
│           ├── hall_bar_panel.py
│           └── generic_panel.py
├── config/
│   └── default_config.json
├── INSTALL.md
├── CHANGELOG.md
└── PROMPT_ENGINEERING.md
```

## GPIB Address Defaults

| Instrument | Default GPIB Address |
|---|---|
| HP 4145A/B | 17 |
| HP 4156A/B | 17 |
| HP 4280A   | 17 |

## License

MIT
