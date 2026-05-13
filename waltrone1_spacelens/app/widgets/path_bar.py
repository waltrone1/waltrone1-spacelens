from __future__ import annotations

import ctypes
import os
import shutil

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QPushButton, QWidget

from ...core.size_format import format_size


class DriveUsageButton(QPushButton):
    """Kompakter Laufwerksbutton mit belegtem Speicher als horizontaler Füllstand."""

    def __init__(self, drive: str) -> None:
        super().__init__(drive)
        self.drive = drive
        self.setObjectName("DriveButton")
        self.setMinimumWidth(52)
        self.update_drive_usage()

    def update_drive_usage(self) -> None:
        try:
            usage = shutil.disk_usage(self.drive)
            total = int(usage.total)
            used = int(usage.used)
            free = int(usage.free)
            used_percent = max(0.0, min(100.0, (used / total * 100.0) if total else 0.0))
        except Exception:
            total = used = free = 0
            used_percent = 0.0

        stop = max(0.0, min(1.0, used_percent / 100.0))
        stop2 = min(1.0, stop + 0.001)
        if used_percent >= 90:
            fill_color = "#fecaca"
            border_color = "#f87171"
            text_color = "#7f1d1d"
        elif used_percent >= 75:
            fill_color = "#fed7aa"
            border_color = "#fb923c"
            text_color = "#7c2d12"
        else:
            fill_color = "#bfdbfe"
            border_color = "#93c5fd"
            text_color = "#1d4ed8"

        self.setStyleSheet(
            "QPushButton#DriveButton {"
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 {fill_color}, stop:{stop:.3f} {fill_color}, "
            f"stop:{stop2:.3f} #eff6ff, stop:1 #eff6ff);"
            f"color: {text_color};"
            f"border: 1px solid {border_color};"
            "border-radius: 10px;"
            "padding: 9px 10px;"
            "font-weight: 700;"
            "min-width: 46px;"
            "}"
            "QPushButton#DriveButton:hover { border: 1px solid #2563eb; }"
            "QPushButton#DriveButton:disabled { color: #9ca3af; background: #f3f4f6; border: 1px solid #d1d5db; }"
        )

        if total > 0:
            self.setToolTip(
                f"{self.drive} sofort scannen\n"
                f"Belegt: {format_size(used)} von {format_size(total)} ({used_percent:.1f} %)\n"
                f"Frei: {format_size(free)}"
            )
        else:
            self.setToolTip(f"{self.drive} sofort scannen\nSpeicherbelegung konnte nicht ermittelt werden.")


class PathBar(QWidget):
    scan_requested = Signal(str)
    cancel_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._drive_buttons: list[DriveUsageButton] = []

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText(r"Pfad eingeben, z. B. C:\Daten oder \\server\freigabe")
        self.path_input.returnPressed.connect(self._scan)

        self.browse_button = QPushButton("Durchsuchen")
        self.browse_button.clicked.connect(self._browse)

        self.scan_button = QPushButton("Scan starten")
        self.scan_button.setObjectName("PrimaryButton")
        self.scan_button.clicked.connect(self._scan)

        self.cancel_button = QPushButton("Abbrechen")
        self.cancel_button.setObjectName("DangerButton")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_requested.emit)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        for drive in self._discover_drives():
            button = DriveUsageButton(drive)
            button.clicked.connect(lambda checked=False, p=drive: self._scan_drive(p))
            self._drive_buttons.append(button)
            layout.addWidget(button)

        layout.addWidget(self.path_input, 1)
        layout.addWidget(self.browse_button)
        layout.addWidget(self.scan_button)
        layout.addWidget(self.cancel_button)

    def set_scanning(self, scanning: bool) -> None:
        self.scan_button.setEnabled(not scanning)
        self.browse_button.setEnabled(not scanning)
        self.cancel_button.setEnabled(scanning)
        for button in self._drive_buttons:
            if not scanning:
                button.update_drive_usage()
            button.setEnabled(not scanning)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Ordner auswählen")
        if path:
            self.path_input.setText(path)

    def _scan(self) -> None:
        path = self.path_input.text().strip()
        if path:
            self.scan_requested.emit(path)

    def _scan_drive(self, path: str) -> None:
        self.path_input.setText(path)
        self.scan_requested.emit(path)

    @staticmethod
    def _discover_drives() -> list[str]:
        """Ermittelt unter Windows alle aktuell verfügbaren Laufwerke, z. B. C:\\ oder R:\\."""
        drives: list[str] = []

        if os.name == "nt":
            try:
                bitmask = ctypes.windll.kernel32.GetLogicalDrives()
                for index in range(26):
                    if bitmask & (1 << index):
                        drive = f"{chr(65 + index)}:\\"
                        if os.path.exists(drive):
                            drives.append(drive)
            except Exception:
                # Fallback, falls die Windows-API unerwartet nicht erreichbar ist.
                for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                    drive = f"{letter}:\\"
                    if os.path.exists(drive):
                        drives.append(drive)
        else:
            # Entwicklungs-/Testumgebung außerhalb von Windows.
            drives.append("/")

        return drives
