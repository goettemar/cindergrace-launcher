"""
Dialog-Klassen für Cindergrace Launcher (PySide6 Version)
Ausgelagert aus cockpit.py für bessere Wartbarkeit
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QGroupBox, QScrollArea, QWidget, QFileDialog, QMessageBox,
    QDialogButtonBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from pathlib import Path
from typing import Optional, Callable
import os

from .config import Config, Project
from .providers import LLMProvider
from .process_manager import validate_command


# Gemeinsames Stylesheet für Dialoge
DIALOG_STYLE = """
QDialog {
    background-color: #1a1a2e;
}

QGroupBox {
    font-weight: bold;
    color: #e0e0e0;
    border: 1px solid #333;
    border-radius: 8px;
    margin-top: 16px;
    padding: 15px;
    padding-top: 25px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
    color: #ff6b35;
}

QLabel {
    color: #e0e0e0;
}

QLineEdit {
    background-color: #2a2a4e;
    border: 1px solid #444;
    border-radius: 4px;
    padding: 8px;
    color: #e0e0e0;
}

QLineEdit:focus {
    border-color: #ff6b35;
}

QLineEdit:disabled {
    background-color: #1a1a2e;
    color: #666;
}

QComboBox {
    background-color: #2a2a4e;
    border: 1px solid #444;
    border-radius: 4px;
    padding: 8px;
    color: #e0e0e0;
}

QComboBox:focus {
    border-color: #ff6b35;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #2a2a4e;
    border: 1px solid #444;
    color: #e0e0e0;
    selection-background-color: #ff6b35;
}

QCheckBox {
    color: #e0e0e0;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 3px;
    border: 1px solid #444;
    background-color: #2a2a4e;
}

QCheckBox::indicator:checked {
    background-color: #ff6b35;
    border-color: #ff6b35;
}

QPushButton {
    background-color: #2a2a4e;
    border: 1px solid #444;
    border-radius: 4px;
    padding: 8px 16px;
    color: #e0e0e0;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #3a3a5e;
    border-color: #ff6b35;
}

QPushButton:pressed {
    background-color: #ff6b35;
}

QPushButton#primary {
    background-color: #ff6b35;
    border-color: #ff6b35;
    color: white;
    font-weight: bold;
}

QPushButton#primary:hover {
    background-color: #ff8555;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}
