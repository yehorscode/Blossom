from gi.repository import Adw, Gtk

from functions.emails import save_credentials


def on_add_account_clicked(button, refresh_account_list):
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
        if (
            not email_row.get_text()
            or not password_row.get_text()
            or not imap_server_row.get_text()
            or not imap_port_row.get_text()
            or not imap_username.get_text()
            or not smtp_server_row.get_text()
            or not smtp_port_row.get_text()
        ):
            alert = Adw.AlertDialog()
            alert.set_heading("Missing Fields")
            alert.set_body("Please fill in all required fields.")
            alert.add_response("ok", "OK")
            alert.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
            alert.present(dialog)
            return
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
