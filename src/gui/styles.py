"""
Application-wide Qt stylesheet.

`build_stylesheet()` is called once after QApplication and the base font
are both set, so all sizes derive from the live font metrics and DPI – the
stylesheet is never hardcoded in pixels.
"""

from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import QApplication

# ── Colour palette ─────────────────────────────────────────────────────────
ACCENT  = "#2196F3"
SUCCESS = "#4CAF50"
WARNING = "#FF9800"
DANGER  = "#F44336"
BG      = "#1E1E2E"
PANEL   = "#2A2A3E"
BORDER  = "#3A3A5E"
TEXT    = "#CDD6F4"
SUBTEXT = "#888AAA"


def _em(n: float = 1.0) -> int:
    """n × current font height in pixels (post-DPI-scaling)."""
    app = QApplication.instance()
    if app:
        fm = QFontMetrics(app.font())
        return max(1, round(fm.height() * n))
    return max(1, round(16 * n))


def build_stylesheet() -> str:
    """
    Build and return the full Qt stylesheet with sizes derived from the
    current font and DPI.  Call once after QApplication + font are set.
    """
    # Derive all sizing from the font so every resolution looks consistent.
    fh   = _em(1.0)          # 1 em  – full font height
    pad  = max(4, _em(0.35)) # comfortable button/input vertical padding
    hpad = max(8, _em(0.75)) # button horizontal padding
    tab_v = max(6, _em(0.5)) # tab vertical padding
    tab_h = max(14, _em(1.2))# tab horizontal padding
    r    = max(3, _em(0.22)) # border-radius
    led  = max(10, _em(0.7)) # StatusLED diameter (kept consistent)

    # Font sizes in pt — Qt already scales pt by DPI, so these stay
    # visually constant across resolutions.
    app   = QApplication.instance()
    base_pt   = app.font().pointSize() if app else 9
    header_pt = base_pt + 3
    small_pt  = max(7, base_pt - 1)

    return f"""
QMainWindow, QDialog {{
    background-color: {BG};
    color: {TEXT};
}}

QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-size: {base_pt}pt;
}}

/* ── Group boxes ─────────────────────────────────────────── */
QGroupBox {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: {r}px;
    margin-top: {_em(0.7)}px;
    padding: {pad}px {max(4,_em(0.25))}px;
    font-weight: bold;
    color: {ACCENT};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 {max(4,_em(0.3))}px;
    color: {ACCENT};
}}

/* ── Buttons ─────────────────────────────────────────────── */
QPushButton {{
    background-color: {ACCENT};
    color: white;
    border: none;
    border-radius: {r}px;
    padding: {pad}px {hpad}px;
    font-weight: bold;
    min-width: {_em(4)}px;
}}
QPushButton:hover   {{ background-color: #42A5F5; }}
QPushButton:pressed {{ background-color: #1565C0; }}
QPushButton:disabled {{ background-color: #555577; color: #888; }}

QPushButton#danger  {{ background-color: {DANGER}; }}
QPushButton#danger:hover {{ background-color: #EF5350; }}
QPushButton#success {{ background-color: {SUCCESS}; }}

/* ── Inputs ──────────────────────────────────────────────── */
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {{
    background-color: #12121E;
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: {r}px;
    padding: {max(2,pad-2)}px {max(4,_em(0.35))}px;
    selection-background-color: {ACCENT};
    min-height: {_em(1.4)}px;
}}
QLineEdit:focus, QDoubleSpinBox:focus,
QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {ACCENT};
}}

QComboBox::drop-down {{ border: none; width: {_em(1.2)}px; }}
QComboBox QAbstractItemView {{
    background-color: {PANEL};
    color: {TEXT};
    selection-background-color: {ACCENT};
}}

QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QSpinBox::up-button, QSpinBox::down-button {{
    width: {_em(0.9)}px;
    border: none;
    background: {BORDER};
}}

/* ── Labels ──────────────────────────────────────────────── */
QLabel {{
    color: {TEXT};
    background: transparent;
}}
QLabel#header {{
    font-size: {header_pt}pt;
    font-weight: bold;
    color: {ACCENT};
}}
QLabel#subtext {{
    color: {SUBTEXT};
    font-size: {small_pt}pt;
}}

/* ── Tabs ────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background-color: {PANEL};
}}
QTabBar::tab {{
    background-color: {BG};
    color: {SUBTEXT};
    padding: {tab_v}px {tab_h}px;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: {r}px;
    border-top-right-radius: {r}px;
    margin-right: 2px;
    min-width: {_em(4)}px;
}}
QTabBar::tab:selected {{
    background-color: {PANEL};
    color: {TEXT};
    border-bottom: 2px solid {ACCENT};
}}
QTabBar::tab:hover:!selected {{
    background-color: {PANEL};
    color: {TEXT};
}}

/* ── Splitter ────────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {BORDER};
}}
QSplitter::handle:horizontal {{ width: 4px; }}
QSplitter::handle:vertical   {{ height: 4px; }}

/* ── Scroll bars ─────────────────────────────────────────── */
QScrollArea, QAbstractScrollArea {{
    background-color: {BG};
    border: none;
}}
QScrollBar:vertical {{
    width: {max(8, _em(0.55))}px;
    background: {BG};
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: {max(3,_em(0.2))}px;
    min-height: {_em(1.5)}px;
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    height: {max(8, _em(0.55))}px;
    background: {BG};
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: {max(3,_em(0.2))}px;
    min-width: {_em(1.5)}px;
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Tables ──────────────────────────────────────────────── */
QTableWidget {{
    background-color: {PANEL};
    color: {TEXT};
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
}}
QHeaderView::section {{
    background-color: {BG};
    color: {ACCENT};
    border: 1px solid {BORDER};
    padding: {pad}px {max(4,_em(0.3))}px;
    font-weight: bold;
}}
QTableWidget::item {{
    padding: {max(2,pad-2)}px {max(4,_em(0.3))}px;
}}

/* ── Status bar ──────────────────────────────────────────── */
QStatusBar {{
    background-color: {BG};
    color: {SUBTEXT};
    border-top: 1px solid {BORDER};
    font-size: {small_pt}pt;
}}

/* ── Progress bar ────────────────────────────────────────── */
QProgressBar {{
    background-color: {BG};
    border: 1px solid {BORDER};
    border-radius: {r}px;
    text-align: center;
    color: {TEXT};
    min-height: {_em(0.9)}px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: {r}px;
}}

/* ── Checkboxes / Radios ─────────────────────────────────── */
QCheckBox {{
    color: {TEXT};
    spacing: {max(4,_em(0.3))}px;
}}
QCheckBox::indicator {{
    width:  {_em(0.85)}px;
    height: {_em(0.85)}px;
    border: 1px solid {BORDER};
    border-radius: {max(2,r-1)}px;
    background: {BG};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

QRadioButton {{
    color: {TEXT};
    spacing: {max(4,_em(0.3))}px;
}}
QRadioButton::indicator {{
    width:  {_em(0.85)}px;
    height: {_em(0.85)}px;
    border: 1px solid {BORDER};
    border-radius: {max(4, _em(0.42))}px;
    background: {BG};
}}
QRadioButton::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

/* ── Form layout label alignment ────────────────────────── */
QFormLayout QLabel {{
    min-width: {_em(5)}px;
}}
"""


# Legacy constant so any code that imported STYLESHEET directly still works.
# It will be an empty string until build_stylesheet() is called; the real
# stylesheet is applied in main.py.
STYLESHEET = ""
