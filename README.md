# LLM Cockpit

Eine GTK4/Adwaita-basierte GUI zur Verwaltung von LLM CLI Sessions für verschiedene Projekte.

**Unterstützte LLM CLIs:**
- Claude Code (Anthropic)
- Codex CLI (OpenAI)
- Gemini CLI (Google)

## Features

- **Multi-Provider**: Flexibel zwischen Claude, Codex und Gemini wechseln
- **Projektverwaltung**: Projekte hinzufügen, bearbeiten und entfernen
- **Session-Steuerung**: LLM CLI Sessions starten und beenden
- **Provider-Auswahl**: Beim Start den gewünschten Provider wählen
- **Status-Anzeige**: Übersicht über laufende Sessions mit Provider-Info
- **Fenster-Fokus**: Laufende Terminal-Fenster in den Vordergrund bringen
- **Kategorien**: Projekte nach Kategorien organisieren
- **Konfigurierbar**: Terminal-Befehl und CLI-Pfade pro Provider anpassbar

## Voraussetzungen

- Python 3.10+
- GTK 4
- libadwaita
- gnome-terminal (oder alternatives Terminal)
- Mindestens ein LLM CLI installiert:
  - Claude CLI: `npm install -g @anthropic-ai/claude-code`
  - Codex CLI: `npm install -g @openai/codex`
  - Gemini CLI: `pip install google-generativeai`
- wmctrl (optional, für Fenster-Fokus)
- xdotool (optional, Fallback für Fenster-Fokus)

### Installation der Abhängigkeiten (Ubuntu/Debian)

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 wmctrl xdotool
```

## Installation

1. Repository klonen oder herunterladen:
```bash
git clone <repository-url>
cd llm-cockpit
```

2. Startskript ausführbar machen:
```bash
chmod +x start.sh
```

3. (Optional) Desktop-Eintrag installieren:
```bash
cp llm-cockpit.desktop ~/.local/share/applications/
```

## Nutzung

### Starten

```bash
./start.sh
```

### Projekte verwalten

- **Hinzufügen**: Klick auf `+` in der Headerbar
- **Bearbeiten**: Klick auf das Stift-Symbol
- **Entfernen**: Klick auf das Papierkorb-Symbol

### Sessions steuern

- **Starten**: Play-Symbol - öffnet Dropdown zur Provider-Auswahl
- **Stoppen**: Stop-Symbol (rot) - nur bei laufenden Sessions
- **Fokussieren**: Fenster-Symbol - bringt Terminal in den Vordergrund

### Provider wechseln

Der Provider kann flexibel beim Starten einer Session gewählt werden:
1. Klick auf Play-Symbol
2. Provider aus dem Dropdown wählen (Claude, Codex, Gemini)

## Konfiguration

Gespeichert unter: `~/.config/llm-cockpit/config.json`

### Allgemeine Einstellungen

| Einstellung     | Standard       |
|-----------------|----------------|
| Terminal-Befehl | gnome-terminal |

### Provider-Einstellungen (pro Provider)

| Einstellung       | Beschreibung                          |
|-------------------|---------------------------------------|
| Aktiviert         | Provider in der Auswahl anzeigen      |
| CLI Pfad          | Pfad zum CLI-Tool                     |
| Auto-Bestätigung  | Automatische Bestätigung (z.B. --dangerously-skip-permissions) |

### Standard-Pfade

| Provider | Standard-Pfad                    | Auto-Flag                         |
|----------|----------------------------------|-----------------------------------|
| Claude   | ~/.npm-global/bin/claude         | --dangerously-skip-permissions    |
| Codex    | codex                            | --full-auto                       |
| Gemini   | gemini                           | -                                 |

## Projektstruktur

```
llm-cockpit/
├── src/
│   ├── main.py            # Einstiegspunkt
│   ├── cockpit.py         # Hauptfenster und UI
│   ├── config.py          # Konfigurationsverwaltung
│   ├── process_manager.py # Session-Verwaltung
│   └── providers.py       # LLM Provider Definitionen
├── start.sh
├── llm-cockpit.desktop
└── README.md
```

## Migration von Claude Cockpit

Beim ersten Start wird die alte Konfiguration aus `~/.config/claude-cockpit/` automatisch migriert.

## Bekannte Einschränkungen

- Session-Erkennung basiert auf Terminal-PID (nicht immer zuverlässig bei gnome-terminal)
- Fenster-Fokus erfordert wmctrl oder xdotool (X11)
- Wayland: Fenster-Fokus funktioniert möglicherweise nicht

## Weitere Provider hinzufügen

Provider sind in `src/providers.py` definiert. Um einen neuen Provider hinzuzufügen:

```python
# In get_default_providers():
"aider": LLMProvider(
    id="aider",
    name="Aider",
    command="aider",
    icon="applications-development-symbolic",
    color="#FF6B6B",
    skip_permissions_flag="--yes",
    end_message="Aider beendet"
),
```

## Lizenz

MIT License
