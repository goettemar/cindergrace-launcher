"""
Konfigurationsmanagement für Cindergrace Launcher
Trennung zwischen lokalen Einstellungen und gesynchten Projektdaten
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .providers import LLMProvider, get_initial_providers
from .sync import SyncManager, SyncProject

CONFIG_DIR = Path.home() / ".config" / "cindergrace-launcher"
LOCAL_CONFIG_FILE = CONFIG_DIR / "local.json"

# Migration: Alte Config-Pfade
OLD_CONFIG_DIRS = [
    Path.home() / ".config" / "llm-cockpit",
    Path.home() / ".config" / "claude-cockpit",
]


@dataclass
class Project:
    """Ein Projekt mit Pfad und Metadaten"""

    name: str
    relative_path: str  # Relativer Pfad vom project_root
    description: str = ""
    category: str = "Allgemein"
    default_provider: str = "claude"
    custom_start_command: str = ""
    hidden: bool = False
    favorite: bool = False

    def get_absolute_path(self, project_root: str) -> str:
        """
        Gibt den absoluten Pfad zurück.
        Schützt gegen Path Traversal Angriffe.
        """
        root = Path(project_root).resolve()
        abs_path = (root / self.relative_path).resolve()

        # SECURITY: Prüfen dass der Pfad innerhalb des project_root bleibt
        try:
            abs_path.relative_to(root)
        except ValueError:
            # Path Traversal Versuch - Fallback auf project_root
            return str(root)

        return str(abs_path)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_sync_project(self) -> SyncProject:
        """Konvertiert zu SyncProject für Export"""
        return SyncProject(
            name=self.name,
            relative_path=self.relative_path,
            description=self.description,
            category=self.category,
            default_provider=self.default_provider,
            custom_start_command=self.custom_start_command,
            hidden=self.hidden,
            favorite=self.favorite,
        )

    @classmethod
    def from_sync_project(cls, sp: SyncProject) -> "Project":
        """Erstellt Project aus SyncProject"""
        return cls(
            name=sp.name,
            relative_path=sp.relative_path,
            description=sp.description,
            category=sp.category,
            default_provider=sp.default_provider,
            custom_start_command=sp.custom_start_command,
            hidden=sp.hidden,
            favorite=sp.favorite,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """Erstellt Project aus Dictionary mit Rückwärtskompatibilität"""
        # Migration: Alter 'path' zu 'relative_path'
        if "path" in data and "relative_path" not in data:
            # Versuche relativen Pfad zu extrahieren
            old_path = data["path"]
            # Nimm nur den letzten Ordnernamen als relativen Pfad
            data["relative_path"] = Path(old_path).name

        defaults = {
            "relative_path": "",
            "description": "",
            "category": "Allgemein",
            "default_provider": "claude",
            "custom_start_command": "",
            "hidden": False,
            "favorite": False,
        }
        for key, default_val in defaults.items():
            if key not in data:
                data[key] = default_val

        # Nur bekannte Felder übernehmen
        known_fields = {
            "name",
            "relative_path",
            "description",
            "category",
            "default_provider",
            "custom_start_command",
            "hidden",
            "favorite",
        }
        filtered = {k: v for k, v in data.items() if k in known_fields}

        return cls(**filtered)


@dataclass
class LocalConfig:
    """Lokale Konfiguration (wird NICHT gesyncht)"""

    # Pfade
    project_root: str = ""  # Root-Verzeichnis für Projekte
    sync_path: str = ""  # Pfad zum Sync-Ordner (Google Drive etc.)

    # Provider (lokal, da Pfade systemspezifisch)
    providers: list[LLMProvider] = field(default_factory=list)

    # UI Einstellungen
    terminal_command: str = "gnome-terminal"
    default_start_command: str = "./start.sh"
    window_width: int = 800
    window_height: int = 600
    last_provider: str = "claude"
    show_hidden: bool = False

    def __post_init__(self):
        if not self.providers:
            self.providers = get_initial_providers()
        if not self.project_root:
            # Default: ~/projekte oder ~/projects
            default_root = Path.home() / "projekte"
            if not default_root.exists():
                default_root = Path.home() / "projects"
            if not default_root.exists():
                default_root = Path.home() / "projekte"
            self.project_root = str(default_root)

    def get_provider(self, provider_id: str) -> LLMProvider | None:
        for p in self.providers:
            if p.id == provider_id:
                return p
        return None

    def get_enabled_providers(self) -> list[LLMProvider]:
        return [p for p in self.providers if p.enabled]

    def to_dict(self) -> dict:
        return {
            "project_root": self.project_root,
            "sync_path": self.sync_path,
            "providers": [p.to_dict() for p in self.providers],
            "terminal_command": self.terminal_command,
            "default_start_command": self.default_start_command,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "last_provider": self.last_provider,
            "show_hidden": self.show_hidden,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LocalConfig":
        providers = []
        if "providers" in data:
            providers = [LLMProvider.from_dict(p) for p in data["providers"]]

        return cls(
            project_root=data.get("project_root", ""),
            sync_path=data.get("sync_path", ""),
            providers=providers,
            terminal_command=data.get("terminal_command", "gnome-terminal"),
            default_start_command=data.get("default_start_command", "./start.sh"),
            window_width=data.get("window_width", 800),
            window_height=data.get("window_height", 600),
            last_provider=data.get("last_provider", "claude"),
            show_hidden=data.get("show_hidden", False),
        )


@dataclass
class Config:
    """Hauptkonfiguration - kombiniert lokal und Projekte"""

    local: LocalConfig = field(default_factory=LocalConfig)
    projects: list[Project] = field(default_factory=list)

    # Convenience-Properties für Rückwärtskompatibilität
    @property
    def providers(self) -> list[LLMProvider]:
        return self.local.providers

    @property
    def terminal_command(self) -> str:
        return self.local.terminal_command

    @property
    def default_start_command(self) -> str:
        return self.local.default_start_command

    @property
    def window_width(self) -> int:
        return self.local.window_width

    @window_width.setter
    def window_width(self, value: int):
        self.local.window_width = value

    @property
    def window_height(self) -> int:
        return self.local.window_height

    @window_height.setter
    def window_height(self, value: int):
        self.local.window_height = value

    @property
    def last_provider(self) -> str:
        return self.local.last_provider

    @last_provider.setter
    def last_provider(self, value: str):
        self.local.last_provider = value

    @property
    def show_hidden(self) -> bool:
        return self.local.show_hidden

    @show_hidden.setter
    def show_hidden(self, value: bool):
        self.local.show_hidden = value

    @property
    def project_root(self) -> str:
        return self.local.project_root

    @property
    def sync_path(self) -> str:
        return self.local.sync_path

    def get_provider(self, provider_id: str) -> LLMProvider | None:
        return self.local.get_provider(provider_id)

    def get_enabled_providers(self) -> list[LLMProvider]:
        return self.local.get_enabled_providers()

    def get_provider_command(self, provider_id: str) -> str:
        provider = self.get_provider(provider_id)
        return provider.command if provider else ""

    def is_provider_enabled(self, provider_id: str) -> bool:
        provider = self.get_provider(provider_id)
        return provider.enabled if provider else False

    def get_skip_permissions(self, provider_id: str) -> bool:
        provider = self.get_provider(provider_id)
        return bool(provider and provider.skip_permissions_flag)

    def add_provider(self, provider: LLMProvider):
        if self.get_provider(provider.id):
            raise ValueError(f"Provider mit ID '{provider.id}' existiert bereits")
        self.local.providers.append(provider)

    def update_provider(self, provider_id: str, updated: LLMProvider):
        for i, p in enumerate(self.local.providers):
            if p.id == provider_id:
                self.local.providers[i] = updated
                return
        raise ValueError(f"Provider '{provider_id}' nicht gefunden")

    def remove_provider(self, provider_id: str):
        self.local.providers = [p for p in self.local.providers if p.id != provider_id]

    def get_start_command(self, project: Project) -> str:
        if project.custom_start_command:
            return project.custom_start_command
        return self.local.default_start_command

    def get_project_absolute_path(self, project: Project) -> str:
        """Gibt den absoluten Pfad eines Projekts zurück"""
        return project.get_absolute_path(self.local.project_root)


def ensure_config_dir():
    """Stellt sicher, dass das Konfigurationsverzeichnis existiert"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _migrate_old_config() -> dict | None:
    """Migriert alte Konfiguration falls vorhanden"""
    for old_dir in OLD_CONFIG_DIRS:
        old_file = old_dir / "config.json"
        if old_file.exists():
            try:
                with open(old_file, encoding="utf-8") as f:
                    return json.load(f)  # type: ignore[no-any-return]
            except (OSError, json.JSONDecodeError):
                # Alte Config nicht lesbar - überspringen
                pass
    return None


