LIGHT_THEME = """
QMainWindow, QWidget {
    background: #f6f8fb;
    color: #1f2937;
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 10pt;
}
QFrame#Card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
}
QLabel#Title {
    font-size: 22pt;
    font-weight: 700;
    color: #111827;
}
QLabel#Subtitle {
    color: #6b7280;
    font-size: 10pt;
}
QLabel#MetricValue {
    font-size: 18pt;
    font-weight: 700;
    color: #111827;
}
QLabel#MetricLabel {
    color: #6b7280;
    font-size: 9pt;
}
QLineEdit {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    padding: 9px 12px;
    selection-background-color: #2563eb;
}
QLineEdit:focus {
    border: 1px solid #2563eb;
}
QPushButton {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    padding: 9px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: #f3f4f6;
}
QPushButton#PrimaryButton {
    background: #2563eb;
    color: white;
    border: 1px solid #2563eb;
}
QPushButton#PrimaryButton:hover {
    background: #1d4ed8;
}

QPushButton#DriveButton {
    background: #eff6ff;
    color: #1d4ed8;
    border: 1px solid #bfdbfe;
    padding: 9px 10px;
    min-width: 46px;
}
QPushButton#DriveButton:hover {
    background: #dbeafe;
}
QPushButton#ReadyGraphicButton {
    background: #16a34a;
    color: white;
    border: 1px solid #15803d;
    font-weight: 800;
}
QPushButton#ReadyGraphicButton:hover {
    background: #15803d;
}
QPushButton#DormantGraphicButton {
    background: #f3f4f6;
    color: #9ca3af;
    border: 1px solid #d1d5db;
}
QPushButton#DormantGraphicButton:disabled {
    background: #f3f4f6;
    color: #9ca3af;
    border: 1px dashed #d1d5db;
}
QPushButton#DangerButton {
    background: #fee2e2;
    color: #991b1b;
    border: 1px solid #fecaca;
}
QPushButton:disabled {
    color: #9ca3af;
    background: #f3f4f6;
}
QTreeWidget, QTableWidget, QTextEdit {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    alternate-background-color: #f9fafb;
    gridline-color: #edf0f5;
}
QHeaderView::section {
    background: #eef2f7;
    color: #111827;
    border: none;
    border-right: 1px solid #d7dde8;
    border-bottom: 2px solid #cfd7e6;
    padding: 9px 10px;
    font-weight: 800;
}
QHeaderView::section:hover {
    background: #e0e7f2;
}
QHeaderView::section:pressed {
    background: #d8e2ef;
}
QProgressBar {
    background: #e5e7eb;
    border: none;
    border-radius: 8px;
    height: 12px;
    text-align: center;
}
QProgressBar::chunk {
    background: #2563eb;
    border-radius: 8px;
}
QTabWidget::pane {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    background: #ffffff;
}
QTabBar::tab {
    background: #f3f4f6;
    color: #374151;
    border: 1px solid #e5e7eb;
    border-bottom: none;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    padding: 9px 16px;
    margin-right: 4px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #111827;
}
QDoubleSpinBox {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    padding: 7px 10px;
}

QFrame#Footer {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
}
QLabel#FooterText {
    color: #2563eb;
    font-size: 9pt;
}
QPushButton#FooterLinkButton {
    background: transparent;
    border: none;
    color: #2563eb;
    padding: 4px 6px;
    font-weight: 500;
}
QPushButton#FooterLinkButton:hover {
    background: #eff6ff;
    border-radius: 8px;
}
"""

# Fehler-Badge wird dynamisch zur Statuszeile hinzugefügt
_ERROR_BADGE_STYLE = """
QPushButton#ErrorBadge {
    background: #fef3c7;
    color: #92400e;
    border: 1px solid #fbbf24;
    border-radius: 10px;
    padding: 4px 10px;
    font-weight: 700;
}
QPushButton#ErrorBadge:hover {
    background: #fde68a;
}
"""

LIGHT_THEME = LIGHT_THEME + _ERROR_BADGE_STYLE
