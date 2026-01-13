"""Cindergrace Launcher - LLM CLI Session Manager.

PySide6/Qt6-based GUI for managing LLM CLI sessions.
Supports Claude, Codex, Gemini and other configurable providers.

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
