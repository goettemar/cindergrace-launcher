"""Internationalization (i18n) module for Cindergrace Launcher.

Supports English (default) and German.
"""

from typing import Callable

# Supported languages
LANGUAGES = {
    "en": "English",
    "de": "Deutsch",
}

# Default language
DEFAULT_LANGUAGE = "en"

# Current language (module-level state)
_current_language = DEFAULT_LANGUAGE

# Translation callback for dynamic updates
_on_language_change: Callable[[], None] | None = None


def set_language(lang: str) -> None:
    """Set the current language."""
    global _current_language
    if lang in LANGUAGES:
        _current_language = lang
        if _on_language_change:
            _on_language_change()


def get_language() -> str:
    """Get the current language code."""
    return _current_language


def get_language_name(lang: str) -> str:
    """Get the display name for a language code."""
    return LANGUAGES.get(lang, lang)


def set_on_language_change(callback: Callable[[], None] | None) -> None:
    """Set callback for language changes (for UI updates)."""
    global _on_language_change
    _on_language_change = callback


def tr(key: str) -> str:
    """Translate a key to the current language.

    Returns the key itself if no translation is found.
    """
    translations = TRANSLATIONS.get(_current_language, TRANSLATIONS[DEFAULT_LANGUAGE])
    return translations.get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))


