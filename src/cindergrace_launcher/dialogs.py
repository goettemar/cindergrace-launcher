"""
Dialog-Klassen für Cindergrace Launcher
Ausgelagert aus cockpit.py für bessere Wartbarkeit
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib
from pathlib import Path
from typing import Optional, Callable, List
import os

from .config import Config, Project
from .providers import LLMProvider
from .process_manager import validate_command


class ProjectDialog(Adw.Window):
    """Dialog zum Hinzufügen/Bearbeiten eines Projekts"""

    def __init__(
        self,
        parent: Gtk.Window,
        config: Config,
        project: Optional[Project] = None,
        on_save: Optional[Callable[[Project], None]] = None
    ):
        super().__init__()
        self.config = config
        self.project = project
        self.on_save = on_save
        self.is_edit = project is not None

        self.set_title("Projekt bearbeiten" if self.is_edit else "Neues Projekt")
        self.set_default_size(500, 550)
        self.set_modal(True)
        self.set_transient_for(parent)

        self._build_ui()

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)

        cancel_btn = Gtk.Button(label="Abbrechen")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)

        save_btn = Gtk.Button(label="Speichern")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save)
        header.pack_end(save_btn)

        main_box.append(header)

        # Scrollable Content
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(20)
        content.set_margin_bottom(20)

        # Name
        name_group = Adw.PreferencesGroup(title="Projektname")
        self.name_entry = Adw.EntryRow(title="Name")
        if self.project:
            self.name_entry.set_text(self.project.name)
        name_group.add(self.name_entry)
        content.append(name_group)

        # Pfad
        path_group = Adw.PreferencesGroup(title="Projektordner")

        root_info = Gtk.Label()
        root_info.set_markup(f'<span size="small" foreground="#888">Projekt-Root: {self.config.project_root}</span>')
        root_info.set_halign(Gtk.Align.START)
        root_info.set_margin_start(12)
        root_info.set_margin_bottom(5)
        path_group.add(root_info)

        path_row = Adw.ActionRow(title="Ordner auswählen")
        self.path_entry = Gtk.Entry()
        self.path_entry.set_hexpand(True)
        self.path_entry.set_valign(Gtk.Align.CENTER)
        self.path_entry.set_placeholder_text("Ordnername (relativ)")
        if self.project:
            self.path_entry.set_text(self.project.relative_path)

        browse_btn = Gtk.Button(icon_name="folder-open-symbolic")
        browse_btn.set_valign(Gtk.Align.CENTER)
        browse_btn.add_css_class("flat")
        browse_btn.connect("clicked", self._on_browse)

        path_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        path_box.append(self.path_entry)
        path_box.append(browse_btn)
        path_row.set_child(path_box)
        path_group.add(path_row)
        content.append(path_group)

        # Kategorie
        cat_group = Adw.PreferencesGroup(title="Kategorie (optional)")
        self.cat_entry = Adw.EntryRow(title="Kategorie")
        self.cat_entry.set_text(self.project.category if self.project and self.project.category else "")
        cat_group.add(self.cat_entry)
        content.append(cat_group)

        # Custom Start Command
        start_group = Adw.PreferencesGroup(title="Start-Befehl (optional)")
        self.start_entry = Adw.EntryRow(title="Befehl")
        self.start_entry.set_text(self.project.custom_start_command if self.project else "")
        start_group.add(self.start_entry)

        start_hint = Gtk.Label()
        start_hint.set_markup(f'<span size="small" foreground="#888">Leer lassen für: {self.config.default_start_command}</span>')
        start_hint.set_halign(Gtk.Align.START)
        start_hint.set_margin_start(12)
        start_group.add(start_hint)
        content.append(start_group)

        # Default Provider
        provider_group = Adw.PreferencesGroup(title="Standard-Provider")
        enabled_providers = self.config.get_enabled_providers()

        self.provider_dropdown = Adw.ComboRow(title="LLM CLI")
        provider_model = Gtk.StringList()
        self.provider_ids = []
        selected_idx = 0

        for i, p in enumerate(enabled_providers):
            provider_model.append(p.name)
            self.provider_ids.append(p.id)
            if self.project and self.project.default_provider == p.id:
                selected_idx = i
            elif not self.project and p.id == self.config.last_provider:
                selected_idx = i

        self.provider_dropdown.set_model(provider_model)
        self.provider_dropdown.set_selected(selected_idx)
        provider_group.add(self.provider_dropdown)
        content.append(provider_group)

        scroll.set_child(content)
        main_box.append(scroll)

    def _on_browse(self, btn):
        file_dialog = Gtk.FileDialog()
        file_dialog.set_title("Projektordner auswählen")

        if self.config.project_root and os.path.isdir(self.config.project_root):
            file_dialog.set_initial_folder(Gio.File.new_for_path(self.config.project_root))
        else:
            file_dialog.set_initial_folder(Gio.File.new_for_path(str(Path.home())))

        file_dialog.select_folder(self, None, self._on_folder_selected)

    def _on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                selected_path = folder.get_path()
                # Relativen Pfad zum project_root berechnen
                if self.config.project_root and selected_path.startswith(self.config.project_root):
                    relative = os.path.relpath(selected_path, self.config.project_root)
                    self.path_entry.set_text(relative)
                else:
                    # Außerhalb des project_root - nur Ordnername verwenden
                    self.path_entry.set_text(Path(selected_path).name)
        except GLib.Error:
            # Dialog wurde abgebrochen oder Fehler bei Ordnerauswahl
            pass

    def _on_save(self, btn):
        name = self.name_entry.get_text().strip()
        relative_path = self.path_entry.get_text().strip()
        category = self.cat_entry.get_text().strip() or "Allgemein"
        start_cmd = self.start_entry.get_text().strip()

        if not name:
            self._show_error("Bitte einen Namen eingeben")
            return

        if not relative_path:
            self._show_error("Bitte einen Ordner auswählen")
            return

        # SECURITY: Start-Befehl validieren
        if start_cmd:
            is_valid, error = validate_command(start_cmd)
            if not is_valid:
                self._show_error(f"Ungültiger Start-Befehl: {error}")
                return

        selected_idx = self.provider_dropdown.get_selected()
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

        self.close()

    def _show_error(self, message: str):
        toast = Adw.Toast(title=message)
        toast.set_timeout(3)
        # Find toast overlay in parent
        parent = self.get_transient_for()
        if hasattr(parent, 'toast_overlay'):
            parent.toast_overlay.add_toast(toast)


class ProviderDialog(Adw.Window):
    """Dialog zum Hinzufügen/Bearbeiten eines Providers"""

    def __init__(
        self,
        parent: Gtk.Window,
        provider: Optional[LLMProvider] = None,
        on_save: Optional[Callable[[LLMProvider], None]] = None
    ):
        super().__init__()
        self.provider = provider
        self.on_save = on_save
        self.is_edit = provider is not None

        self.set_title("Provider bearbeiten" if self.is_edit else "Neuer Provider")
        self.set_default_size(450, 550)
        self.set_modal(True)
        self.set_transient_for(parent)

        self._build_ui()

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)

        cancel_btn = Gtk.Button(label="Abbrechen")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)

        save_btn = Gtk.Button(label="Speichern")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save)
        header.pack_end(save_btn)

        main_box.append(header)

        # Scrollable Content
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(20)
        content.set_margin_bottom(20)

        # Basis-Infos
        basic_group = Adw.PreferencesGroup(title="Grundeinstellungen")

        self.id_entry = Adw.EntryRow(title="ID (eindeutig)")
        self.id_entry.set_text(self.provider.id if self.provider else "")
        if self.is_edit:
            self.id_entry.set_sensitive(False)
        basic_group.add(self.id_entry)

        self.name_entry = Adw.EntryRow(title="Anzeigename")
        self.name_entry.set_text(self.provider.name if self.provider else "")
        basic_group.add(self.name_entry)

        content.append(basic_group)

        # Befehl
        cmd_group = Adw.PreferencesGroup(title="Befehl")

        self.cmd_entry = Adw.EntryRow(title="CLI-Befehl")
        self.cmd_entry.set_text(self.provider.command if self.provider else "")
        cmd_group.add(self.cmd_entry)

        self.skip_flag_entry = Adw.EntryRow(title="Skip-Permissions Flag")
        self.skip_flag_entry.set_text(self.provider.skip_permissions_flag if self.provider else "")
        cmd_group.add(self.skip_flag_entry)

        content.append(cmd_group)

        # UI
        ui_group = Adw.PreferencesGroup(title="Darstellung")

        self.icon_entry = Adw.EntryRow(title="Icon-Name")
        self.icon_entry.set_text(self.provider.icon if self.provider else "utilities-terminal-symbolic")
        ui_group.add(self.icon_entry)

        self.color_entry = Adw.EntryRow(title="CSS Farbe")
        self.color_entry.set_text(self.provider.color if self.provider else "#666666")
        ui_group.add(self.color_entry)

        content.append(ui_group)

        # Status
        status_group = Adw.PreferencesGroup(title="Status")

        self.enabled_switch = Adw.SwitchRow(title="Aktiviert")
        self.enabled_switch.set_active(self.provider.enabled if self.provider else True)
        status_group.add(self.enabled_switch)

        content.append(status_group)

        scroll.set_child(content)
        main_box.append(scroll)

    def _on_save(self, btn):
        provider_id = self.id_entry.get_text().strip()
        name = self.name_entry.get_text().strip()
        command = self.cmd_entry.get_text().strip()

        if not provider_id:
            return
        if not name:
            return
        if not command:
            return

        # SECURITY: Befehle validieren
        is_valid, error = validate_command(command)
        if not is_valid:
            return

        skip_flag = self.skip_flag_entry.get_text().strip()
        if skip_flag:
            is_valid, error = validate_command(skip_flag)
            if not is_valid:
                return

        new_provider = LLMProvider(
            id=provider_id,
            name=name,
            command=command,
            icon=self.icon_entry.get_text().strip() or "utilities-terminal-symbolic",
            color=self.color_entry.get_text().strip() or "#666666",
            enabled=self.enabled_switch.get_active(),
            skip_permissions_flag=skip_flag
        )

        if self.on_save:
            self.on_save(new_provider)

        self.close()


class SettingsDialog(Adw.Window):
    """Einstellungs-Dialog"""

    def __init__(
        self,
        parent: Gtk.Window,
        config: Config,
        on_save: Optional[Callable[[Config], None]] = None,
        on_export: Optional[Callable[[], None]] = None,
        on_import: Optional[Callable[[], None]] = None
    ):
        super().__init__()
        self.config = config
        self.on_save = on_save
        self.on_export_callback = on_export
        self.on_import_callback = on_import

        self.set_title("Einstellungen")
        self.set_default_size(650, 750)
        self.set_modal(True)
        self.set_transient_for(parent)

        self._build_ui()

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)

        close_btn = Gtk.Button(label="Schließen")
        close_btn.add_css_class("suggested-action")
        close_btn.connect("clicked", self._on_close)
        header.pack_end(close_btn)

        main_box.append(header)

        # Scrollable Content
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(20)
        content.set_margin_bottom(20)

        # Pfade
        paths_group = Adw.PreferencesGroup(title="Pfade")

        self.root_entry = Adw.EntryRow(title="Projekt-Root")
        self.root_entry.set_text(self.config.project_root)
        paths_group.add(self.root_entry)

        self.sync_entry = Adw.EntryRow(title="Sync-Ordner (Google Drive etc.)")
        self.sync_entry.set_text(self.config.sync_path)
        paths_group.add(self.sync_entry)

        content.append(paths_group)

        # Terminal
        term_group = Adw.PreferencesGroup(title="Terminal")

        self.term_entry = Adw.EntryRow(title="Terminal-Befehl")
        self.term_entry.set_text(self.config.terminal_command)
        term_group.add(self.term_entry)

        self.start_entry = Adw.EntryRow(title="Standard Start-Befehl")
        self.start_entry.set_text(self.config.default_start_command)
        term_group.add(self.start_entry)

        content.append(term_group)

        # Sync
        from config import get_sync_password, set_sync_password

        sync_group = Adw.PreferencesGroup(title="Sync")

        self.password_entry = Adw.PasswordEntryRow(title="Sync-Passwort")
        current_pw = get_sync_password()
        if current_pw:
            self.password_entry.set_text(current_pw)
        sync_group.add(self.password_entry)

        sync_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        sync_buttons.set_margin_top(10)

        export_btn = Gtk.Button(label="Exportieren")
        export_btn.add_css_class("suggested-action")
        export_btn.connect("clicked", self._on_export)
        sync_buttons.append(export_btn)

        import_btn = Gtk.Button(label="Importieren")
        import_btn.connect("clicked", self._on_import)
        sync_buttons.append(import_btn)

        sync_group.add(sync_buttons)
        content.append(sync_group)

        # Provider (simplified - just count)
        provider_group = Adw.PreferencesGroup(title="LLM Provider")

        provider_info = Adw.ActionRow(title="Konfigurierte Provider")
        provider_info.set_subtitle(f"{len(self.config.providers)} Provider konfiguriert")
        provider_group.add(provider_info)

        content.append(provider_group)

        scroll.set_child(content)
        main_box.append(scroll)

    def _save_settings(self):
        from config import set_sync_password

        self.config.local.project_root = self.root_entry.get_text().strip()
        self.config.local.sync_path = self.sync_entry.get_text().strip()
        self.config.local.terminal_command = self.term_entry.get_text().strip()
        self.config.local.default_start_command = self.start_entry.get_text().strip()

        # Passwort speichern
        password = self.password_entry.get_text()
        if password:
            set_sync_password(password)

        if self.on_save:
            self.on_save(self.config)

    def _on_export(self, btn):
        self._save_settings()
        if self.on_export_callback:
            self.on_export_callback()

    def _on_import(self, btn):
        self._save_settings()
        if self.on_import_callback:
            self.on_import_callback()

    def _on_close(self, btn):
        self._save_settings()
        self.close()
