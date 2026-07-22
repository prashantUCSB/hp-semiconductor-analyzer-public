"""
Results table widget showing analysis summary and raw data preview.
"""

import pandas as pd
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QHeaderView, QFileDialog,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor


class AnalysisTable(QTableWidget):
    """Key–value table for extracted parameters."""

    def __init__(self, parent=None):
        super().__init__(0, 2, parent)
        self.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)

    def populate(self, analysis: dict):
        self.setRowCount(0)
        for key, val in analysis.items():
            row = self.rowCount()
            self.insertRow(row)
            self.setItem(row, 0, QTableWidgetItem(str(key)))
            self.setItem(row, 1, QTableWidgetItem(str(val)))


class DataPreviewTable(QTableWidget):
    """Scrollable preview of the raw data DataFrame (first 500 rows)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.horizontalHeader().setStretchLastSection(True)

    def populate(self, df: pd.DataFrame, max_rows: int = 500):
        df_show = df.head(max_rows)
        self.setColumnCount(len(df_show.columns))
        self.setRowCount(len(df_show))
        self.setHorizontalHeaderLabels(list(df_show.columns))
        for r, row in enumerate(df_show.itertuples(index=False)):
            for c, val in enumerate(row):
                self.setItem(r, c, QTableWidgetItem(f"{val:.6g}" if isinstance(val, float) else str(val)))
        self.resizeColumnsToContents()


class ResultsPanel(QWidget):
    """
    Tabbed panel showing analysis results and raw data.
    Has export buttons for CSV and Excel.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Export buttons
        from .dpi import dp
        btn_row = QHBoxLayout()
        btn_row.addWidget(QLabel("Export:"))
        self.btn_csv   = QPushButton("Save CSV")
        self.btn_excel = QPushButton("Save Excel")
        self.btn_csv.setMinimumWidth(dp(80))
        self.btn_excel.setMinimumWidth(dp(90))
        self.btn_csv.clicked.connect(self._export_csv)
        self.btn_excel.clicked.connect(self._export_excel)
        self.btn_csv.setEnabled(False)
        self.btn_excel.setEnabled(False)
        btn_row.addWidget(self.btn_csv)
        btn_row.addWidget(self.btn_excel)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Tabs
        self.tabs = QTabWidget()
        self.tbl_analysis = AnalysisTable()
        self.tbl_data     = DataPreviewTable()
        self.tabs.addTab(self.tbl_analysis, "Analysis")
        self.tabs.addTab(self.tbl_data,     "Raw Data")
        layout.addWidget(self.tabs)

    def display_result(self, result):
        self._result = result
        self.tbl_analysis.populate(result.analysis)
        self.tbl_data.populate(result.to_dataframe())
        self.btn_csv.setEnabled(True)
        self.btn_excel.setEnabled(True)

    def _export_csv(self):
        if not self._result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", f"{self._result.name}.csv", "CSV (*.csv)"
        )
        if path:
            self._result.save_csv(path)

    def _export_excel(self):
        if not self._result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel", f"{self._result.name}.xlsx",
            "Excel (*.xlsx)"
        )
        if path:
            self._result.save_excel(path)
