from __future__ import annotations

import math
from collections import defaultdict

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QScrollArea,
    QTabWidget,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from ...core.categorizer import categorize_file
from ...core.models import ScanNode
from ...core.size_format import format_size
from ...exports.exporters import top_folders
from .category_detail_window import LoadingSpinner
from .storage_summary_bar import CATEGORY_COLORS

_GRAPH_COLORS = list(CATEGORY_COLORS.values()) + [
    "#22c55e",
    "#06b6d4",
    "#8b5cf6",
    "#ef4444",
    "#eab308",
    "#14b8a6",
]


class _InteractiveCanvas(QWidget):
    """Small helper base for hover/click interactions in custom-painted canvases."""

    def __init__(self) -> None:
        super().__init__()
        self._interactive_areas: list[tuple[object, str, tuple[str, str] | None]] = []
        self.setMouseTracking(True)

    def _clear_interactions(self) -> None:
        self._interactive_areas = []

    def _register_area(self, shape: object, tooltip: str, action: tuple[str, str] | None = None) -> None:
        self._interactive_areas.append((shape, tooltip, action))

    def _shape_contains(self, shape: object, pos) -> bool:
        try:
            return shape.contains(pos)
        except TypeError:
            return False

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = event.pos()
        for shape, tooltip, _action in reversed(self._interactive_areas):
            if self._shape_contains(shape, pos):
                QToolTip.showText(event.globalPos(), tooltip, self)
                return
        QToolTip.hideText()

    def leaveEvent(self, event) -> None:  # noqa: N802
        QToolTip.hideText()
        super().leaveEvent(event)


