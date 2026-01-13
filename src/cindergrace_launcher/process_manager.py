"""Process management for LLM CLI instances.

Manages running terminal sessions for various LLM providers.

Cross-platform support for Windows, macOS, and Linux.
"""

import os
import signal
import subprocess  # nosec B404 - needed for terminal/process management
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass

# Dangerous shell characters that enable command injection
INJECTION_CHARS = set(";|&`$(){}<>\n\r")


def validate_command(cmd: str) -> tuple[bool, str]:
    """Validates a command for dangerous shell characters.

    Allows Windows paths (backslash) and quoted paths (for spaces).
    Returns: (is_valid, error_message)
    """
    if not cmd or not cmd.strip():
        return False, "Command is empty"

    # Check for command injection characters (shell operators)
    injection_found = [c for c in cmd if c in INJECTION_CHARS]
    if injection_found:
        return False, f"Invalid characters in command: {set(injection_found)}"

    # Check for unbalanced quotes (potential injection)
    single_quotes = cmd.count("'")
    double_quotes = cmd.count('"')
    if single_quotes % 2 != 0:
        return False, "Unbalanced single quotes"
    if double_quotes % 2 != 0:
        return False, "Unbalanced double quotes"

    return True, ""


def get_platform() -> str:
    """Determines the platform."""
    if sys.platform == "win32":
        return "windows"
    elif sys.platform == "darwin":
        return "macos"
    else:
        return "linux"


def get_default_terminal() -> str:
    """Returns the default terminal for the platform."""
    platform = get_platform()
    if platform == "windows":
        # Check for Windows Terminal
        wt_path = os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WindowsApps", "wt.exe"
        )
        if os.path.exists(wt_path):
            return "wt"
        return "cmd"
    elif platform == "macos":
        return "Terminal"
    else:
        # Linux - check various terminals
        terminals = ["gnome-terminal", "konsole", "xfce4-terminal", "mate-terminal", "xterm"]
        for term in terminals:
            try:
                result = subprocess.run(  # nosec B603 B607 - trusted which command
                    ["which", term], capture_output=True, text=True
                )
                if result.returncode == 0:
                    return term
            except OSError:
                continue
        return "xterm"


@dataclass
class RunningSession:
    """A running LLM CLI session."""

    project_path: str
    provider_id: str
    terminal_pid: int
    window_id: str | None = None
    started_at: float = 0.0

    def __post_init__(self):
        """Sets the start time if not provided."""
        if self.started_at == 0.0:
            self.started_at = time.time()


