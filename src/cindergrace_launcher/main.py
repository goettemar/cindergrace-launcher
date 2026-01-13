#!/usr/bin/env python3
"""Cindergrace Launcher - Main entry point.

Manages LLM CLI sessions (Claude, Codex, Gemini) for various projects.
"""

import os
import sys

# Unique name for single-instance socket
SOCKET_NAME = "cindergrace-launcher-single-instance"


class SingleInstance:
    """Ensures only one instance of the application runs.

    On second start, the existing instance is activated.
    """

    def __init__(self, socket_name: str):
        """Initialize the single-instance server."""
        from PySide6.QtNetwork import QLocalServer, QLocalSocket

        self.socket_name = socket_name
        self.server = None
        self.is_running = False
        self.window = None

        # Try to connect to existing instance
        socket = QLocalSocket()
        socket.connectToServer(socket_name)

        if socket.waitForConnected(500):
            # Other instance is running - send signal and exit
            self.is_running = True
            socket.write(b"activate")
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
        else:
            # No other instance - start server
            self.is_running = False

            # Remove old socket if present (after crash)
            QLocalServer.removeServer(socket_name)

            self.server = QLocalServer()
            self.server.newConnection.connect(self._on_new_connection)
            if not self.server.listen(socket_name):
                print(
                    f"Warning: Could not start single-instance server: {self.server.errorString()}"
                )

    def set_window(self, window):
        """Set the main window for activation."""
        self.window = window

    def _on_new_connection(self):
        """Handle a connection from another instance."""
        if self.server:
            socket = self.server.nextPendingConnection()
            if socket:
                socket.waitForReadyRead(1000)
                # Activate window
                if self.window:
                    self.window.showNormal()
                    self.window.raise_()
                    self.window.activateWindow()
                socket.disconnectFromServer()

    def cleanup(self):
        """Clean up the server."""
        if self.server:
            self.server.close()


def main():
    """Start the Qt application."""
    # Add cindergrace_common if present as neighbor folder
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
        # Other instance was activated - exit silently
        print("Cindergrace Launcher is already running - activating existing window")
        sys.exit(0)

    # Initialize i18n with saved language preference
    from .config import load_config
    from .i18n import set_language

    config = load_config()
    set_language(config.language)

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
