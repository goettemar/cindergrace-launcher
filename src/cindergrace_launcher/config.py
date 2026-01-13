"""Configuration management for Cindergrace Launcher.

Separation between local settings and synced project data.
"""

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .providers import LLMProvider, get_initial_providers
from .sync import SyncManager, SyncProject


def _get_config_dir() -> Path:
    """Get platform-specific config directory.

    - Windows: %APPDATA%/cindergrace-launcher
    - Linux/macOS: ~/.config/cindergrace-launcher
    """
    if sys.platform == "win32":
        # Windows: Use AppData/Roaming (standard for user config)
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "cindergrace-launcher"
        # Fallback if APPDATA not set
        return Path.home() / "AppData" / "Roaming" / "cindergrace-launcher"
    else:
        # Linux/macOS: Use XDG standard
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config) / "cindergrace-launcher"
        return Path.home() / ".config" / "cindergrace-launcher"


CONFIG_DIR = _get_config_dir()
LOCAL_CONFIG_FILE = CONFIG_DIR / "local.json"

# Migration: Old config paths
OLD_CONFIG_DIRS = [
    Path.home() / ".config" / "llm-cockpit",
    Path.home() / ".config" / "claude-cockpit",
    # Windows: Old non-standard path (before platform-specific fix)
    Path.home() / ".config" / "cindergrace-launcher",
]


@dataclass
class Project:
    """A project with path and metadata."""

    name: str
    relative_path: str  # Relative path from project_root
    description: str = ""
    category: str = "General"
    default_provider: str = "claude"
    custom_start_command: str = ""
    hidden: bool = False
    favorite: bool = False

    def get_absolute_path(self, project_root: str) -> str:
        """Returns the absolute path.

        Protects against path traversal attacks.
        """
        root = Path(project_root).resolve()
        # Strip leading slashes to ensure it's treated as relative path
        # (a leading "/" would make Path treat it as absolute on Windows)
        relative = self.relative_path.lstrip("/").lstrip("\\")
        abs_path = (root / relative).resolve()

        # SECURITY: Check that path stays within project_root
        try:
            abs_path.relative_to(root)
        except ValueError:
            # Path traversal attempt - fallback to project_root
            return str(root)

        return str(abs_path)

    def to_dict(self) -> dict:
        """Serializes the project to a dictionary."""
        return asdict(self)

    def to_sync_project(self) -> SyncProject:
        """Converts to SyncProject for export."""
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
        """Creates Project from SyncProject."""
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
        """Creates Project from dictionary with backwards compatibility."""
        # Migration: Old 'path' to 'relative_path'
        if "path" in data and "relative_path" not in data:
            # Try to extract relative path
            old_path = data["path"]
            # Use only the last folder name as relative path
            data["relative_path"] = Path(old_path).name

        defaults = {
            "relative_path": "",
            "description": "",
            "category": "General",
            "default_provider": "claude",
            "custom_start_command": "",
            "hidden": False,
            "favorite": False,
        }
        for key, default_val in defaults.items():
            if key not in data:
                data[key] = default_val

        # Only take known fields
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
    """Local configuration (NOT synced)."""

    # Paths
    project_root: str = ""  # Root directory for projects
    sync_path: str = ""  # Path to sync folder (Google Drive etc.)

    # Provider (local because paths are system-specific)
    providers: list[LLMProvider] = field(default_factory=list)

    # UI settings
    terminal_command: str = "gnome-terminal"
    default_start_command: str = "./start.sh"
    window_width: int = 800
    window_height: int = 600
    last_provider: str = "claude"
    show_hidden: bool = False
    language: str = "en"  # UI language (en, de)

    def __post_init__(self):
        """Sets default values for empty configurations."""
        if not self.providers:
            self.providers = get_initial_providers()
        if not self.project_root:
            # Default: ~/projekte or ~/projects
            default_root = Path.home() / "projekte"
            if not default_root.exists():
                default_root = Path.home() / "projects"
            if not default_root.exists():
                default_root = Path.home() / "projekte"
            self.project_root = str(default_root)

    def get_provider(self, provider_id: str) -> LLMProvider | None:
        """Returns a provider by ID."""
        for p in self.providers:
            if p.id == provider_id:
                return p
        return None

    def get_enabled_providers(self) -> list[LLMProvider]:
        """Returns all enabled providers."""
        return [p for p in self.providers if p.enabled]

    def to_dict(self) -> dict:
        """Serializes the local configuration to a dictionary."""
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
            "language": self.language,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LocalConfig":
        """Creates a LocalConfig from a dictionary."""
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
            language=data.get("language", "en"),
        )


