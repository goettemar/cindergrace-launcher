"""
Prozess-Management für LLM CLI Instanzen
Verwaltet laufende Terminal-Sessions für verschiedene LLM Provider

Cross-Platform Support für Windows, macOS und Linux
"""

import subprocess
import os
import sys
import signal
from typing import Dict, Optional, Tuple, Callable
from dataclasses import dataclass
import time

from .providers import LLMProvider

# Gefährliche Shell-Zeichen die Command Injection ermöglichen
INJECTION_CHARS = set(';|&`$(){}<>\n\r')


def validate_command(cmd: str) -> Tuple[bool, str]:
    """
    Validiert einen Befehl auf gefährliche Shell-Zeichen.
    Erlaubt Windows-Pfade (Backslash) und gequotete Pfade (für Leerzeichen).
    Returns: (is_valid, error_message)
    """
    if not cmd or not cmd.strip():
        return False, "Befehl ist leer"

    # Prüfe auf Command-Injection-Zeichen (Shell-Operatoren)
    injection_found = [c for c in cmd if c in INJECTION_CHARS]
    if injection_found:
        return False, f"Ungültige Zeichen im Befehl: {set(injection_found)}"

    # Prüfe auf unbalancierte Quotes (potentielle Injection)
    single_quotes = cmd.count("'")
    double_quotes = cmd.count('"')
    if single_quotes % 2 != 0:
        return False, "Unbalancierte einfache Anführungszeichen"
    if double_quotes % 2 != 0:
        return False, "Unbalancierte doppelte Anführungszeichen"

    return True, ""


def get_platform() -> str:
    """Ermittelt die Plattform"""
    if sys.platform == "win32":
        return "windows"
    elif sys.platform == "darwin":
        return "macos"
    else:
        return "linux"


def get_default_terminal() -> str:
    """Gibt das Standard-Terminal für die Plattform zurück"""
    platform = get_platform()
    if platform == "windows":
        # Prüfe auf Windows Terminal
        wt_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WindowsApps", "wt.exe")
        if os.path.exists(wt_path):
            return "wt"
        return "cmd"
    elif platform == "macos":
        return "Terminal"
    else:
        # Linux - prüfe verschiedene Terminals
        terminals = ["gnome-terminal", "konsole", "xfce4-terminal", "mate-terminal", "xterm"]
        for term in terminals:
            try:
                result = subprocess.run(["which", term], capture_output=True, text=True)
                if result.returncode == 0:
                    return term
            except OSError:
                continue
        return "xterm"


@dataclass
class RunningSession:
    """Eine laufende LLM CLI Session"""
    project_path: str
    provider_id: str
    terminal_pid: int
    window_id: Optional[str] = None
    started_at: float = 0.0

    def __post_init__(self):
        if self.started_at == 0.0:
            self.started_at = time.time()


