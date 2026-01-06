#!/bin/bash
# Cindergrace Launcher starten (Linux/macOS)
cd "$(dirname "$0")"

# Prüfe ob virtual environment existiert, sonst erstellen
if [ ! -f .venv/bin/activate ]; then
    echo "Erstelle virtuelle Umgebung..."
    python3 -m venv .venv
fi

# Aktiviere venv
source .venv/bin/activate

# Prüfe ob PySide6 installiert ist
if ! python3 -c "import PySide6" 2>/dev/null; then
    echo "Installiere Abhängigkeiten..."
    pip install -e . --quiet
fi

# Starte Launcher
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
python3 -m cindergrace_launcher "$@"
