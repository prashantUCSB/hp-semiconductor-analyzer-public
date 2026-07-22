# Installation Guide — HP Semiconductor Analyzer Controller

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Option A — One-Click Installer (Recommended)](#2-option-a--one-click-installer-recommended)
3. [Option B — Portable Folder](#3-option-b--portable-folder)
4. [Option C — Run from Python Source](#4-option-c--run-from-python-source)
5. [Option D — Build the EXE Yourself](#5-option-d--build-the-exe-yourself)
6. [GPIB Adapter Setup](#6-gpib-adapter-setup)
7. [Instrument GPIB Address](#7-instrument-gpib-address)
8. [First Launch Walkthrough](#8-first-launch-walkthrough)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. System Requirements

| Requirement        | Minimum                               |
| ------------------ | ------------------------------------- |
| OS                 | Windows 10 / 11 (64-bit)              |
| RAM                | 4 GB                                  |
| Disk               | 500 MB free (EXE + VISA libraries)    |
| GPIB Adapter       | NI USB-GPIB, Keysight 82357B, 82351B  |
| Python (src only)  | 3.8 – 3.13                            |

---

## 2. Option A — One-Click Installer (Recommended)

`HP_Analyzer_v<version>_Setup.exe` installs everything through a standard
Windows setup wizard. **No Python required on the target computer.**

### Step 1 — Download the installer

Get the latest `HP_Analyzer_v*_Setup.exe` from the project releases page.

### Step 2 — Run the setup wizard

Double-click `HP_Analyzer_v*_Setup.exe`. The wizard:

1. Shows a Welcome screen
2. Asks for the installation directory (default: `%ProgramFiles%\HP Semiconductor Analyzer\`)
3. Offers an optional Desktop shortcut
4. Copies all files (~180–220 MB)
5. Registers an uninstaller in **Add / Remove Programs**
6. Optionally launches the app immediately

### Step 3 — Install a VISA runtime for GPIB

The installer bundles `pyvisa-py` but not the hardware VISA runtime.
For GPIB adapters (Keysight 82351B, NI USB-GPIB) install **one** of:

**NI-VISA** (recommended for NI USB-GPIB adapters)

1. Download NI-VISA from <https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html>
2. Run the installer; reboot when prompted.
3. Confirm the adapter appears in **NI MAX**.

**Keysight IO Libraries Suite** (recommended for 82357B / 82351B)

1. Download from <https://www.keysight.com/find/iosuite>
2. Install; reboot when prompted.
3. Confirm in **Keysight Connection Expert**.

> If neither VISA runtime is detected the installer shows a reminder dialog
> with direct links to both download pages.

### Step 4 — Launch

Start → **HP Semiconductor Analyzer** → **HP Semiconductor Analyzer**,
or double-click the Desktop shortcut if you created one.

---

## 3. Option B — Portable Folder

Use this to copy the app manually without running a setup wizard.

### Step 1 — Install a VISA runtime

Follow the instructions in [Section 2 → Step 3](#step-3--install-a-visa-runtime-for-gpib).

If you only use PyVISA-py over USB/serial (not GPIB) no external VISA runtime
is needed — the EXE bundles `pyvisa-py` automatically.

### Step 2 — Copy the EXE folder

Copy the entire `dist\HP_Analyzer\` folder to the target computer.
The folder is self-contained — **do not** separate `HP_Analyzer.exe` from
the rest of its folder.

Suggested destination:

```text
C:\Lab Software\HP_Analyzer\
```

### Step 3 — Create a Desktop shortcut (optional)

1. Right-click `HP_Analyzer.exe` → **Send to → Desktop (create shortcut)**.
2. Right-click the shortcut → **Properties** → change icon if desired.

### Step 4 — Open the app

Double-click `HP_Analyzer.exe`.
The window opens; proceed to [Section 8 — First Launch Walkthrough](#8-first-launch-walkthrough).

---

## 4. Option C — Run from Python Source

Use this if you want to modify the code.

### Step 1 — Install Python 3.8+

Download from <https://python.org/downloads>.
During installation check **Add Python to PATH**.

### Step 2 — Install a VISA runtime

Follow [Section 2 → Step 3](#step-3--install-a-visa-runtime-for-gpib).

### Step 3 — Clone the repository

```bash
git clone https://github.com/prashantUCSB/hp-semiconductor-analyzer.git
cd hp-semiconductor-analyzer
```

Or download the ZIP from GitHub → **Code → Download ZIP** and extract it.

### Step 4 — Create a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
```

### Step 5 — Install Python dependencies

```bash
pip install -r requirements.txt
```

> `pyvisa-py` is included for pure-Python GPIB support.
> If NI-VISA or Keysight IO Libraries are installed, `pyvisa` will detect and use
> them automatically.

### Step 6 — Launch

```bash
python main.py
```

---

## 5. Option D — Build the EXE Yourself

Use this to produce a distributable EXE from source.

### Prerequisites

- Python 3.8–3.13 installed and on `PATH`
- Git (optional — only needed to clone)
- Internet access for pip
- Inno Setup 6 or 7 (optional — only needed for the installer EXE)
  Download from <https://jrsoftware.org/isdl.php>

### Step 1 — Open PowerShell in the project folder

```powershell
cd C:\path\to\tcr-HP-Systems
```

### Step 2 — Run the build script

```powershell
# Allow PowerShell scripts to run (one-time, per user)
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# Portable folder only
.\build_exe.ps1

# Portable folder + one-click installer EXE (requires Inno Setup 6)
.\build_exe.ps1 -Installer

# Portable folder + installer + ZIP of portable folder
.\build_exe.ps1 -Installer -ZipOutput

# Clean previous build artefacts first, then build installer
.\build_exe.ps1 -Clean -Installer
```

**Using Command Prompt instead:**

```bat
build_exe.bat
build_exe.bat /installer
build_exe.bat /clean /installer
```

### Step 3 — Locate the output

| Output                                        | Location                                |
| --------------------------------------------- | --------------------------------------- |
| Portable folder (always produced)             | `dist\HP_Analyzer\HP_Analyzer.exe`      |
| One-click installer (with `-Installer` flag)  | `release\HP_Analyzer_v*_Setup.exe`      |
| Portable ZIP (with `-ZipOutput` flag)         | `HP_Analyzer_v*_Windows_Portable.zip`   |

### Build time

First build: ~5–10 minutes (downloads and packages all dependencies).
Subsequent builds (with existing `.venv_build`): ~2–3 minutes.

---

## 6. GPIB Adapter Setup

### NI USB-GPIB (NI Part 778927-01)

1. Install NI-VISA (see [Section 2 → Step 3](#step-3--install-a-visa-runtime-for-gpib)).
2. Plug the USB-GPIB adapter into a USB port.
3. Connect the GPIB cable to the instrument.
4. Open **NI MAX** → confirm the instrument appears under **Devices and Interfaces → GPIB0**.
5. Resource string in the app: `GPIB0::<address>::INSTR`

### Keysight 82357B USB-GPIB

1. Install Keysight IO Libraries Suite.
2. Plug in the 82357B (drivers install automatically).
3. Connect the GPIB cable.
4. Open **Keysight Connection Expert** → verify instrument is detected.
5. Resource string: `GPIB0::<address>::INSTR`

### Keysight 82351A/B PCIe-GPIB

1. Install IO Libraries Suite.
2. Shut down the PC, insert the card, boot.
3. IO Libraries auto-detects the card on first boot.
4. Resource string: `GPIB0::<address>::INSTR`

---

## 7. Instrument GPIB Address

Use the instrument's front panel to verify (or change) the GPIB address.

| Instrument          | Default Addr | Front-panel navigation                  |
| ------------------- | ------------ | --------------------------------------- |
| HP 4145A            | 17           | `LOCAL` → `GPIB` menu                   |
| HP 4145B            | 17           | `LOCAL` → `GPIB` menu                   |
| HP 4155A / 4155B    | 17           | `LOCAL` key → address display           |
| HP 4156A / 4156B    | 17           | `LOCAL` key → address display           |
| HP 4280A            | 22           | Rear-panel DIP switches (S1–S5)         |

> VISA resource string format: `GPIB0::<address>::INSTR`
> Example for address 17: `GPIB0::17::INSTR`

---

## 8. First Launch Walkthrough

1. **Launch** `HP_Analyzer.exe` (or `python main.py`).

2. **Connection panel** (top bar):
   - Click **Scan VISA** to auto-discover instruments.
   - If nothing appears, type the resource string manually (e.g. `GPIB0::17::INSTR`)
     and select the instrument model, then click **Add**.
   - Click **Connect** in the instrument row.
   - The status dot turns green and the IDN string appears.

3. **Select a measurement tab** (e.g., **MOSFET**).

4. **Assign channels** — match SMU numbers in the form to your physical wiring.
   Common MOSFET wiring: Gate → SMU1, Drain → SMU2, Source → SMU3.

5. **Enter sweep parameters** (start, stop, step voltages, compliance).

6. **Click Run** — the plot updates in real time.

7. **Inspect results** — the Analysis section shows extracted parameters (Vth, gm, etc.).

8. **Export** — click **Save CSV** or **Save Excel**.

### Using the Measurement Queue

1. Configure a sweep in any tab.
2. Click **Add to Queue** — the sweep appears in the **Measurement Queue** dock (right side).
3. Repeat for additional sweeps (different channels, different devices).
4. Click **▶▶ Run Queue** — sweeps execute in order, with optional auto-export per item.

---

## 9. Troubleshooting

### "No VISA resources found" after Scan

- Confirm the GPIB adapter is connected and powered.
- Check NI MAX or Keysight Connection Expert to confirm the instrument is visible at the OS level.
- Type the resource string manually: `GPIB0::17::INSTR` and click **Add**.
- If using pyvisa-py without NI-VISA, install `gpib-ctypes`:

  ```bash
  pip install gpib-ctypes
  ```

### Connection fails / timeout

- Verify the GPIB address on the instrument front panel matches the resource string.
- Check that the GPIB cable is fully seated at both ends.
- Try cycling the instrument power and clicking **Connect** again.
- Use the **Bus Reset** button in the connection panel to send SDC + IFC + `*CLS`.
- Increase timeout: edit `config/default_config.json` → `"timeout_ms": 60000`.

### EXE won't launch (Windows Defender / Antivirus warning)

PyInstaller-packaged EXEs sometimes trigger false positives.
Click **More info → Run anyway**, or add `dist\HP_Analyzer\` to your antivirus
exclusion list.

### "DLL load failed" error on launch

Install the Microsoft Visual C++ Redistributable 2015–2022:
<https://aka.ms/vs/17/release/vc_redist.x64.exe>

### C-V tab is greyed out

The C-V tab is only enabled when an **HP 4280A** is connected.

### UI appears tiny on a 4K or high-DPI monitor

The app honours Windows DPI settings automatically. If text still looks small:

1. Go to **Windows Settings → Display → Scale and layout** and confirm a DPI %
   other than 100 % is selected.
2. Right-click `HP_Analyzer.exe` → **Properties → Compatibility →
   Change high DPI settings** → check **Override high DPI scaling behavior** →
   set to **Application**.
3. Restart the app.

### Both NI-VISA and Keysight IO Libraries are installed — wrong adapter appears

When both VISA runtimes are installed, whichever was installed **last** registers
its VISA DLL as the system default. If the Keysight 82351B PCIe card is not
appearing but the NI USB-GPIB is (or vice versa), force Keysight IO as the
active backend:

#### Option 1 — Environment variable (persistent)

1. `Win + R` → `SystemPropertiesAdvanced` → **Environment Variables**
2. Under **User variables** click **New**:
   - Name: `VISA_LIBRARY`
   - Value: `C:\Windows\System32\agvisa32.dll`
3. Restart the app.

#### Option 2 — Reinstall order

Reinstall Keysight IO Libraries Suite *after* NI-VISA so it takes the registry
slot. Keysight IO enumerates both the 82351B (its own driver) and NI USB-GPIB
adapters, so both will be visible.

**Verify which DLL is active:**

```powershell
python -c "import pyvisa; rm = pyvisa.ResourceManager(); print(rm.visalib)"
```

Expected output when Keysight IO is active: a path containing `agvisa32.dll`.

---

### Measurement data looks wrong / all zeros

- Confirm the SMU channel assignments match your physical wiring.
- Check compliance limits — if hit, current is clamped to the compliance value.
- Verify the instrument is not in local mode (press the front-panel `LOCAL` key
  to return it to remote mode, then reconnect in the app).
