"""
LLM Provider Abstraktionsschicht für LLM Cockpit
Unterstützt verschiedene LLM CLI Tools - vollständig konfigurierbar
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class LLMProvider:
    """Definition eines LLM CLI Providers - vollständig benutzerkonfigurierbar"""

    id: str  # Eindeutiger Identifier (z.B. "claude", "aider")
    name: str  # Anzeigename (z.B. "Claude Code")
    command: str  # Pfad zum CLI-Tool
    icon: str = "utilities-terminal-symbolic"  # GTK Icon Name
    color: str = "#808080"  # CSS Farbe für UI
    default_flags: str = ""  # Standard-Flags (z.B. "--yes")
    skip_permissions_flag: str = ""  # Flag für "keine Nachfragen"
    enabled: bool = True  # Provider aktiviert

    def get_full_command(self, skip_permissions: bool = False) -> str:
        """Gibt den vollständigen Befehl zurück"""
        parts = [self.command]
        if self.default_flags:
            parts.append(self.default_flags)
        if skip_permissions and self.skip_permissions_flag:
            parts.append(self.skip_permissions_flag)
        return " ".join(parts)

    def to_dict(self) -> dict:
        """Serialisiert den Provider für JSON-Speicherung"""
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "icon": self.icon,
            "color": self.color,
            "default_flags": self.default_flags,
            "skip_permissions_flag": self.skip_permissions_flag,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LLMProvider":
        """Erstellt Provider aus Dictionary mit Rückwärtskompatibilität"""
        known_fields = {
            "id",
            "name",
            "command",
            "icon",
            "color",
            "default_flags",
            "skip_permissions_flag",
            "enabled",
        }
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered_data)


def get_initial_providers() -> list[LLMProvider]:
    """Gibt initiale Provider für Erstinstallation zurück"""
    home = str(Path.home())

    return [
        LLMProvider(
            id="claude",
            name="Claude Code",
            command=f"{home}/.npm-global/bin/claude",
            icon="utilities-terminal-symbolic",
            color="#E07A5F",
            skip_permissions_flag="--dangerously-skip-permissions",
            enabled=True,
        ),
        LLMProvider(
            id="codex",
            name="OpenAI Codex CLI",
            command="codex",
            icon="accessories-text-editor-symbolic",
            color="#10A37F",
            skip_permissions_flag="--full-auto",
            enabled=True,
        ),
        LLMProvider(
            id="gemini",
            name="Gemini CLI",
            command="gemini",
            icon="weather-clear-symbolic",
            color="#4285F4",
            skip_permissions_flag="",
            enabled=True,
        ),
    ]
