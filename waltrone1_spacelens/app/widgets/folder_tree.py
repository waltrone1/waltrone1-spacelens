from __future__ import annotations

import os

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import QApplication, QHeaderView, QMenu, QTreeWidget, QTreeWidgetItem

from ...core.models import ScanNode
from ...core.size_format import format_size


class SortableTreeWidgetItem(QTreeWidgetItem):
    def __lt__(self, other: QTreeWidgetItem) -> bool:
        column = self.treeWidget().sortColumn() if self.treeWidget() else 0
        left = self.data(column, Qt.ItemDataRole.UserRole)
        right = other.data(column, Qt.ItemDataRole.UserRole)
        if left is not None and right is not None:
            return left < right
        return super().__lt__(other)


class FolderTree(QTreeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setColumnCount(6)
        self.setHeaderLabels(["Name", "Größe", "Anteil", "Dateien", "Ordner", "Pfad"])
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.setSortingEnabled(True)
        self.sortByColumn(1, Qt.SortOrder.DescendingOrder)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_context_menu)
        self.setExpandsOnDoubleClick(False)
        self.itemDoubleClicked.connect(self._open_item)
        header = self.header()
        header.setSectionsMovable(True)
        header.setSectionsClickable(True)
        header.setHighlightSections(True)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setMinimumSectionSize(80)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.setColumnWidth(0, 360)
        self.setColumnWidth(1, 120)
        self.setColumnWidth(2, 95)
        self.setColumnWidth(3, 95)
        self.setColumnWidth(4, 95)
        self.setColumnWidth(5, 520)
        header.setStretchLastSection(True)

    def show_placeholder(self) -> None:
        self.clear()
        item = QTreeWidgetItem(["Noch kein Scan gestartet", "", "", "", "", ""])
        self.addTopLevelItem(item)

    def set_scan_result(self, root: ScanNode) -> None:
        self.setSortingEnabled(False)
        self.clear()
        root_item = self._build_item(root, root.size)
        self.addTopLevelItem(root_item)
        root_item.setExpanded(True)
        for index in range(min(root_item.childCount(), 20)):
            root_item.child(index).setExpanded(False)
        self.setSortingEnabled(True)
        self.sortByColumn(1, Qt.SortOrder.DescendingOrder)

    def _build_item(self, node: ScanNode, total_size: int) -> QTreeWidgetItem:
        percent = (node.size / total_size * 100) if total_size else 0
        prefix = "📁 " if node.is_dir else "📄 "
        item = SortableTreeWidgetItem([
            f"{prefix}{node.name}",
            format_size(node.size),
            f"{percent:.1f} %",
            f"{node.file_count:,}".replace(",", "."),
            f"{node.folder_count:,}".replace(",", "."),
            node.path,
        ])
        item.setData(0, Qt.ItemDataRole.UserRole, node.name.lower())
        item.setData(1, Qt.ItemDataRole.UserRole, node.size)
        item.setData(2, Qt.ItemDataRole.UserRole, percent)
        item.setData(3, Qt.ItemDataRole.UserRole, node.file_count)
        item.setData(4, Qt.ItemDataRole.UserRole, node.folder_count)
        item.setData(5, Qt.ItemDataRole.UserRole, node.path.lower())
        item.setData(0, Qt.ItemDataRole.UserRole + 1, node.path)
        item.setData(0, Qt.ItemDataRole.UserRole + 2, node.is_dir)
        if node.is_dir:
            item.setToolTip(0, "Doppelklick: Unterordner auf-/zuklappen | Rechtsklick: Ordner im Explorer öffnen")
        else:
            item.setToolTip(0, "Doppelklick: Datei öffnen")
        item.setToolTip(5, node.path)
        for child in node.children:
            item.addChild(self._build_item(child, total_size))
        return item

    def _selected_path(self) -> tuple[str, bool] | None:
        item = self.currentItem()
        if item is None:
            return None
        path = item.data(0, Qt.ItemDataRole.UserRole + 1)
        is_dir = item.data(0, Qt.ItemDataRole.UserRole + 2)
        if not path:
            return None
        return str(path), bool(is_dir)

    def _open_item(self, item: QTreeWidgetItem, column: int) -> None:
        path = item.data(0, Qt.ItemDataRole.UserRole + 1)
        is_dir = bool(item.data(0, Qt.ItemDataRole.UserRole + 2))
        if not path:
            return
        if is_dir:
            item.setExpanded(not item.isExpanded())
            return
        self._open_file(str(path))

    def _open_context_menu(self, position) -> None:
        selected = self._selected_path()
        if selected is None:
            return
        path, is_dir = selected
        menu = QMenu(self)
        open_action = QAction("Im Explorer öffnen", self)
        copy_action = QAction("Pfad kopieren", self)
        open_action.triggered.connect(lambda: self._open_path(path, is_dir))
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(path))
        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(copy_action)
        menu.exec(self.viewport().mapToGlobal(position))

    def _open_path(self, path: str, is_dir: bool = True) -> None:
        target = path if is_dir else os.path.dirname(path)
        if target:
            QDesktopServices.openUrl(QUrl.fromLocalFile(target))

    def _open_file(self, path: str) -> None:
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