class CategoryOverviewCanvas(_InteractiveCanvas):
    category_clicked = Signal(str)

    def __init__(self, large_view: bool = True) -> None:
        super().__init__()
        self.large_view = large_view
        self.root: ScanNode | None = None
        self.category_totals: dict[str, int] = {}
        self.setMinimumWidth(1320 if large_view else 980)
        self.setMinimumHeight(1500 if large_view else 1180)

    def set_data(self, root: ScanNode, category_totals: dict[str, int]) -> None:
        self.root = root
        self.category_totals = dict(category_totals)
        self.update()

    def clear_data(self) -> None:
        self.root = None
        self.category_totals = {}
        self._clear_interactions()
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        pos = event.pos()
        for shape, _tooltip, action in reversed(self._interactive_areas):
            if action and self._shape_contains(shape, pos):
                if action[0] == "category":
                    self.category_clicked.emit(action[1])
                    return
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        self._clear_interactions()
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.fillRect(self.rect(), QColor("#ffffff"))

            if self.root is None:
                painter.setPen(QColor("#6b7280"))
                painter.setFont(QFont("Segoe UI", 11))
                painter.drawText(
                    self.rect(),
                    Qt.AlignmentFlag.AlignCenter,
                    "Noch keine Grafik verfügbar.\nBitte zuerst einen Scan ausführen.",
                )
                return

            margin = 22
            width = max(900, self.width() - margin * 2)
            y = margin

            self._draw_title(painter, margin, y, "Kategorien & Ordnerstruktur")
            y += 40
            self._draw_info(painter, margin, y)
            y += 74

            y = self._draw_category_bars(painter, margin, y, width)
            y += 22
            y = self._draw_sunburst(painter, margin, y, width, 760 if self.large_view else 580)
            y += 22
            y = self._draw_top_folder_bars(painter, margin, y, width)
            y += 18

            if self.minimumHeight() != int(y + 40):
                self.setMinimumHeight(int(y + 40))
        finally:
            painter.end()

    def _draw_title(self, painter: QPainter, x: int, y: int, text: str) -> None:
        painter.setPen(QColor("#111827"))
        painter.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        painter.drawText(x, y + 24, text)

    def _draw_info(self, painter: QPainter, x: int, y: int) -> None:
        if not self.root:
            return
        painter.setFont(QFont("Segoe UI", 10))
        painter.setPen(QColor("#374151"))
        text = (
            f"Basis: {self.root.path}  |  Gesamt: {format_size(self.root.size)}  |  "
            f"Dateien: {self.root.file_count:,}  |  Ordner: {self.root.folder_count:,}"
        ).replace(",", ".")
        painter.drawText(QRectF(x, y, self.width() - x * 2, 52), Qt.TextFlag.TextWordWrap, text)

    def _card(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QPen(QColor("#e5e7eb"), 1))
        painter.setBrush(QColor("#f8fafc"))
        painter.drawRoundedRect(rect, 14, 14)

    def _draw_section_header(self, painter: QPainter, x: int, y: int, text: str, hint: str | None = None) -> None:
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        painter.setPen(QColor("#111827"))
        painter.drawText(x, y + 20, text)
        if hint:
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor("#6b7280"))
            painter.drawText(x, y + 40, hint)

    def _draw_category_bars(self, painter: QPainter, x: int, y: int, width: int) -> int:
        if not self.root:
            return y
        visible = [(category, size) for category, size in self.category_totals.items() if size > 0]
        visible.sort(key=lambda item: item[1], reverse=True)
        visible = visible[:10]
        rows = max(1, len(visible))
        row_height = 28
        card_height = 84 + rows * row_height
        self._card(painter, QRectF(x, y, width, card_height))
        self._draw_section_header(
            painter,
            x + 16,
            y + 12,
            "Top-Kategorien",
            "Klick auf eine Kategorie öffnet die vorhandene Detailansicht.",
        )
        total = self.root.size or 1
        label_w = 180
        value_w = 170
        bar_x = x + 16 + label_w
        bar_w = max(180, width - label_w - value_w - 60)
        start_y = y + 58
        painter.setFont(QFont("Segoe UI", 9))
        metrics = QFontMetrics(painter.font())

        for index, (category, size) in enumerate(visible):
            row_y = start_y + index * row_height
            share = size / total * 100 if total else 0
            row_rect = QRectF(x + 14, row_y - 4, width - 28, row_height - 2)
            color = QColor(CATEGORY_COLORS.get(category, "#9ca3af"))
            color_fill = QColor(color)
            color_fill.setAlpha(225)

            name = metrics.elidedText(category, Qt.TextElideMode.ElideRight, label_w - 18)
            painter.setPen(QColor("#374151"))
            painter.drawText(QRectF(x + 16, row_y, label_w - 8, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#e5e7eb"))
            painter.drawRoundedRect(QRectF(bar_x, row_y + 2, bar_w, 14), 6, 6)
            fill_w = max(3, int(bar_w * (size / total))) if total else 0
            painter.setBrush(color_fill)
            painter.drawRoundedRect(QRectF(bar_x, row_y + 2, fill_w, 14), 6, 6)

            painter.setPen(QColor("#4b5563"))
            painter.drawText(
                QRectF(bar_x + bar_w + 12, row_y, value_w, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{format_size(size)}  |  {share:.1f} %",
            )

            tooltip = f"{category}\n{format_size(size)} ({share:.1f} %)\nKlicken für Details"
            self._register_area(row_rect, tooltip, ("category", category))
        return y + card_height

    def _draw_sunburst(self, painter: QPainter, x: int, y: int, width: int, height: int) -> int:
        self._card(painter, QRectF(x, y, width, height))
        self._draw_section_header(
            painter,
            x + 16,
            y + 12,
            "Ordnerstruktur als Sunburst",
            "Zeigt die größten Verzweigungen der Ordnerstruktur. Mouseover blendet Name, Größe und Pfad ein.",
        )
        if not self.root or self.root.size <= 0:
            painter.setPen(QColor("#6b7280"))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(QRectF(x + 16, y + 58, width - 32, 44), Qt.TextFlag.TextWordWrap, "Keine Größeninformationen vorhanden.")
            return y + height

        chart_size = min(width - 110, height - 120)
        chart_size = max(420 if self.large_view else 340, chart_size)
        center = QPointF(x + width / 2, y + 92 + chart_size / 2)
        max_radius = chart_size / 2
        inner_radius = max(66 if self.large_view else 56, max_radius * 0.18)
        max_depth = 5 if self.large_view else 4
        ring_width = (max_radius - inner_radius - 8) / max_depth

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#eef2f7"))
        painter.drawEllipse(center, max_radius, max_radius)

        center_radius = inner_radius - 5
        painter.setBrush(QColor("#111827"))
        painter.setPen(QPen(QColor("#e5e7eb"), 2))
        painter.drawEllipse(center, center_radius, center_radius)

        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        metrics = QFontMetrics(painter.font())
        root_name = metrics.elidedText(self.root.name or "Root", Qt.TextElideMode.ElideRight, int(center_radius * 1.55))
        painter.drawText(
            QRectF(center.x() - center_radius + 6, center.y() - 19, center_radius * 2 - 12, 18),
            Qt.AlignmentFlag.AlignCenter,
            root_name,
        )
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(
            QRectF(center.x() - center_radius + 6, center.y() + 1, center_radius * 2 - 12, 18),
            Qt.AlignmentFlag.AlignCenter,
            format_size(self.root.size),
        )

        self._register_area(
            QRectF(center.x() - center_radius, center.y() - center_radius, center_radius * 2, center_radius * 2),
            f"{self.root.name}\n{format_size(self.root.size)}\n{self.root.path}",
        )

        child_limit = 24 if self.large_view else 16
        children = self._visible_children(self.root, child_limit)
        self._draw_sunburst_children(
            painter=painter,
            nodes=children,
            parent_size=self.root.size,
            center=center,
            start_angle=90.0,
            sweep_angle=-360.0,
            inner_radius=inner_radius,
            ring_width=ring_width,
            depth=0,
            max_depth=max_depth,
            top_index=0,
        )
        return y + height

    def _visible_children(self, node: ScanNode, limit: int) -> list[ScanNode]:
        children = [child for child in node.children if child.size > 0]
        children.sort(key=lambda item: item.size, reverse=True)
        return children[:limit]

    def _draw_sunburst_children(
        self,
        painter: QPainter,
        nodes: list[ScanNode],
        parent_size: int,
        center: QPointF,
        start_angle: float,
        sweep_angle: float,
        inner_radius: float,
        ring_width: float,
        depth: int,
        max_depth: int,
        top_index: int,
    ) -> None:
        if not nodes or parent_size <= 0 or depth >= max_depth:
            return

        current = start_angle
        scale_base = parent_size if parent_size > 0 else sum(node.size for node in nodes)
        metrics = QFontMetrics(QFont("Segoe UI", 8, QFont.Weight.Bold))

        for index, node in enumerate(nodes):
            ratio = node.size / scale_base if scale_base else 0
            child_sweep = sweep_angle * ratio
            if abs(child_sweep) < 0.45:
                current += child_sweep
                continue

            color_index = top_index if depth > 0 else index
            base = QColor(_GRAPH_COLORS[color_index % len(_GRAPH_COLORS)])
            color = base.lighter(100 + depth * 14)
            color.setAlpha(232)

            outer_radius = inner_radius + ring_width
            path = self._annular_sector_path(center, inner_radius, outer_radius, current, child_sweep)
            painter.setPen(QPen(QColor("#ffffff"), 1.4))
            painter.setBrush(color)
            painter.drawPath(path)

            percent = node.size / self.root.size * 100 if self.root and self.root.size else 0
            tooltip = f"{node.name}\n{format_size(node.size)} ({percent:.1f} %)\n{node.path}"
            self._register_area(path, tooltip)

            if abs(child_sweep) >= 9 and outer_radius - inner_radius >= 24:
                label_radius = inner_radius + ring_width * 0.52
                mid = current + child_sweep / 2
                point = self._polar_point(center, label_radius, mid)
                max_width = max(34, min(145 if self.large_view else 120, abs(child_sweep) / 360 * 2 * math.pi * label_radius * 0.86))
                name = metrics.elidedText(node.name, Qt.TextElideMode.ElideRight, int(max_width))
                painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                painter.setPen(QColor("#ffffff") if color.lightness() < 165 else QColor("#111827"))
                text_rect = QRectF(point.x() - max_width / 2, point.y() - 8, max_width, 16)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, name)

            child_count = 13 if self.large_view and depth < 2 else (10 if depth < 2 else 7)
            next_children = self._visible_children(node, child_count)
            if next_children and abs(child_sweep) >= 3.0:
                self._draw_sunburst_children(
                    painter=painter,
                    nodes=next_children,
                    parent_size=node.size,
                    center=center,
                    start_angle=current,
                    sweep_angle=child_sweep,
                    inner_radius=outer_radius,
                    ring_width=ring_width,
                    depth=depth + 1,
                    max_depth=max_depth,
                    top_index=color_index,
                )

            current += child_sweep

    def _annular_sector_path(self, center: QPointF, inner_radius: float, outer_radius: float, start: float, sweep: float) -> QPainterPath:
        outer = QRectF(center.x() - outer_radius, center.y() - outer_radius, outer_radius * 2, outer_radius * 2)
        inner = QRectF(center.x() - inner_radius, center.y() - inner_radius, inner_radius * 2, inner_radius * 2)
        path = QPainterPath()
        path.arcMoveTo(outer, start)
        path.arcTo(outer, start, sweep)
        path.arcTo(inner, start + sweep, -sweep)
        path.closeSubpath()
        return path

    def _polar_point(self, center: QPointF, radius: float, angle_degrees: float) -> QPointF:
        rad = math.radians(angle_degrees)
        return QPointF(center.x() + math.cos(rad) * radius, center.y() - math.sin(rad) * radius)

    def _draw_top_folder_bars(self, painter: QPainter, x: int, y: int, width: int) -> int:
        h = 278
        self._card(painter, QRectF(x, y, width, h))
        self._draw_section_header(
            painter,
            x + 16,
            y + 12,
            "Größte Ordner als Balkendiagramm",
            "Schnelle Lesart: oben steht, was im Scan am meisten Platz verbraucht.",
        )
        if not self.root:
            return y + h

        folders = top_folders(self.root, 12)
        max_size = max((node.size for node in folders), default=1)
        start_y = y + 62
        label_w = 360 if self.large_view else 290
        bar_w = max(160, width - label_w - 150)
        painter.setFont(QFont("Segoe UI", 9))
        metrics = QFontMetrics(painter.font())
        for idx, node in enumerate(folders):
            row_y = start_y + idx * 17
            name = metrics.elidedText(node.name, Qt.TextElideMode.ElideRight, label_w - 12)
            row_rect = QRectF(x + 16, row_y - 2, width - 32, 17)
            share = node.size / self.root.size * 100 if self.root.size else 0
            self._register_area(row_rect, f"{node.path}\n{format_size(node.size)} ({share:.1f} %)")
            painter.setPen(QColor("#374151"))
            painter.drawText(x + 16, row_y + 12, name)
            fill_w = int(bar_w * node.size / max_size) if max_size else 0
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#e5e7eb"))
            painter.drawRoundedRect(QRectF(x + 16 + label_w, row_y, bar_w, 12), 5, 5)
            painter.setBrush(QColor(_GRAPH_COLORS[idx % len(_GRAPH_COLORS)]))
            painter.drawRoundedRect(QRectF(x + 16 + label_w, row_y, fill_w, 12), 5, 5)
            painter.setPen(QColor("#6b7280"))
            painter.drawText(x + 16 + label_w + bar_w + 12, row_y + 12, format_size(node.size))
        return y + h


class FolderTreemapCanvas(_InteractiveCanvas):
    def __init__(self, large_view: bool = True) -> None:
        super().__init__()
        self.large_view = large_view
        self.root: ScanNode | None = None
        self._dominant_categories: dict[str, str] = {}
        self.setMinimumWidth(1320 if large_view else 980)
        self.setMinimumHeight(1180 if large_view else 920)

    def set_data(self, root: ScanNode, dominant_categories: dict[str, str] | None = None) -> None:
        self.root = root
        if dominant_categories is None:
            self._dominant_categories = self._build_dominant_category_lookup(root)
        else:
            self._dominant_categories = dict(dominant_categories)
        self.update()

    def clear_data(self) -> None:
        self.root = None
        self._dominant_categories = {}
        self._clear_interactions()
        self.update()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        pos = event.pos()
        for shape, _tooltip, action in reversed(self._interactive_areas):
            if action and self._shape_contains(shape, pos):
                if action[0] == "folder":
                    QDesktopServices.openUrl(QUrl.fromLocalFile(action[1]))
                    return
        super().mouseDoubleClickEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        self._clear_interactions()
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.fillRect(self.rect(), QColor("#ffffff"))

            if self.root is None:
                painter.setPen(QColor("#6b7280"))
                painter.setFont(QFont("Segoe UI", 11))
                painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Noch keine Treemap verfügbar.")
                return

            margin = 22
            width = max(900, self.width() - margin * 2)
            y = margin
            self._draw_title(painter, margin, y, "Größte Ordner")
            y += 40
            self._draw_info(painter, margin, y)
            y += 74
            y = self._draw_treemap_card(painter, margin, y, width, 650 if self.large_view else 500)
            y += 22
            y = self._draw_ranking_card(painter, margin, y, width)
            y += 18
            if self.minimumHeight() != int(y + 40):
                self.setMinimumHeight(int(y + 40))
        except Exception as exc:
            painter.setPen(QColor("#991b1b"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(
                self.rect().adjusted(24, 24, -24, -24),
                Qt.TextFlag.TextWordWrap,
                f"Treemap konnte nicht gezeichnet werden.\n{exc}",
            )
        finally:
            painter.end()

    def _draw_title(self, painter: QPainter, x: int, y: int, text: str) -> None:
        painter.setPen(QColor("#111827"))
        painter.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        painter.drawText(x, y + 24, text)

    def _draw_info(self, painter: QPainter, x: int, y: int) -> None:
        if not self.root:
            return
        painter.setFont(QFont("Segoe UI", 10))
        painter.setPen(QColor("#374151"))
        text = (
            "Treemap auf Basis der größten Ordner im gesamten Scan. "
            "Farben orientieren sich an der jeweils dominanten Kategorie des Ordners. "
            "Mouseover zeigt Details, Doppelklick öffnet den Ordner im Explorer."
        )
        painter.drawText(QRectF(x, y, self.width() - x * 2, 52), Qt.TextFlag.TextWordWrap, text)

    def _card(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QPen(QColor("#e5e7eb"), 1))
        painter.setBrush(QColor("#f8fafc"))
        painter.drawRoundedRect(rect, 14, 14)

    def _draw_section_header(self, painter: QPainter, x: int, y: int, text: str, hint: str | None = None) -> None:
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        painter.setPen(QColor("#111827"))
        painter.drawText(x, y + 20, text)
        if hint:
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor("#6b7280"))
            painter.drawText(x, y + 40, hint)

    def _draw_treemap_card(self, painter: QPainter, x: int, y: int, width: int, height: int) -> int:
        self._card(painter, QRectF(x, y, width, height))
        self._draw_section_header(
            painter,
            x + 16,
            y + 12,
            "Treemap der größten Ordner",
            "Es werden nur die wichtigsten Ordner dargestellt, damit die Ansicht klar und lesbar bleibt.",
        )
        if not self.root:
            return y + height

        folders = [node for node in top_folders(self.root, 32 if self.large_view else 24) if node.size > 0]
        if not folders:
            painter.setPen(QColor("#6b7280"))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(QRectF(x + 16, y + 58, width - 32, 44), Qt.TextFlag.TextWordWrap, "Keine Ordnerdaten vorhanden.")
            return y + height

        rect = QRectF(x + 16, y + 58, width - 32, height - 74)
        total = sum(node.size for node in folders) or 1
        placements = self._build_balanced_layout(folders, rect)
        self._draw_placements(painter, placements, total)
        return y + height

    def _draw_ranking_card(self, painter: QPainter, x: int, y: int, width: int) -> int:
        h = 290
        self._card(painter, QRectF(x, y, width, h))
        self._draw_section_header(
            painter,
            x + 16,
            y + 12,
            "Top 15 Ordner im Überblick",
            "Zusätzliche Lesart zur Treemap: Größe, Anteil und dominante Kategorie.",
        )
        if not self.root:
            return y + h

        folders = top_folders(self.root, 15)
        start_y = y + 60
        col_name = 360
        col_cat = 180
        col_size = 130
        painter.setFont(QFont("Segoe UI", 9))
        metrics = QFontMetrics(painter.font())
        total = self.root.size or 1
        for idx, node in enumerate(folders, start=1):
            row_y = start_y + (idx - 1) * 14
            dominant = self._dominant_categories.get(node.path, "Sonstiges")
            share = node.size / total * 100 if total else 0
            row_rect = QRectF(x + 16, row_y - 2, width - 32, 14)
            tooltip = f"{node.path}\n{format_size(node.size)} ({share:.1f} %)\nDominante Kategorie: {dominant}"
            self._register_area(row_rect, tooltip, ("folder", node.path))
            painter.setPen(QColor("#9ca3af"))
            painter.drawText(x + 16, row_y + 11, f"{idx:02d}")
            painter.setPen(QColor("#374151"))
            name = metrics.elidedText(node.name, Qt.TextElideMode.ElideRight, col_name - 30)
            painter.drawText(x + 46, row_y + 11, name)
            color = QColor(CATEGORY_COLORS.get(dominant, "#9ca3af"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x + 46 + col_name, row_y + 2, 10, 10), 3, 3)
            painter.setPen(QColor("#4b5563"))
            cat_text = metrics.elidedText(dominant, Qt.TextElideMode.ElideRight, col_cat - 18)
            painter.drawText(x + 62 + col_name, row_y + 11, cat_text)
            painter.drawText(x + 62 + col_name + col_cat, row_y + 11, format_size(node.size))
            painter.drawText(x + 62 + col_name + col_cat + col_size, row_y + 11, f"{share:.1f} %")
        return y + h

    def _build_dominant_category_lookup(self, root: ScanNode) -> dict[str, str]:
        lookup: dict[str, str] = {}

        def visit(node: ScanNode) -> defaultdict[str, int]:
            totals: defaultdict[str, int] = defaultdict(int)
            if not node.is_dir:
                category = categorize_file(node.path)
                totals[category] += int(node.size)
                lookup[node.path] = category
                return totals
            for child in node.children:
                child_totals = visit(child)
                for category, size in child_totals.items():
                    totals[category] += size
            dominant = max(totals.items(), key=lambda item: item[1])[0] if totals else "Sonstiges"
            lookup[node.path] = dominant
            return totals

        visit(root)
        return lookup

    def _build_balanced_layout(self, nodes: list[ScanNode], rect: QRectF) -> list[tuple[ScanNode, QRectF]]:
        """Build a stable, non-recursive treemap layout.

        V20 used a recursive half-splitter. On very skewed real-world scans it
        could keep splitting the same group and hit Python's recursion limit.
        This row-based layout is intentionally simple, bounded and predictable.
        """
        items = [(node, int(node.size)) for node in nodes if node.size > 0]
        if not items or rect.width() <= 6 or rect.height() <= 6:
            return []

        total_size = sum(size for _node, size in items) or 1
        placements: list[tuple[ScanNode, QRectF]] = []
        remaining_rect = QRectF(rect)
        remaining_size = total_size
        index = 0

        while index < len(items) and remaining_rect.width() > 6 and remaining_rect.height() > 6 and remaining_size > 0:
            horizontal = remaining_rect.width() >= remaining_rect.height()
            row: list[tuple[ScanNode, int]] = []
            row_size = 0

            # Greedy row: keep rows readable instead of trying to be mathematically perfect.
            # This prevents deep recursion and avoids hundreds of tiny unreadable cells.
            target = max(remaining_size * 0.18, remaining_size / max(1, min(6, len(items) - index)))
            while index < len(items):
                node, size = items[index]
                if row and row_size + size > target and len(row) >= 2:
                    break
                row.append((node, size))
                row_size += size
                index += 1
                if len(row) >= 6:
                    break

            if not row:
                break

            row_ratio = min(1.0, row_size / remaining_size) if remaining_size else 1.0
            if horizontal:
                row_height = remaining_rect.height() * row_ratio
                if index >= len(items):
                    row_height = remaining_rect.height()
                row_rect = QRectF(remaining_rect.x(), remaining_rect.y(), remaining_rect.width(), row_height)
                x = row_rect.x()
                for pos, (node, size) in enumerate(row):
                    width_ratio = size / row_size if row_size else 0
                    cell_w = row_rect.width() * width_ratio
                    if pos == len(row) - 1:
                        cell_w = row_rect.right() - x
                    placements.append((node, QRectF(x, row_rect.y(), max(0.0, cell_w), row_rect.height())))
                    x += cell_w
                remaining_rect = QRectF(
                    remaining_rect.x(),
                    remaining_rect.y() + row_height,
                    remaining_rect.width(),
                    max(0.0, remaining_rect.height() - row_height),
                )
            else:
                row_width = remaining_rect.width() * row_ratio
                if index >= len(items):
                    row_width = remaining_rect.width()
                row_rect = QRectF(remaining_rect.x(), remaining_rect.y(), row_width, remaining_rect.height())
                y = row_rect.y()
                for pos, (node, size) in enumerate(row):
                    height_ratio = size / row_size if row_size else 0
                    cell_h = row_rect.height() * height_ratio
                    if pos == len(row) - 1:
                        cell_h = row_rect.bottom() - y
                    placements.append((node, QRectF(row_rect.x(), y, row_rect.width(), max(0.0, cell_h))))
                    y += cell_h
                remaining_rect = QRectF(
                    remaining_rect.x() + row_width,
                    remaining_rect.y(),
                    max(0.0, remaining_rect.width() - row_width),
                    remaining_rect.height(),
                )
            remaining_size -= row_size

        return placements

    def _draw_placements(self, painter: QPainter, placements: list[tuple[ScanNode, QRectF]], total: int) -> None:
        metrics = QFontMetrics(QFont("Segoe UI", 9, QFont.Weight.Bold))
        for index, (node, rect) in enumerate(placements):
            if rect.width() < 6 or rect.height() < 6:
                continue
            dominant = self._dominant_categories.get(node.path, "Sonstiges")
            color = QColor(CATEGORY_COLORS.get(dominant, _GRAPH_COLORS[index % len(_GRAPH_COLORS)]))
            color_fill = QColor(color)
            color_fill.setAlpha(220)
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.setBrush(color_fill)
            painter.drawRoundedRect(rect, 6, 6)

            share = node.size / total * 100 if total else 0
            tooltip = f"{node.name}\n{format_size(node.size)} ({share:.1f} %)\nDominante Kategorie: {dominant}\n{node.path}\nDoppelklick öffnet den Ordner"
            self._register_area(QRectF(rect), tooltip, ("folder", node.path))

            if rect.width() > 90 and rect.height() > 34:
                painter.setPen(QColor("#ffffff") if color.lightness() < 170 else QColor("#111827"))
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                text_rect = rect.adjusted(8, 6, -8, -6)
                name = metrics.elidedText(node.name, Qt.TextElideMode.ElideRight, int(text_rect.width()))
                lines = [name]
                if rect.height() > 52:
                    lines.append(format_size(node.size))
                if rect.height() > 68:
                    lines.append(dominant)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, "\n".join(lines))


class GraphicsLoaderWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, root: ScanNode) -> None:
        super().__init__()
        self.root = root

    def run(self) -> None:
        try:
            lookup: dict[str, str] = {}

            def visit(node: ScanNode) -> defaultdict[str, int]:
                totals: defaultdict[str, int] = defaultdict(int)
                if not node.is_dir:
                    category = categorize_file(node.path)
                    totals[category] += int(node.size)
                    lookup[node.path] = category
                    return totals
                for child in node.children:
                    child_totals = visit(child)
                    for category, size in child_totals.items():
                        totals[category] += size
                dominant = max(totals.items(), key=lambda item: item[1])[0] if totals else "Sonstiges"
                lookup[node.path] = dominant
                return totals

            visit(self.root)
            self.finished.emit(lookup)
        except Exception as exc:  # pragma: no cover - Sicherheitsnetz fuer UI
            self.failed.emit(str(exc))


class LargeGraphicsWindow(QMainWindow):
    def __init__(self, root: ScanNode, category_totals: dict[str, int], category_callback=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.root = root
        self.category_totals = dict(category_totals)
        self.category_callback = category_callback
        self.category_canvas: CategoryOverviewCanvas | None = None
        self.treemap_canvas: FolderTreemapCanvas | None = None
        self._loader_thread: QThread | None = None
        self._loader_worker: GraphicsLoaderWorker | None = None
        self._loading_dot_count = 0

        self.setWindowTitle("waltrone1-SpaceLens - Grafische Auswertung")
        self.resize(1460, 960)
        self.setMinimumSize(1120, 760)

        self.central = QWidget()
        self.layout = QVBoxLayout(self.central)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(10)
        self.setCentralWidget(self.central)

        self.loading_container = QWidget()
        loading_layout = QHBoxLayout(self.loading_container)
        loading_layout.setContentsMargins(0, 0, 0, 0)
        loading_layout.setSpacing(12)
        self.spinner = LoadingSpinner()
        self.loading_label = QLabel("Grafik wird vorbereitet")
        self.loading_label.setObjectName("Subtitle")
        self.loading_label.setWordWrap(True)
        loading_layout.addStretch(1)
        loading_layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignVCenter)
        loading_layout.addWidget(self.loading_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        loading_layout.addStretch(1)
        self.layout.addStretch(1)
        self.layout.addWidget(self.loading_container)
        self.layout.addStretch(1)

        self._label_timer = QTimer(self)
        self._label_timer.timeout.connect(self._animate_loading_text)

        QTimer.singleShot(60, self._start_graphics_load)

    def _start_graphics_load(self) -> None:
        self.spinner.start()
        self._label_timer.start(320)

        self._loader_thread = QThread(self)
        self._loader_worker = GraphicsLoaderWorker(self.root)
        self._loader_worker.moveToThread(self._loader_thread)
        self._loader_thread.started.connect(self._loader_worker.run)
        self._loader_worker.finished.connect(self._on_graphics_ready)
        self._loader_worker.failed.connect(self._on_graphics_failed)
        self._loader_worker.finished.connect(self._loader_thread.quit)
        self._loader_worker.failed.connect(self._loader_thread.quit)
        self._loader_thread.finished.connect(self._cleanup_loader)
        self._loader_thread.start()

    def _animate_loading_text(self) -> None:
        self._loading_dot_count = (self._loading_dot_count + 1) % 4
        dots = "." * self._loading_dot_count
        self.loading_label.setText(f"Grafik wird vorbereitet{dots} bitte kurz warten")

    def _on_graphics_ready(self, dominant_categories: dict[str, str]) -> None:
        self._label_timer.stop()
        self.spinner.stop()
        self._clear_layout()
        self._build_graphics_ui(dominant_categories)

    def _on_graphics_failed(self, error_message: str) -> None:
        self._label_timer.stop()
        self.spinner.stop()
        self.loading_label.setText(f"Grafik konnte nicht vorbereitet werden: {error_message}")

    def _cleanup_loader(self) -> None:
        if self._loader_worker is not None:
            self._loader_worker.deleteLater()
        self._loader_worker = None
        self._loader_thread = None

    def _clear_layout(self) -> None:
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _build_graphics_ui(self, dominant_categories: dict[str, str]) -> None:
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(10)

        intro = QLabel(
            "Klare Übersicht ohne Überladung: links die Kategorien & Struktur, rechts die größten Ordner als Treemap. "
            "Kategorien lassen sich anklicken; in der Treemap öffnet ein Doppelklick den Ordner im Explorer."
        )
        intro.setWordWrap(True)
        intro.setObjectName("Subtitle")
        self.layout.addWidget(intro)

        tabs = QTabWidget()

        self.category_canvas = CategoryOverviewCanvas(large_view=True)
        self.category_canvas.set_data(self.root, self.category_totals)
        if self.category_callback is not None:
            self.category_canvas.category_clicked.connect(self.category_callback)
        category_scroll = QScrollArea()
        category_scroll.setWidgetResizable(True)
        category_scroll.setWidget(self.category_canvas)
        tabs.addTab(category_scroll, "Kategorien & Struktur")

        self.treemap_canvas = FolderTreemapCanvas(large_view=True)
        self.treemap_canvas.set_data(self.root, dominant_categories)
        treemap_scroll = QScrollArea()
        treemap_scroll.setWidgetResizable(True)
        treemap_scroll.setWidget(self.treemap_canvas)
        tabs.addTab(treemap_scroll, "Größte Ordner")

        self.layout.addWidget(tabs, 1)


class GraphicsPanel(QWidget):
    """Legacy placeholder kept for compatibility with older imports.

    The application now opens the dedicated LargeGraphicsWindow directly.
    """

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel("Die Grafik wird jetzt über den Button 'Grafik öffnen' in einer großen Ansicht geöffnet.")
        label.setObjectName("Subtitle")
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addStretch(1)
