"""Dialog classes for Cindergrace Launcher (PySide6 version).

Separated from cockpit.py for better maintainability.
"""

import os
from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .config import Config, Project
from .i18n import LANGUAGES, get_language, set_language, tr
from .process_manager import validate_command
from .providers import LLMProvider


def resolve_cloud_path(path: str) -> str:
    """Converts cloud URLs to local GVFS paths.

    Supports:
    - google-drive://user@gmail.com/driveId/folderId
    - Already correct paths are returned unchanged
    """
    if not path:
        return path

    # Convert Google Drive URL
    if path.startswith("google-drive://"):
        # Format: google-drive://user@domain/driveId/folderId
        # GVFS: /run/user/UID/gvfs/google-drive:host=domain,user=user/driveId/folderId
        try:
            from urllib.parse import urlparse

            parsed = urlparse(path)

            # Extract user and host (user@domain format)
            if "@" in parsed.netloc:
                user, host = parsed.netloc.rsplit("@", 1)
            else:
                return path  # Unknown format

            # Build GVFS path
            gvfs_base = f"/run/user/{os.getuid()}/gvfs"
            gvfs_mount = f"google-drive:host={host},user={user}"
            gvfs_path = f"{gvfs_base}/{gvfs_mount}{parsed.path}"

            # Check if path exists
            if Path(gvfs_path).exists():
                return gvfs_path
        except (ValueError, OSError):
            pass

    return path


# Shared stylesheet for dialogs
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
    """Dialog for adding/editing a project."""

    def __init__(
        self,
        parent,
        config: Config,
        project: Project | None = None,
        on_save: Callable[[Project], None] | None = None,
    ):
        """Initializes the project dialog."""
        super().__init__(parent)
        self.config = config
        self.project = project
        self.on_save = on_save
        self.is_edit = project is not None

        self.setWindowTitle(tr("dialog_edit_project") if self.is_edit else tr("dialog_new_project"))
        self.setFixedSize(500, 580)
        self.setModal(True)
        self.setStyleSheet(DIALOG_STYLE)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)

        # === Name ===
        name_group = QGroupBox(tr("project_name"))
        name_layout = QVBoxLayout(name_group)

        self.name_entry = QLineEdit()
        self.name_entry.setPlaceholderText(tr("project_name_placeholder"))
        if self.project:
            self.name_entry.setText(self.project.name)
        name_layout.addWidget(self.name_entry)

        scroll_layout.addWidget(name_group)

        # === Path ===
        path_group = QGroupBox(tr("project_folder"))
        path_layout = QVBoxLayout(path_group)

        # Root info
        root_label = QLabel(tr("project_root").format(path=self.config.project_root))
        root_label.setStyleSheet("color: #888; font-size: 11px;")
        path_layout.addWidget(root_label)

        # Path row
        path_row = QHBoxLayout()
        self.path_entry = QLineEdit()
        self.path_entry.setPlaceholderText(tr("folder_placeholder"))
        if self.project:
            self.path_entry.setText(self.project.relative_path)
        path_row.addWidget(self.path_entry)

        browse_btn = QPushButton("📁")
        browse_btn.setFixedWidth(40)
        browse_btn.clicked.connect(self._on_browse)
        path_row.addWidget(browse_btn)

        path_layout.addLayout(path_row)
        scroll_layout.addWidget(path_group)

        # === Category ===
        cat_group = QGroupBox(tr("category_optional"))
        cat_layout = QVBoxLayout(cat_group)

        self.cat_entry = QLineEdit()
        self.cat_entry.setPlaceholderText(tr("category_placeholder"))
        if self.project and self.project.category:
            self.cat_entry.setText(self.project.category)
        cat_layout.addWidget(self.cat_entry)

        scroll_layout.addWidget(cat_group)

        # === Start command ===
        start_group = QGroupBox(tr("start_command_optional"))
        start_layout = QVBoxLayout(start_group)

        self.start_entry = QLineEdit()
        self.start_entry.setPlaceholderText(tr("start_command_placeholder"))
        if self.project and self.project.custom_start_command:
            self.start_entry.setText(self.project.custom_start_command)
        start_layout.addWidget(self.start_entry)

        hint_label = QLabel(tr("start_command_hint").format(command=self.config.default_start_command))
        hint_label.setStyleSheet("color: #888; font-size: 11px;")
        start_layout.addWidget(hint_label)

        scroll_layout.addWidget(start_group)

        # === Provider ===
        provider_group = QGroupBox(tr("default_provider"))
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

        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton(tr("save"))
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _on_browse(self):
        start_dir = (
            self.config.project_root
            if self.config.project_root and os.path.isdir(self.config.project_root)
            else str(Path.home())
        )

        folder = QFileDialog.getExistingDirectory(
            self, "Select project folder", start_dir, QFileDialog.Option.ShowDirsOnly
        )

        if folder:
            # Calculate relative path using Path for cross-platform compatibility
            folder_path = Path(folder).resolve()
            root_path = Path(self.config.project_root).resolve() if self.config.project_root else None

            if root_path:
                try:
                    # Check if folder is under project_root
                    relative = folder_path.relative_to(root_path)
                    self.path_entry.setText(str(relative))
                except ValueError:
                    # Folder not under project_root
                    self.path_entry.setText(folder_path.name)
            else:
                self.path_entry.setText(folder_path.name)

    def _on_save(self):
        name = self.name_entry.text().strip()
        relative_path = self.path_entry.text().strip()
        category = self.cat_entry.text().strip() or "General"
        start_cmd = self.start_entry.text().strip()

        if not name:
            QMessageBox.warning(self, tr("error"), tr("error_name_required"))
            return

        if not relative_path:
            QMessageBox.warning(self, tr("error"), tr("error_folder_required"))
            return

        # SECURITY: Validate start command
        if start_cmd:
            is_valid, error = validate_command(start_cmd)
            if not is_valid:
                QMessageBox.warning(self, tr("error"), tr("error_invalid_command").format(error=error))
                return

        selected_idx = self.provider_dropdown.currentIndex()
        provider_id = (
            self.provider_ids[selected_idx]
            if selected_idx < len(self.provider_ids)
            else "claude"
        )

        new_project = Project(
            name=name,
            relative_path=relative_path,
            description="",
            category=category,
            default_provider=provider_id,
            custom_start_command=start_cmd,
            hidden=self.project.hidden if self.project else False,
            favorite=self.project.favorite if self.project else False,
        )

        if self.on_save:
            self.on_save(new_project)

        self.accept()


