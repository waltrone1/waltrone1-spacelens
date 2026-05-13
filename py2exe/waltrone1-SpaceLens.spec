# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

# Dieses Spec-File liegt im Ordner .\py2exe.
# Die eigentliche Anwendung liegt eine Ebene darueber.
PY2EXE_DIR = Path(SPECPATH).resolve()
PROJECT_DIR = PY2EXE_DIR.parent
ENTRY_FILE = PROJECT_DIR / "run.py"
ICON_FILE = PROJECT_DIR / "waltrone1-SpaceLens.ico"
VERSION_FILE = PROJECT_DIR / "version_info.txt"
APP_NAME = "waltrone1-SpaceLens"

hiddenimports = []
datas = [
    (str(PROJECT_DIR / "waltrone1_spacelens" / "data" / "categories.json"), "waltrone1_spacelens/data"),
]

# WICHTIG fuer kleinere EXE:
# Nicht collect_submodules("PySide6") und nicht collect_data_files("PySide6") verwenden.
# Die normalen PyInstaller-Hooks sammeln die wirklich benoetigten Qt-Dateien ein.
# Das vorherige pauschale Einsammeln von PySide6 kann den Build deutlich aufblaehen.
excludes = [
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtBluetooth",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtDesigner",
    "PySide6.QtGraphs",
    "PySide6.QtHelp",
    "PySide6.QtLocation",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetworkAuth",
    "PySide6.QtNfc",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtPrintSupport",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialBus",
    "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio",
    "PySide6.QtSql",
    "PySide6.QtStateMachine",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtTest",
    "PySide6.QtTextToSpeech",
    "PySide6.QtUiTools",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    "PySide6.QtXml",
    "matplotlib",
    "numpy",
    "pandas",
    "PIL",
    "tkinter",
    "unittest",
]

if not ENTRY_FILE.exists():
    raise SystemExit(f"Startdatei nicht gefunden: {ENTRY_FILE}")
if not ICON_FILE.exists():
    raise SystemExit(f"Icon nicht gefunden: {ICON_FILE}")
if not VERSION_FILE.exists():
    raise SystemExit(f"version_info.txt nicht gefunden: {VERSION_FILE}")


a = Analysis(
    [str(ENTRY_FILE)],
    pathex=[str(PROJECT_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_FILE),
    version=str(VERSION_FILE),
)
