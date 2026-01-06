#!/usr/bin/env python3
"""
Cindergrace Launcher - Haupteinstiegspunkt
Verwaltet LLM CLI Sessions (Claude, Codex, Gemini) für verschiedene Projekte
"""

import sys
import os


def main():
    """Hauptfunktion - startet die GTK-Anwendung"""
    # Füge cindergrace_common hinzu falls als Nachbar-Ordner vorhanden
    script_dir = os.path.dirname(os.path.abspath(__file__))
    common_src = os.path.join(script_dir, "..", "..", "..", "cindergrace_common", "src")
    if os.path.isdir(common_src):
        sys.path.insert(0, os.path.abspath(common_src))

    from .cockpit import main as cockpit_main
    cockpit_main()


if __name__ == "__main__":
    main()