class ProcessManager:
    """Manages LLM CLI processes - cross-platform."""

    def __init__(self, terminal_cmd: str = ""):
        """Initializes the ProcessManager."""
        self.platform = get_platform()
        self.terminal_cmd = terminal_cmd or get_default_terminal()
        self.sessions: dict[str, RunningSession] = {}  # project_path -> session
        self._pending_window_search: dict | None = None

    def poll_for_window(self) -> bool:
        """Asynchronously searches for the window of a started session.

        Called by QTimer.

        Returns: True if polling should continue, False if done
        """
        if not self._pending_window_search:
            return False

        title = self._pending_window_search["title"]
        project_path = self._pending_window_search["project_path"]
        callback = self._pending_window_search.get("callback")
        attempts = self._pending_window_search.get("attempts", 0)

        # Max 10 attempts (= 2 seconds at 200ms interval)
        if attempts >= 10:
            self._pending_window_search = None
            return False

        self._pending_window_search["attempts"] = attempts + 1

        # Search for window (Linux only with wmctrl)
        window_id = self._find_window_by_title(title)
        if window_id:
            # Found - update session
            if project_path in self.sessions:
                self.sessions[project_path].window_id = window_id
                if callback:
                    callback(window_id)
            self._pending_window_search = None
            return False

        return True  # Keep searching

    def start_session(
        self,
        project_path: str,
        project_name: str,
        provider_id: str,
        provider_command: str,
        provider_name: str = "",
        default_flags: str = "",
        skip_permissions_flag: str = "",
        on_window_found: Callable[[str], None] | None = None,
    ) -> tuple[bool, str]:
        """Starts a new LLM CLI session for a project.

        Args:
            project_path: Absolute path to the project.
            project_name: Display name of the project.
            provider_id: ID of the provider.
            provider_command: CLI command of the provider.
            provider_name: Display name of the provider.
            default_flags: Default flags for the provider.
            skip_permissions_flag: Flag for automatic confirmation.
            on_window_found: Optional callback when window ID is found.

        Returns:
            Tuple of success and status message.

        """
        if project_path in self.sessions:
            if self.is_running(project_path):
                return False, "Session already running"
            else:
                # Session was ended, remove
                del self.sessions[project_path]

        if not os.path.isdir(project_path):
            return False, f"Path does not exist: {project_path}"

        # Fallback for provider name
        display_name = provider_name or provider_id

        # SECURITY: Validate commands
        is_valid, error = validate_command(provider_command)
        if not is_valid:
            return False, f"Invalid provider command: {error}"

        if default_flags:
            is_valid, error = validate_command(default_flags)
            if not is_valid:
                return False, f"Invalid default flags: {error}"

        if skip_permissions_flag:
            is_valid, error = validate_command(skip_permissions_flag)
            if not is_valid:
                return False, f"Invalid skip flag: {error}"

        try:
            # Build full command (safe because validated)
            full_cmd = provider_command
            if default_flags:
                full_cmd += f" {default_flags}"
            if skip_permissions_flag:
                full_cmd += f" {skip_permissions_flag}"

            # Platform-specific start
            if self.platform == "windows":
                process = self._start_windows_terminal(
                    project_path, project_name, display_name, full_cmd
                )
            elif self.platform == "macos":
                process = self._start_macos_terminal(
                    project_path, project_name, display_name, full_cmd
                )
            else:
                process = self._start_linux_terminal(
                    project_path, project_name, display_name, full_cmd
                )

            session = RunningSession(
                project_path=project_path,
                provider_id=provider_id,
                terminal_pid=process.pid,
                window_id=None,  # Found asynchronously (Linux only)
            )

            self.sessions[project_path] = session

            # Save window title for later search (Linux only)
            if self.platform == "linux":
                self._pending_window_search = {
                    "title": f"{display_name}: {project_name}",
                    "project_path": project_path,
                    "callback": on_window_found,
                }

            return True, f"{display_name} started"

        except FileNotFoundError:
            return False, f"Terminal not found: {self.terminal_cmd}"
        except subprocess.SubprocessError as e:
            return False, f"Process error: {str(e)}"
        except OSError as e:
            return False, f"System error: {str(e)}"

    def _start_windows_terminal(
        self, project_path: str, project_name: str, display_name: str, full_cmd: str
    ):
        """Starts terminal on Windows."""
        safe_display_name = display_name.replace("'", "").replace('"', "")
        title = f"{safe_display_name}: {project_name}"

        if self.terminal_cmd == "wt":
            # Windows Terminal
            cmd = ["wt", "--title", title, "-d", project_path, "cmd", "/k", full_cmd]
        else:
            # Klassisches CMD
            cmd = ["cmd", "/c", f'start "{title}" /d "{project_path}" cmd /k {full_cmd}']

        return subprocess.Popen(  # nosec B603 B607 - trusted terminal command
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,  # type: ignore[attr-defined]
        )

    def _start_macos_terminal(
        self, project_path: str, project_name: str, display_name: str, full_cmd: str
    ):
        """Starts terminal on macOS."""
        safe_display_name = display_name.replace("'", "").replace('"', "")
        end_message = f"{safe_display_name} finished"

        # AppleScript for Terminal.app
        script = f"""
        tell application "Terminal"
            activate
            do script "cd \\"{project_path}\\" && {full_cmd}; echo '{end_message}. Press Enter to close...'; read"
        end tell
        """

        return subprocess.Popen(  # nosec B603 B607 - trusted osascript command
            ["osascript", "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def _start_linux_terminal(
        self, project_path: str, project_name: str, display_name: str, full_cmd: str
    ):
        """Starts terminal on Linux."""
        safe_display_name = display_name.replace("'", "")
        end_message = f"{safe_display_name} finished"

        terminal = self.terminal_cmd.split("/")[-1]  # Extract base name

        if terminal in ("gnome-terminal", "mate-terminal"):
            cmd = [
                self.terminal_cmd,
                f"--title={display_name}: {project_name}",
                f"--working-directory={project_path}",
                "--",
                "bash",
                "-c",
                f"{full_cmd}; echo '{end_message}. Press Enter to close...'; read",
            ]
        elif terminal == "konsole":
            cmd = [
                self.terminal_cmd,
                "--workdir",
                project_path,
                "-e",
                "bash",
                "-c",
                f"{full_cmd}; echo '{end_message}. Press Enter to close...'; read",
            ]
        elif terminal == "xfce4-terminal":
            cmd = [
                self.terminal_cmd,
                f"--title={display_name}: {project_name}",
                f"--working-directory={project_path}",
                "-e",
                f"bash -c \"{full_cmd}; echo '{end_message}. Press Enter to close...'; read\"",
            ]
        else:
            # Fallback for xterm and others
            cmd = [
                self.terminal_cmd,
                "-T",
                f"{display_name}: {project_name}",
                "-e",
                "bash",
                "-c",
                f"cd '{project_path}' && {full_cmd}; echo '{end_message}. Press Enter to close...'; read",
            ]

        return subprocess.Popen(  # nosec B603 B607 - trusted terminal command
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
        )

    def stop_session(self, project_path: str) -> tuple[bool, str]:
        """Stops an LLM CLI session."""
        if project_path not in self.sessions:
            return False, "No active session"

        session = self.sessions[project_path]

        try:
            if self.platform == "windows":
                # Windows: Kill process and children
                subprocess.run(  # nosec B603 B607 - trusted taskkill command
                    ["taskkill", "/F", "/T", "/PID", str(session.terminal_pid)],
                    capture_output=True,
                )
            else:
                # Unix: Kill process group
                os.killpg(os.getpgid(session.terminal_pid), signal.SIGTERM)

            del self.sessions[project_path]
            return True, "Session ended"
        except ProcessLookupError:
            # Process no longer exists
            del self.sessions[project_path]
            return True, "Session was already ended"
        except PermissionError as e:
            return False, f"No permission to end: {str(e)}"
        except OSError as e:
            return False, f"System error while ending: {str(e)}"

    def is_running(self, project_path: str) -> bool:
        """Checks if a session is still running."""
        if project_path not in self.sessions:
            return False

        session = self.sessions[project_path]

        try:
            if self.platform == "windows":
                # Windows: Check if PID exists
                result = subprocess.run(  # nosec B603 B607 - trusted tasklist command
                    ["tasklist", "/FI", f"PID eq {session.terminal_pid}"],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,  # type: ignore[attr-defined]
                )
                return str(session.terminal_pid) in result.stdout
            else:
                # Unix: Signal 0 sends no signal, only checks if process exists
                os.kill(session.terminal_pid, 0)
                return True
        except ProcessLookupError:
            return False
        except PermissionError:
            # Process exists but we don't have permission
            return True
        except OSError:
            return False

    def get_session_provider(self, project_path: str) -> str | None:
        """Returns the provider ID of a running session."""
        if project_path in self.sessions:
            return self.sessions[project_path].provider_id
        return None

    def focus_window(self, project_path: str) -> tuple[bool, str]:
        """Brings the terminal window to the foreground."""
        if project_path not in self.sessions:
            return False, "No active session"

        session = self.sessions[project_path]

        if self.platform == "windows":
            # Windows: No simple way without additional libraries
            return False, "Window focus not supported on Windows"

        if self.platform == "macos":
            # macOS: Activate terminal
            try:
                subprocess.run(  # nosec B603 B607 - trusted osascript command
                    ["osascript", "-e", 'tell application "Terminal" to activate'],
                    check=True,
                    capture_output=True,
                )
                return True, "Terminal activated"
            except subprocess.CalledProcessError:
                return False, "Window could not be activated"

        # Linux: wmctrl or xdotool

        # Try to update window ID if not present
        if not session.window_id:
            window_id = self._find_window_by_pid(session.terminal_pid)
            if window_id:
                session.window_id = window_id

        if session.window_id:
            try:
                subprocess.run(  # nosec B603 B607 - trusted wmctrl command
                    ["wmctrl", "-i", "-a", session.window_id], check=True, capture_output=True
                )
                return True, "Window activated"
            except subprocess.CalledProcessError:
                pass
            except FileNotFoundError:
                pass

        # Fallback: Try via xdotool
        try:
            subprocess.run(  # nosec B603 B607 - trusted xdotool command
                ["xdotool", "search", "--pid", str(session.terminal_pid), "windowactivate"],
                check=True,
                capture_output=True,
            )
            return True, "Window activated"
        except subprocess.CalledProcessError:
            return False, "Window could not be found"
        except FileNotFoundError:
            return False, "wmctrl/xdotool not installed"

    def _find_window_by_title(self, title: str) -> str | None:
        """Finds a window ID by title (Linux only)."""
        if self.platform != "linux":
            return None

        try:
            result = subprocess.run(  # nosec B603 B607 - trusted wmctrl command
                ["wmctrl", "-l"], capture_output=True, text=True
            )
            for line in result.stdout.strip().split("\n"):
                if title in line:
                    return line.split()[0]
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            pass
        return None

    def _find_window_by_pid(self, pid: int) -> str | None:
        """Finds a window ID by PID (Linux only)."""
        if self.platform != "linux":
            return None

        try:
            result = subprocess.run(  # nosec B603 B607 - trusted wmctrl command
                ["wmctrl", "-lp"], capture_output=True, text=True
            )
            for line in result.stdout.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 3 and parts[2] == str(pid):
                    return parts[0]
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            pass
        return None

    def get_all_status(self) -> dict[str, bool]:
        """Returns the status of all known sessions."""
        status = {}
        for path in list(self.sessions.keys()):
            status[path] = self.is_running(path)
        return status

    def cleanup_dead_sessions(self):
        """Removes ended sessions from the list."""
        dead = [path for path in self.sessions if not self.is_running(path)]
        for path in dead:
            del self.sessions[path]