"""


class ProjectDialog(QDialog):
    """Dialog zum Hinzufügen/Bearbeiten eines Projekts"""

    def __init__(
        self,
        parent,
        config: Config,
        project: Optional[Project] = None,
        on_save: Optional[Callable[[Project], None]] = None
    ):
        super().__init__(parent)
        self.config = config
        self.project = project
        self.on_save = on_save
        self.is_edit = project is not None

        self.setWindowTitle("Projekt bearbeiten" if self.is_edit else "Neues Projekt")
        self.setFixedSize(500, 580)
        self.setModal(True)
        self.setStyleSheet(DIALOG_STYLE)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Scrollbereich
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)

        # === Name ===
        name_group = QGroupBox("Projektname")
        name_layout = QVBoxLayout(name_group)

        self.name_entry = QLineEdit()
        self.name_entry.setPlaceholderText("Name des Projekts")
        if self.project:
            self.name_entry.setText(self.project.name)
        name_layout.addWidget(self.name_entry)

        scroll_layout.addWidget(name_group)

        # === Pfad ===
        path_group = QGroupBox("Projektordner")
        path_layout = QVBoxLayout(path_group)

        # Root-Info
        root_label = QLabel(f"Projekt-Root: {self.config.project_root}")
        root_label.setStyleSheet("color: #888; font-size: 11px;")
        path_layout.addWidget(root_label)

        # Pfad-Zeile
        path_row = QHBoxLayout()
        self.path_entry = QLineEdit()
        self.path_entry.setPlaceholderText("Ordnername (relativ zum Root)")
        if self.project:
            self.path_entry.setText(self.project.relative_path)
        path_row.addWidget(self.path_entry)

        browse_btn = QPushButton("📁")
        browse_btn.setFixedWidth(40)
        browse_btn.clicked.connect(self._on_browse)
        path_row.addWidget(browse_btn)

        path_layout.addLayout(path_row)
        scroll_layout.addWidget(path_group)

        # === Kategorie ===
        cat_group = QGroupBox("Kategorie (optional)")
        cat_layout = QVBoxLayout(cat_group)

        self.cat_entry = QLineEdit()
        self.cat_entry.setPlaceholderText("z.B. Python, Web, Tools...")
        if self.project and self.project.category:
            self.cat_entry.setText(self.project.category)
        cat_layout.addWidget(self.cat_entry)

        scroll_layout.addWidget(cat_group)

        # === Start-Befehl ===
        start_group = QGroupBox("Start-Befehl (optional)")
        start_layout = QVBoxLayout(start_group)

        self.start_entry = QLineEdit()
        self.start_entry.setPlaceholderText("Eigener Startbefehl...")
        if self.project and self.project.custom_start_command:
            self.start_entry.setText(self.project.custom_start_command)
        start_layout.addWidget(self.start_entry)

        hint_label = QLabel(f"Leer lassen für: {self.config.default_start_command}")
        hint_label.setStyleSheet("color: #888; font-size: 11px;")
        start_layout.addWidget(hint_label)

        scroll_layout.addWidget(start_group)

        # === Provider ===
        provider_group = QGroupBox("Standard-Provider")
        provider_layout = QVBoxLayout(provider_group)

        self.provider_dropdown = QComboBox()
        self.provider_ids = []
        enabled_providers = self.config.get_enabled_providers()
        selected_idx = 0

        for i, p in enumerate(enabled_providers):
            self.provider_dropdown.addItem(p.name)
            self.provider_ids.append(p.id)
            if self.project and self.project.default_provider == p.id:
                selected_idx = i
            elif not self.project and p.id == self.config.last_provider:
                selected_idx = i

        self.provider_dropdown.setCurrentIndex(selected_idx)
        provider_layout.addWidget(self.provider_dropdown)

        scroll_layout.addWidget(provider_group)

        # Spacer
        scroll_layout.addStretch()

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # === Buttons ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Speichern")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _on_browse(self):
        start_dir = self.config.project_root if self.config.project_root and os.path.isdir(self.config.project_root) else str(Path.home())

        folder = QFileDialog.getExistingDirectory(
            self,
            "Projektordner auswählen",
            start_dir,
            QFileDialog.Option.ShowDirsOnly
        )

        if folder:
            # Relativen Pfad berechnen
            if self.config.project_root and folder.startswith(self.config.project_root):
                relative = os.path.relpath(folder, self.config.project_root)
                self.path_entry.setText(relative)
            else:
                self.path_entry.setText(Path(folder).name)

    def _on_save(self):
        name = self.name_entry.text().strip()
        relative_path = self.path_entry.text().strip()
        category = self.cat_entry.text().strip() or "Allgemein"
        start_cmd = self.start_entry.text().strip()

        if not name:
            QMessageBox.warning(self, "Fehler", "Bitte einen Namen eingeben")
            return

        if not relative_path:
            QMessageBox.warning(self, "Fehler", "Bitte einen Ordner auswählen")
            return

        # SECURITY: Start-Befehl validieren
        if start_cmd:
            is_valid, error = validate_command(start_cmd)
            if not is_valid:
                QMessageBox.warning(self, "Fehler", f"Ungültiger Start-Befehl: {error}")
                return

        selected_idx = self.provider_dropdown.currentIndex()
        provider_id = self.provider_ids[selected_idx] if selected_idx < len(self.provider_ids) else "claude"

        new_project = Project(
            name=name,
            relative_path=relative_path,
            description="",
            category=category,
            default_provider=provider_id,
            custom_start_command=start_cmd,
            hidden=self.project.hidden if self.project else False,
            favorite=self.project.favorite if self.project else False
        )

        if self.on_save:
            self.on_save(new_project)

        self.accept()


class ProviderDialog(QDialog):
    """Dialog zum Hinzufügen/Bearbeiten eines Providers"""

    def __init__(
        self,
        parent,
        provider: Optional[LLMProvider] = None,
        on_save: Optional[Callable[[LLMProvider], None]] = None
    ):
        super().__init__(parent)
        self.provider = provider
        self.on_save = on_save
        self.is_edit = provider is not None

        self.setWindowTitle("Provider bearbeiten" if self.is_edit else "Neuer Provider")
        self.setFixedSize(450, 550)
        self.setModal(True)
        self.setStyleSheet(DIALOG_STYLE)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Scrollbereich
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)

        # === Grundeinstellungen ===
        basic_group = QGroupBox("Grundeinstellungen")
        basic_layout = QGridLayout(basic_group)
        basic_layout.setSpacing(10)

        basic_layout.addWidget(QLabel("ID (eindeutig):"), 0, 0)
        self.id_entry = QLineEdit()
        self.id_entry.setText(self.provider.id if self.provider else "")
        if self.is_edit:
            self.id_entry.setEnabled(False)
        basic_layout.addWidget(self.id_entry, 0, 1)

        basic_layout.addWidget(QLabel("Anzeigename:"), 1, 0)
        self.name_entry = QLineEdit()
        self.name_entry.setText(self.provider.name if self.provider else "")
        basic_layout.addWidget(self.name_entry, 1, 1)

        scroll_layout.addWidget(basic_group)

        # === Befehl ===
        cmd_group = QGroupBox("Befehl")
        cmd_layout = QGridLayout(cmd_group)
        cmd_layout.setSpacing(10)

        cmd_layout.addWidget(QLabel("CLI-Befehl:"), 0, 0)
        self.cmd_entry = QLineEdit()
        self.cmd_entry.setText(self.provider.command if self.provider else "")
        cmd_layout.addWidget(self.cmd_entry, 0, 1)

        cmd_layout.addWidget(QLabel("Skip-Permissions Flag:"), 1, 0)
        self.skip_flag_entry = QLineEdit()
        self.skip_flag_entry.setText(self.provider.skip_permissions_flag if self.provider else "")
        cmd_layout.addWidget(self.skip_flag_entry, 1, 1)

        scroll_layout.addWidget(cmd_group)

        # === Darstellung ===
        ui_group = QGroupBox("Darstellung")
        ui_layout = QGridLayout(ui_group)
        ui_layout.setSpacing(10)

        ui_layout.addWidget(QLabel("Icon-Name:"), 0, 0)
        self.icon_entry = QLineEdit()
        self.icon_entry.setText(self.provider.icon if self.provider else "🤖")
        ui_layout.addWidget(self.icon_entry, 0, 1)

        ui_layout.addWidget(QLabel("CSS Farbe:"), 1, 0)
        self.color_entry = QLineEdit()
        self.color_entry.setText(self.provider.color if self.provider else "#666666")
        ui_layout.addWidget(self.color_entry, 1, 1)

        scroll_layout.addWidget(ui_group)

        # === Status ===
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)

        self.enabled_switch = QCheckBox("Aktiviert")
        self.enabled_switch.setChecked(self.provider.enabled if self.provider else True)
        status_layout.addWidget(self.enabled_switch)

        scroll_layout.addWidget(status_group)

        # Spacer
        scroll_layout.addStretch()

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # === Buttons ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Speichern")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _on_save(self):
        provider_id = self.id_entry.text().strip()
        name = self.name_entry.text().strip()
        command = self.cmd_entry.text().strip()

        if not provider_id:
            QMessageBox.warning(self, "Fehler", "Bitte eine ID eingeben")
            return
        if not name:
            QMessageBox.warning(self, "Fehler", "Bitte einen Namen eingeben")
            return
        if not command:
            QMessageBox.warning(self, "Fehler", "Bitte einen Befehl eingeben")
            return

        # SECURITY: Befehle validieren
        is_valid, error = validate_command(command)
        if not is_valid:
            QMessageBox.warning(self, "Fehler", f"Ungültiger Befehl: {error}")
            return

        skip_flag = self.skip_flag_entry.text().strip()
        if skip_flag:
            is_valid, error = validate_command(skip_flag)
            if not is_valid:
                QMessageBox.warning(self, "Fehler", f"Ungültiges Flag: {error}")
                return

        new_provider = LLMProvider(
            id=provider_id,
            name=name,
            command=command,
            icon=self.icon_entry.text().strip() or "🤖",
            color=self.color_entry.text().strip() or "#666666",
            enabled=self.enabled_switch.isChecked(),
            skip_permissions_flag=skip_flag
        )

        if self.on_save:
            self.on_save(new_provider)

        self.accept()


class SettingsDialog(QDialog):
    """Einstellungs-Dialog"""

    def __init__(
        self,
        parent,
        config: Config,
        on_save: Optional[Callable[[Config], None]] = None,
        on_export: Optional[Callable[[], None]] = None,
        on_import: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.config = config
        self.on_save = on_save
        self.on_export_callback = on_export
        self.on_import_callback = on_import

        self.setWindowTitle("Einstellungen")
        self.setFixedSize(600, 650)
        self.setModal(True)
        self.setStyleSheet(DIALOG_STYLE)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Scrollbereich
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)

        # === Pfade ===
        paths_group = QGroupBox("Pfade")
        paths_layout = QGridLayout(paths_group)
        paths_layout.setSpacing(10)

        paths_layout.addWidget(QLabel("Projekt-Root:"), 0, 0)
        self.root_entry = QLineEdit()
        self.root_entry.setText(self.config.project_root)
        paths_layout.addWidget(self.root_entry, 0, 1)

        root_browse = QPushButton("📁")
        root_browse.setFixedWidth(40)
        root_browse.clicked.connect(lambda: self._browse_folder(self.root_entry))
        paths_layout.addWidget(root_browse, 0, 2)

        paths_layout.addWidget(QLabel("Sync-Ordner:"), 1, 0)
        self.sync_entry = QLineEdit()
        self.sync_entry.setText(self.config.sync_path)
        self.sync_entry.setPlaceholderText("Google Drive, Dropbox etc.")
        paths_layout.addWidget(self.sync_entry, 1, 1)

        sync_browse = QPushButton("📁")
        sync_browse.setFixedWidth(40)
        sync_browse.clicked.connect(lambda: self._browse_folder(self.sync_entry))
        paths_layout.addWidget(sync_browse, 1, 2)

        scroll_layout.addWidget(paths_group)

        # === Terminal ===
        term_group = QGroupBox("Terminal")
        term_layout = QGridLayout(term_group)
        term_layout.setSpacing(10)

        term_layout.addWidget(QLabel("Terminal-Befehl:"), 0, 0)
        self.term_entry = QLineEdit()
        self.term_entry.setText(self.config.terminal_command)
        term_layout.addWidget(self.term_entry, 0, 1)

        term_layout.addWidget(QLabel("Standard Start-Befehl:"), 1, 0)
        self.start_entry = QLineEdit()
        self.start_entry.setText(self.config.default_start_command)
        term_layout.addWidget(self.start_entry, 1, 1)

        scroll_layout.addWidget(term_group)

        # === Sync ===
        sync_group = QGroupBox("Sync-Einstellungen")
        sync_layout = QVBoxLayout(sync_group)

        # Passwort
        pw_layout = QHBoxLayout()
        pw_layout.addWidget(QLabel("Sync-Passwort:"))
        self.password_entry = QLineEdit()
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_entry.setPlaceholderText("Verschlüsselungs-Passwort")

        # Passwort NICHT anzeigen (Sicherheit) - nur Placeholder wenn gesetzt
        try:
            from .config import get_sync_password
            current_pw = get_sync_password()
            if current_pw:
                self.password_entry.setPlaceholderText("••••••••  (bereits gesetzt)")
        except (ImportError, OSError, KeyError, TypeError, ValueError):
            pass

        pw_layout.addWidget(self.password_entry)
        sync_layout.addLayout(pw_layout)

        # Export/Import Buttons
        sync_buttons = QHBoxLayout()
        sync_buttons.addStretch()

        export_btn = QPushButton("Exportieren")
        export_btn.setObjectName("primary")
        export_btn.clicked.connect(self._on_export)
        sync_buttons.addWidget(export_btn)

        import_btn = QPushButton("Importieren")
        import_btn.clicked.connect(self._on_import)
        sync_buttons.addWidget(import_btn)

        sync_layout.addLayout(sync_buttons)
        scroll_layout.addWidget(sync_group)

        # === Provider Info ===
        provider_group = QGroupBox("LLM Provider")
        provider_layout = QVBoxLayout(provider_group)

        provider_count = len(self.config.providers)
        enabled_count = len([p for p in self.config.providers if p.enabled])
        provider_label = QLabel(f"{provider_count} Provider konfiguriert ({enabled_count} aktiviert)")
        provider_layout.addWidget(provider_label)

        scroll_layout.addWidget(provider_group)

        # Spacer
        scroll_layout.addStretch()

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # === Buttons ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Speichern")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._on_close)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _browse_folder(self, target_entry: QLineEdit):
        current = target_entry.text() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(
            self,
            "Ordner auswählen",
            current,
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            target_entry.setText(folder)

    def _save_settings(self):
        try:
            from .config import set_sync_password
        except ImportError:
            set_sync_password = None

        self.config.local.project_root = self.root_entry.text().strip()
        self.config.local.sync_path = self.sync_entry.text().strip()
        self.config.local.terminal_command = self.term_entry.text().strip()
        self.config.local.default_start_command = self.start_entry.text().strip()

        # Passwort nur speichern wenn neu eingegeben (nicht leer = Placeholder)
        password = self.password_entry.text()
        if password and password.strip() and set_sync_password:
            try:
                set_sync_password(password)
            except (OSError, TypeError, ValueError):
                pass

        if self.on_save:
            self.on_save(self.config)

    def _on_export(self):
        self._save_settings()
        if self.on_export_callback:
            self.on_export_callback()

    def _on_import(self):
        self._save_settings()
        if self.on_import_callback:
            self.on_import_callback()

    def _on_close(self):
        self._save_settings()
        self.accept()
