"""Sync module for Cindergrace Launcher.

AES-encrypted synchronization of project data.
"""

import json
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SYNC_FILENAME = "launcher_sync.enc"
SALT_SIZE = 16
NONCE_SIZE = 12
KDF_ITERATIONS = 100000


def derive_key(password: str, salt: bytes) -> bytes:
    """Derives a 256-bit AES key from password using PBKDF2HMAC."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_data(data: dict, password: str) -> bytes:
    """Encrypts data using AES-GCM."""
    # Generate random salt and nonce
    salt = secrets.token_bytes(SALT_SIZE)
    nonce = secrets.token_bytes(NONCE_SIZE)

    # Derive key
    key = derive_key(password, salt)

    # Serialize data to JSON
    plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")

    # Encrypt with AES-GCM (authenticated encryption)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    # Format: salt (16) + nonce (12) + ciphertext
    return salt + nonce + ciphertext


def decrypt_data(encrypted: bytes, password: str) -> dict | None:
    """Decrypts data using AES-GCM."""
    if len(encrypted) < SALT_SIZE + NONCE_SIZE + 16:  # Minimum 16 bytes ciphertext
        return None

    # Extract salt, nonce, and ciphertext
    salt = encrypted[:SALT_SIZE]
    nonce = encrypted[SALT_SIZE : SALT_SIZE + NONCE_SIZE]
    ciphertext = encrypted[SALT_SIZE + NONCE_SIZE :]

    # Derive key
    key = derive_key(password, salt)

    try:
        # Decrypt
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)

        # Parse JSON
        return json.loads(plaintext.decode("utf-8"))  # type: ignore[no-any-return]
    except (
        # Cryptography: Wrong password or corrupt data
        # InvalidTag is raised by AES-GCM when authentication fails
        Exception  # cryptography.exceptions.InvalidTag + json.JSONDecodeError + UnicodeDecodeError
    ):
        # Note: We catch broadly here because:
        # - cryptography.exceptions.InvalidTag on wrong password
        # - json.JSONDecodeError on corrupt plaintext
        # - UnicodeDecodeError on corrupt bytes
        # All mean: decryption failed
        return None


@dataclass
class SyncProject:
    """Project data for sync (without local paths)."""

    name: str
    relative_path: str  # Relative path from project_root
    description: str = ""
    category: str = "General"
    default_provider: str = "claude"
    custom_start_command: str = ""
    hidden: bool = False
    favorite: bool = False

    def to_dict(self) -> dict:
        """Serializes the sync project to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SyncProject":
        """Creates a SyncProject from a dictionary."""
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
        # Defaults für fehlende Felder
        defaults = {
            "description": "",
            "category": "General",
            "default_provider": "claude",
            "custom_start_command": "",
            "hidden": False,
            "favorite": False,
        }
        for k, v in defaults.items():
            if k not in filtered:
                filtered[k] = v
        return cls(**filtered)


@dataclass
class SyncData:
    """Container for all synced data."""

    projects: list  # List of SyncProject dicts
    version: int = 1

    def to_dict(self) -> dict:
        """Serializes sync data to a dictionary."""
        return {"version": self.version, "projects": self.projects}

    @classmethod
    def from_dict(cls, data: dict) -> "SyncData":
        """Creates SyncData from a dictionary."""
        return cls(projects=data.get("projects", []), version=data.get("version", 1))


class SyncManager:
    """Manages sync operations."""

    def __init__(self, sync_path: str, password: str):
        """Initializes the SyncManager."""
        self.sync_path = Path(sync_path)
        self.password = password
        self.sync_file = self.sync_path / SYNC_FILENAME

    def is_configured(self) -> bool:
        """Checks if sync is configured."""
        return bool(self.sync_path) and bool(self.password)

    def _find_sync_file(self) -> Path | None:
        """Finds the sync file in the folder.

        First checks the standard filename, then searches for encrypted
        files (fallback for GVFS/Google Drive which may change filenames).
        """
        # Check standard path
        if self.sync_file.exists():
            return self.sync_file

        # GVFS fallback: Search all files and try to decrypt
        # Google Drive GVFS uses file IDs instead of filenames
        if not self.sync_path.exists():
            return None

        try:
            for file_path in self.sync_path.iterdir():
                if not file_path.is_file():
                    continue
                # Only check files with suitable size (min 44 bytes: salt+nonce+min ciphertext)
                try:
                    if file_path.stat().st_size < 44:
                        continue
                    # Try to decrypt
                    encrypted = file_path.read_bytes()
                    data = decrypt_data(encrypted, self.password)
                    if data and "projects" in data and "version" in data:
                        return file_path
                except (OSError, PermissionError):
                    continue
        except OSError:
            pass

        return None

    def sync_file_exists(self) -> bool:
        """Checks if sync file exists."""
        return self._find_sync_file() is not None

    def export_projects(self, projects: list[SyncProject]) -> bool:
        """Exports projects to encrypted sync file."""
        if not self.is_configured():
            return False

        try:
            # Create sync folder if needed
            self.sync_path.mkdir(parents=True, exist_ok=True)

            # Prepare data
            sync_data = SyncData(
                projects=[p.to_dict() if hasattr(p, "to_dict") else p for p in projects]
            )

            # Encrypt and save
            encrypted = encrypt_data(sync_data.to_dict(), self.password)
            self.sync_file.write_bytes(encrypted)

            return True
        except OSError as e:
            print(f"Sync export file error: {e}")
            return False
        except (TypeError, ValueError) as e:
            print(f"Sync export serialization error: {e}")
            return False

    def import_projects(self) -> list[SyncProject] | None:
        """Imports projects from encrypted sync file."""
        if not self.is_configured():
            return None

        # Find sync file (supports GVFS fallback)
        sync_file = self._find_sync_file()
        if not sync_file:
            return None

        try:
            # Read and decrypt
            encrypted = sync_file.read_bytes()
            data = decrypt_data(encrypted, self.password)

            if data is None:
                return None  # Wrong password

            sync_data = SyncData.from_dict(data)
            return [SyncProject.from_dict(p) for p in sync_data.projects]
        except OSError as e:
            print(f"Sync import file error: {e}")
            return None
        except (KeyError, TypeError, ValueError) as e:
            print(f"Sync import data format error: {e}")
            return None

    def test_password(self) -> bool:
        """Tests if the password is correct."""
        if not self.sync_file_exists():
            return True  # No file = password OK (will be created)

        result = self.import_projects()
        return result is not None
