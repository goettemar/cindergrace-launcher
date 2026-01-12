"""Cindergrace Launcher - LLM CLI Session Manager.

PySide6/Qt6-basierte GUI zur Verwaltung von LLM CLI Sessions.
Unterstützt Claude, Codex, Gemini und andere konfigurierbare Provider.

Cross-Platform: Windows, macOS, Linux
"""

__version__ = "1.1.0"
__author__ = "Cindergrace Team"

from .cockpit import LauncherWindow
from .config import Config, Project, load_config, save_config
from .process_manager import ProcessManager
from .providers import LLMProvider

__all__ = [
    "LauncherWindow",
    "Config",
    "Project",
    "load_config",
    "save_config",
    "ProcessManager",
    "LLMProvider",
]
