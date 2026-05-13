@echo off
setlocal
cd /d "%~dp0"

set "PY2EXE_DIR=%CD%"
for %%I in ("%PY2EXE_DIR%\..") do set "PROJECT_DIR=%%~fI"
set "APP_NAME=waltrone1-SpaceLens"
set "ICON_FILE=%PROJECT_DIR%\waltrone1-SpaceLens.ico"
set "VERSION_FILE=%PROJECT_DIR%\version_info.txt"
set "ENTRY_FILE=%PROJECT_DIR%\run.py"
set "SPEC_FILE=%PY2EXE_DIR%\waltrone1-SpaceLens.spec"
set "DIST_DIR=%PY2EXE_DIR%\dist"
set "WORK_DIR=%PY2EXE_DIR%\build"

cls
echo ==================================================
echo  %APP_NAME% - Single EXE Build ^(optimiert^)
echo ==================================================
echo.
echo py2exe-Ordner:  %PY2EXE_DIR%
echo Projekt-Ordner: %PROJECT_DIR%
echo Startdatei:     %ENTRY_FILE%
echo Icon-Datei:     %ICON_FILE%
echo Version-Datei:  %VERSION_FILE%
echo Ausgabe-Ordner: %DIST_DIR%
echo.

if not exist "%ENTRY_FILE%" (
    echo FEHLER: Startdatei wurde nicht gefunden:
    echo %ENTRY_FILE%
    echo.
    echo Der Ordner py2exe muss direkt im Projektordner liegen.
    pause
    exit /b 1
)

if not exist "%ICON_FILE%" (
    echo FEHLER: Icon wurde nicht gefunden:
    echo %ICON_FILE%
    echo.
    echo Bitte lege dein Icon im Hauptordner ab:
    echo %PROJECT_DIR%\waltrone1-SpaceLens.ico
    pause
    exit /b 1
)

if not exist "%VERSION_FILE%" (
    echo FEHLER: version_info.txt wurde nicht gefunden:
    echo %VERSION_FILE%
    echo.
    echo Diese Datei wird fuer die Windows-Dateieigenschaften benoetigt.
    pause
    exit /b 1
)

where py >nul 2>nul
if %errorlevel% neq 0 (
    echo FEHLER: Python Launcher ^(py^) wurde nicht gefunden.
    echo Bitte Python von python.org installieren und "Add python.exe to PATH" aktivieren.
    pause
    exit /b 1
)

echo [1/6] Virtuelle Python-Umgebung im py2exe-Ordner anlegen / pruefen...
if not exist "%PY2EXE_DIR%\.venv\Scripts\python.exe" (
    py -3 -m venv "%PY2EXE_DIR%\.venv"
)
if not exist "%PY2EXE_DIR%\.venv\Scripts\python.exe" (
    echo FEHLER: Virtuelle Umgebung konnte nicht angelegt werden.
    pause
    exit /b 1
)

echo [2/6] Virtuelle Umgebung aktivieren...
call "%PY2EXE_DIR%\.venv\Scripts\activate.bat"
if errorlevel 1 goto :fail

echo [3/6] Build-Pakete und Projekt-Abhaengigkeiten installieren / aktualisieren...
echo Python-Version in Build-Umgebung:
python --version
python -m pip install -U pip setuptools wheel
if errorlevel 1 goto :fail
pip install -r "%PY2EXE_DIR%\requirements.txt"
if errorlevel 1 goto :fail
pip install -r "%PROJECT_DIR%\requirements.txt"
if errorlevel 1 goto :fail
echo Verwendete PyInstaller-Version:
pyinstaller --version
if errorlevel 1 goto :fail

echo [4/6] Alte Build-Ausgaben im py2exe-Ordner loeschen...
rmdir /s /q "%WORK_DIR%" 2>nul
rmdir /s /q "%DIST_DIR%" 2>nul

echo [5/6] Single EXE ohne _internal Ordner bauen...
pyinstaller --clean --noconfirm --distpath "%DIST_DIR%" --workpath "%WORK_DIR%" "%SPEC_FILE%"
if errorlevel 1 goto :fail

echo [6/6] Ergebnis pruefen...
if exist "%DIST_DIR%\%APP_NAME%.exe" (
    echo.
    echo FERTIG:
    echo %DIST_DIR%\%APP_NAME%.exe
    echo.
    echo Es wurde eine optimierte Single-EXE erstellt. Es gibt keinen _internal Ordner.
    echo Version: v1.0.0.0
    pause
    exit /b 0
)

echo FEHLER: Build wurde beendet, aber die EXE wurde nicht gefunden.
echo Erwartet wurde:
echo %DIST_DIR%\%APP_NAME%.exe
pause
exit /b 1

:fail
echo.
echo FEHLER: Build fehlgeschlagen. Bitte die Meldungen oberhalb pruefen.
pause
exit /b 1
