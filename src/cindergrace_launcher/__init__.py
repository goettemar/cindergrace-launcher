"""
Cindergrace Launcher - Multi-LLM Projekt-Manager

GTK4/Adwaita-basierte GUI zur Verwaltung von LLM CLI Sessions.
Unterstützt Claude, Codex, Gemini und andere konfigurierbare Provider.
"""

__version__ = "1.0.0"
__author__ = "Cindergrace Team"

from .cockpit import LauncherApp, LauncherWindow
from .config import Config, Project, load_config, save_config
from .process_manager import ProcessManager
from .providers import LLMProvider

__all__ = [
    "LauncherApp",
    "LauncherWindow",
    "Config",
    "Project",
    "load_config",
    "save_config",
    "ProcessManager",
    "LLMProvider",
]
