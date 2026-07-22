"""
Reusable form-building helpers for measurement parameter panels.
"""

from PyQt5.QtWidgets import (
    QWidget, QFormLayout, QDoubleSpinBox, QSpinBox,
    QComboBox, QCheckBox, QLabel, QGroupBox, QVBoxLayout,
)
from PyQt5.QtCore import Qt


def make_dspin(value: float, minimum: float = -200.0, maximum: float = 200.0,
               decimals: int = 4, step: float = 0.01,
               suffix: str = "") -> QDoubleSpinBox:
    w = QDoubleSpinBox()
    w.setRange(minimum, maximum)
    w.setDecimals(decimals)
    w.setSingleStep(step)
    w.setValue(value)
    if suffix:
        w.setSuffix(f" {suffix}")
    return w


def make_spin(value: int, minimum: int = 1, maximum: int = 999) -> QSpinBox:
    w = QSpinBox()
    w.setRange(minimum, maximum)
    w.setValue(value)
    return w


def make_combo(options: list, current: str = "") -> QComboBox:
    w = QComboBox()
    w.addItems(options)
    if current in options:
        w.setCurrentText(current)
    return w


def ch_combo(default: int = 1) -> QComboBox:
    """Channel selector for SMU 1–4."""
    w = QComboBox()
    w.addItems(["1", "2", "3", "4"])
    w.setCurrentIndex(default - 1)
    return w


def group(title: str, *widgets) -> QGroupBox:
    """Wrap widgets in a titled QGroupBox with a vertical layout."""
    gb = QGroupBox(title)
    layout = QVBoxLayout(gb)
    layout.setContentsMargins(6, 4, 6, 4)
    layout.setSpacing(3)
    for w in widgets:
        if isinstance(w, QWidget):
            layout.addWidget(w)
    return gb


def form_group(title: str, rows: list) -> QGroupBox:
    """
    Build a QGroupBox with a QFormLayout.
    rows = [(label_str, widget), ...]
    """
    gb = QGroupBox(title)
    form = QFormLayout(gb)
    form.setContentsMargins(6, 4, 6, 4)
    form.setSpacing(4)
    for label, widget in rows:
        form.addRow(label, widget)
    return gb
