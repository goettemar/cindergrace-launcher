#!/bin/bash
# Cindergrace Launcher starten (Linux/macOS)
# Falls als Entwickler: python -m cindergrace_launcher
# Falls installiert: cindergrace-launcher

cd "$(dirname "$0")"

# Prüfe ob virtual environment existiert
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

# Versuche als installiertes Package zu starten
if command -v cindergrace-launcher &> /dev/null; then
    cindergrace-launcher "$@"
else
    # Fallback: Als Modul aus src starten
    export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
    python3 -m cindergrace_launcher "$@"
fi
