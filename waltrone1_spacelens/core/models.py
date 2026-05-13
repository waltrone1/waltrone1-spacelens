from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScanError:
    path: str
    message: str


@dataclass
class ScanNode:
    name: str
    path: str
    is_dir: bool
    size: int = 0
    file_count: int = 0
    folder_count: int = 0
    children: list["ScanNode"] = field(default_factory=list)

    def sort_children_by_size(self) -> None:
        self.children.sort(key=lambda item: item.size, reverse=True)
        for child in self.children:
            child.sort_children_by_size()
