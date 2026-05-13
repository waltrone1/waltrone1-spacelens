from __future__ import annotations

import fnmatch
import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from ...core.size_format import format_size

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


_ROLE_PATH = Qt.ItemDataRole.UserRole + 1


class ResultDetailWindow(QDialog):
    """Einheitliches Detailfenster fuer Scan-Fehler und Aktions-Ergebnisse."""

    def __init__(self, title: str, subtitle: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1180, 760)
        self.setMinimumSize(980, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("Title")
        layout.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("Subtitle")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)

        hint = QLabel("Tipp: Doppelklick oeffnet Dateien direkt. Rechtsklick bietet Datei oeffnen, Speicherort oeffnen und Pfad kopieren. Suche unterstuetzt Wildcards wie *.png.")
        hint.setObjectName("Subtitle")
        layout.addWidget(hint)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Schnellsuche: Pfad, Datei oder Meldung filtern ... Wildcards: *.png, IMG_*.JPG")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search_input)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        close_button = QPushButton("Schliessen")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)

    def add_table_tab(self, tab_title: str, headers: list[str], rows: list[list[str]], path_column: int | None = None) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(False)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(lambda pos, t=table: self._show_table_menu(t, pos))
        table.itemDoubleClicked.connect(lambda item, t=table: self._open_row_file_or_location(t, item.row()))

        table.setRowCount(len(rows))
        for row_index, row_values in enumerate(rows):
            row_path = ""
            if path_column is not None and path_column < len(row_values):
                row_path = row_values[path_column]
            for col_index, value in enumerate(row_values):
                item = QTableWidgetItem(value)
                if row_path:
                    item.setData(_ROLE_PATH, row_path)
                    item.setToolTip(row_path)
                table.setItem(row_index, col_index, item)

        header = table.horizontalHeader()
        if headers:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            for idx in range(1, len(headers)):
                header.setSectionResizeMode(idx, QHeaderView.ResizeMode.Stretch)
        table.setSortingEnabled(True)
        self.tabs.addTab(table, tab_title)
        return table

    def _apply_filter(self, text: str) -> None:
        query = " ".join(text.lower().split())
        for tab_index in range(self.tabs.count()):
            table = self.tabs.widget(tab_index)
            if not isinstance(table, QTableWidget):
                continue
            for row in range(table.rowCount()):
                if not query:
                    table.setRowHidden(row, False)
                    continue
                values: list[str] = []
                for col in range(table.columnCount()):
                    item = table.item(row, col)
                    if item is not None:
                        values.append(item.text())
                        if item.toolTip():
                            values.append(item.toolTip())
                        path = item.data(_ROLE_PATH)
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

    def _show_table_menu(self, table: QTableWidget, pos) -> None:
        row = table.rowAt(pos.y())
        if row < 0:
            return
        path = self._row_path(table, row)
        if not path:
            return

        menu = QMenu(self)
        open_file_action = QAction("Datei oeffnen", self)
        open_location_action = QAction("Speicherort oeffnen", self)
        copy_action = QAction("Pfad kopieren", self)
        open_file_action.setEnabled(os.path.isfile(path))
        open_file_action.triggered.connect(lambda: self._open_file(path))
        open_location_action.triggered.connect(lambda: self._open_location(path))
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(path))
        menu.addAction(open_file_action)
        menu.addAction(open_location_action)
        menu.addSeparator()
        menu.addAction(copy_action)
        menu.exec(table.viewport().mapToGlobal(pos))

    def _open_row_file_or_location(self, table: QTableWidget, row: int) -> None:
        path = self._row_path(table, row)
        if not path:
            return
        if os.path.isfile(path):
            self._open_file(path)
        else:
            self._open_location(path)

    @staticmethod
    def _row_path(table: QTableWidget, row: int) -> str:
        for col in range(table.columnCount()):
            item = table.item(row, col)
            if item is not None:
                path = item.data(_ROLE_PATH)
                if path:
                    return str(path)
        return ""

    @staticmethod
    def _open_file(path: str) -> None:
        if os.path.isfile(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    @staticmethod
    def _open_location(path: str) -> None:
        target = path
        if os.path.isfile(path):
            target = os.path.dirname(path)
        elif not os.path.isdir(path):
            target = os.path.dirname(path)
        if target:
            QDesktopServices.openUrl(QUrl.fromLocalFile(target))



class DuplicateDeleteConfirmWindow(ResultDetailWindow):
    """Grosses, durchsuchbares Sicherheitsfenster vor dem Entfernen von Duplikaten."""

    def __init__(
        self,
        paths_to_delete: list[str],
        kept_paths: list[str] | None = None,
        note: str = "",
        parent=None,
    ) -> None:
        kept_paths = kept_paths or []
        subtitle_parts: list[str] = []
        if note:
            subtitle_parts.append(note.strip())
        subtitle_parts.append(
            f"{len(paths_to_delete)} Datei(en) werden in den Papierkorb verschoben."
        )
        potential_free = 0
        for path in paths_to_delete:
            try:
                potential_free += os.path.getsize(path)
            except OSError:
                pass
        if potential_free > 0:
            subtitle_parts.append(
                f"Nach dem Leeren des Papierkorbs werden dadurch bis zu {format_size(potential_free)} frei."
            )
        if kept_paths:
            subtitle_parts.append(
                f"{len(kept_paths)} Datei(en) bleiben erhalten."
            )

        super().__init__(
            "Duplikate entfernen - Bestaetigung",
            " ".join(subtitle_parts),
            parent,
        )
        self.setMinimumSize(980, 620)
        self.resize(1180, 760)
        self._accepted = False

        self.add_table_tab(
            "Wird entfernt",
            ["#", "Datei"],
            [[str(i), path] for i, path in enumerate(paths_to_delete, start=1)],
            path_column=1,
        )
        if kept_paths:
            self.add_table_tab(
                "Bleibt erhalten",
                ["#", "Datei"],
                [[str(i), path] for i, path in enumerate(kept_paths, start=1)],
                path_column=1,
            )

        # Den Standard-Schliessen-Button der Basisansicht ausblenden, damit unten nur Ja/Nein bleibt.
        for button in self.findChildren(QPushButton):
            if button.text() == "Schliessen":
                button.hide()

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.no_button = QPushButton("Nein")
        self.yes_button = QPushButton("Ja")
        self.yes_button.setObjectName("DangerButton")
        self.no_button.clicked.connect(self.reject)
        self.yes_button.clicked.connect(self.accept)
        self.yes_button.setDefault(True)
        self.yes_button.setAutoDefault(True)
        self.no_button.setAutoDefault(False)
        button_row.addWidget(self.yes_button)
        button_row.addWidget(self.no_button)
        self.layout().addLayout(button_row)
        self.yes_button.setFocus(Qt.FocusReason.OtherFocusReason)


def confirm_duplicate_delete(
    paths_to_delete: list[str],
    kept_paths: list[str] | None = None,
    note: str = "",
    parent=None,
) -> bool:
    dialog = DuplicateDeleteConfirmWindow(paths_to_delete, kept_paths, note, parent)
    return dialog.exec() == QDialog.DialogCode.Accepted

def show_scan_error_details(errors, parent=None) -> None:
    if not errors:
        dialog = ResultDetailWindow("Scan-Fehler", "Keine Zugriffsfehler vorhanden.", parent)
        dialog.add_table_tab("Fehler", ["Status"], [["Keine Zugriffsfehler vorhanden."]])
        dialog.exec()
        return

    rows = [[str(index), err.path, err.message] for index, err in enumerate(errors, start=1)]
    dialog = ResultDetailWindow(
        "Scan-Fehler",
        f"Insgesamt {len(errors)} Zugriffsfehler. Diese Ansicht ersetzt das alte Popup und kann durchsucht werden.",
        parent,
    )
    dialog.add_table_tab("Zugriffsfehler", ["#", "Pfad", "Meldung"], rows, path_column=1)
    dialog.exec()


def show_duplicate_delete_result(deleted: list[str], failed: list[str], parent=None, freed_bytes: int | None = None) -> None:
    subtitle_parts = []
    if deleted:
        text = f"{len(deleted)} Datei(en) wurden in den Papierkorb verschoben."
        if freed_bytes is not None and freed_bytes > 0:
            text += f" Potenziell freigegeben nach Papierkorb-Leerung: {format_size(freed_bytes)}."
        subtitle_parts.append(text)
    if failed:
        subtitle_parts.append(f"{len(failed)} Datei(en) konnten nicht entfernt werden.")
    if not subtitle_parts:
        subtitle_parts.append("Es wurden keine Dateien entfernt.")

    dialog = ResultDetailWindow("Duplikate entfernen - Ergebnis", " ".join(subtitle_parts), parent)
    if deleted:
        dialog.add_table_tab("Entfernt", ["#", "Datei"], [[str(i), path] for i, path in enumerate(deleted, start=1)], path_column=1)
    if failed:
        dialog.add_table_tab("Nicht entfernt", ["#", "Datei"], [[str(i), path] for i, path in enumerate(failed, start=1)], path_column=1)
    if not deleted and not failed:
        dialog.add_table_tab("Ergebnis", ["Status"], [["Keine Datei wurde entfernt."]])
    dialog.exec()
