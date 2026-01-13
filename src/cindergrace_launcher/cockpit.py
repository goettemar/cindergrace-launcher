"""Cindergrace Launcher - Main window.

PySide6-based cross-platform GUI for managing LLM CLI sessions.
Supports: Fully configurable providers + sync.
"""

import os
import subprocess  # nosec B404 - needed for terminal launching
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .config import (
    Config,
    Project,
    add_project,
    export_to_sync,
    import_from_sync,
    load_config,
    remove_project,
    save_config,
    update_project,
)
from .i18n import tr
from .process_manager import ProcessManager, validate_command
from .providers import LLMProvider

# Cindergrace Branding
BRAND_COLORS = {
    "blue_dark": "#1E5AA8",
    "blue_light": "#7CC8FF",
    "blue_hover": "#2d6fc0",
}

# Logo path
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent.parent.parent
LOGO_PATH = _project_root / "cindergrace_projects" / "logo"

# Stylesheet
STYLESHEET = """
QMainWindow {
    background-color: #fafafa;
}
QListWidget {
    border: 1px solid #ddd;
    border-radius: 8px;
    background-color: white;
    padding: 5px;
}
QListWidget::item {
    border-bottom: 1px solid #eee;
    padding: 8px;
}
QListWidget::item:selected {
    background-color: #e3f2fd;
    color: black;
}
QListWidget::item:hover {
    background-color: #f5f5f5;
}
QPushButton {
    padding: 8px 16px;
    border-radius: 6px;
    border: 1px solid #ddd;
    background-color: white;
}
QPushButton:hover {
    background-color: #f0f0f0;
}
QPushButton#primary {
    background-color: #1E5AA8;
    color: white;
    border: none;
}
QPushButton#primary:hover {
    background-color: #2d6fc0;
}
QPushButton#success {
    background-color: #4CAF50;
    color: white;
    border: none;
}
QPushButton#danger {
    background-color: #f44336;
    color: white;
    border: none;
}
QPushButton#icon {
    font-size: 16px;
    min-width: 36px;
    min-height: 36px;
    padding: 4px;
}
QPushButton#icon:hover {
    background-color: #e0e0e0;
}
QLineEdit {
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 6px;
    background-color: white;
}
QLineEdit:focus {
    border-color: #1E5AA8;
}
QComboBox {
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 6px;
    background-color: white;
}
QLabel#title {
    font-size: 18px;
    font-weight: bold;
    color: #1E5AA8;
}
QLabel#subtitle {
    color: #666;
    font-size: 12px;
}
QFrame#card {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 10px;
}
QStatusBar {
    background-color: #f5f5f5;
    border-top: 1px solid #ddd;
}
"""


