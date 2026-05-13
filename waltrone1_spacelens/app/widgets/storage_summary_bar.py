from __future__ import annotations

from PySide6.QtCore import Qt, QRect, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QCursor
from PySide6.QtWidgets import QToolTip, QWidget

from ...core.categorizer import CATEGORY_ORDER
from ...core.size_format import format_size

CATEGORY_COLORS = {
    "Bilder": "#38bdf8",
    "Videos": "#a78bfa",
    "Musik": "#f472b6",
    "Dokumente": "#34d399",
    "Office/PDF": "#10b981",
    "Archive": "#f59e0b",
    "Backups": "#d97706",
    "Programme": "#60a5fa",
    "Installer/Updates": "#2563eb",
    "Spiele": "#84cc16",
    "Temp/Logs": "#fb7185",
    "VM/Images": "#8b5cf6",
    "Datenbanken": "#6366f1",
    "Outlook/Mail": "#0ea5e9",
    "CAD/Design": "#ec4899",
    "Entwicklung": "#22c55e",
    "System/Windows": "#64748b",
    "Sonstiges": "#9ca3af",
}


class StorageSummaryBar(QWidget):
    category_clicked = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(154)
        self.setMouseTracking(True)
        self.totals: dict[str, int] = {category: 0 for category in CATEGORY_ORDER}
        self._segments: list[tuple[str, QRect, int, float]] = []
        self._legend_items: list[tuple[str, QRect, int, float]] = []
        self._hover_category: str | None = None

    def set_totals(self, totals: dict[str, int]) -> None:
        self.totals = {category: int(totals.get(category, 0)) for category in CATEGORY_ORDER}
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt naming
        category_info = self._hit_test(event.pos())
        if not category_info:
            QToolTip.hideText()
            self._hover_category = None
            self.unsetCursor()
            return
        category, value, percent = category_info
        if self._hover_category != category:
            self._hover_category = category
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        QToolTip.showText(
            event.globalPos(),
            f"{category}\n{format_size(value)} ({percent:.1f} %)",
            self,
        )

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt naming
        QToolTip.hideText()
        self._hover_category = None
        self.unsetCursor()
        super().leaveEvent(event)


    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        category_info = self._hit_test(event.pos())
        if not category_info:
            super().mousePressEvent(event)
            return
        category, value, _percent = category_info
        if value > 0:
            self.category_clicked.emit(category)

    def _hit_test(self, pos):
        for category, rect, value, percent in self._segments + self._legend_items:
            if rect.contains(pos):
                return category, value, percent
        return None

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(4, 10, -4, -96)
        total = sum(self.totals.values())
        self._segments = []
        self._legend_items = []

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#e5e7eb"))
        painter.drawRoundedRect(rect, 10, 10)

        if total > 0:
            x = rect.x()
            remaining_width = rect.width()
            visible_categories = [c for c in CATEGORY_ORDER if self.totals.get(c, 0) > 0]
            for index, category in enumerate(visible_categories):
                value = self.totals.get(category, 0)
                if index == len(visible_categories) - 1:
                    width = remaining_width
                else:
                    width = max(3, int(rect.width() * (value / total)))
                    width = min(width, remaining_width)
                segment_rect = QRect(x, rect.y(), width, rect.height())
                percent = value / total * 100
                self._segments.append((category, segment_rect, value, percent))
                painter.setBrush(QColor(CATEGORY_COLORS.get(category, "#9ca3af")))
                painter.drawRoundedRect(segment_rect, 10, 10)
                x += width
                remaining_width -= width
                if remaining_width <= 0:
                    break

        painter.setPen(QPen(QColor("#374151")))
        painter.drawText(4, self.height() - 68, f"Kategorien gesamt: {format_size(total)}")

        legend_start_x = 205
        legend_x = legend_start_x
        legend_y = self.height() - 79
        max_x = self.width() - 20
        for category in CATEGORY_ORDER:
            value = self.totals.get(category, 0)
            if value <= 0:
                continue
            percent = value / total * 100 if total else 0
            text_width = painter.fontMetrics().horizontalAdvance(category)
            item_width = 14 + text_width + 18
            if legend_x + item_width > max_x and legend_x > legend_start_x:
                legend_x = legend_start_x
                legend_y += 24
            item_rect = QRect(legend_x, legend_y - 2, item_width, 18)
            self._legend_items.append((category, item_rect, value, percent))

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(CATEGORY_COLORS.get(category, "#9ca3af")))
            painter.drawRoundedRect(legend_x, legend_y + 3, 10, 10, 3, 3)
            painter.setPen(QPen(QColor("#4b5563")))
            painter.drawText(legend_x + 14, legend_y + 14, category)
            legend_x += item_width
