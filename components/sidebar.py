from gi.repository import Gdk, Gtk


def make_row(icon_name, label):
    row = Gtk.ListBoxRow()
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    box.set_margin_top(6)
    box.set_margin_bottom(6)
    box.set_margin_start(6)
    box.set_margin_end(6)
    icon = Gtk.Image.new_from_icon_name(icon_name)
    lbl = Gtk.Label(label=label)
    box.append(icon)
    box.append(lbl)
    row.set_child(box)
    return row


def set_margins(widget):
    widget.set_margin_top(6)
    widget.set_margin_bottom(6)
    widget.set_margin_start(6)
    widget.set_margin_end(6)


def build_sidebar():

    sidebar_list = Gtk.ListBox()
    sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
    sidebar_list.add_css_class("navigation-sidebar")
    sidebar_list.append(make_row("mail-unread-symbolic", "Emails"))
    sidebar_list.append(make_row("folder-visiting-symbolic", "Folders"))

    bottom_list = Gtk.ListBox()
    bottom_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
    bottom_list.add_css_class("navigation-sidebar")
    bottom_list.append(make_row("preferences-system-symbolic", "Settings"))

    spacer = Gtk.Box()
    spacer.set_vexpand(True)

    sidebar_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    sidebar_content.set_vexpand(True)
    sidebar_content.append(sidebar_list)
    sidebar_content.append(spacer)
    sidebar_content.append(bottom_list)
    set_margins(sidebar_content)
    return sidebar_content, sidebar_list, bottom_list
