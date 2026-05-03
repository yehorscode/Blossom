from gi.repository import Gtk


def _make_row(icon_name, label):
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


def build_sidebar():
    # Sidebar ListBox
    sidebar_list = Gtk.ListBox()
    sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
    sidebar_list.add_css_class("navigation-sidebar")

    # Sidebar content
    sidebar_list.append(_make_row("mail-unread-symbolic", "Emails"))
    sidebar_list.append(_make_row("folder-visiting-symbolic", "Folders"))
    sidebar_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    sidebar_content.append(sidebar_list)
    return sidebar_content
