import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk

from blossom.components.window import MainWindow

def main():
    app = BlossomApp()
    app.run(sys.argv)

class BlossomApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.yehors.Blossom")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.set_title("Blossom")
        self.win.set_default_size(1000, 800)
        self._add_action("preferences", self.on_preferences)
        self._add_action("shortcuts", self.on_shortcuts)
        self._add_action("about", self.on_about)
        self._add_action("quit", self.on_quit)
        self.win.present()

    def _add_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)

    def on_preferences(self, action, param):
        print("Preferences clicked")

    def on_shortcuts(self, action, param):
        print("Shortcuts clicked")

    def on_about(self, action, param):
        dialog = Adw.AboutDialog(
            application_name="Blossom",
            application_icon="mail-unread-symbolic",
            version="1.0.0",
        )
        dialog.present(self.win)

    def on_quit(self, action, param):
        self.quit()


if __name__ == "__main__":
    main()
