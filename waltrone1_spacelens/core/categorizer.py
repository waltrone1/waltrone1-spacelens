from __future__ import annotations

import json
from pathlib import Path

# Kategorien werden aus categories.json geladen – diese Datei ist die einzige Quelle.
# Aenderungen dort wirken sich direkt auf die Kategorisierung aus.

_DATA_FILE = Path(__file__).parent.parent / "data" / "categories.json"

def _load_categories() -> dict[str, set[str]]:
    try:
        raw: dict[str, list[str]] = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        return {category: set(exts) for category, exts in raw.items()}
    except Exception:
        return {}

CATEGORY_EXTENSIONS: dict[str, set[str]] = _load_categories()

CATEGORY_ORDER = [
    "Bilder",
    "Videos",
    "Musik",
    "Dokumente",
    "Office/PDF",
    "Archive",
    "Backups",
    "Programme",
    "Installer/Updates",
    "Spiele",
    "Temp/Logs",
    "VM/Images",
    "Datenbanken",
    "Outlook/Mail",
    "CAD/Design",
    "Entwicklung",
    "System/Windows",
    "Sonstiges",
]

_PATH_CATEGORY_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Entwicklung", ("node_modules", ".git", ".svn", ".hg", ".venv", "venv", "__pycache__", "target", "vendor")),
    ("Temp/Logs", ("cache", "caches", "temp", "tmp", "logs", "thumbnails", "preview")),
    ("Spiele", (
        "steamapps", "epic games", "epicgames", "gog galaxy", "gog.com", "ubisoft",
        "ubisoft game launcher", "battle.net", "ea games", "origin games", "xboxgames",
        "xbox games", "riot games", "rockstar games", "minecraft", "games"
    )),
    ("System/Windows", ("windows", "winsxs", "programdata", "$recycle.bin", "system volume information")),
)


def _path_parts_lower(path: str) -> set[str]:
    return {part.lower() for part in Path(path).parts if part}


def categorize_file(path: str) -> str:
    parts = _path_parts_lower(path)
    for category, hints in _PATH_CATEGORY_HINTS:
        if any(hint in parts for hint in hints):
            return category

    ext = Path(path).suffix.lower()
    for category, extensions in CATEGORY_EXTENSIONS.items():
        if ext in extensions:
            return category
    return "Sonstiges"