def load_config() -> Config:
    """Lädt die Konfiguration"""
    ensure_config_dir()

    local_config = LocalConfig()
    projects = []

    # Versuche lokale Config zu laden
    if LOCAL_CONFIG_FILE.exists():
        try:
            with open(LOCAL_CONFIG_FILE, encoding="utf-8") as f:
                data = json.load(f)
                local_config = LocalConfig.from_dict(data.get("local", data))
                projects = [Project.from_dict(p) for p in data.get("projects", [])]
        except OSError as e:
            print(f"Fehler beim Lesen der Konfigurationsdatei: {e}")
        except json.JSONDecodeError as e:
            print(f"Fehler beim Parsen der Konfiguration (ungültiges JSON): {e}")
        except (KeyError, TypeError, ValueError) as e:
            print(f"Fehler beim Verarbeiten der Konfigurationsdaten: {e}")
    else:
        # Migration von alter Config
        old_data = _migrate_old_config()
        if old_data:
            print("Migriere alte Konfiguration...")

            # Extrahiere project_root aus erstem Projekt
            old_projects = old_data.get("projects", [])
            if old_projects:
                first_path = old_projects[0].get("path", "")
                if first_path:
                    local_config.project_root = str(Path(first_path).parent)

            # Provider migrieren
            if "providers" in old_data:
                local_config.providers = [
                    LLMProvider.from_dict(p) for p in old_data["providers"]
                ]

            # Andere Einstellungen
            local_config.terminal_command = old_data.get("terminal_command", "gnome-terminal")
            local_config.default_start_command = old_data.get(
                "default_start_command", "./start.sh"
            )
            local_config.window_width = old_data.get("window_width", 800)
            local_config.window_height = old_data.get("window_height", 600)
            local_config.last_provider = old_data.get("last_provider", "claude")
            local_config.show_hidden = old_data.get("show_hidden", False)

            # Projekte migrieren
            projects = [Project.from_dict(p) for p in old_projects]

            # Speichern im neuen Format
            config = Config(local=local_config, projects=projects)
            save_config(config)

    return Config(local=local_config, projects=projects)


