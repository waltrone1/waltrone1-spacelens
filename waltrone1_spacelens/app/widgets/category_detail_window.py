from __future__ import annotations

import fnmatch
import math
import os
from collections import defaultdict
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QDesktopServices, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.categorizer import categorize_file
from ...core.models import ScanNode
from ...core.size_format import format_size


class NumericTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other: QTableWidgetItem) -> bool:
        left = self.data(Qt.ItemDataRole.UserRole)
        right = other.data(Qt.ItemDataRole.UserRole)
        if left is not None and right is not None:
            return left < right
        return super().__lt__(other)


class LoadingSpinner(QWidget):
    """Leichter animierter Lade-Kreisel ohne externe Dateien."""

    def __init__(self, parent=None, line_count: int = 12) -> None:
        super().__init__(parent)
        self._line_count = line_count
        self._current = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self.setFixedSize(28, 28)

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start(90)
        self.show()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _rotate(self) -> None:
        self._current = (self._current + 1) % self._line_count
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)

        outer_radius = min(self.width(), self.height()) / 2 - 2
        dot_radius = max(1.8, outer_radius * 0.16)
        orbit_radius = outer_radius - dot_radius - 1

        for i in range(self._line_count):
            painter.save()
            angle = (360 / self._line_count) * i
            painter.rotate(angle)
            alpha_index = (i - self._current) % self._line_count
            alpha = max(35, int(255 * (1 - alpha_index / self._line_count)))
            color = QColor(48, 101, 222, alpha)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            rect = QRectF(-dot_radius, -orbit_radius - dot_radius, dot_radius * 2, dot_radius * 2)
            painter.drawEllipse(rect)
            painter.restore()


class DetailLoaderWorker(QObject):
    finished = Signal(list, list, list)
    failed = Signal(str)

    def __init__(self, root: ScanNode, category: str) -> None:
        super().__init__()
        self.root = root
        self.category = category

    def run(self) -> None:
        try:
            folder_rows: list[tuple[str, int, int, str]] = []
            file_rows: list[tuple[str, int, str, str]] = []
            extension_totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])

            def scan(node: ScanNode) -> tuple[int, int]:
                if not node.is_dir:
                    if categorize_file(node.path) != self.category:
                        return 0, 0
                    extension = Path(node.path).suffix.lower() or "[ohne Endung]"
                    extension_totals[extension][0] += int(node.size)
                    extension_totals[extension][1] += 1
                    file_rows.append((node.name, int(node.size), extension, node.path))
                    return int(node.size), 1

                category_size = 0
                category_files = 0
                for child in node.children:
                    child_size, child_files = scan(child)
                    category_size += child_size
                    category_files += child_files
                if category_size > 0:
                    folder_rows.append((node.name, category_size, category_files, node.path))
                return category_size, category_files

            scan(self.root)

            folder_rows = [row for row in folder_rows if row[3] != self.root.path]
            folder_rows.sort(key=lambda item: item[1], reverse=True)
            file_rows.sort(key=lambda item: item[1], reverse=True)
            extension_rows = [(ext, values[0], values[1]) for ext, values in extension_totals.items()]
            extension_rows.sort(key=lambda item: item[1], reverse=True)

            self.finished.emit(folder_rows[:200], file_rows[:200], extension_rows)
        except Exception as exc:  # pragma: no cover - Sicherheitsnetz fuer UI
            self.failed.emit(str(exc))