class ProjectWidget(QFrame):
    """A project entry in the list."""

    def __init__(
        self,
        project: Project,
        index: int,
        is_running: bool,
        running_provider: str,
        config: Config,
        parent=None,
    ):
        """Initializes a list item for a project."""
        super().__init__(parent)
        self.project = project
        self.index = index
        self.is_running = is_running
        self.running_provider = running_provider
        self.config = config
        self.parent_window = parent

        self.setObjectName("card")
        self.setFrameStyle(QFrame.StyledPanel)  # type: ignore[attr-defined]
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)

        # Favorite button (star on the left)
        self.fav_btn = QPushButton("★" if self.project.favorite else "☆")
        self.fav_btn.setFixedSize(36, 36)
        self.fav_btn.setToolTip(
            tr("favorite") if self.project.favorite else tr("mark_favorite")
        )
        self.fav_btn.setStyleSheet(
            "color: #FFD700; border: none; font-size: 22px; font-weight: bold;"
            if self.project.favorite
            else "color: #bbb; border: none; font-size: 22px;"
        )
        self.fav_btn.setCursor(Qt.PointingHandCursor)
        self.fav_btn.clicked.connect(self._on_toggle_favorite)
        layout.addWidget(self.fav_btn)

        # Status icon
        status_label = QLabel("●")
        if self.is_running:
            status_label.setStyleSheet("color: #4CAF50; font-size: 14px;")
            status_label.setToolTip(tr("running").format(provider=self.running_provider))
        else:
            status_label.setStyleSheet("color: #ccc; font-size: 14px;")
            status_label.setToolTip(tr("stopped"))
        layout.addWidget(status_label)

        # Project info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = QLabel(self.project.name)
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        if self.project.hidden:
            name_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #999;")
        info_layout.addWidget(name_label)

        abs_path = self.config.get_project_absolute_path(self.project)
        subtitle = abs_path
        # Warn if relative_path is empty (misconfigured project)
        # Strip leading slashes for the check (they're handled in get_absolute_path)
        effective_path = self.project.relative_path.lstrip("/").lstrip("\\")
        if not effective_path:
            subtitle = f"⚠️ {self.config.project_root} (Pfad fehlt!)"
        if self.project.category and self.project.category != "General":
            subtitle += f"  [{self.project.category}]"
        path_label = QLabel(subtitle)
        path_color = "#c00" if not effective_path else "#666"
        path_label.setStyleSheet(f"color: {path_color}; font-size: 11px;")
        info_layout.addWidget(path_label)

        layout.addLayout(info_layout, stretch=1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)

        if self.is_running:
            # Focus Button
            focus_btn = QPushButton("◎")
            focus_btn.setToolTip(tr("focus_window"))
            focus_btn.setFixedSize(36, 36)
            focus_btn.setObjectName("icon")
            focus_btn.clicked.connect(self._on_focus)
            btn_layout.addWidget(focus_btn)

            # Stop Button
            stop_btn = QPushButton("■")
            stop_btn.setToolTip(tr("stop_session"))
            stop_btn.setFixedSize(36, 36)
            stop_btn.setObjectName("danger")
            stop_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
            stop_btn.clicked.connect(self._on_stop)
            btn_layout.addWidget(stop_btn)
        else:
            # Start Custom Button
            start_btn = QPushButton("▶")
            start_cmd = self.config.get_start_command(self.project)
            start_btn.setToolTip(f"Start: {start_cmd}")
            start_btn.setFixedSize(36, 36)
            start_btn.setObjectName("icon")
            start_btn.setStyleSheet("font-size: 14px;")
            start_btn.clicked.connect(self._on_start_custom)
            btn_layout.addWidget(start_btn)

            # Provider Menu Button
            enabled_providers = self.config.get_enabled_providers()
            if enabled_providers:
                provider_btn = QPushButton("AI")
                provider_btn.setToolTip(tr("start_provider"))
                provider_btn.setFixedSize(36, 36)
                provider_btn.setObjectName("success")
                provider_btn.setStyleSheet("font-size: 11px; font-weight: bold;")

                menu = QMenu(self)
                for provider in enabled_providers:
                    action = menu.addAction(provider.name)
                    action.triggered.connect(
                        lambda checked, p=provider: self._on_start_provider(p)
                    )
                provider_btn.setMenu(menu)
                btn_layout.addWidget(provider_btn)

        # Edit Button
        edit_btn = QPushButton("✎")
        edit_btn.setToolTip(tr("edit_project"))
        edit_btn.setFixedSize(36, 36)
        edit_btn.setObjectName("icon")
        edit_btn.setStyleSheet("font-size: 16px;")
        edit_btn.clicked.connect(self._on_edit)
        btn_layout.addWidget(edit_btn)

        # Hide/Show Button - use simpler symbols
        hide_text = "○" if self.project.hidden else "●"
        hide_btn = QPushButton(hide_text)
        hide_btn.setToolTip(tr("show_project") if self.project.hidden else tr("hide_project"))
        hide_btn.setFixedSize(36, 36)
        hide_btn.setObjectName("icon")
        hide_btn.setStyleSheet("font-size: 14px;")
        hide_btn.clicked.connect(self._on_toggle_hidden)
        btn_layout.addWidget(hide_btn)

        # Delete Button
        delete_btn = QPushButton("×")
        delete_btn.setToolTip(tr("remove_project"))
        delete_btn.setFixedSize(36, 36)
        delete_btn.setObjectName("icon")
        delete_btn.setStyleSheet("font-size: 20px; font-weight: bold; color: #c00;")
        delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)

    def _on_toggle_favorite(self):
        if self.parent_window:
            self.parent_window.toggle_favorite(self.index)

    def _on_focus(self):
        if self.parent_window:
            abs_path = self.config.get_project_absolute_path(self.project)
            self.parent_window.focus_session(abs_path)

    def _on_stop(self):
        if self.parent_window:
            abs_path = self.config.get_project_absolute_path(self.project)
            self.parent_window.stop_session(abs_path)

    def _on_start_custom(self):
        if self.parent_window:
            self.parent_window.start_custom(self.project)

    def _on_start_provider(self, provider: LLMProvider):
        if self.parent_window:
            abs_path = self.config.get_project_absolute_path(self.project)
            self.parent_window.start_session(abs_path, self.project.name, provider.id)

    def _on_edit(self):
        if self.parent_window:
            self.parent_window.edit_project(self.index)

    def _on_toggle_hidden(self):
        if self.parent_window:
            self.parent_window.toggle_hidden(self.index)

    def _on_delete(self):
        if self.parent_window:
            self.parent_window.delete_project(self.index)