@dataclass
class Config:
    """Main configuration - combines local and projects."""

    local: LocalConfig = field(default_factory=LocalConfig)
    projects: list[Project] = field(default_factory=list)

    # Convenience properties for backwards compatibility
    @property
    def providers(self) -> list[LLMProvider]:
        """Returns the provider list."""
        return self.local.providers

    @property
    def terminal_command(self) -> str:
        """Returns the configured terminal command."""
        return self.local.terminal_command

    @property
    def default_start_command(self) -> str:
        """Returns the default start command."""
        return self.local.default_start_command

    @property
    def window_width(self) -> int:
        """Returns the current window width."""
        return self.local.window_width

    @window_width.setter
    def window_width(self, value: int):
        self.local.window_width = value

    @property
    def window_height(self) -> int:
        """Returns the current window height."""
        return self.local.window_height

    @window_height.setter
    def window_height(self, value: int):
        self.local.window_height = value

    @property
    def last_provider(self) -> str:
        """Returns the last used provider."""
        return self.local.last_provider

    @last_provider.setter
    def last_provider(self, value: str):
        self.local.last_provider = value

    @property
    def show_hidden(self) -> bool:
        """Returns whether hidden projects are shown."""
        return self.local.show_hidden

    @show_hidden.setter
    def show_hidden(self, value: bool):
        self.local.show_hidden = value

    @property
    def language(self) -> str:
        """Returns the UI language."""
        return self.local.language

    @language.setter
    def language(self, value: str):
        self.local.language = value

    @property
    def project_root(self) -> str:
        """Returns the project root directory."""
        return self.local.project_root

    @property
    def sync_path(self) -> str:
        """Returns the sync path."""
        return self.local.sync_path

    def get_provider(self, provider_id: str) -> LLMProvider | None:
        """Returns a provider by ID."""
        return self.local.get_provider(provider_id)

    def get_enabled_providers(self) -> list[LLMProvider]:
        """Returns all enabled providers."""
        return self.local.get_enabled_providers()

    def get_provider_command(self, provider_id: str) -> str:
        """Returns the CLI command of the provider."""
        provider = self.get_provider(provider_id)
        return provider.command if provider else ""

    def is_provider_enabled(self, provider_id: str) -> bool:
        """Checks if the provider is enabled."""
        provider = self.get_provider(provider_id)
        return provider.enabled if provider else False

    def get_skip_permissions(self, provider_id: str) -> bool:
        """Checks if the provider has a skip-permissions flag."""
        provider = self.get_provider(provider_id)
        return bool(provider and provider.skip_permissions_flag)

    def add_provider(self, provider: LLMProvider):
        """Adds a new provider."""
        if self.get_provider(provider.id):
            raise ValueError(f"Provider with ID '{provider.id}' already exists")
        self.local.providers.append(provider)

    def update_provider(self, provider_id: str, updated: LLMProvider):
        """Updates an existing provider."""
        for i, p in enumerate(self.local.providers):
            if p.id == provider_id:
                self.local.providers[i] = updated
                return
        raise ValueError(f"Provider '{provider_id}' not found")

    def remove_provider(self, provider_id: str):
        """Removes a provider by ID."""
        self.local.providers = [p for p in self.local.providers if p.id != provider_id]

    def get_start_command(self, project: Project) -> str:
        """Returns the start command for a project."""
        if project.custom_start_command:
            return project.custom_start_command
        return self.local.default_start_command

    def get_project_absolute_path(self, project: Project) -> str:
        """Returns the absolute path of a project."""
        return project.get_absolute_path(self.local.project_root)


