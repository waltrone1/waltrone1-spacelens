from __future__ import annotations

import time

from PySide6.QtCore import QThread, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .widgets.category_panel import CategoryPanel
from .widgets.duplicate_panel import DuplicatePanel
from .widgets.folder_tree import FolderTree
from .widgets.category_detail_window import CategoryDetailWindow
from .widgets.result_detail_window import show_scan_error_details
from .widgets.graphics_panel import LargeGraphicsWindow
from .widgets.path_bar import PathBar
from .widgets.storage_summary_bar import StorageSummaryBar
from ..core.models import ScanError, ScanNode
from ..core.scanner import ScanWorker
from ..core.size_format import format_size
from ..exports.exporters import export_csv, export_html_report, export_json, top_files, top_folders

# Eigene Rollen – verhindert UserRole-Kollisionen
_ROLE_SORT  = Qt.ItemDataRole.UserRole       # Sortierwert
_ROLE_PATH  = Qt.ItemDataRole.UserRole + 1  # Dateipfad
_ROLE_ISDIR = Qt.ItemDataRole.UserRole + 2  # bool: ist Ordner?


class NumericTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other: QTableWidgetItem) -> bool:
        left = self.data(_ROLE_SORT)
        right = other.data(_ROLE_SORT)
        if left is not None and right is not None:
            return left < right
        return super().__lt__(other)


