# Cindergrace Launcher

**Status:** Final

> **Note:** This is a hobby/experimental project. Use at your own risk.

**Cross-platform GUI for managing LLM CLI sessions across multiple projects.**

Built with PySide6 (Qt6), runs on Windows, macOS, and Linux.

**Supported LLM CLIs:**
- Claude Code (Anthropic)
- Codex CLI (OpenAI)
- Gemini CLI (Google)
- Additional providers configurable

## Features

- **Cross-Platform**: Windows, macOS, and Linux
- **Multi-Provider**: Flexibly switch between Claude, Codex, and Gemini
- **Project Management**: Add, edit, and remove projects
- **Session Control**: Start and stop LLM CLI sessions
- **Provider Selection**: Choose your preferred provider at startup
- **Status Display**: Overview of running sessions with provider info
- **Window Focus**: Bring running terminal windows to foreground (Linux)
- **Categories**: Organize projects by categories
- **Sync**: Synchronize configuration encrypted via cloud services
- **Configurable**: Terminal command and CLI paths customizable per provider

## Requirements

- Python 3.10+
- PySide6 (Qt6)
- At least one LLM CLI installed:
  - Claude CLI: `npm install -g @anthropic-ai/claude-code`
  - Codex CLI: `npm install -g @openai/codex`
  - Gemini CLI: `npm install -g @google/gemini-cli`

### Linux

```bash
# Optional for window focus
sudo apt install wmctrl xdotool
```

### Windows

- Windows Terminal recommended (automatically detected if available)

### macOS

- Terminal.app is used automatically

## Installation

### Via pip (recommended)

```bash
pip install cindergrace-launcher
```

### From Source

```bash
git clone https://github.com/goettemar/cindergrace-launcher
cd cindergrace-launcher
pip install -e .
```

## Usage

### Starting

```bash
# After pip install
cindergrace-launcher

# Or from project directory
./start.sh       # Linux/macOS
start.bat        # Windows
```

### Managing Projects

- **Add**: Click the `+` button
- **Edit**: Click the pencil icon
- **Remove**: Click the trash icon

### Controlling Sessions

- **Start**: Play icon - opens dropdown for provider selection
- **Stop**: Stop icon (red) - only for running sessions
- **Focus**: Window icon - brings terminal to foreground (Linux)

### Switching Providers

The provider can be flexibly chosen when starting a session:
1. Click the play icon
2. Select provider from dropdown (Claude, Codex, Gemini)

## Configuration

Stored at:
- Linux: `~/.config/cindergrace-launcher/config.json`
- Windows: `%APPDATA%/cindergrace-launcher/config.json`
- macOS: `~/Library/Application Support/cindergrace-launcher/config.json`

### General Settings

| Setting          | Default (Linux)   | Default (Windows) |
|------------------|-------------------|-------------------|
| Terminal Command | gnome-terminal    | wt / cmd          |

### Provider Settings (per provider)

| Setting      | Description                           |
|--------------|---------------------------------------|
| Enabled      | Show provider in selection            |
| CLI Command  | Path/command to CLI tool              |
| Skip Flag    | Automatic confirmation                |

### Default Providers

| Provider | Default Command | Auto Flag                         |
|----------|-----------------|-----------------------------------|
| Claude   | claude          | --dangerously-skip-permissions    |
| Codex    | codex           | --full-auto                       |
| Gemini   | gemini          | --yolo                            |

## Project Structure

```
cindergrace-launcher/
├── src/cindergrace_launcher/
│   ├── __init__.py
│   ├── __main__.py        # python -m entry point
│   ├── main.py            # Qt App initialization
│   ├── cockpit.py         # Main window and UI (PySide6)
│   ├── dialogs.py         # Dialogs (PySide6)
│   ├── config.py          # Configuration management
│   ├── sync.py            # Encrypted sync function
│   ├── process_manager.py # Cross-platform session management
│   └── providers.py       # LLM Provider definitions
├── start.sh               # Linux/macOS starter
├── start.bat              # Windows starter
├── pyproject.toml         # Python package definition
└── README.md
```

## Sync Function

The configuration can be synchronized encrypted via cloud services (Google Drive, Dropbox, etc.):

1. Configure sync folder in settings
2. Set password for encryption
3. "Export" to save / "Import" to load

The sync file is AES-256 encrypted.

## Adding More Providers

Providers are defined in `src/cindergrace_launcher/providers.py`. Or configurable via the GUI settings.

## Known Limitations

- **Windows**: Window focus not supported
- **Wayland**: Window focus may not work on Linux

## License

MIT License
