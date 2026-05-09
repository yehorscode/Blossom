from gi.repository import Adw, Gtk

from functions.emails import (
    delete_all_credentials,
    get_all_accounts,
    get_credentials,
    save_credentials,
)


def build_emails_view():
    box = Gtk.Box()
    box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
    return box


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
    add_accounts_box = Gtk.Box()
    add_accounts_button = Gtk.Button()
    add_accounts_button.set_child(
        Adw.ButtonContent(label="Add acount", icon_name="contact-new-symbolic")
    )
    remove_all_button = Gtk.Button()
    remove_all_button.set_child(
        Adw.ButtonContent(label="Delete all accounts", icon_name="edit-clear-symbolic")
    )
    remove_all_button.add_css_class("destructive-action")

    def on_add_account_clicked(button):
        dialog = Adw.Dialog()
        dialog.set_title("Add Account")
        dialog.set_content_width(400)
        dialog.set_content_height(500)

        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)

        email_row = Adw.EntryRow(title="Email")
        password_row = Adw.PasswordEntryRow(title="Password")
        imap_server_row = Adw.EntryRow(title="Imap server")
        imap_port_row = Adw.EntryRow(title="Imap port")
        imap_security_row = Adw.ComboRow(title="Imap security")
        imap_security_row.set_model(Gtk.StringList.new(["None", "SSL/TLS"]))
        imap_username = Adw.EntryRow(title="Imap username")
        imap_auth = Adw.ComboRow(title="Imap auth")
        imap_auth.set_model(Gtk.StringList.new(["password"]))
        smtp_server_row = Adw.EntryRow(title="Smtp server")
        smtp_port_row = Adw.EntryRow(title="Smtp port")
        smtp_security_row = Adw.ComboRow(title="Smtp security")
        smtp_security_row.set_model(Gtk.StringList.new(["None", "SSL/TLS"]))
        smtp_auth = Adw.ComboRow(title="Smtp auth")
        smtp_auth.set_model(Gtk.StringList.new(["password"]))
        credentials_group = Adw.PreferencesGroup(title="Credentials")
        credentials_group.add(email_row)
        credentials_group.add(password_row)
        save_button = Gtk.Button(label="Save account")
        save_button.add_css_class("suggested-action")
        save_button.set_margin_top(12)

        def on_save_clicked(button):
            save_credentials(
                email=email_row.get_text(),
                password=password_row.get_text(),
                imap_server=imap_server_row.get_text(),
                imap_port=imap_port_row.get_text(),
                imap_security=imap_security_row.get_selected_item().get_string(),
                imap_username=imap_username.get_text(),
                imap_auth=imap_auth.get_selected_item().get_string(),
                smtp_server=smtp_server_row.get_text(),
                smtp_port=smtp_port_row.get_text(),
                smtp_security=smtp_security_row.get_selected_item().get_string(),
                smtp_auth=smtp_auth.get_selected_item().get_string(),
            )
            refresh_account_list()
            dialog.close()

        save_button.connect("clicked", on_save_clicked)
        content.append(save_button)

        imap_group = Adw.PreferencesGroup(title="IMAP Configuration")
        imap_group.add(imap_server_row)
        imap_group.add(imap_port_row)
        imap_group.add(imap_security_row)
        imap_group.add(imap_username)
        imap_group.add(imap_auth)

        smtp_group = Adw.PreferencesGroup(title="SMTP Configuration")
        smtp_group.add(smtp_server_row)
        smtp_group.add(smtp_port_row)
        smtp_group.add(smtp_security_row)
        smtp_group.add(smtp_auth)

        content.append(credentials_group)
        content.append(imap_group)
        content.append(smtp_group)

        scrolled.set_child(content)
        toolbar_view.set_content(scrolled)
        dialog.set_child(toolbar_view)
        dialog.present(button)

    account_list_box = Gtk.Box()

    def refresh_account_list():
        child = account_list_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            account_list_box.remove(child)
            child = next_child

        for account in get_all_accounts():
            single_acc = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            single_acc.set_margin_top(6)
            single_acc.set_margin_bottom(6)
            single_acc.set_margin_start(6)
            single_acc.set_margin_end(6)
            single_acc.set_css_classes(["card"])
            acc_label = Gtk.Label(label=account)
            acc_label.set_hexpand(True)
            acc_view_info_btn = Gtk.Button()
            acc_view_info_btn.set_child(
                Adw.ButtonContent(icon_name="help-about-symbolic", label="View info")
            )
            acc_view_info_btn.connect(
                "clicked", lambda btn, acc=account: on_acc_info_clicked(acc)
            )
            single_acc.append(acc_label)
            single_acc.append(acc_view_info_btn)
            account_list_box.append(single_acc)

    def on_remove_all_accounts_clicked(button):
        delete_all_credentials(sure=True)
        refresh_account_list()

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

    add_accounts_button.connect("clicked", on_add_account_clicked)
    remove_all_button.connect("clicked", on_remove_all_accounts_clicked)

    add_accounts_box.append(add_accounts_button)
    add_accounts_box.append(remove_all_button)
    box.append(add_accounts_box)
    box.append(account_list_box)

    return box