class ClickableProgressBar(QProgressBar):
    clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Klicken für Scan-Details.")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("waltrone1-SpaceLens")
        self.resize(1500, 940)
        self.setMinimumSize(1240, 800)
        self._thread: QThread | None = None
        self._worker: ScanWorker | None = None
        self._root: ScanNode | None = None
        self._category_totals: dict[str, int] = {}
        self._errors: list[ScanError] = []
        self._graphics_window: LargeGraphicsWindow | None = None
        self._category_detail_windows: list[CategoryDetailWindow] = []
        self._finalizing_results = False
        self._pending_scan_result: tuple[ScanNode, dict[str, int], list[ScanError]] | None = None
        self._scan_started_at: float | None = None
        self._scan_phase = "Bereit"
        self._scan_last_path = ""
        self._scan_files_seen = 0
        self._scan_bytes_seen = 0
        self._scan_errors_seen = 0

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        title = QLabel("waltrone1-SpaceLens")
        title.setObjectName("Title")
        subtitle = QLabel("Moderner Speicherplatz-Analyzer für Laufwerke, Ordner und UNC-Pfade")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.path_bar = PathBar()
        self.path_bar.scan_requested.connect(self.start_scan)
        self.path_bar.cancel_requested.connect(self.cancel_scan)
        layout.addWidget(self.path_bar)

        self.status_label = QLabel("Bereit. Gib einen Pfad ein und starte den Scan.")
        self.status_label.setObjectName("Subtitle")
        self.progress = ClickableProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.clicked.connect(self.show_scan_details)
        self.progress.setFormat("Scan läuft ...")

        # Fehler-Badge: zeigt Anzahl der Scan-Fehler nach dem Scan
        self._error_badge = QPushButton("⚠ 0 Fehler")
        self._error_badge.setObjectName("ErrorBadge")
        self._error_badge.setVisible(False)
        self._error_badge.clicked.connect(self._show_error_list)

        status_row = QHBoxLayout()
        status_row.addWidget(self.status_label, 1)
        status_row.addWidget(self._error_badge)
        layout.addLayout(status_row)
        layout.addWidget(self.progress)

        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        self.total_card, self.total_value = self._metric_card("Gesamtgröße", "0 B")
        self.files_card, self.files_value = self._metric_card("Dateien", "0")
        self.folders_card, self.folders_value = self._metric_card("Ordner", "0")
        for card in [self.total_card, self.files_card, self.folders_card]:
            metrics.addWidget(card)
        layout.addLayout(metrics)

        summary_card = self._card()
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(14, 12, 14, 12)
        summary_title = QLabel("Speicherübersicht nach Kategorien - Kategorie anklicken für Details")
        summary_title.setObjectName("Subtitle")
        self.summary_bar = StorageSummaryBar()
        self.summary_bar.category_clicked.connect(self.open_category_details)
        summary_layout.addWidget(summary_title)
        summary_layout.addWidget(self.summary_bar)
        layout.addWidget(summary_card)

        actions = QHBoxLayout()
        self.export_csv_button = QPushButton("Export CSV")
        self.export_json_button = QPushButton("Export JSON")
        self.report_button = QPushButton("HTML-Report")
        self.graphic_button = QPushButton("Grafik öffnen")
        self.graphic_button.setObjectName("DormantGraphicButton")
        self.graphic_button.setToolTip("Nach einem erfolgreichen Scan wird die große Grafikansicht hier verfügbar.")
        for button in [self.export_csv_button, self.export_json_button, self.report_button, self.graphic_button]:
            button.setEnabled(False)
            actions.addWidget(button)
        actions.addStretch(1)
        self.export_csv_button.clicked.connect(self.export_as_csv)
        self.export_json_button.clicked.connect(self.export_as_json)
        self.report_button.clicked.connect(self.export_report)
        self.graphic_button.clicked.connect(self.open_large_graphics)
        layout.addLayout(actions)

        splitter = QSplitter()
        self.tabs = QTabWidget()
        self.tree = FolderTree()
        self.tree.show_placeholder()
        self.tabs.addTab(self.tree, "Ordnerbaum")

        self.top_folders_table = self._create_top_table()
        self.tabs.addTab(self.top_folders_table, "Top 50 Ordner")

        files_tab = QWidget()
        files_layout = QVBoxLayout(files_tab)
        files_layout.setContentsMargins(0, 0, 0, 0)
        filter_row = QHBoxLayout()
        filter_label = QLabel("Nur Dateien größer als")
        self.min_file_size_gb = QDoubleSpinBox()
        self.min_file_size_gb.setRange(0, 100000)
        self.min_file_size_gb.setDecimals(2)
        self.min_file_size_gb.setSuffix(" GB")
        self.min_file_size_gb.setSingleStep(0.5)
        self.min_file_size_gb.valueChanged.connect(self.refresh_top_files)
        filter_row.addWidget(filter_label)
        filter_row.addWidget(self.min_file_size_gb)
        filter_row.addStretch(1)
        self.top_files_table = self._create_top_table()
        files_layout.addLayout(filter_row)
        files_layout.addWidget(self.top_files_table)
        self.tabs.addTab(files_tab, "Top 50 Dateien")

        self.duplicate_panel = DuplicatePanel()
        self.tabs.addTab(self.duplicate_panel, "🔍 Duplikate")

        splitter.addWidget(self.tabs)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        category_card = self._card()
        category_layout = QVBoxLayout(category_card)
        category_title = QLabel("Kategorien")
        category_title.setObjectName("Subtitle")
        self.category_panel = CategoryPanel()
        self.category_panel.cellDoubleClicked.connect(self._open_category_from_table)
        category_layout.addWidget(category_title)
        category_layout.addWidget(self.category_panel)
        right_layout.addWidget(category_card, 2)

        splitter.addWidget(right_panel)
        splitter.setSizes([1080, 360])
        layout.addWidget(splitter, 1)

        footer = QFrame()
        footer.setObjectName("Footer")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 8, 12, 8)
        footer_layout.setSpacing(12)
        footer_text = QLabel("waltrone1-SpaceLens  |  Version 1.0.0.0  |  Build 2026-05-06")
        footer_text.setObjectName("FooterText")
        website_button = QPushButton("Website öffnen")
        website_button.setObjectName("FooterLinkButton")
        mail_button = QPushButton("Kontakt per E-Mail")
        mail_button.setObjectName("FooterLinkButton")
        website_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://waltrone1.de/wltones-admin-tools/")))
        mail_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("mailto:gwaltrone@gmail.com")))
        footer_layout.addWidget(footer_text)
        footer_layout.addStretch(1)
        footer_layout.addWidget(website_button)
        footer_layout.addWidget(QLabel("|"))
        footer_layout.addWidget(mail_button)
        layout.addWidget(footer)

    def _card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        return card

    def _metric_card(self, label_text: str, value_text: str) -> tuple[QFrame, QLabel]:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        label = QLabel(label_text)
        label.setObjectName("MetricLabel")
        value = QLabel(value_text)
        value.setObjectName("MetricValue")
        layout.addWidget(label)
        layout.addWidget(value)
        return card, value

    def _create_top_table(self) -> QTableWidget:
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["Name", "Größe", "Anteil", "Typ", "Pfad"])
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionsMovable(True)
        header.setSectionsClickable(True)
        header.setHighlightSections(True)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.setColumnWidth(0, 260)
        table.setColumnWidth(1, 110)
        table.setColumnWidth(2, 90)
        table.setColumnWidth(3, 90)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(lambda pos, t=table: self._open_table_context_menu(t, pos))
        table.cellDoubleClicked.connect(lambda row, column, t=table: self._open_table_row(t, row))
        return table

    @Slot(str)
    def start_scan(self, path: str) -> None:
        if self._thread is not None:
            return
        self._reset_result_view()
        self._scan_started_at = time.monotonic()
        self._scan_phase = "Scan läuft"
        self._scan_last_path = path
        self._scan_files_seen = 0
        self._scan_bytes_seen = 0
        self._scan_errors_seen = 0
        self.path_bar.set_scanning(True)
        self.progress.setRange(0, 0)
        self.progress.setFormat("Scan läuft ...")
        self.progress.setVisible(True)
        self.progress.setToolTip("Scan läuft. Klicken für Details zum aktuellen Scan.")
        self.status_label.setText(f"Starte Scan: {path}")

        self._thread = QThread(self)
        self._worker = ScanWorker(path)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.on_progress)
        self._worker.finished.connect(self.on_finished)
        self._worker.failed.connect(self.on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    @Slot()
    def cancel_scan(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self._scan_phase = "Scan wird abgebrochen"
            self.progress.setFormat("Abbruch wird vorbereitet ...")
            self.status_label.setText("Scan wird abgebrochen ...")

    @Slot(str, object, object, object)
    def on_progress(self, current_path: str, files: int, bytes_seen: int, errors: int) -> None:
        self._scan_phase = "Scan läuft"
        self._scan_last_path = current_path
        self._scan_files_seen = int(files)
        self._scan_bytes_seen = int(bytes_seen)
        self._scan_errors_seen = int(errors)
        self.total_value.setText(format_size(bytes_seen))
        self.files_value.setText(f"{files:,}".replace(",", "."))
        self.progress.setFormat(f"Scan läuft ... {int(files):,} Dateien".replace(",", "."))
        self.status_label.setText(f"Scanne: {current_path}")

    @Slot(object, object, object)
    def on_finished(self, root: ScanNode, totals: dict[str, int], errors: list[ScanError]) -> None:
        self._pending_scan_result = (root, totals, errors)
        self._finalizing_results = True
        self._scan_phase = "Scan abgeschlossen - Ergebnisse werden vorbereitet"
        self._scan_last_path = root.path
        self._scan_files_seen = int(root.file_count)
        self._scan_bytes_seen = int(root.size)
        self._scan_errors_seen = len(errors)
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.progress.setFormat("Ergebnisse werden vorbereitet ...")
        self.progress.setToolTip("Scan abgeschlossen. Die Oberfläche wird vorbereitet. Klicken für Details.")
        self.status_label.setText("Scan abgeschlossen. Ergebnisse werden jetzt vorbereitet ...")
        QApplication.processEvents()
        QTimer.singleShot(30, self._finalize_scan_stage_tree)

    @Slot(str)
    def on_failed(self, message: str) -> None:
        self._scan_phase = "Scanfehler"
        self.progress.setVisible(False)
        self.path_bar.set_scanning(False)
        self.status_label.setText("Scan konnte nicht gestartet werden.")
        QMessageBox.warning(self, "Scanfehler", message)

    @Slot()
    def _cleanup_thread(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
        if self._thread is not None:
            self._thread.deleteLater()
        self._worker = None
        self._thread = None
        if not self._finalizing_results:
            self.path_bar.set_scanning(False)
            self.progress.setVisible(False)

    def _reset_result_view(self) -> None:
        self._root = None
        self._category_totals = {}
        self._errors = []
        self._pending_scan_result = None
        self._finalizing_results = False
        self._scan_phase = "Bereit"
        self._scan_last_path = ""
        self._scan_files_seen = 0
        self._scan_bytes_seen = 0
        self._scan_errors_seen = 0
        self.total_value.setText("0 B")
        self.files_value.setText("0")
        self.folders_value.setText("0")
        self.summary_bar.set_totals({})
        self.category_panel.set_totals({})
        self.top_folders_table.setRowCount(0)
        self.top_files_table.setRowCount(0)
        self.tree.clear()
        self._error_badge.setVisible(False)
        self.duplicate_panel.set_root(None)
        self.duplicate_panel.cancel_if_running()
        self._set_action_buttons(False)

    def _finalize_scan_stage_tree(self) -> None:
        if not self._pending_scan_result:
            return
        root, totals, errors = self._pending_scan_result
        self._root = root
        self._category_totals = totals
        self._errors = errors
        self._scan_phase = "Erzeuge Ordnerbaum"
        self.progress.setFormat("Erzeuge Ordnerbaum ...")
        self.status_label.setText("Scan abgeschlossen. Erzeuge Ordnerbaum ...")
        QApplication.processEvents()
        self.tree.set_scan_result(root)
        QTimer.singleShot(30, self._finalize_scan_stage_categories)

    def _finalize_scan_stage_categories(self) -> None:
        if self._root is None:
            return
        self._scan_phase = "Berechne Kategorien"
        self.progress.setFormat("Berechne Kategorien ...")
        self.status_label.setText("Berechne Kategorien und Kennzahlen ...")
        QApplication.processEvents()
        self.summary_bar.set_totals(self._category_totals)
        self.category_panel.set_totals(self._category_totals)
        self.total_value.setText(format_size(self._root.size))
        self.files_value.setText(f"{self._root.file_count:,}".replace(",", "."))
        self.folders_value.setText(f"{self._root.folder_count:,}".replace(",", "."))
        self._update_error_badge(self._errors)
        QTimer.singleShot(30, self._finalize_scan_stage_tables)

    def _finalize_scan_stage_tables(self) -> None:
        if self._root is None:
            return
        self._scan_phase = "Erzeuge Top-Listen"
        self.progress.setFormat("Erzeuge Top-Listen ...")
        self.status_label.setText("Erzeuge Top-50-Listen ...")
        QApplication.processEvents()
        self.refresh_top_tables()
        QTimer.singleShot(30, self._finalize_scan_done)

    def _finalize_scan_done(self) -> None:
        if self._root is None:
            return
        self._scan_phase = "Scan abgeschlossen"
        self._pending_scan_result = None
        self._finalizing_results = False
        self.progress.setVisible(False)
        self.path_bar.set_scanning(False)
        self._set_action_buttons(True)
        self.duplicate_panel.set_root(self._root)
        err_count = len(self._errors)
        if err_count:
            self.status_label.setText(
                f"Scan abgeschlossen. {err_count} Zugriffsfehler – Details über den ⚠-Button."
            )
        else:
            self.status_label.setText(
                "Scan abgeschlossen. Die große Grafik kann jetzt über 'Grafik öffnen' geladen werden."
            )

    def _update_error_badge(self, errors: list[ScanError]) -> None:
        count = len(errors)
        if count > 0:
            self._error_badge.setText(f"⚠ {count} Fehler")
            self._error_badge.setVisible(True)
        else:
            self._error_badge.setVisible(False)

    def _show_error_list(self) -> None:
        """Zeigt die Liste der Scan-Fehler in einem durchsuchbaren Detailfenster."""
        show_scan_error_details(self._errors, self)

    def _elapsed_text(self) -> str:
        if self._scan_started_at is None:
            return "-"
        seconds = max(0, int(time.monotonic() - self._scan_started_at))
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:d} h {minutes:02d} min {seconds:02d} s"
        if minutes:
            return f"{minutes:d} min {seconds:02d} s"
        return f"{seconds:d} s"

    @Slot()
    def show_scan_details(self) -> None:
        if self._root is None and self._scan_started_at is None and not self._scan_last_path:
            QMessageBox.information(self, "Scan-Details", "Es liegen noch keine Scan-Details vor.")
            return

        folder_count = self._root.folder_count if self._root is not None else "wird ermittelt"
        lines = [
            f"Status: {self._scan_phase}",
            f"Laufzeit: {self._elapsed_text()}",
            f"Aktueller/letzter Pfad: {self._scan_last_path or '-'}",
            "",
            f"Gefundene Dateien: {self._scan_files_seen:,}".replace(",", "."),
            f"Gefundene Ordner: {folder_count if isinstance(folder_count, str) else f'{folder_count:,}'.replace(',', '.')}",
            f"Gelesene Größe: {format_size(self._scan_bytes_seen)}",
            f"Zugriffsfehler: {self._scan_errors_seen:,}".replace(",", "."),
        ]
        if self._finalizing_results:
            lines.extend([
                "",
                "Hinweis: Der Scan ist fertig. Die Oberfläche baut gerade Ordnerbaum, Kategorien und Top-Listen auf.",
            ])
        elif self._root is not None:
            lines.extend([
                "",
                "Ergebnis ist vollständig geladen.",
            ])
        QMessageBox.information(self, "Scan-Details", "\n".join(lines))

    def refresh_top_tables(self) -> None:
        if self._root is None:
            return
        self._fill_top_table(self.top_folders_table, top_folders(self._root, 50))
        self.refresh_top_files()

    @Slot()
    def refresh_top_files(self) -> None:
        if self._root is None:
            return
        min_bytes = int(self.min_file_size_gb.value() * 1024 * 1024 * 1024)
        self._fill_top_table(self.top_files_table, top_files(self._root, 50, min_bytes))

    def _fill_top_table(self, table: QTableWidget, nodes: list[ScanNode]) -> None:
        table.setSortingEnabled(False)
        table.setRowCount(len(nodes))
        total = self._root.size if self._root else 0
        for row, node in enumerate(nodes):
            percent = (node.size / total * 100) if total else 0
            values = [
                node.name,
                format_size(node.size),
                f"{percent:.1f} %",
                "Ordner" if node.is_dir else "Datei",
                node.path,
            ]
            for column, value in enumerate(values):
                item = NumericTableWidgetItem(value)
                # Sortierwert je nach Spaltentyp
                if column == 1:
                    item.setData(_ROLE_SORT, node.size)
                elif column == 2:
                    item.setData(_ROLE_SORT, percent)
                else:
                    item.setData(_ROLE_SORT, str(value).lower())
                # Pfad und is_dir immer in eigenen Rollen
                item.setData(_ROLE_PATH, node.path)
                item.setData(_ROLE_ISDIR, node.is_dir)
                item.setToolTip(node.path)
                table.setItem(row, column, item)
        table.setSortingEnabled(True)
        table.sortItems(1, Qt.SortOrder.DescendingOrder)
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)

    def _open_table_context_menu(self, table: QTableWidget, position) -> None:
        item = table.item(table.currentRow(), 0)
        if item is None:
            return
        path = item.data(_ROLE_PATH)
        is_dir = bool(item.data(_ROLE_ISDIR))
        if not path:
            return
        menu = QMenu(self)
        open_action = QAction("Im Explorer öffnen", self)
        copy_action = QAction("Pfad kopieren", self)
        open_action.triggered.connect(lambda: self._open_path(str(path), is_dir))
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(str(path)))
        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(copy_action)
        menu.exec(table.viewport().mapToGlobal(position))

    def _open_table_row(self, table: QTableWidget, row: int) -> None:
        item = table.item(row, 0)
        if item is None:
            return
        path = item.data(_ROLE_PATH)
        is_dir = bool(item.data(_ROLE_ISDIR))
        if not path:
            return
        if is_dir:
            self.status_label.setText("Ordner können per Rechtsklick im Explorer geöffnet werden.")
            return
        self._open_file(str(path))

    def _open_path(self, path: str, is_dir: bool) -> None:
        import os
        target = path if is_dir else os.path.dirname(path)
        if target:
            QDesktopServices.openUrl(QUrl.fromLocalFile(target))

    def _open_file(self, path: str) -> None:
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _set_action_buttons(self, enabled: bool) -> None:
        self.export_csv_button.setEnabled(enabled)
        self.export_json_button.setEnabled(enabled)
        self.report_button.setEnabled(enabled)
        self._set_graphic_button_ready(enabled)

    def _set_graphic_button_ready(self, ready: bool) -> None:
        self.graphic_button.setEnabled(ready)
        self.graphic_button.setObjectName("ReadyGraphicButton" if ready else "DormantGraphicButton")
        self.graphic_button.setToolTip(
            "Große Scan-Grafik öffnen."
            if ready
            else "Nach einem erfolgreichen Scan wird die große Grafikansicht hier verfügbar."
        )
        self.graphic_button.style().unpolish(self.graphic_button)
        self.graphic_button.style().polish(self.graphic_button)
        self.graphic_button.update()

    def _open_category_from_table(self, row: int, column: int) -> None:
        item = self.category_panel.item(row, 0)
        if item is None:
            return
        self.open_category_details(item.text())

    def open_category_details(self, category: str) -> None:
        if self._root is None:
            QMessageBox.information(self, "Kategorie-Details", "Bitte zuerst einen Scan ausführen.")
            return
        total_size = int(self._category_totals.get(category, 0))
        if total_size <= 0:
            QMessageBox.information(self, "Kategorie-Details", f"Für die Kategorie '{category}' wurden keine Daten gefunden.")
            return
        window = CategoryDetailWindow(self._root, category, total_size, self)
        window.finished.connect(lambda _result, w=window: self._forget_category_detail_window(w))
        self._category_detail_windows.append(window)
        window.show()
        self.status_label.setText(f"Kategorie-Details geöffnet: {category}")

    def _forget_category_detail_window(self, window: CategoryDetailWindow) -> None:
        if window in self._category_detail_windows:
            self._category_detail_windows.remove(window)

    def open_large_graphics(self) -> None:
        if self._root is None:
            QMessageBox.information(self, "Grafik", "Bitte zuerst einen Scan ausführen.")
            return
        self._graphics_window = LargeGraphicsWindow(self._root, self._category_totals, self.open_category_details, self)
        self._graphics_window.show()
        self.status_label.setText("Grafik wurde in einer großen Ansicht geöffnet.")

    def export_as_csv(self) -> None:
        if self._root is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "CSV exportieren", "spacelens_scan.csv", "CSV-Dateien (*.csv)")
        if path:
            export_csv(self._root, path)
            self.status_label.setText(f"CSV exportiert: {path}")

    def export_as_json(self) -> None:
        if self._root is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "JSON exportieren", "spacelens_scan.json", "JSON-Dateien (*.json)")
        if path:
            export_json(self._root, self._category_totals, self._errors, path)
            self.status_label.setText(f"JSON exportiert: {path}")

    def export_report(self) -> None:
        if self._root is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "HTML-Report speichern", "spacelens_report.html", "HTML-Dateien (*.html)")
        if path:
            export_html_report(self._root, self._category_totals, self._errors, path)
            self.status_label.setText(f"HTML-Report erstellt: {path}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
