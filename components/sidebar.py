from gi.repository import Adw, Gtk


def make_sidebar_item(icon):
    row = Gtk.ListBoxRow()
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    # box.set_margin_top(6)
    # box.set_margin_bottom(6)
    # box.set_margin_start(6)
    # box.set_margin_end(6)
    box.append(Gtk.Image.new_from_icon_name(icon))
    row.set_child(box)
    return row


def build_sidebar():
    sidebar = Gtk.ListBox()
    sidebar.set_selection_mode(Gtk.SelectionMode.SINGLE)
    sidebar.add_css_class("navigation-sidebar")
    sidebar.append(make_sidebar_item("mail-unread-symbolic"))
    sidebar.append(make_sidebar_item("folder-visiting-symbolic"))
    sidebar.append(make_sidebar_item("preferences-system-symbolic"))

    refresh_button = Gtk.Button()
    refresh_button.set_icon_name("view-refresh-symbolic")
    # refresh_button.set_margin_top(6)
    # refresh_button.set_margin_bottom(6)
    # refresh_button.set_margin_start(6)
    # refresh_button.set_margin_end(6)

    update_spinner = Adw.Spinner()
    update_indicator = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    update_indicator.append(update_spinner)
    update_indicator.add_css_class("body")
    # update_indicator.set_margin_top(6)
    update_indicator.set_margin_bottom(12)
    # update_indicator.set_margin_start(6)
    # update_indicator.set_margin_end(6)
    update_indicator.set_halign(Gtk.Align.CENTER)
    update_indicator.set_visible(False)

    sidebar_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    sidebar_content.set_vexpand(True)
    # sidebar_content.set_margin_top(6)
    # sidebar_content.set_margin_bottom(6)
    # sidebar_content.set_margin_start(6)
    # sidebar_content.set_margin_end(6)
    sidebar_content.append(sidebar)
    spacer = Gtk.Box()
    spacer.set_vexpand(True)
    sidebar_content.append(spacer)
    sidebar_content.append(update_indicator)
    sidebar_content.append(refresh_button)

    return sidebar_content, sidebar, refresh_button, update_indicator
