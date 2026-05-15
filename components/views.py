import html
import threading

import gi

gi.require_version("WebKit", "6.0")
from gi.repository import Adw, GLib, Gtk, WebKit

from components.view_components.comp_settings import on_add_account_clicked
from functions.emails import (
    delete_all_credentials,
    delete_credential,
    fetch_all_emails_and_store,
    get_all_accounts,
    get_all_emails_cached,
    get_credentials,
    init_email_db,
    save_credentials,
)


def makeEmailRow(email, on_clicked_callback=None):
    container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    # container.set_margin_top(4)
    # container.set_margin_bottom(4)
    # container.set_margin_start(4)
    # container.set_margin_end(4)

    em_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

    inner_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    inner_content.set_margin_top(6)
    inner_content.set_margin_bottom(6)
    inner_content.set_margin_start(6)
    inner_content.set_margin_end(6)

    email_title = Gtk.Label(label=email["subject"], xalign=0)
    email_title.add_css_class("heading")
    email_from = Gtk.Label(label=email["from"], xalign=0)
    email_from.set_hexpand(True)
    email_date = Gtk.Label(label=email["date"], xalign=0)
    email_from.add_css_class("caption-heading")
    email_date.add_css_class("caption")
    top_em_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
    top_em_box.append(email_from)
    top_em_box.append(email_date)
    inner_content.append(top_em_box)
    inner_content.append(email_title)
    em_box.append(inner_content)
    container.append(em_box)
    but = Gtk.Button()
    but.set_child(container)
    if on_clicked_callback:
        but.connect("clicked", lambda btn: on_clicked_callback(email))
    return but


# TODO: add another sidebar to see the actual body of the emails
# 	- also somehow figure out html rendering in gtk :skulk:
class EmailsView(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        init_email_db()
        self.main_container = Adw.OverlaySplitView()
        self.main_container.set_sidebar_position(Gtk.PackType.END)
        self.main_container.set_show_sidebar(False)
        self.email_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.email_extended = Adw.Bin()
        self.email_extended.set_visible(False)
        self.emails = []
        self.updating = False
        self.update_indicator = None
        self.email_details = self.make_email_details()
        self.email_extended.set_child(self.email_details)

        scroll_window = Gtk.ScrolledWindow()
        scroll_window.set_child(self.email_list)
        scroll_window.set_vexpand(True)
        scroll_window.set_hexpand(True)
        self.main_container.set_content(scroll_window)
        self.main_container.set_sidebar(self.email_extended)

        self.main_container.set_sidebar_width_fraction(0.8)
        self.append(self.main_container)
        self.refetch_emails()

    def on_email_clicked(self, email):
        self.main_container.set_show_sidebar(True)
        self.email_extended.set_visible(True)
        self.date_label.set_label(str(email.get("date", "")))
        self.sender_label.set_label(str(email.get("from", "")))
        self.subject_label.set_label(str(email.get("subject", "")))
        self.body_view.load_html(self._build_email_html(email), "about:blank")

    def _build_email_html(self, email: dict) -> str:
        body_plain = email.get("body_plain", "")
        body_html = email.get("body_html", "")
        if body_html:
            return body_html
        if body_plain:
            escaped_plain = html.escape(body_plain).replace("\n", "<br>")
            return f"<html><body>{escaped_plain}</body></html>"
        return "<html><body><i>No message body</i></body></html>"

    def make_email_details(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        top_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.date_label = Gtk.Label(label="")
        self.date_label.set_xalign(0)
        self.date_label.add_css_class("caption")
        self.sender_label = Gtk.Label(label="")
        self.sender_label.set_xalign(0)
        self.sender_label.add_css_class("caption")
        self.subject_label = Gtk.Label(label="")
        self.subject_label.set_xalign(0)
        self.subject_label.add_css_class("heading")

        top_box.append(self.date_label)
        top_box.append(self.sender_label)
        box.append(top_box)
        box.append(self.subject_label)

        self.body_view = WebKit.WebView()
        self.body_view.set_hexpand(True)
        self.body_view.set_vexpand(True)
        body_settings = self.body_view.get_settings()
        body_settings.set_enable_javascript(False)
        body_settings.set_auto_load_images(True)
        self.body_view.load_html(
            "<html><body><i>Select an email</i></body></html>", "about:blank"
        )

        body_scroll = Gtk.ScrolledWindow()
        body_scroll.set_hexpand(True)
        body_scroll.set_vexpand(True)
        body_scroll.set_child(self.body_view)
        box.append(body_scroll)
        return box

    def refetch_emails(self):
        thread = threading.Thread(target=self._fetch_emails_thread)
        thread.daemon = True
        thread.start()

    def _fetch_emails_thread(self):
        self.updating = True
        GLib.idle_add(lambda: self.update_indicator.set_visible(True))

        self.emails = get_all_emails_cached()
        if not self.email_list.get_first_child():
            GLib.idle_add(self._on_emails_fetched_from_cache)

        fetch_all_emails_and_store()
        self.emails = get_all_emails_cached()
        GLib.idle_add(self._on_emails_updated)

    def _clear_email_list(self):
        child = self.email_list.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.email_list.remove(child)
            child = next_child

    def _render_emails(self, emails):
        for email in emails:
            email_row = makeEmailRow(email, self.on_email_clicked)
            self.email_list.append(email_row)

    def _on_emails_fetched_from_cache(self):
        # self.spinner.set_hexpand(False)
        # self.spinner.set_vexpand(False)
        # self.spinner_label.set_hexpand(False)
        # self.spinner_label.set_vexpand(False)
        # self.spinner_label.set_visible(False)
        # self.spinner.set_visible(False)
        print(f"Loaded {len(self.emails)} email batches from cache")
        if not self.updating:
            for email_batch in self.emails:
                self._render_emails(email_batch)

    def _on_emails_updated(self):
        self.update_indicator.set_visible(False)
        self.updating = False
        self._clear_email_list()
        print(f"Updated with {len(self.emails)} email batches")
        for email_batch in self.emails:
            self._render_emails(email_batch)


def build_emails_view():
    return EmailsView()


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
        Adw.ButtonContent(label="Add acount", icon_name="contact-new-symbolic")
    )
    remove_all_button = Gtk.Button()
    remove_all_button.set_child(
        Adw.ButtonContent(label="Delete all accounts", icon_name="edit-clear-symbolic")
    )
    remove_all_button.add_css_class("destructive-action")

    account_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

    def refresh_account_list():
        child = account_list_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            account_list_box.remove(child)
            child = next_child

        for account in get_all_accounts():
            single_acc = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            single_acc.set_margin_top(8)
            single_acc.set_margin_bottom(8)
            single_acc.set_margin_start(12)
            single_acc.set_margin_end(12)
            single_acc.set_css_classes(["card"])
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
            single_acc.append(acc_label)
            single_acc.append(button_box)
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
    add_accounts_box.append(remove_all_button)
    box.append(add_accounts_box)
    box.append(account_list_box)

    return box
