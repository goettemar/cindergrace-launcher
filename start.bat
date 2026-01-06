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

REM Prüfe ob PySide6 installiert ist
python -c "import PySide6" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Installiere Abhaengigkeiten...
    pip install -e . --quiet
)

REM Starte Launcher
set PYTHONPATH=%~dp0src
python -m cindergrace_launcher %*
