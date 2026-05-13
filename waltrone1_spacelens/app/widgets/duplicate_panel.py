from __future__ import annotations

import hashlib
import os
from collections import defaultdict
from threading import Event

from PySide6.QtCore import QEvent, QFile, QObject, QThread, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QAction, QColor, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.models import ScanNode
from ...core.size_format import format_size
from ..widgets.category_detail_window import LoadingSpinner
from ..widgets.result_detail_window import confirm_duplicate_delete, show_duplicate_delete_result

# ---------------------------------------------------------------------------
# Datenmodell
# ---------------------------------------------------------------------------

class DuplicateGroup:
    """Eine Gruppe von Dateien mit identischem Inhalt."""

    def __init__(self, size: int, paths: list[str]) -> None:
        self.size = size          # Größe einer einzelnen Datei
        self.paths = paths        # alle Pfade dieser Gruppe
        self.wasted = size * (len(paths) - 1)  # verschwendeter Speicher


# ---------------------------------------------------------------------------
# Worker-Thread: Phase 1 (Größen-Vorfilter) + Phase 2 (SHA-256-Hash)
# ---------------------------------------------------------------------------

class DuplicateWorker(QObject):
    progress = Signal(str)          # Fortschrittstext
    finished = Signal(list)         # list[DuplicateGroup]
    failed = Signal(str)

    def __init__(self, root: ScanNode) -> None:
        super().__init__()
        self.root = root
        self._cancel = Event()

    def cancel(self) -> None:
        self._cancel.set()

    @Slot()
    def run(self) -> None:
        try:
            # --- Phase 1: alle Dateien sammeln und nach Größe gruppieren ---
            self.progress.emit("Phase 1: Dateien nach Größe gruppieren …")
            size_map: dict[int, list[str]] = defaultdict(list)
            stack = [self.root]
            while stack and not self._cancel.is_set():
                node = stack.pop()
                if node.is_dir:
                    stack.extend(node.children)
                elif node.size > 0:
                    size_map[node.size].append(node.path)

            if self._cancel.is_set():
                self.finished.emit([])
                return

            # Nur Größen mit mind. 2 Dateien sind Duplikat-Kandidaten
            candidates = {size: paths for size, paths in size_map.items() if len(paths) >= 2}
            total_candidates = sum(len(p) for p in candidates.values())

            # --- Phase 2: SHA-256-Hash der Kandidaten ---
            self.progress.emit(f"Phase 2: {total_candidates} Kandidaten hashen …")
            hash_map: dict[str, list[str]] = defaultdict(list)
            hashed = 0
            for size, paths in candidates.items():
                for path in paths:
                    if self._cancel.is_set():
                        self.finished.emit([])
                        return
                    digest = self._hash_file(path)
                    if digest:
                        hash_map[digest].append(path)
                    hashed += 1
                    if hashed % 50 == 0:
                        self.progress.emit(
                            f"Phase 2: {hashed}/{total_candidates} Dateien gehasht …"
                        )

            # Nur echte Duplikate (mind. 2 Pfade pro Hash)
            groups: list[DuplicateGroup] = []
            for paths in hash_map.values():
                if len(paths) >= 2:
                    # Größe aus erstem Pfad bestimmen
                    try:
                        size = os.path.getsize(paths[0])
                    except OSError:
                        size = 0
                    groups.append(DuplicateGroup(size=size, paths=paths))

            # Sortierung: meisten verschwendeten Speicher zuerst
            groups.sort(key=lambda g: g.wasted, reverse=True)
            self.finished.emit(groups)

        except Exception as exc:
            self.failed.emit(str(exc))

    def _hash_file(self, path: str) -> str | None:
        """SHA-256-Hash einer Datei; gibt None bei Lesefehlern zurück."""
        try:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                while chunk := f.read(65536):
                    if self._cancel.is_set():
                        return None
                    h.update(chunk)
            return h.hexdigest()
        except OSError:
            return None


# ---------------------------------------------------------------------------
# UI-Widget
# ---------------------------------------------------------------------------

