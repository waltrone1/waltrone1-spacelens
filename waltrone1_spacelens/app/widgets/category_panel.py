from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView

from ...core.categorizer import CATEGORY_ORDER
from ...core.size_format import format_size


class CategoryPanel(QTableWidget):
    def __init__(self) -> None:
        super().__init__(0, 3)
        self.setHorizontalHeaderLabels(["Kategorie", "Größe", "Anteil"])
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

    def set_totals(self, totals: dict[str, int]) -> None:
        total = sum(totals.values())
        rows = [(category, totals.get(category, 0)) for category in CATEGORY_ORDER if totals.get(category, 0) > 0]
        rows.sort(key=lambda item: item[1], reverse=True)
        self.setRowCount(len(rows))
        for row, (category, size) in enumerate(rows):
            percent = (size / total * 100) if total else 0

            category_item = QTableWidgetItem(category)
            size_item = QTableWidgetItem(format_size(size))
            percent_item = QTableWidgetItem(f"{percent:.1f} %")

            for item in (category_item, size_item, percent_item):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.setItem(row, 0, category_item)
            self.setItem(row, 1, size_item)
            self.setItem(row, 2, percent_item)
