"""
Cindergrace Launcher - Hauptfenster
GTK4/Adwaita-basierte GUI zur Verwaltung von LLM CLI Sessions
Unterstützt: Vollständig konfigurierbare Provider + Sync
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio, Pango, Gdk
from pathlib import Path
import os
import subprocess

# Cindergrace Branding
BRAND_COLORS = {
    "blue_dark": "#1E5AA8",
    "blue_light": "#7CC8FF",
    "blue_hover": "#2d6fc0",
}

# Logo-Pfad (absolut)
_script_dir = Path(__file__).resolve().parent  # src/
_project_root = _script_dir.parent.parent  # ~/projekte/
LOGO_PATH = _project_root / "cindergrace_projects" / "logo"

# GTK CSS für Cindergrace-Branding
CINDERGRACE_CSS = """
/* Favoriten-Stern in Markenfarbe */
.cg-favorite {
    color: #1E5AA8;
}

.cg-favorite:hover {
    color: #2d6fc0;
}

/* Suggested-Action Buttons in Markenfarbe */
.suggested-action {
    background-color: #1E5AA8;
    color: white;
}

.suggested-action:hover {
    background-color: #2d6fc0;
}

/* Logo styling */
.cg-logo {
    margin: 4px;
}

/* Accent-Farbe für aktive Elemente */
.accent {
    color: #1E5AA8;
}
"""

from .config import (
    Config, Project, load_config, save_config, add_project, remove_project, update_project,
    export_to_sync, import_from_sync, get_sync_password, set_sync_password
)
from .process_manager import ProcessManager, validate_command
from .providers import LLMProvider, get_initial_providers
from .dialogs import ProjectDialog, ProviderDialog, SettingsDialog


class ProjectRow(Adw.ActionRow):
    """Eine Zeile in der Projektliste"""

    def __init__(self, project: Project, index: int, is_running: bool, running_provider: str, callbacks: dict, config: Config):
        super().__init__()
        self.project = project
        self.index = index
        self.callbacks = callbacks
        self.is_running = is_running
        self.running_provider = running_provider
        self.config = config

        # Absoluter Pfad für Anzeige
        abs_path = config.get_project_absolute_path(project)

        # Titel und Untertitel
        self.set_title(GLib.markup_escape_text(project.name))
        subtitle = abs_path
        if project.category and project.category != "Allgemein":
            subtitle += f"  [{project.category}]"
        self.set_subtitle(subtitle)

        # Favorit-Icon als Prefix
        self.fav_btn = Gtk.Button()
        self.fav_btn.add_css_class("flat")
        self.fav_btn.set_valign(Gtk.Align.CENTER)
        self._update_favorite_icon()
        self.fav_btn.connect("clicked", self._on_toggle_favorite)
        self.add_prefix(self.fav_btn)

        # Status-Prefix (zeigt Provider wenn läuft)
        self.status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self._update_status_display()
        self.add_prefix(self.status_box)

        # Buttons
        self._create_buttons()

        # Ausgegrauter Stil wenn versteckt
        if project.hidden:
            self.add_css_class("dim-label")

    def _update_favorite_icon(self):
        icon_name = "starred-symbolic" if self.project.favorite else "non-starred-symbolic"
        self.fav_btn.set_icon_name(icon_name)
        self.fav_btn.set_tooltip_text("Aus Favoriten entfernen" if self.project.favorite else "Zu Favoriten hinzufügen")
        # Brand-Farbe für aktive Favoriten
        if self.project.favorite:
            self.fav_btn.add_css_class("cg-favorite")
        else:
            self.fav_btn.remove_css_class("cg-favorite")

    def _on_toggle_favorite(self, btn):
        self.callbacks["toggle_favorite"](self.index)

    def _update_status_display(self):
        while self.status_box.get_first_child():
            self.status_box.remove(self.status_box.get_first_child())

        if self.is_running and self.running_provider:
            provider = self.config.get_provider(self.running_provider)
            if provider:
                icon = Gtk.Image.new_from_icon_name(provider.icon)
                icon.add_css_class("success")
                self.status_box.append(icon)

                label = Gtk.Label(label=provider.name)
                label.add_css_class("caption")
                label.add_css_class("success")
                self.status_box.append(label)

                self.set_tooltip_text(f"{provider.name} läuft")
        else:
            icon = Gtk.Image.new_from_icon_name("media-playback-stop-symbolic")
            self.status_box.append(icon)
            self.set_tooltip_text("Gestoppt")

    def _create_buttons(self):
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        button_box.set_valign(Gtk.Align.CENTER)

        # Absoluter Pfad für Operationen
        abs_path = self.config.get_project_absolute_path(self.project)

        if self.is_running:
            # Fokus-Button
            focus_btn = Gtk.Button(icon_name="view-reveal-symbolic")
            focus_btn.set_tooltip_text("Fenster in Vordergrund")
            focus_btn.add_css_class("flat")
            focus_btn.connect("clicked", lambda b: self.callbacks["focus"](abs_path))
            button_box.append(focus_btn)

            # Stop-Button
            stop_btn = Gtk.Button(icon_name="media-playback-stop-symbolic")
            stop_btn.set_tooltip_text("Session beenden")
            stop_btn.add_css_class("flat")
            stop_btn.add_css_class("error")
            stop_btn.connect("clicked", lambda b: self.callbacks["stop"](abs_path))
            button_box.append(stop_btn)
        else:
            # Start-Button (für custom start command)
            start_cmd = self.config.get_start_command(self.project)
            start_btn = Gtk.Button(icon_name="media-playback-start-symbolic")
            start_btn.set_tooltip_text(f"Starten: {start_cmd}")
            start_btn.add_css_class("flat")
            start_btn.add_css_class("accent")
            start_btn.connect("clicked", lambda b: self.callbacks["start_custom"](self.project))
            button_box.append(start_btn)

            # Provider-Auswahl Dropdown
            enabled_providers = self.config.get_enabled_providers()

            if len(enabled_providers) > 1:
                provider_menu = Gio.Menu()
                for provider in enabled_providers:
                    provider_menu.append(provider.name, f"row.start-{provider.id}")

                menu_btn = Gtk.MenuButton()
                menu_btn.set_icon_name("utilities-terminal-symbolic")
                menu_btn.set_menu_model(provider_menu)
                menu_btn.set_tooltip_text("LLM CLI starten")
                menu_btn.add_css_class("flat")
                menu_btn.add_css_class("success")

                action_group = Gio.SimpleActionGroup()
                for provider in enabled_providers:
                    action = Gio.SimpleAction.new(f"start-{provider.id}", None)
                    action.connect("activate", self._on_start_provider, provider.id)
                    action_group.add_action(action)

                self.insert_action_group("row", action_group)
                button_box.append(menu_btn)
            elif len(enabled_providers) == 1:
                provider = enabled_providers[0]
                llm_btn = Gtk.Button(icon_name="utilities-terminal-symbolic")
                llm_btn.set_tooltip_text(f"{provider.name} starten")
                llm_btn.add_css_class("flat")
                llm_btn.add_css_class("success")
                llm_btn.connect("clicked", lambda b: self.callbacks["start"](
                    abs_path, self.project.name, provider.id
                ))
                button_box.append(llm_btn)

        # Bearbeiten-Button
        edit_btn = Gtk.Button(icon_name="document-edit-symbolic")
        edit_btn.set_tooltip_text("Bearbeiten")
        edit_btn.add_css_class("flat")
        edit_btn.connect("clicked", lambda b: self.callbacks["edit"](self.index))
        button_box.append(edit_btn)

        # Verstecken/Anzeigen Button
        hide_icon = "view-reveal-symbolic" if self.project.hidden else "view-conceal-symbolic"
        hide_btn = Gtk.Button(icon_name=hide_icon)
        hide_btn.set_tooltip_text("Einblenden" if self.project.hidden else "Ausblenden")
        hide_btn.add_css_class("flat")
        hide_btn.connect("clicked", lambda b: self.callbacks["toggle_hidden"](self.index))
        button_box.append(hide_btn)

        # Löschen-Button
        delete_btn = Gtk.Button(icon_name="user-trash-symbolic")
        delete_btn.set_tooltip_text("Entfernen")
        delete_btn.add_css_class("flat")
        delete_btn.connect("clicked", lambda b: self.callbacks["delete"](self.index))
        button_box.append(delete_btn)

        self.add_suffix(button_box)

    def _on_start_provider(self, action, param, provider_id):
        abs_path = self.config.get_project_absolute_path(self.project)
        self.callbacks["start"](abs_path, self.project.name, provider_id)


class LauncherWindow(Adw.ApplicationWindow):
    """Hauptfenster des Cindergrace Launcher"""

    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Cindergrace Launcher")
        self.set_default_size(900, 650)

        self.config = load_config()
        self.process_manager = ProcessManager(
            terminal_cmd=self.config.terminal_command
        )

        self.search_text = ""
        self.filter_category = None

        # Toast Overlay als Hauptcontainer
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Hauptcontainer
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay.set_child(main_box)

        # Header Bar
        header = Adw.HeaderBar()

        # Custom Title mit Logo
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_box.set_halign(Gtk.Align.CENTER)

        # Mini-Logo laden
        logo_file = LOGO_PATH / "logo_v2_1024_transparent.png"
        if logo_file.exists():
            try:
                from gi.repository import GdkPixbuf
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(logo_file), 28, 28, True
                )
                logo_img = Gtk.Image.new_from_pixbuf(pixbuf)
                logo_img.add_css_class("cg-logo")
                title_box.append(logo_img)
            except (GLib.Error, OSError):
                # Logo konnte nicht geladen werden - Header ohne Logo anzeigen
                pass

        window_title = Adw.WindowTitle(title="Cindergrace Launcher", subtitle="Multi-LLM Projekt-Manager")
        title_box.append(window_title)
        header.set_title_widget(title_box)

        # Neues Projekt Button
        add_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_btn.set_tooltip_text("Neues Projekt hinzufügen")
        add_btn.connect("clicked", self._on_add_project)
        header.pack_start(add_btn)

        # Toggle Hidden Button
        self.show_hidden_btn = Gtk.ToggleButton(icon_name="view-reveal-symbolic")
        self.show_hidden_btn.set_tooltip_text("Versteckte Projekte anzeigen")
        self.show_hidden_btn.set_active(self.config.show_hidden)
        self.show_hidden_btn.connect("toggled", self._on_toggle_show_hidden)
        header.pack_start(self.show_hidden_btn)

        # Refresh Button
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Status aktualisieren")
        refresh_btn.connect("clicked", lambda b: self._refresh_list())
        header.pack_end(refresh_btn)

        # Einstellungen Button
        settings_btn = Gtk.Button(icon_name="emblem-system-symbolic")
        settings_btn.set_tooltip_text("Einstellungen")
        settings_btn.connect("clicked", self._on_settings)
        header.pack_end(settings_btn)

        # About Button
        about_btn = Gtk.Button(icon_name="help-about-symbolic")
        about_btn.set_tooltip_text("Über Cindergrace Launcher")
        about_btn.connect("clicked", self._on_about)
        header.pack_end(about_btn)

        main_box.append(header)

        # Such- und Filterleiste
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        filter_box.set_margin_start(15)
        filter_box.set_margin_end(15)
        filter_box.set_margin_top(10)

        # Suchfeld
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Projekte suchen...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        filter_box.append(self.search_entry)

        # Kategorie-Filter
        self.category_dropdown = Gtk.DropDown()
        self.category_dropdown.set_tooltip_text("Nach Kategorie filtern")
        self._update_category_filter()
        self.category_dropdown.connect("notify::selected", self._on_category_changed)
        filter_box.append(self.category_dropdown)

        main_box.append(filter_box)

        # Status-Leiste
        self.status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.status_bar.set_margin_start(15)
        self.status_bar.set_margin_end(15)
        self.status_bar.set_margin_top(10)
        self.status_bar.set_margin_bottom(5)

        self.status_label = Gtk.Label()
        self.status_label.set_halign(Gtk.Align.START)
        self.status_bar.append(self.status_label)

        self.provider_badges = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.provider_badges.set_halign(Gtk.Align.END)
        self.provider_badges.set_hexpand(True)
        self.status_bar.append(self.provider_badges)

        main_box.append(self.status_bar)

        # Content mit Clamp
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_vexpand(True)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_margin_start(15)
        self.list_box.set_margin_end(15)
        self.list_box.set_margin_top(10)
        self.list_box.set_margin_bottom(15)

        scroll.set_child(self.list_box)
        clamp.set_child(scroll)
        main_box.append(clamp)

        # Leere-Liste Platzhalter
        self.empty_placeholder = Adw.StatusPage()
        self.empty_placeholder.set_icon_name("folder-symbolic")
        self.empty_placeholder.set_title("Keine Projekte")
        self.empty_placeholder.set_description("Klicke auf '+' um ein Projekt hinzuzufügen")
        self.empty_placeholder.set_vexpand(True)
        self.empty_placeholder.set_visible(False)
        main_box.append(self.empty_placeholder)

        self._refresh_list()
        GLib.timeout_add_seconds(5, self._auto_refresh)

    def _update_category_filter(self):
        """Aktualisiert das Kategorie-Dropdown"""
        categories = set(["Alle"])
        for p in self.config.projects:
            if p.category:
                categories.add(p.category)

        model = Gtk.StringList()
        for cat in sorted(categories):
            model.append(cat)
        self.category_dropdown.set_model(model)

    def _on_search_changed(self, entry):
        self.search_text = entry.get_text().lower()
        self._refresh_list()

    def _on_category_changed(self, dropdown, param):
        idx = dropdown.get_selected()
        model = dropdown.get_model()
        if idx >= 0 and model:
            selected = model.get_string(idx)
            self.filter_category = None if selected == "Alle" else selected
            self._refresh_list()

    def _on_toggle_show_hidden(self, btn):
        self.config.show_hidden = btn.get_active()
        save_config(self.config)
        self._refresh_list()

    def _filter_projects(self) -> list:
        """Filtert Projekte nach Suchtext, Kategorie und Hidden-Status"""
        filtered = []
        for i, p in enumerate(self.config.projects):
            # Hidden-Filter
            if p.hidden and not self.config.show_hidden:
                continue

            # Suchtext-Filter (inkl. relativem Pfad)
            if self.search_text:
                abs_path = self.config.get_project_absolute_path(p)
                if (self.search_text not in p.name.lower() and
                    self.search_text not in abs_path.lower() and
                    self.search_text not in p.relative_path.lower() and
                    self.search_text not in p.category.lower()):
                    continue

            # Kategorie-Filter
            if self.filter_category and p.category != self.filter_category:
                continue

            filtered.append((i, p))

        # Sortierung: Favoriten zuerst, dann alphabetisch
        filtered.sort(key=lambda x: (not x[1].favorite, x[1].name.lower()))
        return filtered

    def _refresh_list(self):
        """Aktualisiert die Projektliste"""
        while True:
            row = self.list_box.get_row_at_index(0)
            if row is None:
                break
            self.list_box.remove(row)

        self.process_manager.cleanup_dead_sessions()

        running_count = 0
        provider_counts = {}

        filtered_projects = self._filter_projects()

        if not filtered_projects:
            self.list_box.set_visible(False)
            self.empty_placeholder.set_visible(True)
        else:
            self.list_box.set_visible(True)
            self.empty_placeholder.set_visible(False)

            callbacks = {
                "start": self._start_session,
                "start_custom": self._start_custom,
                "stop": self._stop_session,
                "focus": self._focus_session,
                "edit": self._edit_project,
                "delete": self._delete_project,
                "toggle_hidden": self._toggle_hidden,
                "toggle_favorite": self._toggle_favorite,
            }

            for orig_index, project in filtered_projects:
                abs_path = self.config.get_project_absolute_path(project)
                is_running = self.process_manager.is_running(abs_path)
                running_provider = None

                if is_running:
                    running_count += 1
                    running_provider = self.process_manager.get_session_provider(abs_path)
                    if running_provider:
                        provider_counts[running_provider] = provider_counts.get(running_provider, 0) + 1

                row = ProjectRow(project, orig_index, is_running, running_provider, callbacks, self.config)
                self.list_box.append(row)

        total = len(self.config.projects)
        visible = len(filtered_projects)
        hidden_count = sum(1 for p in self.config.projects if p.hidden)

        status_text = f"<b>{visible}</b>/{total} Projekte"
        if hidden_count > 0:
            status_text += f" | <span foreground='#888'>{hidden_count} versteckt</span>"
        status_text += f" | <span foreground='#4CAF50'><b>{running_count}</b> aktiv</span>"
        self.status_label.set_markup(status_text)

        # Provider-Badges
        while self.provider_badges.get_first_child():
            self.provider_badges.remove(self.provider_badges.get_first_child())

        for provider_id, count in provider_counts.items():
            provider = self.config.get_provider(provider_id)
            if provider:
                badge = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
                badge.add_css_class("card")
                badge.set_margin_start(2)
                badge.set_margin_end(2)

                icon = Gtk.Image.new_from_icon_name(provider.icon)
                icon.set_margin_start(5)
                badge.append(icon)

                label = Gtk.Label(label=str(count))
                label.set_margin_end(5)
                badge.append(label)

                self.provider_badges.append(badge)

    def _auto_refresh(self):
        """Auto-Refresh: Nur Status aktualisieren, nicht neu aufbauen"""
        self.process_manager.cleanup_dead_sessions()
        self._update_status_bar()
        return True

    def _update_status_bar(self):
        """Aktualisiert nur die Status-Leiste (effizient)"""
        running_count = 0
        provider_counts = {}

        for project in self.config.projects:
            abs_path = self.config.get_project_absolute_path(project)
            if self.process_manager.is_running(abs_path):
                running_count += 1
                provider_id = self.process_manager.get_session_provider(abs_path)
                if provider_id:
                    provider_counts[provider_id] = provider_counts.get(provider_id, 0) + 1

        # Status-Text aktualisieren
        total = len(self.config.projects)
        visible = len(self._filter_projects())
        hidden_count = sum(1 for p in self.config.projects if p.hidden)

        status_text = f"<b>{visible}</b>/{total} Projekte"
        if hidden_count > 0:
            status_text += f" | <span foreground='#888'>{hidden_count} versteckt</span>"
        status_text += f" | <span foreground='#4CAF50'><b>{running_count}</b> aktiv</span>"
        self.status_label.set_markup(status_text)

        # Provider-Badges aktualisieren
        while self.provider_badges.get_first_child():
            self.provider_badges.remove(self.provider_badges.get_first_child())

        for provider_id, count in provider_counts.items():
            provider = self.config.get_provider(provider_id)
            if provider:
                badge = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
                badge.add_css_class("card")
                badge.set_margin_start(2)
                badge.set_margin_end(2)

                icon = Gtk.Image.new_from_icon_name(provider.icon)
                icon.set_margin_start(5)
                badge.append(icon)

                label = Gtk.Label(label=str(count))
                label.set_margin_end(5)
                badge.append(label)

                self.provider_badges.append(badge)

    def _start_custom(self, project: Project):
        """Startet den Custom Start-Befehl für ein Projekt"""
        abs_path = self.config.get_project_absolute_path(project)
        start_cmd = self.config.get_start_command(project)

        # SECURITY: Start-Befehl validieren
        is_valid, error = validate_command(start_cmd)
        if not is_valid:
            self._show_toast(f"Ungültiger Start-Befehl: {error}")
            return

        # Prüfe ob Befehl/Datei existiert
        if start_cmd.startswith("./"):
            check_path = os.path.join(abs_path, start_cmd[2:])
            if not os.path.exists(check_path):
                self._show_toast(f"Nicht gefunden: {start_cmd}")
                return

        try:
            subprocess.Popen(
                [self.config.terminal_command, f"--working-directory={abs_path}", "--", "bash", "-c", f"{start_cmd}; exec bash"],
                start_new_session=True
            )
            self._show_toast(f"Gestartet: {project.name}")
        except FileNotFoundError:
            self._show_toast(f"Terminal nicht gefunden: {self.config.terminal_command}")
        except subprocess.SubprocessError as e:
            self._show_toast(f"Prozess-Fehler: {e}")

    def _start_session(self, path: str, name: str, provider_id: str):
        """Startet eine LLM CLI Session"""
        provider = self.config.get_provider(provider_id)
        if not provider:
            self._show_toast(f"Provider nicht gefunden: {provider_id}")
            return

        success, message = self.process_manager.start_session(
            path, name, provider_id, provider.command,
            provider.name, provider.skip_permissions_flag
        )

        if success:
            self.config.last_provider = provider_id
            save_config(self.config)
            self._show_toast(f"{provider.name} gestartet: {name}")
            # Starte asynchrones Window-Polling (200ms Intervall)
            GLib.timeout_add(200, self.process_manager.poll_for_window)
        else:
            self._show_toast(f"Fehler: {message}")
        self._refresh_list()

    def _stop_session(self, path: str):
        success, message = self.process_manager.stop_session(path)
        if success:
            self._show_toast("Session beendet")
        else:
            self._show_toast(f"Fehler: {message}")
        self._refresh_list()

    def _focus_session(self, path: str):
        success, message = self.process_manager.focus_window(path)
        if not success:
            self._show_toast(message)

    def _toggle_hidden(self, index: int):
        if 0 <= index < len(self.config.projects):
            self.config.projects[index].hidden = not self.config.projects[index].hidden
            save_config(self.config)
            self._refresh_list()

    def _toggle_favorite(self, index: int):
        if 0 <= index < len(self.config.projects):
            self.config.projects[index].favorite = not self.config.projects[index].favorite
            save_config(self.config)
            self._refresh_list()

    def _on_add_project(self, button):
        self._show_project_dialog(None, -1)

    def _edit_project(self, index: int):
        if 0 <= index < len(self.config.projects):
            project = self.config.projects[index]
            self._show_project_dialog(project, index)

    def _show_project_dialog(self, project: Project, index: int):
        """Zeigt Dialog zum Hinzufügen/Bearbeiten eines Projekts"""
        is_edit = project is not None

        def on_save(new_project: Project):
            if is_edit:
                self.config = update_project(self.config, index, new_project)
                self._show_toast(f"Projekt aktualisiert: {new_project.name}")
            else:
                self.config = add_project(self.config, new_project)
                self._show_toast(f"Projekt hinzugefügt: {new_project.name}")

            self._update_category_filter()
            self._refresh_list()

        dialog = ProjectDialog(
            parent=self,
            config=self.config,
            project=project,
            on_save=on_save
        )
        dialog.present()

    def _delete_project(self, index: int):
        if 0 <= index < len(self.config.projects):
            project = self.config.projects[index]

            dialog = Adw.MessageDialog(
                transient_for=self,
                heading="Projekt entfernen?",
                body=f"Möchtest du '{project.name}' aus der Liste entfernen?\n\nDer Projektordner wird nicht gelöscht."
            )
            dialog.add_response("cancel", "Abbrechen")
            dialog.add_response("delete", "Entfernen")
            dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.connect("response", self._on_delete_response, index)
            dialog.present()

    def _on_delete_response(self, dialog, response, index):
        if response == "delete":
            self.config = remove_project(self.config, index)
            self._update_category_filter()
            self._refresh_list()
            self._show_toast("Projekt entfernt")

    def _on_about(self, button):
        """Zeigt About-Dialog mit Cindergrace-Branding"""
        about = Adw.AboutWindow()
        about.set_transient_for(self)

        about.set_application_name("Cindergrace Launcher")
        about.set_application_icon("utilities-terminal")
        about.set_developer_name("Cindergrace Team")
        about.set_version("1.0.0")
        about.set_website("https://github.com/cindergrace")
        about.set_copyright("© 2025 Cindergrace")
        about.set_license_type(Gtk.License.MIT_X11)
        about.set_comments("Multi-LLM Projekt-Manager\nVerwaltet Claude, Codex, Gemini und andere KI-CLIs")

        # Logo laden wenn verfügbar
        logo_file = LOGO_PATH / "logo_v2_1024_transparent.png"
        if logo_file.exists():
            try:
                from gi.repository import GdkPixbuf
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(logo_file), 128, 128, True
                )
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                about.set_icon(texture)
            except (GLib.Error, OSError):
                pass  # Fallback auf Default-Icon

        about.set_developers(["Cindergrace Team"])
        about.add_credit_section(
            "Unterstützte KI-CLIs",
            ["Claude (Anthropic)", "Codex (OpenAI)", "Gemini (Google)"]
        )

        about.present()

    def _on_settings(self, button):
        """Öffnet Einstellungs-Dialog mit Provider CRUD und Sync"""
        dialog = Adw.Window()
        dialog.set_title("Einstellungen")
        dialog.set_default_size(650, 750)
        dialog.set_modal(True)
        dialog.set_transient_for(self)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        dialog.set_content(main_box)

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)

        close_btn = Gtk.Button(label="Schließen")
        close_btn.add_css_class("suggested-action")
        header.pack_end(close_btn)

        main_box.append(header)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(20)
        content.set_margin_bottom(20)

        # === Pfade ===
        paths_group = Adw.PreferencesGroup(title="Pfade")

        # Project Root
        root_entry = Adw.EntryRow(title="Projekt-Root")
        root_entry.set_text(self.config.project_root)
        paths_group.add(root_entry)

        root_hint = Gtk.Label()
        root_hint.set_markup('<span size="small" foreground="#888">Basisverzeichnis für alle Projekte</span>')
        root_hint.set_halign(Gtk.Align.START)
        root_hint.set_margin_start(12)
        paths_group.add(root_hint)

        content.append(paths_group)

        # === Sync ===
        sync_group = Adw.PreferencesGroup(title="Sync (Google Drive / Cloud)")

        # Sync Path
        sync_path_entry = Adw.EntryRow(title="Sync-Ordner")
        sync_path_entry.set_text(self.config.sync_path)
        sync_group.add(sync_path_entry)

        sync_hint = Gtk.Label()
        sync_hint.set_markup('<span size="small" foreground="#888">Pfad zum gemappten Cloud-Ordner (z.B. Google Drive)</span>')
        sync_hint.set_halign(Gtk.Align.START)
        sync_hint.set_margin_start(12)
        sync_group.add(sync_hint)

        # Sync Password
        password_row = Adw.PasswordEntryRow(title="Sync-Passwort")
        current_pw = get_sync_password()
        if current_pw:
            password_row.set_text("********")  # Placeholder
        sync_group.add(password_row)

        pw_hint = Gtk.Label()
        pw_hint.set_markup('<span size="small" foreground="#888">Wird im OS-Keyring gespeichert</span>')
        pw_hint.set_halign(Gtk.Align.START)
        pw_hint.set_margin_start(12)
        sync_group.add(pw_hint)

        # Sync Buttons
        sync_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        sync_buttons.set_margin_top(10)
        sync_buttons.set_halign(Gtk.Align.CENTER)

        export_btn = Gtk.Button(label="Export (Hochladen)")
        export_btn.set_icon_name("go-up-symbolic")
        export_btn.add_css_class("suggested-action")
        sync_buttons.append(export_btn)

        import_btn = Gtk.Button(label="Import (Herunterladen)")
        import_btn.set_icon_name("go-down-symbolic")
        sync_buttons.append(import_btn)

        sync_group.add(sync_buttons)

        # Sync Status
        sync_status = Gtk.Label()
        sync_status.set_halign(Gtk.Align.CENTER)
        sync_status.set_margin_top(5)
        sync_group.add(sync_status)

        content.append(sync_group)

        # === Terminal ===
        term_group = Adw.PreferencesGroup(title="Terminal")
        term_entry = Adw.EntryRow(title="Terminal-Befehl")
        term_entry.set_text(self.config.terminal_command)
        term_group.add(term_entry)
        content.append(term_group)

        # Default Start Command
        start_group = Adw.PreferencesGroup(title="Standard Start-Befehl")
        start_entry = Adw.EntryRow(title="Befehl")
        start_entry.set_text(self.config.default_start_command)
        start_group.add(start_entry)

        start_hint = Gtk.Label()
        start_hint.set_markup('<span size="small" foreground="#888">Wird für alle Projekte verwendet, die keinen eigenen Befehl haben</span>')
        start_hint.set_halign(Gtk.Align.START)
        start_hint.set_margin_start(12)
        start_group.add(start_hint)
        content.append(start_group)

        # Provider-Verwaltung
        provider_group = Adw.PreferencesGroup(title="LLM Provider")

        # Header mit Add-Button
        provider_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        provider_header.set_margin_bottom(10)

        add_provider_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_provider_btn.set_tooltip_text("Provider hinzufügen")
        add_provider_btn.add_css_class("suggested-action")
        provider_header.append(add_provider_btn)

        provider_group.add(provider_header)

        # Provider-Liste Container
        provider_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        def refresh_provider_list():
            # Clear existing
            while provider_list.get_first_child():
                provider_list.remove(provider_list.get_first_child())

            for provider in self.config.providers:
                row = self._create_provider_row(provider, dialog, refresh_provider_list)
                provider_list.append(row)

        refresh_provider_list()
        provider_group.add(provider_list)
        content.append(provider_group)

        def on_add_provider(btn):
            self._show_provider_dialog(None, dialog, refresh_provider_list)

        add_provider_btn.connect("clicked", on_add_provider)

        # Sync-Event-Handler
        def on_export(btn):
            # Erst Einstellungen speichern
            self._save_settings(root_entry, sync_path_entry, password_row, term_entry, start_entry)

            success, msg = export_to_sync(self.config)
            if success:
                sync_status.set_markup(f'<span foreground="#4CAF50">{msg}</span>')
                self._show_toast(msg)
            else:
                sync_status.set_markup(f'<span foreground="#F44336">{msg}</span>')
                self._show_toast(f"Export fehlgeschlagen: {msg}")

        def on_import(btn):
            # Erst Einstellungen speichern
            self._save_settings(root_entry, sync_path_entry, password_row, term_entry, start_entry)

            success, msg = import_from_sync(self.config)
            if success:
                # Config neu laden
                self.config = load_config()
                sync_status.set_markup(f'<span foreground="#4CAF50">{msg}</span>')
                self._show_toast(msg)
                self._refresh_list()
                self._update_category_filter()
            else:
                sync_status.set_markup(f'<span foreground="#F44336">{msg}</span>')
                self._show_toast(f"Import fehlgeschlagen: {msg}")

        export_btn.connect("clicked", on_export)
        import_btn.connect("clicked", on_import)

        # Info
        info_group = Adw.PreferencesGroup()
        info_label = Gtk.Label()
        info_label.set_markup('<span size="small" foreground="#888">Konfigurationsdatei: ~/.config/cindergrace-launcher/local.json</span>')
        info_label.set_halign(Gtk.Align.START)
        info_group.add(info_label)
        content.append(info_group)

        scroll.set_child(content)
        main_box.append(scroll)

        def on_close(btn):
            self._save_settings(root_entry, sync_path_entry, password_row, term_entry, start_entry)
            self._refresh_list()
            dialog.close()

        close_btn.connect("clicked", on_close)
        dialog.present()

    def _save_settings(self, root_entry, sync_path_entry, password_row, term_entry, start_entry):
        """Speichert die Einstellungen"""
        self.config.local.project_root = root_entry.get_text().strip() or str(Path.home() / "projekte")
        self.config.local.sync_path = sync_path_entry.get_text().strip()
        self.config.local.terminal_command = term_entry.get_text().strip() or "gnome-terminal"
        self.config.local.default_start_command = start_entry.get_text().strip() or "./start.sh"
        self.process_manager.terminal_cmd = self.config.local.terminal_command

        # Passwort nur speichern wenn geändert (nicht Placeholder)
        pw_text = password_row.get_text()
        if pw_text and pw_text != "********":
            set_sync_password(pw_text)

        save_config(self.config)

    def _create_provider_row(self, provider: LLMProvider, parent_dialog, refresh_callback) -> Gtk.Widget:
        """Erstellt eine Provider-Zeile für die Settings"""
        row = Adw.ActionRow()
        row.set_title(provider.name)
        row.set_subtitle(provider.command)

        # Icon
        icon = Gtk.Image.new_from_icon_name(provider.icon)
        row.add_prefix(icon)

        # Enabled Switch
        switch = Gtk.Switch()
        switch.set_active(provider.enabled)
        switch.set_valign(Gtk.Align.CENTER)
        switch.connect("state-set", lambda s, state: self._on_provider_enabled_changed(provider.id, state))
        row.add_suffix(switch)

        # Edit Button
        edit_btn = Gtk.Button(icon_name="document-edit-symbolic")
        edit_btn.add_css_class("flat")
        edit_btn.set_valign(Gtk.Align.CENTER)
        edit_btn.connect("clicked", lambda b: self._show_provider_dialog(provider, parent_dialog, refresh_callback))
        row.add_suffix(edit_btn)

        # Delete Button
        delete_btn = Gtk.Button(icon_name="user-trash-symbolic")
        delete_btn.add_css_class("flat")
        delete_btn.add_css_class("error")
        delete_btn.set_valign(Gtk.Align.CENTER)
        delete_btn.connect("clicked", lambda b: self._delete_provider(provider.id, refresh_callback))
        row.add_suffix(delete_btn)

        return row

    def _on_provider_enabled_changed(self, provider_id: str, enabled: bool):
        provider = self.config.get_provider(provider_id)
        if provider:
            provider.enabled = enabled
            save_config(self.config)
        return False

    def _delete_provider(self, provider_id: str, refresh_callback):
        self.config.remove_provider(provider_id)
        save_config(self.config)
        refresh_callback()
        self._show_toast("Provider entfernt")

    def _show_provider_dialog(self, provider: LLMProvider, parent_dialog, refresh_callback):
        """Dialog zum Hinzufügen/Bearbeiten eines Providers"""
        is_edit = provider is not None

        dialog = Adw.Window()
        dialog.set_title("Provider bearbeiten" if is_edit else "Neuer Provider")
        dialog.set_default_size(450, 500)
        dialog.set_modal(True)
        dialog.set_transient_for(parent_dialog)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        dialog.set_content(main_box)

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)

        cancel_btn = Gtk.Button(label="Abbrechen")
        cancel_btn.connect("clicked", lambda b: dialog.close())
        header.pack_start(cancel_btn)

        save_btn = Gtk.Button(label="Speichern")
        save_btn.add_css_class("suggested-action")
        header.pack_end(save_btn)

        main_box.append(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(20)
        content.set_margin_bottom(20)

        # ID (nur bei neuem Provider editierbar)
        id_group = Adw.PreferencesGroup(title="ID")
        id_entry = Adw.EntryRow(title="Eindeutige ID")
        id_entry.set_text(provider.id if provider else "")
        id_entry.set_sensitive(not is_edit)
        id_group.add(id_entry)
        content.append(id_group)

        # Name
        name_group = Adw.PreferencesGroup(title="Name")
        name_entry = Adw.EntryRow(title="Anzeigename")
        name_entry.set_text(provider.name if provider else "")
        name_group.add(name_entry)
        content.append(name_group)

        # Command
        cmd_group = Adw.PreferencesGroup(title="Befehl")
        cmd_entry = Adw.EntryRow(title="CLI Pfad/Befehl")
        cmd_entry.set_text(provider.command if provider else "")
        cmd_group.add(cmd_entry)
        content.append(cmd_group)

        # Default Flags
        flags_group = Adw.PreferencesGroup(title="Standard-Flags (optional)")
        flags_entry = Adw.EntryRow(title="Flags")
        flags_entry.set_text(provider.default_flags if provider else "")
        flags_group.add(flags_entry)
        content.append(flags_group)

        # Skip Permissions Flag
        skip_group = Adw.PreferencesGroup(title="Auto-Bestätigung Flag (optional)")
        skip_entry = Adw.EntryRow(title="Flag")
        skip_entry.set_text(provider.skip_permissions_flag if provider else "")
        skip_group.add(skip_entry)

        skip_hint = Gtk.Label()
        skip_hint.set_markup('<span size="small" foreground="#888">z.B. --dangerously-skip-permissions oder --full-auto</span>')
        skip_hint.set_halign(Gtk.Align.START)
        skip_hint.set_margin_start(12)
        skip_group.add(skip_hint)
        content.append(skip_group)

        # Icon
        icon_group = Adw.PreferencesGroup(title="Icon (optional)")
        icon_entry = Adw.EntryRow(title="GTK Icon Name")
        icon_entry.set_text(provider.icon if provider else "utilities-terminal-symbolic")
        icon_group.add(icon_entry)
        content.append(icon_group)

        # Color
        color_group = Adw.PreferencesGroup(title="Farbe (optional)")
        color_entry = Adw.EntryRow(title="CSS Farbe")
        color_entry.set_text(provider.color if provider else "#808080")
        color_group.add(color_entry)
        content.append(color_group)

        main_box.append(content)

        def on_save(btn):
            new_id = id_entry.get_text().strip()
            new_name = name_entry.get_text().strip()
            new_cmd = cmd_entry.get_text().strip()

            if not new_id or not new_name or not new_cmd:
                self._show_toast("ID, Name und Befehl sind erforderlich")
                return

            new_provider = LLMProvider(
                id=new_id,
                name=new_name,
                command=new_cmd,
                icon=icon_entry.get_text().strip() or "utilities-terminal-symbolic",
                color=color_entry.get_text().strip() or "#808080",
                default_flags=flags_entry.get_text().strip(),
                skip_permissions_flag=skip_entry.get_text().strip(),
                enabled=provider.enabled if provider else True,
            )

            try:
                if is_edit:
                    self.config.update_provider(provider.id, new_provider)
                    self._show_toast(f"Provider aktualisiert: {new_name}")
                else:
                    self.config.add_provider(new_provider)
                    self._show_toast(f"Provider hinzugefügt: {new_name}")

                save_config(self.config)
                refresh_callback()
                dialog.close()
            except ValueError as e:
                self._show_toast(str(e))

        save_btn.connect("clicked", on_save)
        dialog.present()

    def _show_toast(self, message: str):
        toast = Adw.Toast(title=message)
        toast.set_timeout(2)
        self.toast_overlay.add_toast(toast)


class LauncherApp(Adw.Application):
    """Hauptanwendung"""

    def __init__(self):
        super().__init__(application_id="de.cindergrace.launcher")
        self.connect("activate", self.on_activate)
        self.connect("startup", self.on_startup)

    def on_startup(self, app):
        """Lädt CSS beim App-Start"""
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CINDERGRACE_CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def on_activate(self, app):
        win = LauncherWindow(app)
        win.present()


def main():
    app = LauncherApp()
    app.run(None)


if __name__ == "__main__":
    main()
