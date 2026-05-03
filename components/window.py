from gi.repository import Adw, Gio, Gtk

from components.sidebar import build_sidebar


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

        sidebar_page = Adw.NavigationPage(title="Sidebar")
        sidebar_page.set_child(build_sidebar())

        # Main content config
        content_content = Gtk.Box()
        content_page = Adw.NavigationPage(title="Content")
        content_page.set_child(content_content)

        # Main content content
        app_welcome = Gtk.Label(label="This is content")

        # ↑ Adding main content content
        content_content.append(app_welcome)

        # ↑ Adding all the content (sidebar+main content) into one
        mainbox.set_sidebar(sidebar_page)
        mainbox.set_content(content_page)

        # _Displaying the thing
        self.set_content(toolbar_view)
