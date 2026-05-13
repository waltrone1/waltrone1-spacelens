from __future__ import annotations

import os
from collections import defaultdict, deque
from threading import Event
from PySide6.QtCore import QObject, Signal, Slot

from .categorizer import CATEGORY_ORDER, categorize_file
from .models import ScanError, ScanNode


class ScanWorker(QObject):
    # Wichtig: object statt int, weil PySide6/Shiboken sonst bei großen Byte-Werten
    # (> 2.147.483.647) in einen 32-bit-int überläuft.
    progress = Signal(str, object, object, object)  # current path, files, bytes, errors
    finished = Signal(object, object, object)  # ScanNode, category totals, errors
    failed = Signal(str)

    def __init__(self, root_path: str) -> None:
        super().__init__()
        self.root_path = os.path.abspath(root_path) if not root_path.startswith("\\\\") else root_path
        self._cancel_event = Event()
        self._files_seen = 0
        self._bytes_seen = 0
        self._errors: list[ScanError] = []
        self._category_totals: dict[str, int] = defaultdict(int)

    @Slot()
    def run(self) -> None:
        try:
            if not os.path.exists(self.root_path):
                self.failed.emit(f"Pfad nicht gefunden: {self.root_path}")
                return
            if not os.path.isdir(self.root_path):
                self.failed.emit(f"Der angegebene Pfad ist kein Ordner: {self.root_path}")
                return

            node = self._scan_iterative(self.root_path)
            for category in CATEGORY_ORDER:
                self._category_totals.setdefault(category, 0)
            self.finished.emit(node, dict(self._category_totals), list(self._errors))
        except Exception as exc:  # defensive fallback for unexpected issues
            self.failed.emit(str(exc))

    def cancel(self) -> None:
        self._cancel_event.set()

    def _emit_progress(self, current_path: str) -> None:
        self.progress.emit(
            current_path,
            int(self._files_seen),
            int(self._bytes_seen),
            int(len(self._errors)),
        )

    def _remember_error(self, path: str, exc: BaseException) -> None:
        self._errors.append(ScanError(path=path, message=str(exc)))

    def _scan_iterative(self, root_path: str) -> ScanNode:
        """
        Iterativer Scan statt rekursiver Implementierung.
        Vermeidet RecursionError bei sehr tiefen Ordnerbäumen (z.B. node_modules).
        """
        root_name = os.path.basename(os.path.normpath(root_path)) or root_path
        root_node = ScanNode(name=root_name, path=root_path, is_dir=True)

        # Stack-Einträge: (pfad, ScanNode) – noch zu verarbeitende Verzeichnisse
        stack: deque[tuple[str, ScanNode]] = deque()
        stack.append((root_path, root_node))

        # Für Bottom-up-Größenberechnung: Reihenfolge der verarbeiteten Knoten merken
        processed: list[tuple[ScanNode, ScanNode | None]] = []  # (node, parent)
        parent_map: dict[str, ScanNode] = {root_path: root_node}

        while stack and not self._cancel_event.is_set():
            path, node = stack.pop()

            try:
                with os.scandir(path) as entries:
                    for entry in entries:
                        if self._cancel_event.is_set():
                            break
                        try:
                            if entry.is_symlink():
                                continue
                            if entry.is_dir(follow_symlinks=False):
                                child_node = ScanNode(name=entry.name, path=entry.path, is_dir=True)
                                node.children.append(child_node)
                                node.folder_count += 1
                                stack.append((entry.path, child_node))
                                parent_map[entry.path] = node
                            elif entry.is_file(follow_symlinks=False):
                                try:
                                    size = entry.stat(follow_symlinks=False).st_size
                                except OSError as exc:
                                    self._remember_error(entry.path, exc)
                                    size = 0
                                file_node = ScanNode(
                                    name=entry.name,
                                    path=entry.path,
                                    is_dir=False,
                                    size=size,
                                    file_count=1,
                                )
                                node.children.append(file_node)
                                node.size += size
                                node.file_count += 1
                                self._files_seen += 1
                                self._bytes_seen += size
                                self._category_totals[categorize_file(entry.path)] += size
                                if self._files_seen % 250 == 0:
                                    self._emit_progress(entry.path)
                        except PermissionError as exc:
                            self._remember_error(entry.path, exc)
                        except OSError as exc:
                            self._remember_error(entry.path, exc)
            except PermissionError as exc:
                self._remember_error(path, exc)
            except OSError as exc:
                self._remember_error(path, exc)

            processed.append((node, parent_map.get(path)))
            self._emit_progress(path)

        # Bottom-up: Größen der Unterordner nach oben addieren
        # processed ist in Reihenfolge des DFS – wir gehen rückwärts (Blätter zuerst)
        for node, parent in reversed(processed):
            if parent is not None and node.is_dir:
                parent.size += node.size
                parent.file_count += node.file_count
                # folder_count wurde bereits beim Einfügen inkrementiert (direkte Kinder),
                # aber die Enkel müssen noch addiert werden
                parent.folder_count += node.folder_count

        # Kinder nach Größe sortieren (nur eine Ebene – Blätter sind bereits Blätter)
        def _sort(n: ScanNode) -> None:
            if n.children:
                n.children.sort(key=lambda c: c.size, reverse=True)
                for child in n.children:
                    if child.is_dir:
                        _sort(child)

        _sort(root_node)
        return root_node
