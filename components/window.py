from gi.repository import Adw, Gio, Gtk

from components.sidebar import build_sidebar
from components.views import build_emails_view, build_folders_view, build_settings_view


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        mainbox = Adw.NavigationSplitView()
        header = Adw.HeaderBar()
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header)
        toolbar_view.set_content(mainbox)

        # Header config
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

        # Sidebar config
        sidebar_content, sidebar_list, sidebar_bottom_list = build_sidebar()
        sidebar_page = Adw.NavigationPage(title="Blossom")
        sidebar_page.set_child(sidebar_content)

        # Sidebar view stack
        self.stack = Gtk.Stack()
        self.stack.set_margin_start(12)
        self.stack.set_margin_end(12)
        self.stack.add_named(build_emails_view(), "emails")
        self.stack.add_named(build_folders_view(), "folders")
        self.stack.add_named(build_settings_view(), "settings")
        sidebar_list.connect(
            "row-selected",
            self.on_sidebar_selected,
            ["emails", "folders"],
            sidebar_bottom_list,
        )
        sidebar_bottom_list.connect(
            "row-selected", self.on_sidebar_selected, ["settings"], sidebar_list
        )

        # Main content config
        content_page = Adw.NavigationPage(title="Content")
        content_page.set_child(self.stack)

        mainbox.set_sidebar(sidebar_page)
        mainbox.set_content(content_page)
        self.set_content(toolbar_view)

    def on_sidebar_selected(self, listbox, row, page_names, other_list):
        if row is None:
            return
        other_list.unselect_all()
        self.stack.set_visible_child_name(page_names[row.get_index()])
