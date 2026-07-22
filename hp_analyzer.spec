# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec file for HP Semiconductor Analyzer Controller
# Run with:  pyinstaller hp_analyzer.spec --noconfirm
#
# PyInstaller 6+ produces:
#   dist/HP_Analyzer/HP_Analyzer.exe
#   dist/HP_Analyzer/_internal/   (all bundled runtime files)
#

from pathlib import Path

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'config'), 'config'),
    ],
    hiddenimports=[
        # ── PyQt5 ─────────────────────────────────────────────────
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.sip',
        # ── Matplotlib Qt5 backend ────────────────────────────────
        'matplotlib',
        'matplotlib.backends.backend_qt5agg',
        'matplotlib.backends.backend_agg',
        'matplotlib.figure',
        'matplotlib.pyplot',
        # ── PyVISA ────────────────────────────────────────────────
        'pyvisa',
        'pyvisa.resources',
        'pyvisa.resources.gpib',
        'pyvisa.resources.messagebased',
        'pyvisa_py',
        'pyvisa_py.gpib',
        'pyvisa_py.usb',
        'pyvisa_py.serial',
        'pyvisa_py.tcpip',
        # ── SciPy / NumPy / Pandas ────────────────────────────────
        'scipy',
        'scipy.optimize',
        'scipy.signal',
        'scipy.stats',
        'numpy',
        'pandas',
        'openpyxl',
        # ── src.instruments ───────────────────────────────────────
        'src',
        'src.instruments',
        'src.instruments.visa_manager',
        'src.instruments.base_instrument',
        'src.instruments.hp4145',
        'src.instruments.hp4155',
        'src.instruments.hp4156',
        'src.instruments.hp4280',
        # ── src.measurements ──────────────────────────────────────
        'src.measurements',
        'src.measurements.base_measurement',
        'src.measurements.queue_manager',
        'src.measurements.mosfet',
        'src.measurements.diode_iv',
        'src.measurements.resistor_iv',
        'src.measurements.capacitance_cv',
        'src.measurements.van_der_pauw',
        'src.measurements.kelvin_4probe',
        'src.measurements.hall_bar',
        'src.measurements.generic_4port',
        # ── src.gui ───────────────────────────────────────────────
        'src.gui',
        'src.gui.main_window',
        'src.gui.connection_panel',
        'src.gui.plot_canvas',
        'src.gui.results_table',
        'src.gui.styles',
        'src.gui.dpi',
        'src.gui.panels.base_panel',
        'src.gui.panels.form_helpers',
        'src.gui.panels.mosfet_panel',
        'src.gui.panels.diode_panel',
        'src.gui.panels.resistor_panel',
        'src.gui.panels.cv_panel',
        'src.gui.panels.van_der_pauw_panel',
        'src.gui.panels.kelvin_panel',
        'src.gui.panels.hall_bar_panel',
        'src.gui.panels.generic_panel',
        'src.gui.panels.queue_panel',
        'src.gui.dialogs',
        'src.gui.dialogs.wiring_guide_dialog',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'IPython',
        'jupyter',
        'notebook',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HP_Analyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no console window on Windows
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # set to 'icons/app.ico' if an icon is added
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='HP_Analyzer',
)
