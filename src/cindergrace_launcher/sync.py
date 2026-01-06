"""
Sync-Modul für Cindergrace Launcher
AES-verschlüsselte Synchronisation von Projektdaten
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
    """Leitet einen 256-bit AES-Key vom Passwort ab (PBKDF2HMAC)"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(password.encode('utf-8'))


def encrypt_data(data: dict, password: str) -> bytes:
    """Verschlüsselt Daten mit AES-GCM"""
    # Zufälliges Salt und Nonce generieren
    salt = secrets.token_bytes(SALT_SIZE)
    nonce = secrets.token_bytes(NONCE_SIZE)

    # Key ableiten
    key = derive_key(password, salt)

    # Daten zu JSON serialisieren
    plaintext = json.dumps(data, ensure_ascii=False).encode('utf-8')

    # Verschlüsseln mit AES-GCM (authentifizierte Verschlüsselung)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    # Format: salt (16) + nonce (12) + ciphertext
    return salt + nonce + ciphertext


def decrypt_data(encrypted: bytes, password: str) -> dict | None:
    """Entschlüsselt Daten mit AES-GCM"""
    if len(encrypted) < SALT_SIZE + NONCE_SIZE + 16:  # Mindestens 16 Bytes Ciphertext
        return None

    # Salt, Nonce und Ciphertext extrahieren
    salt = encrypted[:SALT_SIZE]
    nonce = encrypted[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
    ciphertext = encrypted[SALT_SIZE + NONCE_SIZE:]

    # Key ableiten
    key = derive_key(password, salt)

    try:
        # Entschlüsseln
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)

        # JSON parsen
        return json.loads(plaintext.decode('utf-8'))
    except (
        # Cryptography: Falsches Passwort oder korrupte Daten
        # InvalidTag wird bei AES-GCM geworfen wenn Authentifizierung fehlschlägt
        Exception  # cryptography.exceptions.InvalidTag + json.JSONDecodeError + UnicodeDecodeError
    ):
        # Hinweis: Wir fangen hier absichtlich breit, da:
        # - cryptography.exceptions.InvalidTag bei falschem Passwort
        # - json.JSONDecodeError bei korruptem Plaintext
        # - UnicodeDecodeError bei korrupten Bytes
        # Alle bedeuten: Entschlüsselung fehlgeschlagen
        return None


@dataclass
class SyncProject:
    """Projekt-Daten für Sync (ohne lokale Pfade)"""
    name: str
    relative_path: str  # Relativer Pfad vom project_root
    description: str = ""
    category: str = "Allgemein"
    default_provider: str = "claude"
    custom_start_command: str = ""
    hidden: bool = False
    favorite: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'SyncProject':
        known_fields = {'name', 'relative_path', 'description', 'category',
                       'default_provider', 'custom_start_command', 'hidden', 'favorite'}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        # Defaults für fehlende Felder
        defaults = {
            'description': '',
            'category': 'Allgemein',
            'default_provider': 'claude',
            'custom_start_command': '',
            'hidden': False,
            'favorite': False
        }
        for k, v in defaults.items():
            if k not in filtered:
                filtered[k] = v
        return cls(**filtered)


@dataclass
class SyncData:
    """Container für alle gesynchten Daten"""
    projects: list  # Liste von SyncProject dicts
    version: int = 1

    def to_dict(self) -> dict:
        return {
            'version': self.version,
            'projects': self.projects
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SyncData':
        return cls(
            projects=data.get('projects', []),
            version=data.get('version', 1)
        )


class SyncManager:
    """Verwaltet Sync-Operationen"""

    def __init__(self, sync_path: str, password: str):
        self.sync_path = Path(sync_path)
        self.password = password
        self.sync_file = self.sync_path / SYNC_FILENAME

    def is_configured(self) -> bool:
        """Prüft ob Sync konfiguriert ist"""
        return bool(self.sync_path) and bool(self.password)

    def _find_sync_file(self) -> Path | None:
        """
        Findet die Sync-Datei im Ordner.

        Prüft zuerst den Standard-Dateinamen, dann sucht nach verschlüsselten
        Dateien (Fallback für GVFS/Google Drive die Dateinamen ändern).
        """
        # Standard-Pfad prüfen
        if self.sync_file.exists():
            return self.sync_file

        # GVFS-Fallback: Alle Dateien durchsuchen und versuchen zu entschlüsseln
        # Google Drive GVFS nutzt File-IDs statt Dateinamen
        if not self.sync_path.exists():
            return None

        try:
            for file_path in self.sync_path.iterdir():
                if not file_path.is_file():
                    continue
                # Nur Dateien mit passender Größe prüfen (min 44 Bytes: salt+nonce+min ciphertext)
                try:
                    if file_path.stat().st_size < 44:
                        continue
                    # Versuchen zu entschlüsseln
                    encrypted = file_path.read_bytes()
                    data = decrypt_data(encrypted, self.password)
                    if data and 'projects' in data and 'version' in data:
                        return file_path
                except (OSError, PermissionError):
                    continue
        except OSError:
            pass

        return None

    def sync_file_exists(self) -> bool:
        """Prüft ob Sync-Datei existiert"""
        return self._find_sync_file() is not None

    def export_projects(self, projects: list[SyncProject]) -> bool:
        """Exportiert Projekte in verschlüsselte Sync-Datei"""
        if not self.is_configured():
            return False

        try:
            # Sync-Ordner erstellen falls nötig
            self.sync_path.mkdir(parents=True, exist_ok=True)

            # Daten vorbereiten
            sync_data = SyncData(
                projects=[p.to_dict() if hasattr(p, 'to_dict') else p for p in projects]
            )

            # Verschlüsseln und speichern
            encrypted = encrypt_data(sync_data.to_dict(), self.password)
            self.sync_file.write_bytes(encrypted)

            return True
        except OSError as e:
            print(f"Sync-Export Dateifehler: {e}")
            return False
        except (TypeError, ValueError) as e:
            print(f"Sync-Export Serialisierungsfehler: {e}")
            return False

    def import_projects(self) -> list[SyncProject] | None:
        """Importiert Projekte aus verschlüsselter Sync-Datei"""
        if not self.is_configured():
            return None

        # Sync-Datei finden (unterstützt GVFS-Fallback)
        sync_file = self._find_sync_file()
        if not sync_file:
            return None

        try:
            # Lesen und entschlüsseln
            encrypted = sync_file.read_bytes()
            data = decrypt_data(encrypted, self.password)

            if data is None:
                return None  # Falsches Passwort

            sync_data = SyncData.from_dict(data)
            return [SyncProject.from_dict(p) for p in sync_data.projects]
        except OSError as e:
            print(f"Sync-Import Dateifehler: {e}")
            return None
        except (KeyError, TypeError, ValueError) as e:
            print(f"Sync-Import Datenformat-Fehler: {e}")
            return None

    def test_password(self) -> bool:
        """Testet ob das Passwort korrekt ist"""
        if not self.sync_file_exists():
            return True  # Keine Datei = Passwort OK (wird neu erstellt)

        result = self.import_projects()
        return result is not None
