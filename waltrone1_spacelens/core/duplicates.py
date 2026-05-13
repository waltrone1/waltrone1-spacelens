from __future__ import annotations

import hashlib
from collections import defaultdict
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from .models import ScanNode


def _iter_files(root: ScanNode):
    """Alle Datei-Knoten im Baum iterieren."""
    stack = [root]
    while stack:
        node = stack.pop()
        if not node.is_dir:
            yield node
        else:
            stack.extend(node.children)


def _hash_file(path: str, block_size: int = 65536) -> str | None:
    """SHA-256-Hash einer Datei berechnen. Gibt None bei Fehler zurück."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(block_size):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


class DuplicateGroup:
    """Eine Gruppe von Dateien mit identischem Inhalt."""
    def __init__(self, file_hash: str, size: int, paths: list[str]) -> None:
        self.file_hash = file_hash
        self.size = size          # Größe einer Datei in der Gruppe
        self.paths = paths        # Alle Pfade mit diesem Hash
        self.wasted = size * (len(paths) - 1)  # Verschwendeter Speicher


class DuplicateScanWorker(QObject):
    """
    Sucht im bereits gescannten ScanNode-Baum nach Duplikaten.
    Schritt 1: Gruppierung nach Dateigröße (kostenlos)
    Schritt 2: SHA-256-Hash nur für Größen-Kandidaten
    """
    progress = Signal(int, int)   # (geprüfte Dateien, Gesamt-Kandidaten)
    finished = Signal(list)       # list[DuplicateGroup]
    failed = Signal(str)

    def __init__(self, root: ScanNode) -> None:
        super().__init__()
        self.root = root
        self._cancel_event = Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        try:
            # Schritt 1: Alle Dateien nach Größe gruppieren
            by_size: dict[int, list[str]] = defaultdict(list)
            for node in _iter_files(self.root):
                if node.size > 0:
                    by_size[node.size].append(node.path)

            # Nur Größen mit mehr als einer Datei sind Kandidaten
            candidates: list[tuple[int, list[str]]] = [
                (size, paths)
                for size, paths in by_size.items()
                if len(paths) > 1
            ]
            total = sum(len(paths) for _, paths in candidates)

            # Schritt 2: Hash-Vergleich
            checked = 0
            hash_groups: dict[str, list[str]] = defaultdict(list)
            size_map: dict[str, int] = {}

            for size, paths in candidates:
                for path in paths:
                    if self._cancel_event.is_set():
                        self.finished.emit([])
                        return
                    file_hash = _hash_file(path)
                    if file_hash is not None:
                        hash_groups[file_hash].append(path)
                        size_map[file_hash] = size
                    checked += 1
                    if checked % 20 == 0:
                        self.progress.emit(checked, total)

            self.progress.emit(checked, total)

            # Nur Gruppen mit echten Duplikaten (>1 Datei gleicher Hash)
            groups = [
                DuplicateGroup(h, size_map[h], paths)
                for h, paths in hash_groups.items()
                if len(paths) > 1
            ]
            # Sortierung: meisten verschwendeten Speicher zuerst
            groups.sort(key=lambda g: g.wasted, reverse=True)
            self.finished.emit(groups)

        except Exception as exc:
            self.failed.emit(str(exc))
