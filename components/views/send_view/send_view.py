import email.message
from email.utils import parseaddr

import gi

from functions.emails import (
    get_all_accounts,
)
from functions.mouth import send_email

gi.require_version("WebKit", "6.0")
gi.require_version("GtkSource", "5")
from gi.repository import Adw, Gtk, GtkSource, WebKit


def _build_reply_subject(subject: str) -> str:
    clean_subject = str(subject or "").strip()
    if not clean_subject:
        return "Re:"
    if clean_subject.lower().startswith("re:"):
        return clean_subject
    return f"Re: {clean_subject}"


def _build_reply_body(email: dict) -> str:
    sender = str(email.get("from", "") or "")
    date = str(email.get("date", "") or "")
    body_plain = str(email.get("body_plain", "") or "")
    if body_plain:
        quoted_body = "\n".join(
            f"> {line}" if line else ">" for line in body_plain.splitlines()
        )
    else:
        quoted_body = "> "

    if sender and date:
        intro = f"On {date}, {sender} wrote:"
    elif sender:
        intro = f"{sender} wrote:"
    elif date:
        intro = f"On {date}:"
    else:
        intro = "Original message:"
    return f"\n\n{intro}\n{quoted_body}"


class SendView(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        metadata_group = Adw.PreferencesGroup()

        self.email_sender_form = Adw.ComboRow(title="From:")
        email_list = Gtk.StringList()
        for acc in get_all_accounts():
            email_list.append(acc)
        self.email_sender_form.set_model(email_list)

        self.email_receivers_form_to = Adw.EntryRow(
            title="To: (separate receivers with ,)"
        )
        self.email_receivers_form_cc = Adw.EntryRow(title="CC:")
        self.email_receivers_form_bcc = Adw.EntryRow(title="BCC:")

        metadata_group.add(self.email_sender_form)
        metadata_group.add(self.email_receivers_form_to)
        metadata_group.add(self.email_receivers_form_cc)
        metadata_group.add(self.email_receivers_form_bcc)

        top_box.append(metadata_group)

        top_box_right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        send_button = Gtk.Button(icon_name="mail-send-symbolic")
        send_button.connect("clicked", self._send)
        top_box_right.append(send_button)

        metadata_group.set_hexpand(True)
        metadata_group.set_margin_end(8)

        top_box.append(top_box_right)
        self.append(top_box)

        title_group = Adw.PreferencesGroup()
        self.email_title = Adw.EntryRow(title="Title:")
        title_group.add(self.email_title)
        self.append(title_group)

        GtkSource.init()
        self.buffer = GtkSource.Buffer()

        lang = GtkSource.LanguageManager.get_default().get_language("markdown")
        self.buffer.set_language(lang)

        style_manager = Adw.StyleManager.get_default()
        scheme_manager = GtkSource.StyleSchemeManager.get_default()

        def apply_scheme(*_):
            name = "Adwaita-dark" if style_manager.get_dark() else "Adwaita"
            scheme = scheme_manager.get_scheme(name)
            if scheme:
                self.buffer.set_style_scheme(scheme)

        apply_scheme()
        style_manager.connect("notify::dark", apply_scheme)

        editor = GtkSource.View.new_with_buffer(self.buffer)
        editor.set_wrap_mode(Gtk.WrapMode.WORD)
        editor.set_top_margin(8)
        editor.set_left_margin(8)
        editor.set_right_margin(8)
        editor.set_bottom_margin(8)
        editor.set_size_request(-1, 300)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(editor)
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        body_group = Adw.PreferencesGroup()
        body_group.add(scrolled)
        self.append(body_group)

    def _send(self, _button):
        selected_sender_item = self.email_sender_form.get_selected_item()
        if selected_sender_item is None:
            alert = Adw.AlertDialog()
            alert.set_heading("No sender selected")
            alert.set_body("Select a sender account before sending an email.")
            alert.add_response("ok", "OK")
            alert.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
            alert.present()
            return

        sender = selected_sender_item.get_string()
        to_addrs = [
            addr.strip()
            for addr in self.email_receivers_form_to.get_text().split(",")
            if addr.strip()
        ]
        cc_addrs = [
            addr.strip()
            for addr in self.email_receivers_form_cc.get_text().split(",")
            if addr.strip()
        ]
        bcc_addrs = [
            addr.strip()
            for addr in self.email_receivers_form_bcc.get_text().split(",")
            if addr.strip()
        ]
        recipients = to_addrs + cc_addrs + bcc_addrs
        if not recipients:
            alert = Adw.AlertDialog()
            alert.set_heading("No recipients")
            alert.set_body("Add at least one recipient before sending an email.")
            alert.add_response("ok", "OK")
            alert.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
            alert.present()
            return

        msg = email.message.EmailMessage()
        if to_addrs:
            msg["to"] = to_addrs
        if cc_addrs:
            msg["cc"] = cc_addrs
        msg["from"] = sender
        msg["subject"] = self.email_title.get_text()
        msg.set_content(
            self.buffer.get_text(
                self.buffer.get_start_iter(), self.buffer.get_end_iter(), True
            )
        )
        print("Sending email:")
        print(msg)
        sent, send_error = send_email(msg, sender, recipients)

        alert = Adw.AlertDialog()
        if sent:
            alert.set_heading("Email sent")
            alert.set_body("Your email was sent successfully.")
        else:
            alert.set_heading("Send failed")
            alert.set_body(send_error or "Unknown SMTP error while sending the email.")
        alert.add_response("ok", "OK")
        alert.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        alert.present()

    def _select_sender(self, sender_email: str) -> None:
        model = self.email_sender_form.get_model()
        if model is None:
            return

        for index in range(model.get_n_items()):
            item = model.get_item(index)
            if item and item.get_string() == sender_email:
                self.email_sender_form.set_selected(index)
                return

    def prefill_reply(self, source_email: dict) -> None:
        sender = str(source_email.get("account", "") or "")
        from_header = str(source_email.get("from", "") or "")
        _, reply_to_address = parseaddr(from_header)

        self.email_receivers_form_to.set_text(reply_to_address or from_header)
        self.email_receivers_form_cc.set_text("")
        self.email_receivers_form_bcc.set_text("")
        self.email_title.set_text(
            _build_reply_subject(str(source_email.get("subject", "") or ""))
        )
        self.buffer.set_text(_build_reply_body(source_email))
        if sender:
            self._select_sender(sender)