class ProviderDialog(QDialog):
    """Dialog for adding/editing a provider."""

    def __init__(
        self,
        parent,
        provider: LLMProvider | None = None,
        on_save: Callable[[LLMProvider], None] | None = None,
    ):
        """Initializes the provider dialog."""
        super().__init__(parent)
        self.provider = provider
        self.on_save = on_save
        self.is_edit = provider is not None

        self.setWindowTitle(tr("dialog_edit_provider") if self.is_edit else tr("dialog_new_provider"))
        self.setFixedSize(550, 550)
        self.setModal(True)
        self.setStyleSheet(DIALOG_STYLE)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)

        # === Basic settings ===
        basic_group = QGroupBox(tr("basic_settings"))
        basic_layout = QGridLayout(basic_group)
        basic_layout.setSpacing(10)

        basic_layout.addWidget(QLabel(tr("id_unique")), 0, 0)
        self.id_entry = QLineEdit()
        self.id_entry.setText(self.provider.id if self.provider else "")
        if self.is_edit:
            self.id_entry.setEnabled(False)
        basic_layout.addWidget(self.id_entry, 0, 1)

        basic_layout.addWidget(QLabel(tr("display_name")), 1, 0)
        self.name_entry = QLineEdit()
        self.name_entry.setText(self.provider.name if self.provider else "")
        basic_layout.addWidget(self.name_entry, 1, 1)

        scroll_layout.addWidget(basic_group)

        # === Command ===
        cmd_group = QGroupBox(tr("command_section"))
        cmd_layout = QGridLayout(cmd_group)
        cmd_layout.setSpacing(10)

        cmd_layout.addWidget(QLabel(tr("cli_command")), 0, 0)
        self.cmd_entry = QLineEdit()
        self.cmd_entry.setText(self.provider.command if self.provider else "")
        cmd_layout.addWidget(self.cmd_entry, 0, 1)

        cmd_layout.addWidget(QLabel(tr("skip_permissions_flag")), 1, 0)
        self.skip_flag_entry = QLineEdit()
        self.skip_flag_entry.setText(
            self.provider.skip_permissions_flag if self.provider else ""
        )
        cmd_layout.addWidget(self.skip_flag_entry, 1, 1)

        scroll_layout.addWidget(cmd_group)

        # === Appearance ===
        ui_group = QGroupBox(tr("appearance"))
        ui_layout = QGridLayout(ui_group)
        ui_layout.setSpacing(10)

        ui_layout.addWidget(QLabel(tr("icon_name")), 0, 0)
        self.icon_entry = QLineEdit()
        self.icon_entry.setText(self.provider.icon if self.provider else "🤖")
        ui_layout.addWidget(self.icon_entry, 0, 1)

        ui_layout.addWidget(QLabel(tr("css_color")), 1, 0)
        self.color_entry = QLineEdit()
        self.color_entry.setText(self.provider.color if self.provider else "#666666")
        ui_layout.addWidget(self.color_entry, 1, 1)

        scroll_layout.addWidget(ui_group)

        # === Status ===
        status_group = QGroupBox(tr("status"))
        status_layout = QVBoxLayout(status_group)

        self.enabled_switch = QCheckBox(tr("enabled"))
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

        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton(tr("save"))
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _on_save(self):
        provider_id = self.id_entry.text().strip()
        name = self.name_entry.text().strip()
        command = self.cmd_entry.text().strip()

        if not provider_id:
            QMessageBox.warning(self, tr("error"), tr("error_id_required"))
            return
        if not name:
            QMessageBox.warning(self, tr("error"), tr("error_name_required_provider"))
            return
        if not command:
            QMessageBox.warning(self, tr("error"), tr("error_command_required"))
            return

        # SECURITY: Validate commands
        is_valid, error = validate_command(command)
        if not is_valid:
            QMessageBox.warning(self, tr("error"), tr("error_invalid_cmd").format(error=error))
            return

        skip_flag = self.skip_flag_entry.text().strip()
        if skip_flag:
            is_valid, error = validate_command(skip_flag)
            if not is_valid:
                QMessageBox.warning(self, tr("error"), tr("error_invalid_flag").format(error=error))
                return

        new_provider = LLMProvider(
            id=provider_id,
            name=name,
            command=command,
            icon=self.icon_entry.text().strip() or "🤖",
            color=self.color_entry.text().strip() or "#666666",
            enabled=self.enabled_switch.isChecked(),
            skip_permissions_flag=skip_flag,
        )

        if self.on_save:
            self.on_save(new_provider)

        self.accept()


