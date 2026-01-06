"""
Prozess-Management für LLM CLI Instanzen
Verwaltet laufende Terminal-Sessions für verschiedene LLM Provider
"""

import subprocess
import os
import signal
import shlex
from typing import Dict, Optional, Tuple, Callable
from dataclasses import dataclass
import time

from .providers import LLMProvider

# Gefährliche Shell-Zeichen die in Befehlen nicht erlaubt sind
DANGEROUS_CHARS = set(';|&`$(){}[]<>\\"\'\n\r')


def validate_command(cmd: str) -> Tuple[bool, str]:
    """
    Validiert einen Befehl auf gefährliche Shell-Zeichen.
    Returns: (is_valid, error_message)
    """
    if not cmd or not cmd.strip():
        return False, "Befehl ist leer"

    # Erlaube nur alphanumerische Zeichen, Leerzeichen, Bindestriche, Unterstriche, Punkte, Schrägstriche
    # und das Gleichheitszeichen (für Flags wie --flag=value)
    dangerous_found = [c for c in cmd if c in DANGEROUS_CHARS]
    if dangerous_found:
        return False, f"Ungültige Zeichen im Befehl: {set(dangerous_found)}"

    return True, ""


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
    """Verwaltet LLM CLI Prozesse"""

    def __init__(self, terminal_cmd: str = "gnome-terminal"):
        self.terminal_cmd = terminal_cmd
        self.sessions: Dict[str, RunningSession] = {}  # project_path -> session
        self._pending_window_search: Optional[dict] = None

    def poll_for_window(self) -> bool:
        """
        Sucht asynchron nach dem Fenster einer gestarteten Session.
        Wird von GLib.timeout_add aufgerufen.

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

        # Fenster suchen
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

        if skip_permissions_flag:
            is_valid, error = validate_command(skip_permissions_flag)
            if not is_valid:
                return False, f"Ungültiges Skip-Flag: {error}"

        try:
            # Vollständigen Befehl zusammenbauen (sicher, da validiert)
            full_cmd = provider_command
            if skip_permissions_flag:
                full_cmd += f" {skip_permissions_flag}"

            # Sichere End-Message (keine Shell-Zeichen)
            safe_display_name = display_name.replace("'", "")
            end_message = f"{safe_display_name} beendet"

            # Terminal mit LLM CLI starten
            cmd = [
                self.terminal_cmd,
                f"--title={display_name}: {project_name}",
                f"--working-directory={project_path}",
                "--",
                "bash", "-c",
                f"{full_cmd}; echo '{end_message}. Enter zum Schließen...'; read"
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            session = RunningSession(
                project_path=project_path,
                provider_id=provider_id,
                terminal_pid=process.pid,
                window_id=None  # Wird asynchron gefunden
            )

            self.sessions[project_path] = session

            # Window-Titel für spätere Suche speichern
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

    def stop_session(self, project_path: str) -> Tuple[bool, str]:
        """Beendet eine LLM CLI Session"""
        if project_path not in self.sessions:
            return False, "Keine aktive Session"

        session = self.sessions[project_path]

        try:
            # Versuche den Prozess und seine Kinder zu beenden
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
            # Prüfen ob der Prozess noch existiert
            os.kill(session.terminal_pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            # Prozess existiert, aber wir haben keine Berechtigung
            return True

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

        # Versuche Window ID zu aktualisieren falls nicht vorhanden
        if not session.window_id:
            # Suche nach Fenster mit passendem Titel
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
                return False, "wmctrl nicht installiert (sudo apt install wmctrl)"

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
            return False, "xdotool nicht installiert (sudo apt install xdotool)"

    def _find_window_by_title(self, title: str) -> Optional[str]:
        """Findet eine Window ID anhand des Titels"""
        try:
            result = subprocess.run(
                ["wmctrl", "-l"],
                capture_output=True,
                text=True
            )
            for line in result.stdout.strip().split('\n'):
                if title in line:
                    return line.split()[0]
        except:
            pass
        return None

    def _find_window_by_pid(self, pid: int) -> Optional[str]:
        """Findet eine Window ID anhand der PID"""
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
        except:
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
