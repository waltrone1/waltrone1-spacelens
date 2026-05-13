from __future__ import annotations

import os

from PySide6.QtCore import QThread, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QDesktopServices,
)

from ...core.duplicates import DuplicateGroup, DuplicateScanWorker
from ...core.models import ScanNode
from ...core.size_format import format_size
from .category_detail_window import LoadingSpinner

# Eigene Rollen
_ROLE_SORT  = Qt.ItemDataRole.UserRole
_ROLE_PATH  = Qt.ItemDataRole.UserRole + 1
_ROLE_ISDIR = Qt.ItemDataRole.UserRole + 2


class DuplicatesPanel(QWidget):
    """
    Tab-Panel für Duplikat-Erkennung.
    Wird als Tab in das Haupt-TabWidget eingebettet.
    """

    status_message = Signal(str)  # für die Statuszeile im Hauptfenster

    def __init__(self) -> None:
        super().__init__()
        self._root: ScanNode | None = None
        self._groups: list[DuplicateGroup] = []
        self._thread: QThread | None = None
        self._worker: DuplicateScanWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # --- Kopfzeile ---
        header_row = QHBoxLayout()
        info = QLabel(
            "Findet Dateien mit identischem Inhalt (SHA-256). "
            "Schritt 1 gruppiert nach Größe, Schritt 2 prüft nur echte Kandidaten."
        )
        info.setObjectName("Subtitle")
        info.setWordWrap(True)

        self.scan_button = QPushButton("Duplikate suchen")
        self.scan_button.setObjectName("PrimaryButton")
        self.scan_button.setEnabled(False)
        self.scan_button.clicked.connect(self._start_scan)

        self.cancel_button = QPushButton("Abbrechen")
        self.cancel_button.setObjectName("DangerButton")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel_scan)

        header_row.addWidget(info, 1)
        header_row.addWidget(self.scan_button)
        header_row.addWidget(self.cancel_button)
        layout.addLayout(header_row)

        # --- Fortschritt ---
        progress_row = QHBoxLayout()
        self.spinner = LoadingSpinner()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("Subtitle")
        progress_row.addWidget(self.spinner)
        progress_row.addWidget(self.progress_bar, 1)
        progress_row.addWidget(self.progress_label)
        layout.addLayout(progress_row)

        # --- Ergebnis-Zusammenfassung ---
        self.summary_label = QLabel("Noch kein Duplikat-Scan durchgeführt.")
        self.summary_label.setObjectName("Subtitle")
        layout.addWidget(self.summary_label)

        # --- Duplikat-Tabelle (Gruppen-Übersicht) ---
        self.group_table = QTableWidget(0, 4)
        self.group_table.setHorizontalHeaderLabels(
            ["Dateigröße", "Anzahl Kopien", "Verschwendet", "Beispiel-Dateiname"]
        )
        self.group_table.setAlternatingRowColors(True)
        self.group_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.group_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.group_table.setSortingEnabled(True)
        self.group_table.verticalHeader().setVisible(False)
        header = self.group_table.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.group_table.currentRowChanged.connect(self._on_group_selected)
        layout.addWidget(QLabel("Duplikat-Gruppen (Klick für Details):"))
        layout.addWidget(self.group_table, 2)

        # --- Detail-Baum (Pfade der ausgewählten Gruppe) ---
        layout.addWidget(QLabel("Dateipfade in der ausgewählten Gruppe:"))
        self.detail_tree = QTreeWidget()
        self.detail_tree.setColumnCount(2)
        self.detail_tree.setHeaderLabels(["Pfad", "Ordner"])
        self.detail_tree.setAlternatingRowColors(True)
        self.detail_tree.setRootIsDecorated(False)
        self.detail_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.detail_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.detail_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.detail_tree.customContextMenuRequested.connect(self._open_detail_context_menu)
        self.detail_tree.itemDoubleClicked.connect(self._open_detail_item)
        layout.addWidget(self.detail_tree, 1)

    # ------------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------------

    def set_root(self, root: ScanNode | None) -> None:
        """Wird vom Hauptfenster nach jedem Scan aufgerufen."""
        self._root = root
        self._groups = []
        self.group_table.setRowCount(0)
        self.detail_tree.clear()
        self.scan_button.setEnabled(root is not None)
        if root is None:
            self.summary_label.setText("Noch kein Haupt-Scan vorhanden. Bitte zuerst einen Ordner scannen.")
        else:
            self.summary_label.setText(
                f"Bereit. {root.file_count:,} Dateien im Scan-Ergebnis vorhanden. "
                "Klicke 'Duplikate suchen' um den Hash-Vergleich zu starten.".replace(",", ".")
            )

    # ------------------------------------------------------------------
    # Scan starten / abbrechen
    # ------------------------------------------------------------------

    def _start_scan(self) -> None:
        if self._root is None or self._thread is not None:
            return
        self.scan_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.group_table.setRowCount(0)
        self.detail_tree.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.spinner.start()
        self.summary_label.setText("Schritt 1: Dateien nach Größe gruppieren …")
        self.status_message.emit("Duplikat-Scan läuft …")

        self._thread = QThread(self)
        self._worker = DuplicateScanWorker(self._root)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _cancel_scan(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self.summary_label.setText("Scan wird abgebrochen …")
            self.cancel_button.setEnabled(False)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    @Slot(int, int)
    def _on_progress(self, checked: int, total: int) -> None:
        if total > 0:
            pct = int(checked / total * 100)
            self.progress_bar.setValue(pct)
            self.summary_label.setText(
                f"Schritt 2: Hash-Vergleich … {checked:,} / {total:,} Kandidaten geprüft.".replace(",", ".")
            )
        else:
            self.summary_label.setText("Schritt 1: Dateien nach Größe gruppieren …")

    @Slot(list)
    def _on_finished(self, groups: list[DuplicateGroup]) -> None:
        self._groups = groups
        self._fill_group_table(groups)
        self.spinner.stop()
        self.progress_bar.setVisible(False)
        self.cancel_button.setEnabled(False)

        total_wasted = sum(g.wasted for g in groups)
        if groups:
            self.summary_label.setText(
                f"✓ {len(groups)} Duplikat-Gruppen gefunden – "
                f"verschwendeter Speicher: {format_size(total_wasted)}"
            )
            self.status_message.emit(
                f"Duplikat-Scan abgeschlossen: {len(groups)} Gruppen, {format_size(total_wasted)} verschwendet."
            )
        else:
            self.summary_label.setText("✓ Keine Duplikate gefunden.")
            self.status_message.emit("Duplikat-Scan abgeschlossen: Keine Duplikate gefunden.")

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        self.spinner.stop()
        self.progress_bar.setVisible(False)
        self.cancel_button.setEnabled(False)
        self.scan_button.setEnabled(self._root is not None)
        self.summary_label.setText(f"Fehler beim Duplikat-Scan: {message}")

    def _cleanup_thread(self) -> None:
        if self._worker:
            self._worker.deleteLater()
        self._worker = None
        self._thread = None
        self.scan_button.setEnabled(self._root is not None)

    # ------------------------------------------------------------------
    # Tabelle befüllen
    # ------------------------------------------------------------------

    def _fill_group_table(self, groups: list[DuplicateGroup]) -> None:
        self.group_table.setSortingEnabled(False)
        self.group_table.setRowCount(len(groups))
        for row, group in enumerate(groups):
            example_name = os.path.basename(group.paths[0])

            items = [
                (format_size(group.size), group.size),
                (str(len(group.paths)), len(group.paths)),
                (format_size(group.wasted), group.wasted),
                (example_name, example_name.lower()),
            ]
            for col, (text, sort_val) in enumerate(items):
                item = QTableWidgetItem(text)
                item.setData(_ROLE_SORT, sort_val)
                item.setData(_ROLE_PATH, row)  # Gruppen-Index für Detail-Ansicht
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                # Zeilen mit viel verschwendetem Speicher leicht hervorheben
                if group.wasted > 100 * 1024 * 1024:  # > 100 MB
                    item.setBackground(QColor("#fef3c7"))
                self.group_table.setItem(row, col, item)

        self.group_table.setSortingEnabled(True)
        self.group_table.sortItems(2, Qt.SortOrder.DescendingOrder)
        self.group_table.resizeColumnsToContents()
        self.group_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

    @Slot(int)
    def _on_group_selected(self, row: int) -> None:
        self.detail_tree.clear()
        if row < 0 or row >= len(self._groups):
            return
        # Hole die echte Gruppe über den gespeicherten Index (vor Sortierung)
        index_item = self.group_table.item(row, 0)
        if index_item is None:
            return
        group_index = index_item.data(_ROLE_PATH)
        if group_index is None or group_index >= len(self._groups):
            return
        group = self._groups[group_index]

        for path in group.paths:
            folder = os.path.dirname(path)
            name = os.path.basename(path)
            item = QTreeWidgetItem([path, folder])
            item.setData(0, _ROLE_PATH, path)
            item.setData(0, _ROLE_ISDIR, False)
            item.setToolTip(0, path)
            self.detail_tree.addTopLevelItem(item)

    # ------------------------------------------------------------------
    # Kontextmenü / Öffnen
    # ------------------------------------------------------------------

    def _open_detail_context_menu(self, position) -> None:
        item = self.detail_tree.currentItem()
        if item is None:
            return
        path = item.data(0, _ROLE_PATH)
        if not path:
            return
        menu = QMenu(self)
        open_file_action = QAction("Datei öffnen", self)
        open_folder_action = QAction("Im Explorer öffnen", self)
        copy_action = QAction("Pfad kopieren", self)
        open_file_action.triggered.connect(lambda: self._open_file(path))
        open_folder_action.triggered.connect(lambda: self._open_folder(path))
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(path))
        menu.addAction(open_file_action)
        menu.addAction(open_folder_action)
        menu.addSeparator()
        menu.addAction(copy_action)
        menu.exec(self.detail_tree.viewport().mapToGlobal(position))

    def _open_detail_item(self, item: QTreeWidgetItem, column: int) -> None:
        path = item.data(0, _ROLE_PATH)
        if path:
            self._open_file(path)

    def _open_file(self, path: str) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _open_folder(self, path: str) -> None:
        folder = os.path.dirname(path)
        if folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
