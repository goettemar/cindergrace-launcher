"""
Sync-Modul für Cindergrace Launcher
AES-verschlüsselte Synchronisation von Projektdaten
"""

import json
import os
import hashlib
import secrets
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SYNC_FILENAME = "launcher_sync.enc"
SALT_SIZE = 16
NONCE_SIZE = 12


def derive_key(password: str, salt: bytes) -> bytes:
    """Leitet einen 256-bit AES-Key vom Passwort ab (PBKDF2-ähnlich)"""
    # Einfache aber sichere Key-Ableitung mit mehreren Runden
    key = password.encode('utf-8') + salt
    for _ in range(100000):  # 100k Iterationen
        key = hashlib.sha256(key).digest()
    return key


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


def decrypt_data(encrypted: bytes, password: str) -> Optional[dict]:
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

    def sync_file_exists(self) -> bool:
        """Prüft ob Sync-Datei existiert"""
        return self.sync_file.exists()

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

    def import_projects(self) -> Optional[list[SyncProject]]:
        """Importiert Projekte aus verschlüsselter Sync-Datei"""
        if not self.is_configured() or not self.sync_file_exists():
            return None

        try:
            # Lesen und entschlüsseln
            encrypted = self.sync_file.read_bytes()
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
