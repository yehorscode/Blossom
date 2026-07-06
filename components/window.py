from gi.repository import Adw, Gio, GLib, Gtk

from components.sidebar import build_sidebar
from components.views import (
    build_emails_view,
    build_folders_view,
    build_send_view,
    build_settings_view,
)


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Header
        header = Adw.HeaderBar()

        # Sidebar toggle button
        toggle_btn = Gtk.ToggleButton()
        toggle_btn.set_icon_name("sidebar-show-symbolic")
        toggle_btn.set_active(True)

        menu = Gio.Menu()
        section = Gio.Menu()
        section.append("_Preferences", "app.preferences")
        section.append("_Keyboard Shortcuts", "app.shortcuts")
        section.append("_About Blossom", "app.about")
        section.append("_Quit", "app.quit")
        menu.append_section(None, section)
        header_menu_button = Gtk.MenuButton()
        header_menu_button.set_icon_name("open-menu-symbolic")
        header_menu_button.set_menu_model(menu)
        header.pack_end(header_menu_button)
        header.pack_start(toggle_btn)

        # Content stack
        self.stack = Gtk.Stack()
        self.stack.set_margin_start(6)
        self.stack.set_margin_end(6)
        self.emails_view = build_emails_view()
        self.stack.add_named(self.emails_view, "Emails")
        self.stack.add_named(build_folders_view(), "Folders")
        self.stack.add_named(build_settings_view(), "Settings")
        self.stack.add_named(build_send_view(), "Send")
        # Sidebar
        sidebar_content, sidebar, refresh_button, update_indicator = build_sidebar()
        sidebar_content.set_hexpand(False)
        sidebar.connect("row-selected", self._on_sidebar_selected)
        refresh_button.connect("clicked", self._on_refresh_clicked)

        self.update_indicator = update_indicator
        self.emails_view.update_indicator = update_indicator

        # Layout
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header)

        split = Adw.OverlaySplitView()
        split.set_sidebar(Adw.NavigationPage(title="Blossom", child=sidebar_content))
        split.set_content(Adw.NavigationPage(title="Content", child=self.stack))
        split.set_show_sidebar(True)
        split.set_sidebar_width_unit(Adw.LengthUnit.PX)

        toggle_btn.connect(
            "toggled", lambda btn: split.set_show_sidebar(btn.get_active())
        )

        toolbar_view.set_content(split)
        self.set_content(toolbar_view)
        self.set_default_size(900, 600)

        self._split = split
        self._sidebar_content = sidebar_content
        self._sidebar_map_id = sidebar_content.connect("map", self._on_sidebar_mapped)

    # vibecoding start
    # genuienly idk why is auto-setting the width so complicated :hs:
    def _on_sidebar_mapped(self, widget):
        self._sync_sidebar_width()
        if self._sidebar_map_id:
            widget.disconnect(self._sidebar_map_id)
            self._sidebar_map_id = None

    def _sync_sidebar_width(self):
        min_size, nat_size = self._sidebar_content.get_preferred_size()
        width = max(min_size.width, nat_size.width)
        if width <= 0:
            GLib.idle_add(self._sync_sidebar_width)
            return
        self._split.set_min_sidebar_width(width)
        self._split.set_max_sidebar_width(width)

    # vibecoding end
    def _on_sidebar_selected(self, listbox, row):
        if row is None:
            return
        page_names = ["Emails", "Folders", "Settings", "Send"]
        self.stack.set_visible_child_name(page_names[row.get_index()])

    def _on_refresh_clicked(self, button):
        if hasattr(self.emails_view, "refetch_emails"):
            self.emails_view.refetch_emails()
            print("Emails refreshed")
