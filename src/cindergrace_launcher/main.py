#!/usr/bin/env python3
"""
Cindergrace Launcher - Haupteinstiegspunkt
Verwaltet LLM CLI Sessions (Claude, Codex, Gemini) für verschiedene Projekte
"""

import sys
import os


def main():
    """Hauptfunktion - startet die Qt-Anwendung"""
    # Füge cindergrace_common hinzu falls als Nachbar-Ordner vorhanden
    script_dir = os.path.dirname(os.path.abspath(__file__))
    common_src = os.path.join(script_dir, "..", "..", "..", "cindergrace_common", "src")
    if os.path.isdir(common_src):
        sys.path.insert(0, os.path.abspath(common_src))

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from .cockpit import LauncherWindow

    # High DPI Support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Cindergrace Launcher")
    app.setOrganizationName("Cindergrace")
    app.setOrganizationDomain("cindergrace.de")

    window = LauncherWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