def save_config(config: Config):
    """Speichert die Konfiguration"""
    ensure_config_dir()

    data = {
        "local": config.local.to_dict(),
        "projects": [p.to_dict() for p in config.projects],
    }

    with open(LOCAL_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_project(config: Config, project: Project) -> Config:
    """Fügt ein Projekt hinzu"""
    config.projects.append(project)
    save_config(config)
    return config


def remove_project(config: Config, index: int) -> Config:
    """Entfernt ein Projekt nach Index"""
    if 0 <= index < len(config.projects):
        config.projects.pop(index)
        save_config(config)
    return config


def update_project(config: Config, index: int, project: Project) -> Config:
    """Aktualisiert ein Projekt"""
    if 0 <= index < len(config.projects):
        config.projects[index] = project
        save_config(config)
    return config


# === Sync-Funktionen ===

# Secret Store für Sync-Passwort
try:
    from cindergrace_common import SecretStore

    _secret_store = SecretStore("cindergrace-launcher", warn_on_fallback=False)
except ImportError:
    _secret_store = None


def get_sync_password() -> str | None:
    """Holt Sync-Passwort aus OS Keyring (via cindergrace_common.SecretStore)"""
    if _secret_store:
        return _secret_store.get("sync_password")  # type: ignore[no-any-return]

    # Fallback ohne cindergrace_common
    try:
        import keyring

        return keyring.get_password("cindergrace-launcher", "sync")
    except ImportError:
        return None
    except OSError:
        # Keyring-Backend nicht verfügbar
        return None


def set_sync_password(password: str):
    """Speichert Sync-Passwort im OS Keyring (via cindergrace_common.SecretStore)"""
    if _secret_store:
        success = _secret_store.set("sync_password", password)
        if not success:
            print(
                "Hinweis: Passwort in Environment Variable gespeichert (Keyring nicht verfügbar)"
            )
        return

    # Fallback ohne cindergrace_common
    try:
        import keyring

        keyring.set_password("cindergrace-launcher", "sync", password)
    except ImportError:
        print("Fehler: Weder cindergrace_common noch keyring verfügbar")
    except OSError as e:
        print(f"Keyring nicht verfügbar: {e}")


def export_to_sync(config: Config) -> tuple[bool, str]:
    """Exportiert Projekte in Sync-Datei"""
    if not config.sync_path:
        return False, "Kein Sync-Pfad konfiguriert"

    password = get_sync_password()
    if not password:
        return False, "Kein Sync-Passwort konfiguriert"

    sync_mgr = SyncManager(config.sync_path, password)
    sync_projects = [p.to_sync_project() for p in config.projects]

    if sync_mgr.export_projects(sync_projects):
        return True, f"{len(sync_projects)} Projekte exportiert"
    return False, "Export fehlgeschlagen"


def import_from_sync(config: Config) -> tuple[bool, str]:
    """Importiert Projekte aus Sync-Datei"""
    if not config.sync_path:
        return False, "Kein Sync-Pfad konfiguriert"

    password = get_sync_password()
    if not password:
        return False, "Kein Sync-Passwort konfiguriert"

    sync_mgr = SyncManager(config.sync_path, password)

    if not sync_mgr.sync_file_exists():
        return False, "Keine Sync-Datei gefunden"

    sync_projects = sync_mgr.import_projects()
    if sync_projects is None:
        return False, "Falsches Passwort oder korrupte Datei"

    # Projekte aktualisieren
    config.projects = [Project.from_sync_project(sp) for sp in sync_projects]
    save_config(config)

    return True, f"{len(sync_projects)} Projekte importiert"
