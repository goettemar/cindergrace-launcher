# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-01-12

### Added
- Provider management in settings dialog
- Single-instance support (only one launcher window)
- Scanner tool configurations (bandit, pydocstyle, mypy, coverage, radon)

### Fixed
- Project save dialog now works correctly with callback pattern
- Security: nosec markers for subprocess calls (B404, B603, B607)
- Type annotations with ignore markers for platform-specific code
- Updated cryptography to 44.0.1 (CVE fixes)

### Changed
- Improved code quality configuration per FAQ guidelines

## [1.0.0] - 2025-12-01

### Added
- Initial release
- Cross-platform GUI for LLM CLI management (Claude, Codex, Gemini)
- Project management with categories
- Terminal session launching and management
- Configuration sync with encryption
- PySide6-based modern UI
