@echo off
REM Cindergrace Launcher starten (Windows)
cd /d "%~dp0"

REM Prüfe ob virtual environment existiert, sonst erstellen
if not exist .venv\Scripts\activate.bat (
    echo Erstelle virtuelle Umgebung...
    python -m venv .venv
)

REM Aktiviere venv
call .venv\Scripts\activate.bat

REM Installiere/Aktualisiere Abhaengigkeiten
pip install --upgrade -e . --quiet 2>nul

REM Starte Launcher
set PYTHONPATH=%~dp0src
python -m cindergrace_launcher %*
