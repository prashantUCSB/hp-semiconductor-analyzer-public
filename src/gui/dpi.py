"""
DPI / HiDPI scaling utilities.

Qt with AA_EnableHighDpiScaling handles integer scale factors (2×, 3×) well,
but fractional factors (1.25×, 1.5×, 1.75×) common on 1440p/4K/5K monitors
need PassThrough rounding policy (set in main.py before QApplication).

Use `dp(n)` anywhere you need a pixel value that should scale with the screen.
Use `em(n)` to get a size relative to the current application font height.
"""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics


def _dpr() -> float:
    """Device-pixel ratio of the primary screen (e.g. 2.0 on 4K @ 200%)."""
    app = QApplication.instance()
    if app:
        screen = app.primaryScreen()
        if screen:
            return screen.devicePixelRatio()
    return 1.0


def _logical_dpi() -> float:
    """Logical DPI of the primary screen (96 = 100%, 144 = 150%, 192 = 200%)."""
    app = QApplication.instance()
    if app:
        screen = app.primaryScreen()
        if screen:
            return screen.logicalDotsPerInch()
    return 96.0


def scale_factor() -> float:
    """
    Returns the effective UI scale factor relative to a 96-DPI baseline.
    This already accounts for fractional scaling (e.g. 1.5 at 144 DPI).
    """
    return _logical_dpi() / 96.0


def dp(pixels: int) -> int:
    """
    Scale a 'density-independent pixel' value by the current DPI factor.
    Use for minimum widths, margins, icon sizes, and the StatusLED.

    Example:
        btn.setMinimumWidth(dp(80))   # 80 dp → 120 px at 144 DPI
    """
    return max(1, round(pixels * scale_factor()))


def em(n: float = 1.0) -> int:
    """
    Return n × the pixel height of the current application font.
    Useful for sizing widgets relative to text height.
    """
    app = QApplication.instance()
    if app:
        fm = QFontMetrics(app.font())
        return max(1, round(fm.height() * n))
    return max(1, round(16 * n))


def base_font_pt() -> int:
    """
    Recommended base font size in points, scaled for the current DPI.
    Keeps text readable across 720p → 5K without the stylesheet needing
    to hardcode pt values.

    Baseline: 9 pt at 96 DPI. Scales linearly with logical DPI.
    """
    raw = 9.0 * scale_factor()
    # Clamp to a sane range (never smaller than 9pt, never larger than 18pt)
    return int(max(9, min(18, round(raw))))