class ProcessManager:
    """Verwaltet LLM CLI Prozesse - Cross-Platform"""

    def __init__(self, terminal_cmd: str = ""):
        self.platform = get_platform()
        self.terminal_cmd = terminal_cmd or get_default_terminal()
        self.sessions: Dict[str, RunningSession] = {}  # project_path -> session
        self._pending_window_search: Optional[dict] = None

    def poll_for_window(self) -> bool:
        """
        Sucht asynchron nach dem Fenster einer gestarteten Session.
        Wird von QTimer aufgerufen.

        Returns: True wenn weiter gepollt werden soll, False wenn fertig
        """
        if not self._pending_window_search:
            return False

        title = self._pending_window_search['title']
        project_path = self._pending_window_search['project_path']
        callback = self._pending_window_search.get('callback')
        attempts = self._pending_window_search.get('attempts', 0)

        # Max 10 Versuche (= 2 Sekunden bei 200ms Intervall)
        if attempts >= 10:
            self._pending_window_search = None
            return False

        self._pending_window_search['attempts'] = attempts + 1

        # Fenster suchen (nur auf Linux mit wmctrl)
        window_id = self._find_window_by_title(title)
        if window_id:
            # Gefunden - Session updaten
            if project_path in self.sessions:
                self.sessions[project_path].window_id = window_id
                if callback:
                    callback(window_id)
            self._pending_window_search = None
            return False

        return True  # Weiter suchen

    def start_session(
        self,
        project_path: str,
        project_name: str,
        provider_id: str,
        provider_command: str,
        provider_name: str = "",
        default_flags: str = "",
        skip_permissions_flag: str = "",
        on_window_found: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str]:
        """
        Startet eine neue LLM CLI Session für ein Projekt.

        Args:
            on_window_found: Optionaler Callback wenn Window-ID gefunden wird (für async UI-Update)

        Returns: (success, message)
        """
        if project_path in self.sessions:
            if self.is_running(project_path):
                return False, "Session läuft bereits"
            else:
                # Session war beendet, entfernen
                del self.sessions[project_path]

        if not os.path.isdir(project_path):
            return False, f"Pfad existiert nicht: {project_path}"

        # Fallback für Provider-Name
        display_name = provider_name or provider_id

        # SECURITY: Befehle validieren
        is_valid, error = validate_command(provider_command)
        if not is_valid:
            return False, f"Ungültiger Provider-Befehl: {error}"

        if default_flags:
            is_valid, error = validate_command(default_flags)
            if not is_valid:
                return False, f"Ungültige Default-Flags: {error}"

        if skip_permissions_flag:
            is_valid, error = validate_command(skip_permissions_flag)
            if not is_valid:
                return False, f"Ungültiges Skip-Flag: {error}"

        try:
            # Vollständigen Befehl zusammenbauen (sicher, da validiert)
            full_cmd = provider_command
            if default_flags:
                full_cmd += f" {default_flags}"
            if skip_permissions_flag:
                full_cmd += f" {skip_permissions_flag}"

            # Platform-spezifischer Start
            if self.platform == "windows":
                process = self._start_windows_terminal(project_path, project_name, display_name, full_cmd)
            elif self.platform == "macos":
                process = self._start_macos_terminal(project_path, project_name, display_name, full_cmd)
            else:
                process = self._start_linux_terminal(project_path, project_name, display_name, full_cmd)

            session = RunningSession(
                project_path=project_path,
                provider_id=provider_id,
                terminal_pid=process.pid,
                window_id=None  # Wird asynchron gefunden (nur Linux)
            )

            self.sessions[project_path] = session

            # Window-Titel für spätere Suche speichern (nur Linux)
            if self.platform == "linux":
                self._pending_window_search = {
                    'title': f"{display_name}: {project_name}",
                    'project_path': project_path,
                    'callback': on_window_found
                }

            return True, f"{display_name} gestartet"

        except FileNotFoundError:
            return False, f"Terminal nicht gefunden: {self.terminal_cmd}"
        except subprocess.SubprocessError as e:
            return False, f"Prozess-Fehler: {str(e)}"
        except OSError as e:
            return False, f"System-Fehler: {str(e)}"

    def _start_windows_terminal(self, project_path: str, project_name: str, display_name: str, full_cmd: str):
        """Startet Terminal auf Windows"""
        safe_display_name = display_name.replace("'", "").replace('"', "")
        title = f"{safe_display_name}: {project_name}"

        if self.terminal_cmd == "wt":
            # Windows Terminal
            cmd = [
                "wt",
                "--title", title,
                "-d", project_path,
                "cmd", "/k", full_cmd
            ]
        else:
            # Klassisches CMD
            cmd = [
                "cmd", "/c",
                f'start "{title}" /d "{project_path}" cmd /k {full_cmd}'
            ]

        return subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )

    def _start_macos_terminal(self, project_path: str, project_name: str, display_name: str, full_cmd: str):
        """Startet Terminal auf macOS"""
        safe_display_name = display_name.replace("'", "").replace('"', "")
        end_message = f"{safe_display_name} beendet"

        # AppleScript für Terminal.app
        script = f'''
        tell application "Terminal"
            activate
            do script "cd \\"{project_path}\\" && {full_cmd}; echo '{end_message}. Enter zum Schließen...'; read"
        end tell
        '''

        return subprocess.Popen(
            ["osascript", "-e", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def _start_linux_terminal(self, project_path: str, project_name: str, display_name: str, full_cmd: str):
        """Startet Terminal auf Linux"""
        safe_display_name = display_name.replace("'", "")
        end_message = f"{safe_display_name} beendet"

        terminal = self.terminal_cmd.split("/")[-1]  # Basis-Name extrahieren

        if terminal in ("gnome-terminal", "mate-terminal"):
            cmd = [
                self.terminal_cmd,
                f"--title={display_name}: {project_name}",
                f"--working-directory={project_path}",
                "--",
                "bash", "-c",
                f"{full_cmd}; echo '{end_message}. Enter zum Schließen...'; read"
            ]
        elif terminal == "konsole":
            cmd = [
                self.terminal_cmd,
                "--workdir", project_path,
                "-e", "bash", "-c",
                f"{full_cmd}; echo '{end_message}. Enter zum Schließen...'; read"
            ]
        elif terminal == "xfce4-terminal":
            cmd = [
                self.terminal_cmd,
                f"--title={display_name}: {project_name}",
                f"--working-directory={project_path}",
                "-e", f"bash -c \"{full_cmd}; echo '{end_message}. Enter zum Schließen...'; read\""
            ]
        else:
            # Fallback für xterm und andere
            cmd = [
                self.terminal_cmd,
                "-T", f"{display_name}: {project_name}",
                "-e", "bash", "-c",
                f"cd '{project_path}' && {full_cmd}; echo '{end_message}. Enter zum Schließen...'; read"
            ]

        return subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

    def stop_session(self, project_path: str) -> Tuple[bool, str]:
        """Beendet eine LLM CLI Session"""
        if project_path not in self.sessions:
            return False, "Keine aktive Session"

        session = self.sessions[project_path]

        try:
            if self.platform == "windows":
                # Windows: Prozess und Kinder beenden
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(session.terminal_pid)],
                    capture_output=True
                )
            else:
                # Unix: Prozessgruppe beenden
                os.killpg(os.getpgid(session.terminal_pid), signal.SIGTERM)

            del self.sessions[project_path]
            return True, "Session beendet"
        except ProcessLookupError:
            # Prozess existiert nicht mehr
            del self.sessions[project_path]
            return True, "Session war bereits beendet"
        except PermissionError as e:
            return False, f"Keine Berechtigung zum Beenden: {str(e)}"
        except OSError as e:
            return False, f"System-Fehler beim Beenden: {str(e)}"

    def is_running(self, project_path: str) -> bool:
        """Prüft ob eine Session noch läuft"""
        if project_path not in self.sessions:
            return False

        session = self.sessions[project_path]

        try:
            if self.platform == "windows":
                # Windows: Prüfen ob PID existiert
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {session.terminal_pid}"],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                return str(session.terminal_pid) in result.stdout
            else:
                # Unix: Signal 0 sendet kein Signal, prüft nur ob Prozess existiert
                os.kill(session.terminal_pid, 0)
                return True
        except ProcessLookupError:
            return False
        except PermissionError:
            # Prozess existiert, aber wir haben keine Berechtigung
            return True
        except OSError:
            return False

    def get_session_provider(self, project_path: str) -> Optional[str]:
        """Gibt die Provider-ID einer laufenden Session zurück"""
        if project_path in self.sessions:
            return self.sessions[project_path].provider_id
        return None

    def focus_window(self, project_path: str) -> Tuple[bool, str]:
        """Bringt das Terminal-Fenster in den Vordergrund"""
        if project_path not in self.sessions:
            return False, "Keine aktive Session"

        session = self.sessions[project_path]

        if self.platform == "windows":
            # Windows: Keine einfache Möglichkeit ohne zusätzliche Bibliotheken
            return False, "Fenster-Fokussierung auf Windows nicht unterstützt"

        if self.platform == "macos":
            # macOS: Terminal aktivieren
            try:
                subprocess.run(
                    ["osascript", "-e", 'tell application "Terminal" to activate'],
                    check=True,
                    capture_output=True
                )
                return True, "Terminal aktiviert"
            except subprocess.CalledProcessError:
                return False, "Fenster konnte nicht aktiviert werden"

        # Linux: wmctrl oder xdotool

        # Versuche Window ID zu aktualisieren falls nicht vorhanden
        if not session.window_id:
            window_id = self._find_window_by_pid(session.terminal_pid)
            if window_id:
                session.window_id = window_id

        if session.window_id:
            try:
                subprocess.run(
                    ["wmctrl", "-i", "-a", session.window_id],
                    check=True,
                    capture_output=True
                )
                return True, "Fenster aktiviert"
            except subprocess.CalledProcessError:
                pass
            except FileNotFoundError:
                pass

        # Fallback: Versuche über xdotool
        try:
            subprocess.run(
                ["xdotool", "search", "--pid", str(session.terminal_pid), "windowactivate"],
                check=True,
                capture_output=True
            )
            return True, "Fenster aktiviert"
        except subprocess.CalledProcessError:
            return False, "Fenster konnte nicht gefunden werden"
        except FileNotFoundError:
            return False, "wmctrl/xdotool nicht installiert"

    def _find_window_by_title(self, title: str) -> Optional[str]:
        """Findet eine Window ID anhand des Titels (nur Linux)"""
        if self.platform != "linux":
            return None

        try:
            result = subprocess.run(
                ["wmctrl", "-l"],
                capture_output=True,
                text=True
            )
            for line in result.stdout.strip().split('\n'):
                if title in line:
                    return line.split()[0]
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            pass
        return None

    def _find_window_by_pid(self, pid: int) -> Optional[str]:
        """Findet eine Window ID anhand der PID (nur Linux)"""
        if self.platform != "linux":
            return None

        try:
            result = subprocess.run(
                ["wmctrl", "-lp"],
                capture_output=True,
                text=True
            )
            for line in result.stdout.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 3 and parts[2] == str(pid):
                    return parts[0]
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            pass
        return None

    def get_all_status(self) -> Dict[str, bool]:
        """Gibt den Status aller bekannten Sessions zurück"""
        status = {}
        for path in list(self.sessions.keys()):
            status[path] = self.is_running(path)
        return status

    def cleanup_dead_sessions(self):
        """Entfernt beendete Sessions aus der Liste"""
        dead = [path for path in self.sessions if not self.is_running(path)]
        for path in dead:
            del self.sessions[path]