class DuplicatePanel(QWidget):
    """Tab-Inhalt: Duplikatfinder."""

    def __init__(self) -> None:
        super().__init__()
        self._root: ScanNode | None = None
        self._thread: QThread | None = None
        self._worker: DuplicateWorker | None = None
        self._groups: list[DuplicateGroup] = []
        self._dot_count = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # --- Kopfzeile ---
        head_row = QHBoxLayout()
        self._info_label = QLabel(
            "Findet Dateien mit identischem Inhalt (SHA-256). "
            "Starte zuerst einen Scan, dann klicke auf 'Duplikate suchen'."
        )
        self._info_label.setObjectName("Subtitle")
        self._info_label.setWordWrap(True)

        self._scan_button = QPushButton("🔍  Duplikate suchen")
        self._scan_button.setObjectName("PrimaryButton")
        self._scan_button.setEnabled(False)
        self._scan_button.clicked.connect(self._start_search)

        self._cancel_button = QPushButton("Abbrechen")
        self._cancel_button.setObjectName("DangerButton")
        self._cancel_button.setEnabled(False)
        self._cancel_button.clicked.connect(self._cancel_search)

        self._delete_all_button = QPushButton("Alle Duplikate entfernen")
        self._delete_all_button.setObjectName("DangerButton")
        self._delete_all_button.setEnabled(False)
        self._delete_all_button.setToolTip(
            "Verschiebt automatisch alle Duplikate bis auf die jeweils neueste Datei pro Gruppe in den Papierkorb."
        )
        self._delete_all_button.clicked.connect(self._delete_all_duplicates_keep_newest)

        head_row.addWidget(self._info_label, 1)
        head_row.addWidget(self._scan_button)
        head_row.addWidget(self._delete_all_button)
        head_row.addWidget(self._cancel_button)
        layout.addLayout(head_row)

        # --- Fortschritt / Ergebnis-Zusammenfassung ---
        status_row = QHBoxLayout()
        self._spinner = LoadingSpinner()
        self._status_label = QLabel("Bereit.")
        self._status_label.setObjectName("Subtitle")
        status_row.addWidget(self._spinner)
        status_row.addWidget(self._status_label, 1)
        layout.addLayout(status_row)

        # --- Ergebnis-Baum ---
        self._tree = QTreeWidget()
        self._tree.setColumnCount(3)
        self._tree.setHeaderLabels(["Datei / Pfad", "Größe", "Verschwendet"])
        self._tree.setAlternatingRowColors(True)
        self._tree.setUniformRowHeights(False)
        self._tree.setSortingEnabled(True)
        self._tree.sortByColumn(2, Qt.SortOrder.DescendingOrder)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._context_menu)
        self._tree.itemDoubleClicked.connect(self._open_item)
        self._tree.installEventFilter(self)
        self._tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        header = self._tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._tree, 1)

        # Animationszeit für "…"
        self._dot_timer = QTimer(self)
        self._dot_timer.timeout.connect(self._animate_dots)
        self._set_scan_button_ready(False)
        self._set_delete_all_button_ready(False)

    def _apply_button_style(self, button: QPushButton, object_name: str) -> None:
        """Setzt den Button-Style sofort neu, wenn der ObjectName dynamisch wechselt."""
        if button.objectName() == object_name:
            return
        button.setObjectName(object_name)
        style = button.style()
        style.unpolish(button)
        style.polish(button)
        button.update()

    def _set_scan_button_ready(self, ready: bool) -> None:
        self._apply_button_style(self._scan_button, "PrimaryButton" if ready else "DormantGraphicButton")

    def _set_delete_all_button_ready(self, ready: bool) -> None:
        self._apply_button_style(self._delete_all_button, "DangerButton" if ready else "DormantGraphicButton")

    # ------------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------------

    def set_root(self, root: ScanNode | None) -> None:
        """Wird vom MainWindow nach einem erfolgreichen Scan aufgerufen."""
        self._root = root
        is_ready = root is not None
        self._scan_button.setEnabled(is_ready)
        self._set_scan_button_ready(is_ready)
        if root is None:
            self._groups = []
            self._tree.clear()
            self._delete_all_button.setEnabled(False)
            self._set_delete_all_button_ready(False)
            self._status_label.setText("Bereit.")
        else:
            self._delete_all_button.setEnabled(False)
            self._set_delete_all_button_ready(False)

    def cancel_if_running(self) -> None:
        """Bricht einen laufenden Duplikat-Scan ab (z.B. bei neuem Ordner-Scan)."""
        if self._worker is not None:
            self._worker.cancel()

    # ------------------------------------------------------------------
    # Internes
    # ------------------------------------------------------------------

    @Slot()
    def _start_search(self) -> None:
        if self._root is None or self._thread is not None:
            return
        self._tree.clear()
        self._groups = []
        self._delete_all_button.setEnabled(False)
        self._set_delete_all_button_ready(False)
        self._scan_button.setEnabled(False)
        self._set_scan_button_ready(False)
        self._cancel_button.setEnabled(True)
        self._spinner.start()
        self._dot_timer.start(400)
        self._status_label.setText("Starte Duplikatsuche …")

        self._thread = QThread(self)
        self._worker = DuplicateWorker(self._root)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    @Slot()
    def _cancel_search(self) -> None:
        if self._worker:
            self._worker.cancel()
            self._status_label.setText("Wird abgebrochen …")
            self._cancel_button.setEnabled(False)

    @Slot(str)
    def _on_progress(self, text: str) -> None:
        self._status_label.setText(text)

    @Slot(list)
    def _on_finished(self, groups: list[DuplicateGroup]) -> None:
        self._groups = groups
        self._dot_timer.stop()
        self._spinner.stop()
        self._scan_button.setEnabled(self._root is not None)
        self._set_scan_button_ready(self._root is not None)
        self._cancel_button.setEnabled(False)
        self._delete_all_button.setEnabled(bool(groups))
        self._set_delete_all_button_ready(bool(groups))

        if not groups:
            self._status_label.setText("Keine Duplikate gefunden.")
            return

        total_wasted = sum(g.wasted for g in groups)
        self._status_label.setText(
            f"{len(groups)} Duplikat-Gruppen gefunden – "
            f"{format_size(total_wasted)} verschwendeter Speicher."
        )
        self._fill_tree(groups)

    @Slot(str)
    def _on_failed(self, msg: str) -> None:
        self._dot_timer.stop()
        self._spinner.stop()
        self._scan_button.setEnabled(self._root is not None)
        self._set_scan_button_ready(self._root is not None)
        self._cancel_button.setEnabled(False)
        self._delete_all_button.setEnabled(False)
        self._set_delete_all_button_ready(False)
        self._status_label.setText(f"Fehler: {msg}")

    def _cleanup_thread(self) -> None:
        if self._worker:
            self._worker.deleteLater()
        if self._thread:
            self._thread.deleteLater()
        self._worker = None
        self._thread = None

    def _animate_dots(self) -> None:
        self._dot_count = (self._dot_count + 1) % 4
        current = self._status_label.text().rstrip(".")
        self._status_label.setText(current + "." * self._dot_count)

    def _fill_tree(self, groups: list[DuplicateGroup]) -> None:
        self._tree.setSortingEnabled(False)
        self._tree.clear()

        for group in groups:
            # Gruppen-Kopfzeile
            wasted_text = format_size(group.wasted)
            size_text = format_size(group.size)
            count = len(group.paths)
            header_item = QTreeWidgetItem([
                f"📋  {count}× identisch – {os.path.basename(group.paths[0])}",
                size_text,
                wasted_text,
            ])
            header_item.setData(0, Qt.ItemDataRole.UserRole + 3, list(group.paths))
            header_item.setData(1, Qt.ItemDataRole.UserRole, group.size)
            header_item.setData(2, Qt.ItemDataRole.UserRole, group.wasted)
            # Gruppe einfärben
            for col in range(3):
                header_item.setForeground(col, QColor("#92400e"))
                header_item.setBackground(col, QColor("#fef3c7"))
            font = header_item.font(0)
            font.setBold(True)
            header_item.setFont(0, font)
            header_item.setToolTip(0, f"{count} Dateien mit identischem Inhalt, {size_text} je Datei")

            # Einzelne Dateipfade als Kinder
            for path in group.paths:
                child = QTreeWidgetItem([
                    f"   {os.path.basename(path)}",
                    "",
                    "",
                ])
                child.setToolTip(0, path)
                child.setData(0, Qt.ItemDataRole.UserRole + 1, path)
                child.setData(0, Qt.ItemDataRole.UserRole + 2, False)
                # Vollpfad in zweiter Zeile als ToolTip sichtbar machen
                path_child = QTreeWidgetItem(["   " + path, "", ""])
                path_child.setForeground(0, QColor("#6b7280"))
                path_child.setData(0, Qt.ItemDataRole.UserRole + 1, path)
                path_child.setData(0, Qt.ItemDataRole.UserRole + 2, False)
                path_child.setToolTip(0, path)
                header_item.addChild(child)
                header_item.addChild(path_child)

            header_item.setExpanded(True)
            self._tree.addTopLevelItem(header_item)

        self._tree.setSortingEnabled(True)
        self._tree.sortByColumn(2, Qt.SortOrder.DescendingOrder)

    def _context_menu(self, pos) -> None:
        item = self._tree.itemAt(pos)
        if item is None:
            return

        path: str | None = item.data(0, Qt.ItemDataRole.UserRole + 1)
        group_paths: list[str] | None = item.data(0, Qt.ItemDataRole.UserRole + 3)
        menu = QMenu(self)

        if path:
            open_file_action = QAction("Datei öffnen", self)
            open_action = QAction("Im Explorer öffnen", self)
            copy_action = QAction("Pfad kopieren", self)
            delete_action = QAction("Entfernen", self)
            delete_action.setObjectName("DangerAction")
            open_file_action.triggered.connect(lambda: self._open_file(path))
            open_action.triggered.connect(lambda: self._open_in_explorer(path))
            copy_action.triggered.connect(lambda: QApplication.clipboard().setText(path))
            delete_action.triggered.connect(lambda: self._delete_paths([path]))
            menu.addAction(open_file_action)
            menu.addAction(open_action)
            menu.addSeparator()
            menu.addAction(copy_action)
            menu.addSeparator()
            menu.addAction(delete_action)


        if group_paths:
            if not menu.isEmpty():
                menu.addSeparator()
            group_delete_action = QAction("Gruppe bereinigen: neueste Datei behalten", self)
            group_delete_action.setToolTip("Verschiebt alle Duplikate dieser Gruppe bis auf die neueste Datei in den Papierkorb.")
            group_delete_action.triggered.connect(lambda: self._delete_group_keep_newest(group_paths))
            menu.addAction(group_delete_action)

        if not menu.isEmpty():
            menu.exec(self._tree.viewport().mapToGlobal(pos))

    def eventFilter(self, watched, event) -> bool:
        """Entfernen-Taste im Duplikatbaum abfangen und markierte Datei(en) in den Papierkorb verschieben."""
        if watched is self._tree and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Delete and not event.modifiers():
                paths = self._selected_file_paths()
                if paths:
                    self._delete_paths(paths)
                    return True
        return super().eventFilter(watched, event)

    def _open_item(self, item: QTreeWidgetItem, column: int) -> None:
        del column
        path: str | None = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if path and os.path.isfile(path):
            self._open_file(path)

    def _update_delete_button(self) -> None:
        # Kein separater Button mehr: Auswahl bleibt nur für Entfernen-Taste / Kontextmenü relevant.
        pass

    def _selected_file_paths(self) -> list[str]:
        paths: list[str] = []
        seen: set[str] = set()
        for item in self._tree.selectedItems():
            path: str | None = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if path and os.path.isfile(path) and path not in seen:
                seen.add(path)
                paths.append(path)
        return paths

    def _delete_group_keep_newest(self, paths: list[str]) -> None:
        existing = [p for p in paths if os.path.isfile(p)]
        if len(existing) <= 1:
            return
        try:
            keep = max(existing, key=lambda p: os.path.getmtime(p))
        except OSError:
            keep = existing[0]
        to_delete = [p for p in existing if p != keep]
        self._delete_paths(to_delete, kept_paths=[keep])

    def _delete_all_duplicates_keep_newest(self) -> None:
        """Entfernt automatisch alle Duplikate und behält je Gruppe die neueste vorhandene Datei."""
        if not self._groups:
            return

        to_delete: list[str] = []
        kept: list[str] = []
        for group in self._groups:
            existing = [p for p in group.paths if os.path.isfile(p)]
            if len(existing) <= 1:
                continue
            try:
                keep = max(existing, key=lambda p: os.path.getmtime(p))
            except OSError:
                keep = existing[0]
            kept.append(keep)
            to_delete.extend(p for p in existing if p != keep)

        if not to_delete:
            self._status_label.setText("Keine entfernbaren Duplikate vorhanden.")
            self._delete_all_button.setEnabled(False)
            self._set_delete_all_button_ready(False)
            return

        self._delete_paths(
            to_delete,
            note="Automatisches Entfernen: Pro Duplikat-Gruppe bleibt die jeweils neueste Datei erhalten.",
            kept_paths=kept,
            show_result_dialog=True,
        )

    def _delete_paths(
        self,
        paths: list[str],
        note: str = "",
        kept_paths: list[str] | None = None,
        show_result_dialog: bool = False,
    ) -> None:
        paths = [p for p in dict.fromkeys(paths) if os.path.isfile(p)]
        if not paths:
            self._update_delete_button()
            return

        kept_paths = [p for p in dict.fromkeys(kept_paths or []) if os.path.exists(p)]
        size_before_delete: dict[str, int] = {}
        for path in paths:
            try:
                size_before_delete[path] = os.path.getsize(path)
            except OSError:
                size_before_delete[path] = 0

        if not confirm_duplicate_delete(paths, kept_paths=kept_paths, note=note, parent=self):
            return

        deleted: list[str] = []
        failed: list[str] = []
        for path in paths:
            try:
                if QFile.moveToTrash(path):
                    deleted.append(path)
                else:
                    failed.append(path)
            except Exception:
                failed.append(path)

        freed_bytes = sum(size_before_delete.get(path, 0) for path in deleted)

        if deleted:
            self._remove_deleted_paths_from_groups(deleted)
            self._fill_tree(self._groups)
            total_wasted = sum(g.wasted for g in self._groups)
            has_groups = bool(self._groups)
            self._delete_all_button.setEnabled(has_groups)
            self._set_delete_all_button_ready(has_groups)
            freed_text = f"Potenziell freigegeben: {format_size(freed_bytes)}." if freed_bytes > 0 else ""
            if self._groups:
                self._status_label.setText(
                    f"{len(deleted)} Datei(en) entfernt. "
                    f"{freed_text} "
                    f"Verbleibend: {len(self._groups)} Gruppe(n), {format_size(total_wasted)} verschwendet."
                )
            else:
                self._status_label.setText(
                    f"{len(deleted)} Datei(en) entfernt. {freed_text} Keine Duplikate mehr vorhanden."
                )

        if show_result_dialog or failed:
            show_duplicate_delete_result(deleted, failed, self, freed_bytes=freed_bytes)

        self._update_delete_button()

    def _remove_deleted_paths_from_groups(self, deleted: list[str]) -> None:
        deleted_set = set(deleted)
        new_groups: list[DuplicateGroup] = []
        for group in self._groups:
            remaining = [p for p in group.paths if p not in deleted_set and os.path.isfile(p)]
            if len(remaining) >= 2:
                new_groups.append(DuplicateGroup(size=group.size, paths=remaining))
        new_groups.sort(key=lambda g: g.wasted, reverse=True)
        self._groups = new_groups

    @staticmethod
    def _open_file(path: str) -> None:
        if os.path.isfile(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    @staticmethod
    def _open_in_explorer(path: str) -> None:
        target = os.path.dirname(path) if os.path.isfile(path) else path
        if target:
            QDesktopServices.openUrl(QUrl.fromLocalFile(target))
