#!/usr/bin/env python3
"""
Cindergrace Launcher - Haupteinstiegspunkt
Verwaltet LLM CLI Sessions (Claude, Codex, Gemini) für verschiedene Projekte
"""

import os
import sys

# Eindeutiger Name fuer Single-Instance Socket
SOCKET_NAME = "cindergrace-launcher-single-instance"


class SingleInstance:
    """
    Stellt sicher, dass nur eine Instanz der Anwendung laeuft.
    Bei zweitem Start wird die existierende Instanz aktiviert.
    """

    def __init__(self, socket_name: str):
        from PySide6.QtNetwork import QLocalServer, QLocalSocket

        self.socket_name = socket_name
        self.server = None
        self.is_running = False
        self.window = None

        # Versuche, mit existierender Instanz zu verbinden
        socket = QLocalSocket()
        socket.connectToServer(socket_name)

        if socket.waitForConnected(500):
            # Andere Instanz laeuft - Signal senden und beenden
            self.is_running = True
            socket.write(b"activate")
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
        else:
            # Keine andere Instanz - Server starten
            self.is_running = False

            # Alten Socket entfernen falls vorhanden (nach Crash)
            QLocalServer.removeServer(socket_name)

            self.server = QLocalServer()
            self.server.newConnection.connect(self._on_new_connection)
            if not self.server.listen(socket_name):
                print(f"Warnung: Konnte Single-Instance Server nicht starten: "
                      f"{self.server.errorString()}")

    def set_window(self, window):
        """Setzt das Hauptfenster fuer Aktivierung"""
        self.window = window

    def _on_new_connection(self):
        """Wird aufgerufen wenn eine andere Instanz sich verbindet"""
        if self.server:
            socket = self.server.nextPendingConnection()
            if socket:
                socket.waitForReadyRead(1000)
                # Fenster aktivieren
                if self.window:
                    self.window.showNormal()
                    self.window.raise_()
                    self.window.activateWindow()
                socket.disconnectFromServer()

    def cleanup(self):
        """Raumt den Server auf"""
        if self.server:
            self.server.close()


def main():
    """Hauptfunktion - startet die Qt-Anwendung"""
    # Fuege cindergrace_common hinzu falls als Nachbar-Ordner vorhanden
    script_dir = os.path.dirname(os.path.abspath(__file__))
    common_src = os.path.join(script_dir, "..", "..", "..", "cindergrace_common", "src")
    if os.path.isdir(common_src):
        sys.path.insert(0, os.path.abspath(common_src))

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    # High DPI Support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Cindergrace Launcher")
    app.setOrganizationName("Cindergrace")
    app.setOrganizationDomain("cindergrace.de")

    # Single-Instance Check
    single_instance = SingleInstance(SOCKET_NAME)
    if single_instance.is_running:
        # Andere Instanz wurde aktiviert - still beenden
        print("Cindergrace Launcher laeuft bereits - aktiviere existierendes Fenster")
        sys.exit(0)

    from .cockpit import LauncherWindow

    window = LauncherWindow()
    single_instance.set_window(window)
    window.show()

    exit_code = app.exec()

    # Cleanup
    single_instance.cleanup()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
