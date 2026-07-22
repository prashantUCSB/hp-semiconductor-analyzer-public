"""
HP4145 / HP4156 / HP4280 Semiconductor Parameter Analyzer Controller
Entry point for the application.
"""

import sys
import os

# Ensure src is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# ── HiDPI setup ────────────────────────────────────────────────────────────
# Must be called BEFORE QApplication is constructed.
#
# AA_EnableHighDpiScaling  – scales all logical coordinates by the screen's
#                            DPI factor so the layout looks identical across
#                            720p/1080p/1440p/4K/5K.
#
# PassThrough rounding     – allows fractional scale factors (1.25×, 1.5×,
#                            1.75×) which are common on 1440p and 5K2K
#                            monitors set to 125 % or 150 % in Windows
#                            Display Settings.  Without this, Qt would round
#                            1.5× down to 1× and the UI would appear tiny.
#
# AA_UseHighDpiPixmaps     – renders icons and images at full physical
#                            resolution instead of upscaling bitmaps.

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

try:
    # Qt 5.14+ only – safe to skip on older builds
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
except AttributeError:
    pass


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("HP Semiconductor Analyzer Controller")
    app.setOrganizationName("UCSB ECE")

    # Import dpi helper AFTER QApplication exists so primaryScreen() works
    from src.gui.dpi import base_font_pt
    font = QFont("Segoe UI", base_font_pt())
    app.setFont(font)

    # Build and apply stylesheet after font is set (stylesheet uses `em` internally)
    from src.gui.styles import build_stylesheet
    app.setStyleSheet(build_stylesheet())

    from src.gui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    # Required for PyInstaller frozen EXEs: prevents multiprocessing from
    # re-launching the GUI when spawning worker subprocesses on Windows.
    import multiprocessing
    multiprocessing.freeze_support()
    main()