class LauncherWindow(QMainWindow):
    """Main window of Cindergrace Launcher."""

    def __init__(self):
        """Initializes the main window and loads the configuration."""
        super().__init__()
        self.setWindowTitle(tr("window_title"))
        self.setMinimumSize(900, 650)

        self.config = load_config()
        self.process_manager = ProcessManager(terminal_cmd=self.config.terminal_command)

        self.search_text = ""
        self.filter_category = None

        self.setStyleSheet(STYLESHEET)
        self._build_ui()
        self._refresh_list()

        # Auto-refresh timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._auto_refresh)
        self.refresh_timer.start(5000)

        # Window Polling Timer
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_for_window)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel(tr("window_title"))
        title_label.setObjectName("title")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Add Project Button
        add_btn = QPushButton(tr("new_project"))
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._on_add_project)
        header_layout.addWidget(add_btn)

        # Show Hidden Toggle
        self.show_hidden_btn = QPushButton("👁 " + tr("hidden"))
        self.show_hidden_btn.setCheckable(True)
        self.show_hidden_btn.setChecked(self.config.show_hidden)
        self.show_hidden_btn.clicked.connect(self._on_toggle_show_hidden)
        header_layout.addWidget(self.show_hidden_btn)

        # Settings Button
        settings_btn = QPushButton("⚙ " + tr("settings"))
        settings_btn.clicked.connect(self._on_settings)
        header_layout.addWidget(settings_btn)

        # About Button
        about_btn = QPushButton("ℹ")
        about_btn.setFixedSize(36, 36)
        about_btn.clicked.connect(self._on_about)
        header_layout.addWidget(about_btn)

        main_layout.addLayout(header_layout)

        # Search and Filter
        filter_layout = QHBoxLayout()

        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("🔍 " + tr("search_placeholder"))
        self.search_entry.textChanged.connect(self._on_search_changed)
        filter_layout.addWidget(self.search_entry, stretch=1)

        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(150)
        self._update_category_filter()
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        filter_layout.addWidget(self.category_combo)

        main_layout.addLayout(filter_layout)

        # Project List Container
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch()

        self.scroll_area.setWidget(self.list_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        # Empty State
        self.empty_label = QLabel(tr("no_projects"))
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #999; font-size: 16px;")
        self.empty_label.hide()
        main_layout.addWidget(self.empty_label)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel()
        self.status_bar.addWidget(self.status_label)

    def _update_category_filter(self):
        """Updates the category dropdown."""
        current = self.category_combo.currentText()
        self.category_combo.clear()
        all_text = tr("category_all")
        categories = [all_text]
        for p in self.config.projects:
            if p.category and p.category not in categories:
                categories.append(p.category)
        self.category_combo.addItems(sorted(categories))
        if current in categories:
            self.category_combo.setCurrentText(current)

    def _on_search_changed(self, text):
        self.search_text = text.lower()
        self._refresh_list()

    def _on_category_changed(self, text):
        self.filter_category = None if text == tr("category_all") else text
        self._refresh_list()

    def _on_toggle_show_hidden(self):
        self.config.show_hidden = self.show_hidden_btn.isChecked()
        save_config(self.config)
        self._refresh_list()

    def _filter_projects(self) -> list:
        """Filters projects by search text, category, and hidden status."""
        filtered = []
        for i, p in enumerate(self.config.projects):
            if p.hidden and not self.config.show_hidden:
                continue

            if self.search_text:
                abs_path = self.config.get_project_absolute_path(p)
                if (
                    self.search_text not in p.name.lower()
                    and self.search_text not in abs_path.lower()
                    and self.search_text not in p.relative_path.lower()
                    and self.search_text not in p.category.lower()
                ):
                    continue

            if self.filter_category and p.category != self.filter_category:
                continue

            filtered.append((i, p))

        filtered.sort(key=lambda x: (not x[1].favorite, x[1].name.lower()))
        return filtered

    def _refresh_list(self):
        """Refreshes the project list."""
        # Clear existing widgets
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.process_manager.cleanup_dead_sessions()

        running_count = 0
        filtered_projects = self._filter_projects()

        if not filtered_projects:
            self.scroll_area.hide()
            self.empty_label.show()
        else:
            self.scroll_area.show()
            self.empty_label.hide()

            for orig_index, project in filtered_projects:
                abs_path = self.config.get_project_absolute_path(project)
                is_running = self.process_manager.is_running(abs_path)
                running_provider = None

                if is_running:
                    running_count += 1
                    running_provider = self.process_manager.get_session_provider(abs_path)

                widget = ProjectWidget(
                    project, orig_index, is_running, running_provider, self.config, parent=self
                )
                self.list_layout.insertWidget(self.list_layout.count() - 1, widget)

        # Update status
        total = len(self.config.projects)
        visible = len(filtered_projects)
        hidden_count = sum(1 for p in self.config.projects if p.hidden)

        status = tr("projects_status").format(visible=visible, total=total)
        if hidden_count > 0:
            status += " | " + tr("hidden_count").format(count=hidden_count)
        status += " | " + tr("active_count").format(count=running_count)
        self.status_label.setText(status)

    def _auto_refresh(self):
        """Auto-refresh: Only updates the status."""
        self.process_manager.cleanup_dead_sessions()
        self._update_status()

    def _update_status(self):
        """Updates only the status display."""
        running_count = sum(
            1
            for p in self.config.projects
            if self.process_manager.is_running(self.config.get_project_absolute_path(p))
        )
        total = len(self.config.projects)
        visible = len(self._filter_projects())
        hidden_count = sum(1 for p in self.config.projects if p.hidden)

        status = tr("projects_status").format(visible=visible, total=total)
        if hidden_count > 0:
            status += " | " + tr("hidden_count").format(count=hidden_count)
        status += " | " + tr("active_count").format(count=running_count)
        self.status_label.setText(status)

    def _poll_for_window(self):
        """Polls for new window."""
        if self.process_manager.poll_for_window():
            return  # Continue polling
        self.poll_timer.stop()

    def show_toast(self, message: str):
        """Shows a toast message."""
        self.status_bar.showMessage(message, 3000)

    # === Actions ===

    def start_custom(self, project: Project):
        """Starts the custom start command."""
        abs_path = self.config.get_project_absolute_path(project)
        start_cmd = self.config.get_start_command(project)

        is_valid, error = validate_command(start_cmd)
        if not is_valid:
            self.show_toast(tr("invalid_start_command").format(error=error))
            return

        # Check if script file exists (cross-platform)
        if start_cmd.startswith("./"):
            # Unix-style relative path
            check_path = os.path.join(abs_path, start_cmd[2:])
        elif not os.path.isabs(start_cmd) and not start_cmd.startswith(".\\"):
            # Simple filename like "start.bat" or "start.sh"
            check_path = os.path.join(abs_path, start_cmd)
        else:
            check_path = None

        if check_path and not os.path.exists(check_path):
            self.show_toast(tr("not_found").format(path=start_cmd))
            return

        try:
            if sys.platform == "win32":
                # Normalize path for Windows and quote it
                win_path = os.path.normpath(abs_path)
                subprocess.Popen(  # nosec B603 B607 - trusted terminal command
                    ["cmd", "/c", f'cd /d "{win_path}" && {start_cmd}'],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:
                subprocess.Popen(  # nosec B603 B607 - trusted terminal command
                    [
                        self.config.terminal_command,
                        f"--working-directory={abs_path}",
                        "--",
                        "bash",
                        "-c",
                        f"{start_cmd}; exec bash",
                    ],
                    start_new_session=True,
                )
            self.show_toast(tr("started").format(provider="", name=project.name))
        except FileNotFoundError:
            self.show_toast(tr("terminal_not_found").format(terminal=self.config.terminal_command))
        except subprocess.SubprocessError as e:
            self.show_toast(tr("process_error").format(error=e))

    def start_session(self, path: str, name: str, provider_id: str):
        """Starts an LLM CLI session."""
        provider = self.config.get_provider(provider_id)
        if not provider:
            self.show_toast(tr("provider_not_found").format(id=provider_id))
            return

        success, message = self.process_manager.start_session(
            path,
            name,
            provider_id,
            provider.command,
            provider.name,
            provider.default_flags,
            provider.skip_permissions_flag,
        )

        if success:
            self.config.last_provider = provider_id
            save_config(self.config)
            self.show_toast(tr("started").format(provider=provider.name, name=name))
            self.poll_timer.start(200)
        else:
            self.show_toast(f"{tr('error')}: {message}")
        self._refresh_list()

    def stop_session(self, path: str):
        """Stops a running session for the project."""
        success, message = self.process_manager.stop_session(path)
        if success:
            self.show_toast(tr("session_stopped"))
        else:
            self.show_toast(f"{tr('error')}: {message}")
        self._refresh_list()

    def focus_session(self, path: str):
        """Focuses the window of a running session."""
        success, message = self.process_manager.focus_window(path)
        if not success:
            self.show_toast(message)

    def toggle_hidden(self, index: int):
        """Toggles the visibility of a project."""
        if 0 <= index < len(self.config.projects):
            self.config.projects[index].hidden = not self.config.projects[index].hidden
            save_config(self.config)
            self._refresh_list()

    def toggle_favorite(self, index: int):
        """Toggles the favorite status of a project."""
        if 0 <= index < len(self.config.projects):
            self.config.projects[index].favorite = not self.config.projects[index].favorite
            save_config(self.config)
            self._refresh_list()

    def _on_add_project(self):
        self._show_project_dialog(None, -1)

    def edit_project(self, index: int):
        """Opens the dialog for editing a project."""
        if 0 <= index < len(self.config.projects):
            self._show_project_dialog(self.config.projects[index], index)

    def _show_project_dialog(self, project: Project | None, index: int):
        """Shows dialog for adding/editing a project."""
        from .dialogs import ProjectDialog

        saved_project: Project | None = None

        def on_save(new_project: Project):
            nonlocal saved_project
            saved_project = new_project

        dialog = ProjectDialog(self, self.config, project, on_save=on_save)
        if dialog.exec() == QDialog.Accepted and saved_project:  # type: ignore[attr-defined]
            if project is not None:
                self.config = update_project(self.config, index, saved_project)
                self.show_toast(tr("project_updated").format(name=saved_project.name))
            else:
                self.config = add_project(self.config, saved_project)
                self.show_toast(tr("project_added").format(name=saved_project.name))

            # Reload config to ensure UI shows current state
            self.config = load_config()
            self._update_category_filter()
            self._refresh_list()

    def delete_project(self, index: int):
        """Deletes a project by index."""
        if 0 <= index < len(self.config.projects):
            project = self.config.projects[index]

            reply = QMessageBox.question(
                self,
                tr("remove_project_title"),
                tr("remove_project_confirm").format(name=project.name),
                QMessageBox.Yes | QMessageBox.No,  # type: ignore[attr-defined]
            )

            if reply == QMessageBox.Yes:  # type: ignore[attr-defined]
                self.config = remove_project(self.config, index)
                # Reload config to ensure UI shows current state
                self.config = load_config()
                self._update_category_filter()
                self._refresh_list()
                self.show_toast(tr("project_removed"))

    def _on_about(self):
        """Shows About dialog."""
        QMessageBox.about(
            self,
            tr("about_title"),
            tr("about_text"),
        )

    def _on_settings(self):
        """Opens Settings dialog."""
        from .dialogs import SettingsDialog

        def on_save(config):
            save_config(config)
            self.show_toast(tr("settings_saved"))

        def on_export():
            if not self.config.sync_path:
                QMessageBox.warning(self, tr("export_title"), tr("no_sync_folder"))
                return
            success, msg = export_to_sync(self.config)
            if success:
                QMessageBox.information(self, tr("export_title"), msg)
            else:
                QMessageBox.warning(self, tr("export_title"), msg)

        def on_import():
            if not self.config.sync_path:
                QMessageBox.warning(self, tr("import_title"), tr("no_sync_folder"))
                return
            success, msg = import_from_sync(self.config)
            if success:
                # Reload config to ensure UI shows current state
                self.config = load_config()
                self._update_category_filter()
                self._refresh_list()
                QMessageBox.information(self, tr("import_title"), msg)
            else:
                QMessageBox.warning(self, tr("import_title"), msg)

        dialog = SettingsDialog(
            self, self.config, on_save=on_save, on_export=on_export, on_import=on_import
        )
        if dialog.exec() == QDialog.Accepted:
            self.config = load_config()
            self.process_manager.terminal_cmd = self.config.terminal_command
            self._update_category_filter()
            self._refresh_list()


def main():
    """Called from __init__.py for backwards compatibility."""
    from .main import main as entry_main

    entry_main()
