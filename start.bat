@echo off
REM Cindergrace Launcher starten (Windows)
REM Falls als Entwickler: python -m cindergrace_launcher
REM Falls installiert: cindergrace-launcher

cd /d "%~dp0"

REM Prüfe ob virtual environment existiert
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

REM Versuche als installiertes Package zu starten
where cindergrace-launcher >nul 2>nul
if %ERRORLEVEL% equ 0 (
    cindergrace-launcher %*
) else (
    REM Fallback: Als Modul aus src starten
    set PYTHONPATH=%~dp0src
    python -m cindergrace_launcher %*
)