def ensure_config_dir():
    """Ensures that the configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _migrate_old_config() -> dict | None:
    """Migrates old configuration if present."""
    for old_dir in OLD_CONFIG_DIRS:
        old_file = old_dir / "config.json"
        if old_file.exists():
            try:
                with open(old_file, encoding="utf-8") as f:
                    return json.load(f)  # type: ignore[no-any-return]
            except (OSError, json.JSONDecodeError):
                # Old config not readable - skip
                pass
    return None


def load_config() -> Config:
    """Loads the configuration."""
    ensure_config_dir()

    local_config = LocalConfig()
    projects = []

    # Try to load local config
    if LOCAL_CONFIG_FILE.exists():
        try:
            with open(LOCAL_CONFIG_FILE, encoding="utf-8") as f:
                data = json.load(f)
                local_config = LocalConfig.from_dict(data.get("local", data))
                projects = [Project.from_dict(p) for p in data.get("projects", [])]
        except OSError as e:
            print(f"Error reading configuration file: {e}")
        except json.JSONDecodeError as e:
            print(f"Error parsing configuration (invalid JSON): {e}")
        except (KeyError, TypeError, ValueError) as e:
            print(f"Error processing configuration data: {e}")
    else:
        # Migration from old config
        old_data = _migrate_old_config()
        if old_data:
            print("Migrating old configuration...")

            # Extract project_root from first project
            old_projects = old_data.get("projects", [])
            if old_projects:
                first_path = old_projects[0].get("path", "")
                if first_path:
                    local_config.project_root = str(Path(first_path).parent)

            # Migrate providers
            if "providers" in old_data:
                local_config.providers = [
                    LLMProvider.from_dict(p) for p in old_data["providers"]
                ]

            # Other settings
            local_config.terminal_command = old_data.get("terminal_command", "gnome-terminal")
            local_config.default_start_command = old_data.get(
                "default_start_command", "./start.sh"
            )
            local_config.window_width = old_data.get("window_width", 800)
            local_config.window_height = old_data.get("window_height", 600)
            local_config.last_provider = old_data.get("last_provider", "claude")
            local_config.show_hidden = old_data.get("show_hidden", False)

            # Migrate projects
            projects = [Project.from_dict(p) for p in old_projects]

            # Save in new format
            config = Config(local=local_config, projects=projects)
            save_config(config)

    return Config(local=local_config, projects=projects)


def save_config(config: Config):
    """Saves the configuration."""
    ensure_config_dir()

    data = {
        "local": config.local.to_dict(),
        "projects": [p.to_dict() for p in config.projects],
    }

    with open(LOCAL_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_project(config: Config, project: Project) -> Config:
    """Adds a project."""
    config.projects.append(project)
    save_config(config)
    return config


def remove_project(config: Config, index: int) -> Config:
    """Removes a project by index."""
    if 0 <= index < len(config.projects):
        config.projects.pop(index)
        save_config(config)
    return config


def update_project(config: Config, index: int, project: Project) -> Config:
    """Updates a project."""
    if 0 <= index < len(config.projects):
        config.projects[index] = project
        save_config(config)
    return config


# === Sync functions ===

# Secret store for sync password
try:
    from cindergrace_common import SecretStore

    _secret_store = SecretStore("cindergrace-launcher", warn_on_fallback=False)
except ImportError:
    _secret_store = None


def get_sync_password() -> str | None:
    """Gets sync password from OS keyring (via cindergrace_common.SecretStore)."""
    if _secret_store:
        return _secret_store.get("sync_password")  # type: ignore[no-any-return]

    # Fallback without cindergrace_common
    try:
        import keyring

        return keyring.get_password("cindergrace-launcher", "sync")
    except ImportError:
        return None
    except OSError:
        # Keyring backend not available
        return None


def set_sync_password(password: str):
    """Saves sync password in OS keyring (via cindergrace_common.SecretStore)."""
    if _secret_store:
        success = _secret_store.set("sync_password", password)
        if not success:
            print(
                "Note: Password stored in environment variable (keyring not available)"
            )
        return

    # Fallback without cindergrace_common
    try:
        import keyring

        keyring.set_password("cindergrace-launcher", "sync", password)
    except ImportError:
        print("Error: Neither cindergrace_common nor keyring available")
    except OSError as e:
        print(f"Keyring not available: {e}")


def export_to_sync(config: Config) -> tuple[bool, str]:
    """Exports projects to sync file."""
    if not config.sync_path:
        return False, "No sync path configured"

    password = get_sync_password()
    if not password:
        return False, "No sync password configured"

    sync_mgr = SyncManager(config.sync_path, password)
    sync_projects = [p.to_sync_project() for p in config.projects]

    if sync_mgr.export_projects(sync_projects):
        return True, f"{len(sync_projects)} projects exported"
    return False, "Export failed"


def import_from_sync(config: Config) -> tuple[bool, str]:
    """Imports projects from sync file."""
    if not config.sync_path:
        return False, "No sync path configured"

    password = get_sync_password()
    if not password:
        return False, "No sync password configured"

    sync_mgr = SyncManager(config.sync_path, password)

    if not sync_mgr.sync_file_exists():
        return False, "No sync file found"

    sync_projects = sync_mgr.import_projects()
    if sync_projects is None:
        return False, "Wrong password or corrupt file"

    # Update projects
    config.projects = [Project.from_sync_project(sp) for sp in sync_projects]
    save_config(config)

    return True, f"{len(sync_projects)} projects imported"