class CategoryDetailWindow(QDialog):
    """Shows a drill-down view for one storage category.

    The main scan result stays untouched. The dialog only derives additional
    summaries from the already existing ScanNode tree.
    """

    def __init__(self, root: ScanNode, category: str, total_size: int, parent=None) -> None:
        super().__init__(parent)
        self.root = root
        self.category = category
        self.category_total_size = int(total_size)
        self.root_total_size = int(root.size)

        self._loader_thread: QThread | None = None
        self._loader_worker: DetailLoaderWorker | None = None
        self._loading_dot_count = 0

        self.setWindowTitle(f"Kategorie-Details: {category}")
        self.resize(1180, 760)
        self.setMinimumSize(980, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel(f"{category} im Detail")
        title.setObjectName("Title")
        subtitle = QLabel(self._build_subtitle())
        subtitle.setObjectName("Subtitle")
        hint = QLabel("Tipp: Doppelklick oeffnet Dateien direkt. Rechtsklick bietet Datei oeffnen, Explorer oeffnen und Pfad kopieren. Suche unterstuetzt Wildcards wie *.png.")
        hint.setObjectName("Subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(hint)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Schnellsuche: Name, Endung, Größe oder Pfad filtern ... Wildcards: *.png, IMG_*.JPG")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search_input)

        self.loading_container = QWidget()
        loading_layout = QHBoxLayout(self.loading_container)
        loading_layout.setContentsMargins(0, 2, 0, 2)
        loading_layout.setSpacing(10)

        self.spinner = LoadingSpinner()
        self.loading_label = QLabel("Details werden geladen")
        self.loading_label.setObjectName("Subtitle")
        loading_layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignVCenter)
        loading_layout.addWidget(self.loading_label, 1, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.loading_container)

        self.tabs = QTabWidget()
        self.tabs.setEnabled(False)
        self.folder_table = self._create_table(["Ordner", "Groesse", "Dateien", "Anteil Kategorie", "Pfad"])
        self.file_table = self._create_table(["Datei", "Groesse", "Endung", "Pfad"])
        self.extension_table = self._create_table(["Endung", "Groesse", "Dateien", "Anteil Kategorie"])
        self.tabs.addTab(self.folder_table, "Top Ordner")
        self.tabs.addTab(self.file_table, "Top Dateien")
        self.tabs.addTab(self.extension_table, "Dateiendungen")
        layout.addWidget(self.tabs, 1)

        close_button = QPushButton("Schliessen")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)

        self._label_timer = QTimer(self)
        self._label_timer.timeout.connect(self._animate_loading_text)

        QTimer.singleShot(80, self._start_initial_load)

    def _start_initial_load(self) -> None:
        self.spinner.start()
        self._label_timer.start(320)

        self._loader_thread = QThread(self)
        self._loader_worker = DetailLoaderWorker(self.root, self.category)
        self._loader_worker.moveToThread(self._loader_thread)

        self._loader_thread.started.connect(self._loader_worker.run)
        self._loader_worker.finished.connect(self._on_load_finished)
        self._loader_worker.failed.connect(self._on_load_failed)
        self._loader_worker.finished.connect(self._loader_thread.quit)
        self._loader_worker.failed.connect(self._loader_thread.quit)
        self._loader_thread.finished.connect(self._cleanup_loader)
        self._loader_thread.start()

    def _animate_loading_text(self) -> None:
        self._loading_dot_count = (self._loading_dot_count + 1) % 4
        dots = "." * self._loading_dot_count
        self.loading_label.setText(f"Details werden geladen{dots} bitte kurz warten")

    def _on_load_finished(
        self,
        folder_rows: list[tuple[str, int, int, str]],
        file_rows: list[tuple[str, int, str, str]],
        extension_rows: list[tuple[str, int, int]],
    ) -> None:
        self._fill_folder_table(folder_rows)
        self._fill_file_table(file_rows)
        self._fill_extension_table(extension_rows)
        self._apply_filter(self.search_input.text())
        self._finish_loading_state()

    def _on_load_failed(self, error_message: str) -> None:
        self.loading_label.setText(f"Fehler beim Laden der Details: {error_message}")
        self.spinner.stop()
        self._label_timer.stop()

    def _cleanup_loader(self) -> None:
        if self._loader_worker is not None:
            self._loader_worker.deleteLater()
        self._loader_worker = None
        self._loader_thread = None

    def _finish_loading_state(self) -> None:
        self.spinner.stop()
        self._label_timer.stop()
        self.loading_container.hide()
        self.tabs.setEnabled(True)

    def _build_subtitle(self) -> str:
        if not self.root_total_size:
            share = 0.0
        else:
            share = self.category_total_size / self.root_total_size * 100
        return f"{format_size(self.category_total_size)} in dieser Kategorie | {share:.1f} % des gesamten Scans"

    def _create_table(self, headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(lambda pos, t=table: self._open_context_menu(t, pos))
        table.cellDoubleClicked.connect(lambda row, column, t=table: self._open_row(t, row))
        return table

    def _apply_filter(self, text: str) -> None:
        query = " ".join(text.lower().split())
        for table in (self.folder_table, self.file_table, self.extension_table):
            for row in range(table.rowCount()):
                if not query:
                    table.setRowHidden(row, False)
                    continue
                values: list[str] = []
                for column in range(table.columnCount()):
                    item = table.item(row, column)
                    if item is not None:
                        values.append(item.text())
                        if item.toolTip():
                            values.append(item.toolTip())
                        path = item.data(Qt.ItemDataRole.UserRole + 1)
                        if path:
                            values.append(str(path))
                            values.append(os.path.basename(str(path)))
                table.setRowHidden(row, not self._matches_filter(query, values))

    @staticmethod
    def _matches_filter(query: str, values: list[str]) -> bool:
        tokens = [token for token in query.split() if token]
        lowered_values = [value.lower() for value in values if value]
        haystack = " ".join(lowered_values)
        for token in tokens:
            if any(char in token for char in "*?["):
                if not any(fnmatch.fnmatch(value, token) or fnmatch.fnmatch(os.path.basename(value), token) for value in lowered_values):
                    return False
            elif token not in haystack:
                return False
        return True

    def _fill_folder_table(self, rows: list[tuple[str, int, int, str]]) -> None:
        self.folder_table.setSortingEnabled(False)
        self.folder_table.setRowCount(len(rows))
        for row, (name, size, file_count, path) in enumerate(rows):
            share = size / self.category_total_size * 100 if self.category_total_size else 0
            values = [name, format_size(size), f"{file_count:,}".replace(",", "."), f"{share:.1f} %", path]
            self._set_row(self.folder_table, row, values, numeric={1: size, 2: file_count, 3: share}, path=path, is_dir=True)
        self.folder_table.setSortingEnabled(True)
        self.folder_table.sortItems(1, Qt.SortOrder.DescendingOrder)
        self.folder_table.resizeColumnsToContents()
        self.folder_table.horizontalHeader().setStretchLastSection(True)

    def _fill_file_table(self, rows: list[tuple[str, int, str, str]]) -> None:
        self.file_table.setSortingEnabled(False)
        self.file_table.setRowCount(len(rows))
        for row, (name, size, extension, path) in enumerate(rows):
            values = [name, format_size(size), extension, path]
            self._set_row(self.file_table, row, values, numeric={1: size}, path=path, is_dir=False)
        self.file_table.setSortingEnabled(True)
        self.file_table.sortItems(1, Qt.SortOrder.DescendingOrder)
        self.file_table.resizeColumnsToContents()
        self.file_table.horizontalHeader().setStretchLastSection(True)

    def _fill_extension_table(self, rows: list[tuple[str, int, int]]) -> None:
        self.extension_table.setSortingEnabled(False)
        self.extension_table.setRowCount(len(rows))
        for row, (extension, size, file_count) in enumerate(rows):
            share = size / self.category_total_size * 100 if self.category_total_size else 0
            values = [extension, format_size(size), f"{file_count:,}".replace(",", "."), f"{share:.1f} %"]
            self._set_row(self.extension_table, row, values, numeric={1: size, 2: file_count, 3: share})
        self.extension_table.setSortingEnabled(True)
        self.extension_table.sortItems(1, Qt.SortOrder.DescendingOrder)
        self.extension_table.resizeColumnsToContents()
        self.extension_table.horizontalHeader().setStretchLastSection(True)

    def _set_row(
        self,
        table: QTableWidget,
        row: int,
        values: list[str],
        numeric: dict[int, int | float] | None = None,
        path: str | None = None,
        is_dir: bool | None = None,
    ) -> None:
        numeric = numeric or {}
        for column, value in enumerate(values):
            item = NumericTableWidgetItem(str(value))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setData(Qt.ItemDataRole.UserRole, numeric.get(column, str(value).lower()))
            if path:
                item.setData(Qt.ItemDataRole.UserRole + 1, path)
                item.setData(Qt.ItemDataRole.UserRole + 2, bool(is_dir))
                item.setToolTip(path)
            table.setItem(row, column, item)

    def _open_context_menu(self, table: QTableWidget, position) -> None:
        item = table.item(table.currentRow(), 0)
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole + 1)
        if not path:
            return
        is_dir = bool(item.data(Qt.ItemDataRole.UserRole + 2))
        menu = QMenu(self)
        open_file_action = QAction("Datei oeffnen", self)
        open_action = QAction("Im Explorer oeffnen", self)
        copy_action = QAction("Pfad kopieren", self)
        open_file_action.setEnabled((not is_dir) and os.path.isfile(str(path)))
        open_file_action.triggered.connect(lambda: self._open_file(str(path)))
        open_action.triggered.connect(lambda: self._open_location(str(path), is_dir))
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(str(path)))
        menu.addAction(open_file_action)
        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(copy_action)
        menu.exec(table.viewport().mapToGlobal(position))

    def _open_row(self, table: QTableWidget, row: int) -> None:
        item = table.item(row, 0)
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole + 1)
        if not path:
            return
        is_dir = bool(item.data(Qt.ItemDataRole.UserRole + 2))
        if is_dir:
            self._open_location(str(path), is_dir)
        else:
            self._open_file(str(path))

    def _open_file(self, path: str) -> None:
        if os.path.isfile(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _open_location(self, path: str, is_dir: bool) -> None:
        target = path if is_dir else os.path.dirname(path)
        if target:
            QDesktopServices.openUrl(QUrl.fromLocalFile(target))
