import gi

from components.view_components.comp_settings import on_add_account_clicked
from components.views.emails_view.emails_view import EmailsView
from components.views.send_view.send_view import SendView
from functions.emails import (
    delete_all_credentials,
    delete_credential,
    get_all_accounts,
    get_credentials,
)

gi.require_version("WebKit", "6.0")
gi.require_version("GtkSource", "5")
from gi.repository import Adw, Gtk


def build_send_view() -> Gtk.Box:
    return SendView()


def build_emails_view(on_reply_requested=None) -> Gtk.Box:
    return EmailsView(on_reply_requested=on_reply_requested)


def build_folders_view():
    box = Gtk.Box()
    box.append(Gtk.Label(label="Folders view"))
    return box


def build_settings_view():
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    # box.set_margin_top(24)
    # box.set_margin_bottom(24)
    # box.set_margin_start(24)
    # box.set_margin_end(24)
    # box.set_halign(Gtk.Align.START)
    box.set_valign(Gtk.Align.START)
    # box.set_hexpand(True)
    add_accounts_box = Gtk.Box(spacing=6)
    add_accounts_button = Gtk.Button()
    add_accounts_button.set_child(
        Adw.ButtonContent(label="Add account", icon_name="contact-new-symbolic")
    )
    remove_all_button = Gtk.Button()
    remove_all_button.set_child(
        Adw.ButtonContent(label="Delete all accounts", icon_name="edit-clear-symbolic")
    )
    remove_all_button.add_css_class("destructive-action")

    account_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

    def refresh_account_list():
        child = account_list_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            account_list_box.remove(child)
            child = next_child

        for account in get_all_accounts():
            single_acc = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            single_acc.add_css_class("card")
            single_acc_inner = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL, spacing=12
            )
            single_acc_inner.set_margin_top(6)
            single_acc_inner.set_margin_bottom(6)
            single_acc_inner.set_margin_start(6)
            single_acc_inner.set_margin_end(6)
            single_acc.append(single_acc_inner)
            acc_label = Gtk.Label(label=account)
            acc_label.set_hexpand(True)

            button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            acc_delete_button = Gtk.Button()
            acc_delete_button.set_child(
                Adw.ButtonContent(icon_name="edit-delete-symbolic", label="Delete")
            )
            acc_delete_button.add_css_class("destructive-action")
            acc_view_info_btn = Gtk.Button()
            acc_view_info_btn.set_child(
                Adw.ButtonContent(icon_name="help-about-symbolic", label="View info")
            )
            acc_delete_button.connect(
                "clicked", lambda btn, acc=account: on_acc_del_clicked(acc)
            )
            acc_view_info_btn.connect(
                "clicked", lambda btn, acc=account: on_acc_info_clicked(acc)
            )
            button_box.append(acc_view_info_btn)
            button_box.append(acc_delete_button)
            single_acc_inner.append(acc_label)
            single_acc_inner.append(button_box)
            account_list_box.append(single_acc)

    def on_remove_all_accounts_clicked(button):
        def confirm_delete_all(dialog, response):
            if response == "delete":
                delete_all_credentials(sure=True)
                refresh_account_list()

        alert = Adw.AlertDialog()
        alert.set_heading("Delete everything?")
        alert.set_body(
            "This is a permanent action that cannot be udone. Are you fully sure?"
        )
        alert.add_response("cancel", "Cancel")
        alert.add_response("delete", "Delete All")
        alert.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        alert.connect("response", confirm_delete_all)
        alert.present()

    def on_acc_del_clicked(account: str):
        def confirm_delete_account(dialog, response):
            if response == "delete":
                delete_credential(account)
                refresh_account_list()
                success_alert = Adw.AlertDialog()
                success_alert.set_heading("Deleted")
                success_alert.set_body(f"Account {account} has been deleted.")
                success_alert.add_response("ok", "OK")
                success_alert.set_response_appearance(
                    "ok", Adw.ResponseAppearance.SUGGESTED
                )
                success_alert.present()

        alert = Adw.AlertDialog()
        alert.set_heading(f"Delete {account}?")
        alert.set_body(
            "This will permanently remove this email account and all associated credentials."
        )
        alert.add_response("cancel", "Cancel")
        alert.add_response("delete", "Delete")
        alert.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        alert.connect("response", confirm_delete_account)
        alert.present()

    def on_acc_info_clicked(account: str, parent_widget=account_list_box):
        dialog = Adw.Dialog()
        dialog.set_title(account)
        dialog.set_content_width(400)
        dialog.set_content_height(300)

        toolbar_view = Adw.ToolbarView()

        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(12)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)

        info = get_credentials(account)
        if info is None:
            info = {"Error": "Could not retrieve account info"}
        else:
            for key, value in info.items():
                row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                key_label = Gtk.Label(label=f"<b>{key}</b>", use_markup=True, xalign=0)
                key_label.set_hexpand(True)
                val_label = Gtk.Label(label=str(value), xalign=1)
                row_box.append(key_label)
                row_box.append(val_label)
                content_box.append(row_box)

        toolbar_view.set_content(content_box)
        dialog.set_child(toolbar_view)

        dialog.present(account_list_box)

    refresh_account_list()

    add_accounts_button.connect(
        "clicked", lambda btn: on_add_account_clicked(btn, refresh_account_list)
    )
    remove_all_button.connect("clicked", on_remove_all_accounts_clicked)

    add_accounts_box.append(add_accounts_button)
    # add_accounts_box.append(remove_all_button)
    box.append(add_accounts_box)
    box.append(account_list_box)

    return box