# Translation dictionaries
TRANSLATIONS = {
    "en": {
        # Main window
        "window_title": "Cindergrace Launcher",
        "new_project": "+ New Project",
        "hidden": "Hidden",
        "settings": "Settings",
        "search_placeholder": "Search projects...",
        "category_all": "All",
        "no_projects": "No projects\nClick '+ New Project' to get started",
        "projects_status": "{visible}/{total} projects",
        "hidden_count": "{count} hidden",
        "active_count": "{count} active",

        # Project widget
        "favorite": "Favorite",
        "mark_favorite": "Mark as favorite",
        "running": "{provider} running",
        "stopped": "Stopped",
        "focus_window": "Bring window to foreground",
        "stop_session": "Stop session",
        "start_provider": "Start LLM CLI (Claude, Codex, Gemini...)",
        "edit_project": "Edit project",
        "show_project": "Show",
        "hide_project": "Hide",
        "remove_project": "Remove project",

        # Project dialog
        "dialog_new_project": "New project",
        "dialog_edit_project": "Edit project",
        "project_name": "Project name",
        "project_name_placeholder": "Name of the project",
        "project_folder": "Project folder",
        "project_root": "Project root: {path}",
        "folder_placeholder": "Folder name (relative to root)",
        "category_optional": "Category (optional)",
        "category_placeholder": "e.g. Python, Web, Tools...",
        "start_command_optional": "Start command (optional)",
        "start_command_placeholder": "Custom start command...",
        "start_command_hint": "Leave empty for: {command}",
        "default_provider": "Default provider",
        "cancel": "Cancel",
        "save": "Save",
        "error": "Error",
        "error_name_required": "Please enter a name",
        "error_folder_required": "Please select a folder",
        "error_invalid_command": "Invalid start command: {error}",

        # Provider dialog
        "dialog_new_provider": "New provider",
        "dialog_edit_provider": "Edit provider",
        "basic_settings": "Basic settings",
        "id_unique": "ID (unique):",
        "display_name": "Display name:",
        "command_section": "Command",
        "cli_command": "CLI command:",
        "skip_permissions_flag": "Skip-Permissions Flag:",
        "appearance": "Appearance",
        "icon_name": "Icon name:",
        "css_color": "CSS color:",
        "status": "Status",
        "enabled": "Enabled",
        "error_id_required": "Please enter an ID",
        "error_name_required_provider": "Please enter a name",
        "error_command_required": "Please enter a command",
        "error_invalid_cmd": "Invalid command: {error}",
        "error_invalid_flag": "Invalid flag: {error}",

        # Settings dialog
        "settings_title": "Settings",
        "paths": "Paths",
        "project_root_label": "Project root:",
        "sync_folder": "Sync folder:",
        "sync_folder_placeholder": "Google Drive, Dropbox etc.",
        "terminal": "Terminal",
        "terminal_command": "Terminal command:",
        "default_start_command": "Default start command:",
        "sync_settings": "Sync settings",
        "sync_password": "Sync password:",
        "password_placeholder": "Encryption password",
        "password_already_set": "(already set)",
        "export": "Export",
        "import": "Import",
        "llm_providers": "LLM Provider",
        "add_provider": "+ Add provider",
        "edit": "Edit",
        "delete": "Delete",
        "delete_provider_title": "Delete provider",
        "delete_provider_confirm": "Really delete provider '{name}'?",
        "min_provider_error": "At least one provider must be configured.",
        "not_possible": "Not possible",

        # Language settings
        "language": "Language",
        "language_label": "Language:",
        "language_restart_hint": "Changes take effect after restart",

        # Messages
        "settings_saved": "Settings saved",
        "export_title": "Export",
        "import_title": "Import",
        "no_sync_folder": "No sync folder configured",
        "project_updated": "Project updated: {name}",
        "project_added": "Project added: {name}",
        "project_removed": "Project removed",
        "remove_project_title": "Remove project?",
        "remove_project_confirm": "Do you want to remove '{name}' from the list?\n\nThe project folder will not be deleted.",
        "session_stopped": "Session stopped",
        "started": "{provider} started: {name}",
        "not_found": "Not found: {path}",
        "invalid_start_command": "Invalid start command: {error}",
        "terminal_not_found": "Terminal not found: {terminal}",
        "process_error": "Process error: {error}",
        "provider_not_found": "Provider not found: {id}",

        # About dialog
        "about_title": "About Cindergrace Launcher",
        "about_text": (
            "<h2>Cindergrace Launcher</h2>"
            "<p>Version 1.1.0</p>"
            "<p>LLM CLI Session Manager</p>"
            "<p>Manages Claude, Codex, Gemini and other AI CLIs</p>"
            "<p><br>&copy; 2025 Cindergrace Team</p>"
            "<p><a href='https://github.com/goettemar/cindergrace-launcher'>GitHub</a></p>"
        ),
    },
    "de": {
        # Hauptfenster
        "window_title": "Cindergrace Launcher",
        "new_project": "+ Neues Projekt",
        "hidden": "Versteckte",
        "settings": "Einstellungen",
        "search_placeholder": "Projekte suchen...",
        "category_all": "Alle",
        "no_projects": "Keine Projekte\nKlicke '+ Neues Projekt' um zu beginnen",
        "projects_status": "{visible}/{total} Projekte",
        "hidden_count": "{count} versteckt",
        "active_count": "{count} aktiv",

        # Projekt-Widget
        "favorite": "Favorit",
        "mark_favorite": "Als Favorit markieren",
        "running": "{provider} l\u00e4uft",
        "stopped": "Gestoppt",
        "focus_window": "Fenster in den Vordergrund",
        "stop_session": "Sitzung beenden",
        "start_provider": "LLM CLI starten (Claude, Codex, Gemini...)",
        "edit_project": "Projekt bearbeiten",
        "show_project": "Anzeigen",
        "hide_project": "Verstecken",
        "remove_project": "Projekt entfernen",

        # Projekt-Dialog
        "dialog_new_project": "Neues Projekt",
        "dialog_edit_project": "Projekt bearbeiten",
        "project_name": "Projektname",
        "project_name_placeholder": "Name des Projekts",
        "project_folder": "Projektordner",
        "project_root": "Projektwurzel: {path}",
        "folder_placeholder": "Ordnername (relativ zur Wurzel)",
        "category_optional": "Kategorie (optional)",
        "category_placeholder": "z.B. Python, Web, Tools...",
        "start_command_optional": "Startbefehl (optional)",
        "start_command_placeholder": "Eigener Startbefehl...",
        "start_command_hint": "Leer lassen f\u00fcr: {command}",
        "default_provider": "Standard-Provider",
        "cancel": "Abbrechen",
        "save": "Speichern",
        "error": "Fehler",
        "error_name_required": "Bitte einen Namen eingeben",
        "error_folder_required": "Bitte einen Ordner ausw\u00e4hlen",
        "error_invalid_command": "Ung\u00fcltiger Startbefehl: {error}",

        # Provider-Dialog
        "dialog_new_provider": "Neuer Provider",
        "dialog_edit_provider": "Provider bearbeiten",
        "basic_settings": "Grundeinstellungen",
        "id_unique": "ID (eindeutig):",
        "display_name": "Anzeigename:",
        "command_section": "Befehl",
        "cli_command": "CLI-Befehl:",
        "skip_permissions_flag": "Skip-Permissions Flag:",
        "appearance": "Darstellung",
        "icon_name": "Icon-Name:",
        "css_color": "CSS-Farbe:",
        "status": "Status",
        "enabled": "Aktiviert",
        "error_id_required": "Bitte eine ID eingeben",
        "error_name_required_provider": "Bitte einen Namen eingeben",
        "error_command_required": "Bitte einen Befehl eingeben",
        "error_invalid_cmd": "Ung\u00fcltiger Befehl: {error}",
        "error_invalid_flag": "Ung\u00fcltiges Flag: {error}",

        # Einstellungen-Dialog
        "settings_title": "Einstellungen",
        "paths": "Pfade",
        "project_root_label": "Projektwurzel:",
        "sync_folder": "Sync-Ordner:",
        "sync_folder_placeholder": "Google Drive, Dropbox etc.",
        "terminal": "Terminal",
        "terminal_command": "Terminal-Befehl:",
        "default_start_command": "Standard-Startbefehl:",
        "sync_settings": "Sync-Einstellungen",
        "sync_password": "Sync-Passwort:",
        "password_placeholder": "Verschl\u00fcsselungs-Passwort",
        "password_already_set": "(bereits gesetzt)",
        "export": "Exportieren",
        "import": "Importieren",
        "llm_providers": "LLM-Provider",
        "add_provider": "+ Provider hinzuf\u00fcgen",
        "edit": "Bearbeiten",
        "delete": "L\u00f6schen",
        "delete_provider_title": "Provider l\u00f6schen",
        "delete_provider_confirm": "Provider '{name}' wirklich l\u00f6schen?",
        "min_provider_error": "Es muss mindestens ein Provider konfiguriert sein.",
        "not_possible": "Nicht m\u00f6glich",

        # Spracheinstellungen
        "language": "Sprache",
        "language_label": "Sprache:",
        "language_restart_hint": "\u00c4nderungen werden nach Neustart wirksam",

        # Meldungen
        "settings_saved": "Einstellungen gespeichert",
        "export_title": "Export",
        "import_title": "Import",
        "no_sync_folder": "Kein Sync-Ordner konfiguriert",
        "project_updated": "Projekt aktualisiert: {name}",
        "project_added": "Projekt hinzugef\u00fcgt: {name}",
        "project_removed": "Projekt entfernt",
        "remove_project_title": "Projekt entfernen?",
        "remove_project_confirm": "M\u00f6chtest du '{name}' aus der Liste entfernen?\n\nDer Projektordner wird nicht gel\u00f6scht.",
        "session_stopped": "Sitzung beendet",
        "started": "{provider} gestartet: {name}",
        "not_found": "Nicht gefunden: {path}",
        "invalid_start_command": "Ung\u00fcltiger Startbefehl: {error}",
        "terminal_not_found": "Terminal nicht gefunden: {terminal}",
        "process_error": "Prozessfehler: {error}",
        "provider_not_found": "Provider nicht gefunden: {id}",

        # \u00dcber-Dialog
        "about_title": "\u00dcber Cindergrace Launcher",
        "about_text": (
            "<h2>Cindergrace Launcher</h2>"
            "<p>Version 1.1.0</p>"
            "<p>LLM CLI Sitzungsmanager</p>"
            "<p>Verwaltet Claude, Codex, Gemini und andere KI-CLIs</p>"
            "<p><br>&copy; 2025 Cindergrace Team</p>"
            "<p><a href='https://github.com/goettemar/cindergrace-launcher'>GitHub</a></p>"
        ),
    },
}
