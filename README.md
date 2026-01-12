# Cindergrace Launcher

**Status:** Final


**Cross-Platform GUI zur Verwaltung von LLM CLI Sessions für verschiedene Projekte.**

Basiert auf PySide6 (Qt6) und läuft auf Windows, macOS und Linux.

**Unterstützte LLM CLIs:**
- Claude Code (Anthropic)
- Codex CLI (OpenAI)
- Gemini CLI (Google)
- Weitere Provider konfigurierbar

## Features

- **Cross-Platform**: Windows, macOS und Linux
- **Multi-Provider**: Flexibel zwischen Claude, Codex und Gemini wechseln
- **Projektverwaltung**: Projekte hinzufügen, bearbeiten und entfernen
- **Session-Steuerung**: LLM CLI Sessions starten und beenden
- **Provider-Auswahl**: Beim Start den gewünschten Provider wählen
- **Status-Anzeige**: Übersicht über laufende Sessions mit Provider-Info
- **Fenster-Fokus**: Laufende Terminal-Fenster in den Vordergrund bringen (Linux)
- **Kategorien**: Projekte nach Kategorien organisieren
- **Sync**: Konfiguration verschlüsselt über Cloud-Dienste synchronisieren
- **Konfigurierbar**: Terminal-Befehl und CLI-Pfade pro Provider anpassbar

## Voraussetzungen

- Python 3.10+
- PySide6 (Qt6)
- Mindestens ein LLM CLI installiert:
  - Claude CLI: `npm install -g @anthropic-ai/claude-code`
  - Codex CLI: `npm install -g @openai/codex`
  - Gemini CLI: `npm install -g @anthropic/gemini-cli`

### Linux

```bash
# Optional für Fenster-Fokus
sudo apt install wmctrl xdotool
```

### Windows

- Windows Terminal empfohlen (automatisch erkannt wenn vorhanden)

### macOS

- Terminal.app wird automatisch verwendet

## Installation

### Via pip (empfohlen)

```bash
pip install cindergrace-launcher
```

### Aus Source

```bash
git clone https://github.com/goettemar/cindergrace-launcher
cd cindergrace-launcher
pip install -e .
```

## Nutzung

### Starten

```bash
# Nach pip install
cindergrace-launcher

# Oder aus dem Projektverzeichnis
./start.sh       # Linux/macOS
start.bat        # Windows
```

### Projekte verwalten

- **Hinzufügen**: Klick auf `+` Button
- **Bearbeiten**: Klick auf das Stift-Symbol
- **Entfernen**: Klick auf das Papierkorb-Symbol

### Sessions steuern

- **Starten**: Play-Symbol - öffnet Dropdown zur Provider-Auswahl
- **Stoppen**: Stop-Symbol (rot) - nur bei laufenden Sessions
- **Fokussieren**: Fenster-Symbol - bringt Terminal in den Vordergrund (Linux)

### Provider wechseln

Der Provider kann flexibel beim Starten einer Session gewählt werden:
1. Klick auf Play-Symbol
2. Provider aus dem Dropdown wählen (Claude, Codex, Gemini)

## Konfiguration

Gespeichert unter:
- Linux: `~/.config/cindergrace-launcher/config.json`
- Windows: `%APPDATA%/cindergrace-launcher/config.json`
- macOS: `~/Library/Application Support/cindergrace-launcher/config.json`

### Allgemeine Einstellungen

| Einstellung     | Standard (Linux)  | Standard (Windows)  |
|-----------------|-------------------|---------------------|
| Terminal-Befehl | gnome-terminal    | wt / cmd            |

### Provider-Einstellungen (pro Provider)

| Einstellung       | Beschreibung                          |
|-------------------|---------------------------------------|
| Aktiviert         | Provider in der Auswahl anzeigen      |
| CLI Befehl        | Pfad/Befehl zum CLI-Tool              |
| Skip-Flag         | Automatische Bestätigung              |

### Standard Provider

| Provider | Standard-Befehl              | Auto-Flag                         |
|----------|------------------------------|-----------------------------------|
| Claude   | claude                       | --dangerously-skip-permissions    |
| Codex    | codex                        | --full-auto                       |
| Gemini   | gemini                       | --yolo                            |

## Projektstruktur

```
cindergrace-launcher/
├── src/cindergrace_launcher/
│   ├── __init__.py
│   ├── __main__.py        # python -m Einstieg
│   ├── main.py            # Qt App Initialisierung
│   ├── cockpit.py         # Hauptfenster und UI (PySide6)
│   ├── dialogs.py         # Dialoge (PySide6)
│   ├── config.py          # Konfigurationsverwaltung
│   ├── sync.py            # Verschlüsselte Sync-Funktion
│   ├── process_manager.py # Cross-Platform Session-Verwaltung
│   └── providers.py       # LLM Provider Definitionen
├── start.sh               # Linux/macOS Starter
├── start.bat              # Windows Starter
├── pyproject.toml         # Python Package Definition
└── README.md
```

## Sync-Funktion

Die Konfiguration kann verschlüsselt über Cloud-Dienste (Google Drive, Dropbox, etc.) synchronisiert werden:

1. Sync-Ordner in den Einstellungen konfigurieren
2. Passwort für Verschlüsselung setzen
3. "Exportieren" zum Speichern / "Importieren" zum Laden

Die Sync-Datei ist AES-256 verschlüsselt.

## Weitere Provider hinzufügen

Provider sind in `src/cindergrace_launcher/providers.py` definiert. Oder über die Einstellungen der GUI konfigurierbar.

## Bekannte Einschränkungen

- **Windows**: Fenster-Fokussierung nicht unterstützt
- **Wayland**: Fenster-Fokus funktioniert möglicherweise nicht auf Linux

## Lizenz

MIT License
