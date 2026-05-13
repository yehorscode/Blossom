from gi.repository import Adw, Gio, Gtk

from components.sidebar import build_sidebar
from components.views import build_emails_view, build_folders_view, build_settings_view


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Header
        header = Adw.HeaderBar()
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

        # Content stack
        self.stack = Gtk.Stack()
        self.stack.set_margin_start(12)
        self.stack.set_margin_end(12)
        self.emails_view = build_emails_view()
        self.stack.add_named(self.emails_view, "Emails")
        self.stack.add_named(build_folders_view(), "Folders")
        self.stack.add_named(build_settings_view(), "Settings")
        # Sidebar
        sidebar_content, sidebar, refresh_button, update_indicator = build_sidebar()
        sidebar.connect("row-selected", self._on_sidebar_selected)
        refresh_button.connect("clicked", self._on_refresh_clicked)
        
        self.update_indicator = update_indicator
        self.emails_view.update_indicator = update_indicator

        # Layout
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header)

        split = Adw.NavigationSplitView()
        split.set_sidebar(Adw.NavigationPage(title="Blossom", child=sidebar_content))
        split.set_content(Adw.NavigationPage(title="Content", child=self.stack))

        toolbar_view.set_content(split)
        self.set_content(toolbar_view)
        self.set_default_size(900, 600)

    def _on_sidebar_selected(self, listbox, row):
        if row is None:
            return
        page_names = ["Emails", "Folders", "Settings"]
        self.stack.set_visible_child_name(page_names[row.get_index()])

    def _on_refresh_clicked(self, button):
        if hasattr(self.emails_view, "refetch_emails"):
            self.emails_view.refetch_emails()
            print("Emails refreshed")