class SettingsDialog(QDialog):
    """Settings dialog."""

    def __init__(
        self,
        parent,
        config: Config,
        on_save: Callable[[Config], None] | None = None,
        on_export: Callable[[], None] | None = None,
        on_import: Callable[[], None] | None = None,
    ):
        """Initializes the settings dialog."""
        super().__init__(parent)
        self.config = config
        self.on_save = on_save
        self.on_export_callback = on_export
        self.on_import_callback = on_import

        self.setWindowTitle(tr("settings_title"))
        self.setFixedSize(600, 650)
        self.setModal(True)
        self.setStyleSheet(DIALOG_STYLE)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)

        # === Paths ===
        paths_group = QGroupBox(tr("paths"))
        paths_layout = QGridLayout(paths_group)
        paths_layout.setSpacing(10)

        paths_layout.addWidget(QLabel(tr("project_root_label")), 0, 0)
        self.root_entry = QLineEdit()
        self.root_entry.setText(self.config.project_root)
        paths_layout.addWidget(self.root_entry, 0, 1)

        root_browse = QPushButton("📁")
        root_browse.setFixedWidth(40)
        root_browse.clicked.connect(lambda: self._browse_folder(self.root_entry))
        paths_layout.addWidget(root_browse, 0, 2)

        paths_layout.addWidget(QLabel(tr("sync_folder")), 1, 0)
        self.sync_entry = QLineEdit()
        self.sync_entry.setText(self.config.sync_path)
        self.sync_entry.setPlaceholderText(tr("sync_folder_placeholder"))
        paths_layout.addWidget(self.sync_entry, 1, 1)

        sync_browse = QPushButton("📁")
        sync_browse.setFixedWidth(40)
        sync_browse.clicked.connect(lambda: self._browse_folder(self.sync_entry))
        paths_layout.addWidget(sync_browse, 1, 2)

        scroll_layout.addWidget(paths_group)

        # === Terminal ===
        term_group = QGroupBox(tr("terminal"))
        term_layout = QGridLayout(term_group)
        term_layout.setSpacing(10)

        term_layout.addWidget(QLabel(tr("terminal_command")), 0, 0)
        self.term_entry = QLineEdit()
        self.term_entry.setText(self.config.terminal_command)
        term_layout.addWidget(self.term_entry, 0, 1)

        term_layout.addWidget(QLabel(tr("default_start_command")), 1, 0)
        self.start_entry = QLineEdit()
        self.start_entry.setText(self.config.default_start_command)
        term_layout.addWidget(self.start_entry, 1, 1)

        scroll_layout.addWidget(term_group)

        # === Sync ===
        sync_group = QGroupBox(tr("sync_settings"))
        sync_layout = QVBoxLayout(sync_group)

        # Password
        pw_layout = QHBoxLayout()
        pw_layout.addWidget(QLabel(tr("sync_password")))
        self.password_entry = QLineEdit()
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_entry.setPlaceholderText(tr("password_placeholder"))

        # Do NOT show password (security) - only placeholder if set
        try:
            from .config import get_sync_password

            current_pw = get_sync_password()
            if current_pw:
                self.password_entry.setPlaceholderText("••••••••  " + tr("password_already_set"))
        except (ImportError, OSError, KeyError, TypeError, ValueError):
            pass

        pw_layout.addWidget(self.password_entry)
        sync_layout.addLayout(pw_layout)

        # Export/Import Buttons
        sync_buttons = QHBoxLayout()
        sync_buttons.addStretch()

        export_btn = QPushButton(tr("export"))
        export_btn.setObjectName("primary")
        export_btn.clicked.connect(self._on_export)
        sync_buttons.addWidget(export_btn)

        import_btn = QPushButton(tr("import"))
        import_btn.clicked.connect(self._on_import)
        sync_buttons.addWidget(import_btn)

        sync_layout.addLayout(sync_buttons)
        scroll_layout.addWidget(sync_group)

        # === Language ===
        lang_group = QGroupBox(tr("language"))
        lang_layout = QGridLayout(lang_group)
        lang_layout.setSpacing(10)

        lang_layout.addWidget(QLabel(tr("language_label")), 0, 0)
        self.lang_combo = QComboBox()
        self.lang_codes = list(LANGUAGES.keys())
        for code in self.lang_codes:
            self.lang_combo.addItem(LANGUAGES[code])
        # Set current language
        current_lang = get_language()
        if current_lang in self.lang_codes:
            self.lang_combo.setCurrentIndex(self.lang_codes.index(current_lang))
        lang_layout.addWidget(self.lang_combo, 0, 1)

        hint_label = QLabel(tr("language_restart_hint"))
        hint_label.setStyleSheet("color: #888; font-size: 11px;")
        lang_layout.addWidget(hint_label, 1, 0, 1, 2)

        scroll_layout.addWidget(lang_group)

        # === Provider management ===
        provider_group = QGroupBox(tr("llm_providers"))
        provider_layout = QVBoxLayout(provider_group)

        # Provider list (scrollable)
        self.provider_list_widget = QWidget()
        self.provider_list_layout = QVBoxLayout(self.provider_list_widget)
        self.provider_list_layout.setSpacing(5)
        self.provider_list_layout.setContentsMargins(0, 0, 0, 0)

        self._refresh_provider_list()

        provider_layout.addWidget(self.provider_list_widget)

        # Button to add
        add_provider_btn = QPushButton(tr("add_provider"))
        add_provider_btn.clicked.connect(self._on_add_provider)
        provider_layout.addWidget(add_provider_btn)

        scroll_layout.addWidget(provider_group)

        # Spacer
        scroll_layout.addStretch()

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # === Buttons ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton(tr("save"))
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._on_close)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _browse_folder(self, target_entry: QLineEdit):
        current = target_entry.text() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(
            self, "Select folder", current, QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            target_entry.setText(folder)

    def _save_settings(self):
        try:
            from .config import set_sync_password
        except ImportError:
            set_sync_password = None

        self.config.local.project_root = self.root_entry.text().strip()
        # Automatically convert cloud URLs to GVFS paths
        sync_path = resolve_cloud_path(self.sync_entry.text().strip())
        self.config.local.sync_path = sync_path
        # Update field if converted
        if sync_path != self.sync_entry.text().strip():
            self.sync_entry.setText(sync_path)
        self.config.local.terminal_command = self.term_entry.text().strip()
        self.config.local.default_start_command = self.start_entry.text().strip()

        # Save language setting
        lang_idx = self.lang_combo.currentIndex()
        if 0 <= lang_idx < len(self.lang_codes):
            new_lang = self.lang_codes[lang_idx]
            self.config.local.language = new_lang
            set_language(new_lang)

        # Only save password if newly entered (not empty = placeholder)
        password = self.password_entry.text()
        if password and password.strip() and set_sync_password:  # type: ignore[truthy-function]
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

    def _refresh_provider_list(self):
        """Refreshes the provider list."""
        # Remove old widgets
        while self.provider_list_layout.count():
            child = self.provider_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Add providers
        for provider in self.config.providers:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.setSpacing(6)

            # Status indicator (colored dot)
            status_label = QLabel("●" if provider.enabled else "○")
            status_label.setStyleSheet(f"color: {provider.color}; font-size: 12px;")
            status_label.setFixedWidth(16)
            row_layout.addWidget(status_label)

            # Name only (without icon string)
            name_label = QLabel(provider.name)
            name_label.setStyleSheet("color: #e0e0e0;")
            row_layout.addWidget(name_label, 1)

            # Edit button
            edit_btn = QPushButton("✏")
            edit_btn.setFixedSize(26, 26)
            edit_btn.setToolTip(tr("edit"))
            edit_btn.clicked.connect(lambda checked, p=provider: self._on_edit_provider(p))
            row_layout.addWidget(edit_btn)

            # Delete button
            del_btn = QPushButton("🗑")
            del_btn.setFixedSize(26, 26)
            del_btn.setToolTip(tr("delete"))
            del_btn.clicked.connect(lambda checked, p=provider: self._on_delete_provider(p))
            row_layout.addWidget(del_btn)

            self.provider_list_layout.addWidget(row)

    def _on_add_provider(self):
        """Adds a new provider."""

        def save_new_provider(new_provider: LLMProvider):
            try:
                self.config.add_provider(new_provider)
                self._refresh_provider_list()
            except ValueError as e:
                QMessageBox.warning(self, tr("error"), str(e))

        dialog = ProviderDialog(self, provider=None, on_save=save_new_provider)
        dialog.exec()

    def _on_edit_provider(self, provider: LLMProvider):
        """Edits the provider."""

        def save_updated_provider(updated: LLMProvider):
            try:
                self.config.update_provider(provider.id, updated)
                self._refresh_provider_list()
            except ValueError as e:
                QMessageBox.warning(self, tr("error"), str(e))

        dialog = ProviderDialog(self, provider=provider, on_save=save_updated_provider)
        dialog.exec()

    def _on_delete_provider(self, provider: LLMProvider):
        """Deletes the provider."""
        # At least one provider must remain
        if len(self.config.providers) <= 1:
            QMessageBox.warning(
                self, tr("not_possible"), tr("min_provider_error")
            )
            return

        reply = QMessageBox.question(
            self,
            tr("delete_provider_title"),
            tr("delete_provider_confirm").format(name=provider.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.config.remove_provider(provider.id)
            self._refresh_provider_list()
