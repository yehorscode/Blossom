import base64
import html
import re
import threading
from email.utils import parsedate_to_datetime
from pathlib import Path

import gi

from blossom.functions.emails import (
    fetch_all_emails_and_store,
    get_all_emails_cached,
    init_email_db,
    set_email_read_state,
)
from blossom.functions.ear import delete_emails_batch, delete_emails_from_db

gi.require_version("WebKit", "6.0")
gi.require_version("GtkSource", "5")
from gi.repository import Adw, GLib, Gtk, WebKit


def _replace_cid_references(
    body_html: str, attachments: list[dict[str, object]]
) -> str:
    if not body_html or not attachments:
        return body_html

    cid_map: dict[str, str] = {}
    for attachment in attachments:
        cid = attachment.get("content_id")
        content = attachment.get("content")
        if not isinstance(cid, str) or not isinstance(
            content, (bytes, bytearray, memoryview)
        ):
            continue
        mime = attachment.get("mime_type")
        mime_type = (
            mime if isinstance(mime, str) and mime else "application/octet-stream"
        )
        if isinstance(content, memoryview):
            content = content.tobytes()
        elif isinstance(content, bytearray):
            content = bytes(content)
        b64_content = base64.b64encode(content).decode("utf-8")
        cid_map[cid] = f"data:{mime_type};base64,{b64_content}"

    if not cid_map:
        return body_html

    def _replace(match: re.Match[str]) -> str:
        content_id = match.group(1)
        if content_id is None:
            return match.group(0) or ""
        return cid_map.get(content_id, match.group(0) or "")

    return _CID_PATTERN.sub(_replace, body_html)


_CID_PATTERN = re.compile(r'cid:([^"\'\s)]+)', re.IGNORECASE)


def makeEmailRow(email, on_clicked_callback=None, is_selected=False, select_mode=False, on_selection_changed=None):
    """Create an email row with optional checkbox for selection when in select mode."""
    container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    container.set_margin_start(6)
    container.set_margin_end(6)

    # Checkbox only shown in select mode
    checkbox = Gtk.CheckButton()
    checkbox.set_active(is_selected)
    checkbox.set_valign(Gtk.Align.CENTER)
    checkbox.set_visible(select_mode)

    def on_checkbox_toggled(cb):
        email["_selected"] = cb.get_active()
        if on_selection_changed:
            on_selection_changed()

    checkbox.connect("toggled", on_checkbox_toggled)
    container.append(checkbox)

    # Email content box
    em_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

    inner_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    inner_content.set_margin_top(6)
    inner_content.set_margin_bottom(6)
    inner_content.set_margin_start(6)
    inner_content.set_margin_end(6)

    is_read = bool(email.get("read", False))
    title = str(email.get("subject", "") or "(No subject)")
    if not is_read:
        title = f"● {title}"
    email_title = Gtk.Label(label=title, xalign=0)
    email_title.add_css_class("heading")
    from_name = (
        email["from"].split("<")[0].strip() if "<" in email["from"] else email["from"]
    )
    from_email = (
        email["from"].split("<")[1].strip(" >")
        if "<" in email["from"]
        else email["from"]
    )
    email_from = Gtk.Label(label=f"From {from_name} ({from_email})", xalign=0)
    email_from.set_hexpand(True)
    email_date = Gtk.Label(xalign=0)
    email_date.set_label(_format_email_date(email))
    email_from.add_css_class("caption")
    email_date.add_css_class("caption")
    top_em_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
    attachments_container = Gtk.Box(
        orientation=Gtk.Orientation.HORIZONTAL, spacing=3, halign=Gtk.Align.START
    )
    for attachment in email["attachments"]:
        attachments_container.append(makeAttachmentRow(attachment))
    top_em_box.append(email_from)
    top_em_box.append(email_date)
    inner_content.append(top_em_box)
    inner_content.append(email_title)
    em_box.append(inner_content)
    container.append(em_box)
    if email["attachments"]:
        inner_content.append(attachments_container)

    but = Gtk.Button()
    but.set_child(container)

    # In select mode, clicking toggles checkbox
    # In normal mode, clicking opens email
    if on_clicked_callback:
        def on_button_clicked(btn):
            if select_mode:
                checkbox.set_active(not checkbox.get_active())
            else:
                on_clicked_callback(email)

        but.connect("clicked", on_button_clicked)

    return but


def makeAttachmentRow(attachment, on_clicked_callback=None, inContent=False):
    container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
    labelText = ""
    button = Gtk.Button()
    if inContent:
        button.set_child(container)
    inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    inner.set_margin_top(3)
    inner.set_margin_bottom(3)
    inner.set_margin_start(6)
    inner.set_margin_end(6)
    icon = Gtk.Image.new_from_icon_name("document-x-generic-symbolic")
    if attachment["mime_type"][:5] == "image":
        icon = Gtk.Image.new_from_icon_name("image-x-generic-symbolic")
    elif attachment["mime_type"][:5] == "video":
        icon = Gtk.Image.new_from_icon_name("video-x-generic-symbolic")
    elif attachment["mime_type"][:5] == "audio":
        icon = Gtk.Image.new_from_icon_name("audio-x-generic-symbolic")
    elif attachment["mime_type"][:4] == "text":
        icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic")
    elif attachment["mime_type"][:4] == "font":
        icon = Gtk.Image.new_from_icon_name("font-x-generic-symbolic")
    elif attachment["mime_type"] == "application/pdf":
        icon = Gtk.Image.new_from_icon_name("x-office-document-symbolic")
    if inContent:
        labelText = attachment["filename"]
    else:
        labelText = attachment["filename"]
    inner.append(icon)
    container.append(inner)
    title = Gtk.Label(label=labelText, xalign=0)
    title.set_margin_start(6)
    title.add_css_class("caption")
    inner.append(title)
    download_indicator = Gtk.Image.new_from_icon_name("document-save-symbolic")
    download_indicator.set_margin_start(6)
    if inContent:
        inner.append(download_indicator)
        button.connect("clicked", lambda btn: _download_attachment(btn, attachment))
    if not inContent:
        container.add_css_class("card")
        return container
    else:
        return button


def _download_attachment(button, attachment) -> None:
    parent = button.get_root()
    if not isinstance(parent, Gtk.Window):
        parent = None

    chooser = Gtk.FileChooserNative.new(
        "Select download folder",
        parent,
        Gtk.FileChooserAction.SELECT_FOLDER,
        "Select",
        "Cancel",
    )

    def _on_response(dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            folder = dialog.get_file()
            path = folder.get_path() if folder else None
            if path:
                content = attachment["content"]
                if isinstance(content, memoryview):
                    content = content.tobytes()
                elif isinstance(content, bytearray):
                    content = bytes(content)
                filename = Path(attachment["filename"]).name or "attachment.bin"
                Path(path, filename).write_bytes(content)
        dialog.destroy()

    chooser.connect("response", _on_response)
    chooser.show()


def _format_email_date(email: dict) -> str:
    raw_date = str(email.get("date", "") or "")
    if not raw_date:
        fetched_at = str(email.get("fetched_at", "") or "")
        return f"No date. Arrived at {fetched_at}" if fetched_at else "No date"

    try:
        return f"Got at {parsedate_to_datetime(raw_date).strftime('%H:%M %d-%m-%Y ')}"
    except (TypeError, ValueError, IndexError, OverflowError):
        fetched_at = str(email.get("fetched_at", "") or "")
        return f"No date. Arrived at {fetched_at}" if fetched_at else raw_date


class EmailsView(Gtk.Box):
    def __init__(self, on_reply_requested=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        init_email_db()
        self.main_container = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        self.main_container.set_wide_handle(True)
        self.main_container.set_resize_start_child(True)
        self.main_container.set_resize_end_child(True)
        self.main_container.set_shrink_start_child(False)
        self.main_container.set_shrink_end_child(False)
        self.email_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.email_extended = Adw.Bin()
        self.email_extended.set_visible(False)
        self.emails = []
        self.selected_email = None
        self.updating = False
        self.update_indicator: Gtk.Widget | None = None
        self.style_manager = Adw.StyleManager.get_default()
        self.style_manager.connect("notify::dark", self._on_dark_mode_changed)
        self._on_reply_requested = on_reply_requested
        self.email_details = self.make_email_details()
        self.email_extended.set_child(self.email_details)
        self.clicked_email_id = ""

        # Selection state
        self.select_mode = False
        self.selected_emails = set()

        scroll_window_parent = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.set_margin_start(6)
        toolbar.set_margin_end(6)
        toolbar.set_margin_top(6)

        # Selection info label
        self.selection_label = Gtk.Label(label="")
        self.selection_label.add_css_class("caption")
        self.selection_label.set_hexpand(True)
        self.selection_label.set_xalign(0)
        toolbar.append(self.selection_label)

        # Select mode toggle button
        self.toolbar_enter_select_mode = Gtk.Button()
        toolbar_enter_select_mode_content = Adw.ButtonContent(
            icon_name="selection-mode-symbolic",
            label="Select"
        )
        self.toolbar_enter_select_mode.set_child(toolbar_enter_select_mode_content)
        self.toolbar_enter_select_mode.connect("clicked", self._on_toggle_select_mode)

        # Mark read button
        self.toolbar_mark_read = Gtk.Button()
        toolbar_mark_read_content = Adw.ButtonContent(
            icon_name="mail-mark-notjunk-symbolic",
            label="Mark read",
        )
        self.toolbar_mark_read.set_child(toolbar_mark_read_content)
        self.toolbar_mark_read.set_visible(False)

        # Delete button
        self.toolbar_email_delete = Gtk.Button()
        toolbar_email_delete_content = Adw.ButtonContent(
            icon_name="edit-delete-symbolic", label="Delete"
        )
        self.toolbar_email_delete.set_child(toolbar_email_delete_content)
        self.toolbar_email_delete.set_visible(False)

        toolbar.append(self.toolbar_mark_read)
        toolbar.append(self.toolbar_email_delete)
        toolbar.append(self.toolbar_enter_select_mode)

        # Connect bulk action handlers
        self.toolbar_mark_read.connect("clicked", self._on_mark_selected_read)
        self.toolbar_email_delete.connect("clicked", self._on_delete_selected)

        scroll_window_parent.append(toolbar)
        scroll_window = Gtk.ScrolledWindow()
        scroll_window_parent.append(scroll_window)
        scroll_window.set_child(self.email_list)
        scroll_window.set_vexpand(True)
        scroll_window.set_hexpand(True)
        self.main_container.set_start_child(scroll_window_parent)
        self.main_container.set_end_child(self.email_extended)
        self.main_container.connect(
            "notify::width", self._on_main_container_width_changed
        )
        self.append(self.main_container)
        self.refetch_emails()

    def _on_toggle_select_mode(self, button):
        """Toggle selection mode on/off."""
        self.select_mode = not self.select_mode

        if self.select_mode:
            self.toolbar_enter_select_mode.add_css_class("suggested-action")
            self.toolbar_mark_read.set_visible(True)
            self.toolbar_email_delete.set_visible(True)
        else:
            self.toolbar_enter_select_mode.remove_css_class("suggested-action")
            self.toolbar_mark_read.set_visible(False)
            self.toolbar_email_delete.set_visible(False)
            for email in self.emails:
                email["_selected"] = False

        # rerender emails
        self._clear_email_list()
        self._render_emails(self.emails)
        self._update_selection_label()

    def _update_selection_label(self):
        """Update the selection count label."""
        selected_count = sum(1 for email in self.emails if email.get("_selected", False))
        total_count = len(self.emails)

        if selected_count == 0 or not self.select_mode:
            self.selection_label.set_label("")
        elif selected_count == total_count:
            self.selection_label.set_label(f"All {total_count} selected")
        else:
            self.selection_label.set_label(f"{selected_count} of {total_count} selected")

    def _get_selected_emails(self) -> list[dict]:
        """Return list of selected emails."""
        return [email for email in self.emails if email.get("_selected", False)]

    def _update_pane_position(self):
        width = self.main_container.get_width()
        if width <= 0:
            return
        if self.email_extended.get_visible():
            self.main_container.set_position(width * 2 // 3)
        else:
            self.main_container.set_position(width // 4)

    def _on_main_container_width_changed(self, *_):
        self._update_pane_position()

    def on_email_clicked(self, email):

        if self.clicked_email_id == email["uid"]:
            self.email_extended.set_visible(False)
            self.clicked_email_id = ""
            self._update_pane_position()
            return
        self.selected_email = email
        self.clicked_email_id = email["uid"]
        self.email_extended.set_visible(True)
        self._update_pane_position()
        if not bool(email.get("read", False)):
            self._sync_email_read_state(email, True)
        self._update_read_toggle_button()
        self.date_label.set_label(_format_email_date(email))
        self.sender_label.set_label(str(f"Sent by {email.get('from', '')}"))
        self.receivers_label.set_label(str(f"Sent to {email.get('to')}"))
        self.subject_label.set_label(str(email.get("subject", "")))
        self.body_view.load_html(self._build_email_html(email), "about:blank")

        child = self.expanded_attachment_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.expanded_attachment_box.remove(child)
            child = next_child
        for attachment in email["attachments"]:
            self.expanded_attachment_box.append(
                makeAttachmentRow(attachment, inContent=True)
            )

    def _sync_email_read_state(self, email: dict, read: bool) -> None:
        account = str(email.get("account", ""))
        uid = str(email.get("uid", ""))
        if not account or not uid:
            return
        if not set_email_read_state(account, uid, read):
            return

        for cached_email in self.emails:
            if (
                str(cached_email.get("account", "")) == account
                and str(cached_email.get("uid", "")) == uid
            ):
                cached_email["read"] = read

        email["read"] = read
        if self.selected_email is not None:
            self.selected_email["read"] = read
        self._clear_email_list()
        self._render_emails(self.emails)

    def _update_read_toggle_button(self) -> None:
        if self.selected_email is None:
            self.read_toggle_button.set_visible(False)
            return
        is_read = bool(self.selected_email.get("read", False))
        self.read_toggle_button.set_visible(True)
        self.read_toggle_button.set_label(
            "Mark as unread" if is_read else "Mark as read"
        )

    def _on_toggle_read_clicked(self, _button) -> None:
        if self.selected_email is None:
            return
        read_now = bool(self.selected_email.get("read", False))
        self._sync_email_read_state(self.selected_email, not read_now)
        self._update_read_toggle_button()

    def _on_dark_mode_changed(self, *_):
        if self.selected_email:
            self.body_view.load_html(
                self._build_email_html(self.selected_email), "about:blank"
            )
            return
        self.body_view.load_html(self._build_placeholder_html(), "about:blank")

    def _build_theme_style(self) -> str:
        if self.style_manager.get_dark():
            background = "#222226"
            text = "#fffff"
            muted = "#9aa0a6"
            link = "#7bb1ff"
            color_scheme = "dark"
        else:
            background = "#FAFAFB"
            text = "#1f1f1f"
            muted = "#5f6368"
            link = "#1557b0"
            color_scheme = "light"

        return f"""
            :root {{
                color-scheme: {color_scheme};
            }}
            html, body {{
                background-color: {background} !important;
                color: {text} !important;
            }}
            a {{
                color: {link} !important;
            }}
            blockquote {{
                border-left: 3px solid {muted};
                margin-left: 0;
                padding-left: 0.75rem;
            }}
            img {{
                max-width: 100%;
                height: auto;
            }}
        """

    def _inject_theme_style(self, raw_html: str) -> str:
        style_block = f"<style>{self._build_theme_style()}</style>"
        html_lower = raw_html.lower()
        head_close = html_lower.find("</head>")
        if head_close != -1:
            return f"{raw_html[:head_close]}{style_block}{raw_html[head_close:]}"

        if "<html" in html_lower:
            return f"{style_block}{raw_html}"

        return (
            "<html><head><meta charset='utf-8'>"
            f"{style_block}</head><body>{raw_html}</body></html>"
        )

    def _build_email_html(self, email: dict) -> str:
        body_plain = email.get("body_plain", "")
        body_html = email.get("body_html", "")
        if body_html:
            body_html = _replace_cid_references(body_html, email.get("attachments", []))
            return self._inject_theme_style(body_html)
        if body_plain:
            escaped_plain = html.escape(body_plain).replace("\n", "<br>")
            return self._inject_theme_style(escaped_plain)
        return self._build_placeholder_html()

    def _build_placeholder_html(self) -> str:
        return self._inject_theme_style("<i>No message body</i>")

    def _on_email_reply_clicked(self):
        """Reply to email"""
        if self.selected_email is None:
            return
        if callable(self._on_reply_requested):
            self._on_reply_requested(self.selected_email)

    def _on_mark_selected_read(self, button):
        """Mark all selected emails as read."""
        selected = self._get_selected_emails()
        if not selected:
            return

        print(f"Marking {len(selected)} emails as read")
        for email in selected:
            if not bool(email.get("read", False)):
                self._sync_email_read_state(email, True)

        self.select_mode = False
        self.toolbar_enter_select_mode.remove_css_class("suggested-action")
        self._clear_email_list()
        self._render_emails(self.emails)
        self._update_selection_label()

    def _on_delete_selected(self, button):
        """Delete all selected emails with confirmation."""
        selected = self._get_selected_emails()
        if not selected:
            return

        parent = self.get_root()
        dialog = Adw.AlertDialog.new()
        dialog.set_heading(f"Sure to delete {len(selected)} emails?")
        dialog.set_body("You can't undo this, they will be also deleted from server")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_response(d, response, user_data):
            if response == "delete":
                self._perform_delete_selected(selected)

        if isinstance(parent, Gtk.Window):
            dialog.choose(parent, None, on_response, None)
        else:
            dialog.choose(None, None, on_response, None)

    def _perform_delete_selected(self, selected: list[dict]):
        """Actually delete the emails from the backend and UI"""
        print(f"Deleting {len(selected)} emails")

        # Group emails by account
        emails_by_account: dict[str, list[str]] = {}
        for email in selected:
            account = str(email.get("account", ""))
            uid = str(email.get("uid", ""))
            if account and uid:
                if account not in emails_by_account:
                    emails_by_account[account] = []
                emails_by_account[account].append(uid)

        # Delete from backend in a thread
        def delete_thread():
            for account, uids in emails_by_account.items():
                # Delete from IMAP server
                deleted_count, error = delete_emails_batch(account, uids)
                if error:
                    print(f"Error deleting emails from {account}: {error}")
                else:
                    print(f"Successfully deleted {deleted_count} emails from {account}")

                # Delete from local database
                if delete_emails_from_db(account, uids):
                    print(f"Deleted {len(uids)} emails from database for {account}")
                else:
                    print(f"Failed to delete emails from database for {account}")

            # Update UI on main thread
            GLib.idle_add(self._finalize_delete, selected)

        thread = threading.Thread(target=delete_thread, daemon=True)
        thread.start()

    def _finalize_delete(self, deleted_emails: list[dict]):
        """Finalize the UI after deletion"""
        # Remove deleted emails from list
        for email in deleted_emails:
            if email in self.emails:
                self.emails.remove(email)

        # Close email detail pane if selected email was deleted
        if self.selected_email in deleted_emails:
            self.email_extended.set_visible(False)
            self.selected_email = None
            self.clicked_email_id = ""
            self._update_pane_position()

        # Exit select mode and re-render
        self.select_mode = False
        self.toolbar_enter_select_mode.remove_css_class("suggested-action")
        self._clear_email_list()
        self._render_emails(self.emails)
        self._update_selection_label()

    def make_email_details(self):
        def copy_sender(_button):
            import pyperclip

            if self.selected_email:
                pyperclip.copy(str(self.selected_email.get("from", "")))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        top_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.date_label = Gtk.Label(label="")
        self.date_label.set_xalign(0)
        self.date_label.add_css_class("caption")
        self.sender_label_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=6
        )
        self.sender_label_copy = Gtk.Button(icon_name="edit-copy-symbolic")
        self.sender_label = Gtk.Label(label="")
        self.sender_label.set_xalign(0)
        self.sender_label.add_css_class("caption")
        self.sender_label_box.append(self.sender_label)
        self.sender_label_box.append(self.sender_label_copy)
        self.receivers_label = Gtk.Label()
        self.receivers_label.add_css_class("caption")
        self.receivers_label.set_xalign(0)
        self.subject_label = Gtk.Label(label="")
        self.subject_label.set_xalign(0)
        self.subject_label.add_css_class("heading")
        self.sender_label_copy.connect("clicked", copy_sender)
        self.read_toggle_button = Gtk.Button(label="Mark as read")
        self.read_toggle_button.set_halign(Gtk.Align.START)
        self.read_toggle_button.connect("clicked", self._on_toggle_read_clicked)
        self.read_toggle_button.set_visible(False)

        top_box.append(self.date_label)
        top_box.append(self.sender_label_box)
        top_box.append(self.receivers_label)
        box.append(top_box)
        box.append(self.subject_label)

        self.body_view = WebKit.WebView()
        self.body_view.set_hexpand(True)
        self.body_view.set_vexpand(True)
        body_settings = self.body_view.get_settings()
        body_settings.set_enable_javascript(False)
        body_settings.set_auto_load_images(True)
        self.body_view.load_html(
            self._inject_theme_style("<i>Select an email</i>"), "about:blank"
        )
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.expanded_attachment_box = Gtk.Box(spacing=6)

        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.email_reply_button = Gtk.Button(label="Reply")
        self.email_reply_button.connect(
            "clicked", lambda btn: self._on_email_reply_clicked()
        )
        actions_box.set_halign(Gtk.Align.START)
        actions_box.append(self.email_reply_button)
        actions_box.append(self.read_toggle_button)

        bottom_box.append(actions_box)
        bottom_box.append(self.expanded_attachment_box)
        body_scroll = Gtk.ScrolledWindow()
        body_scroll.set_hexpand(True)
        body_scroll.set_vexpand(True)
        body_scroll.set_child(self.body_view)
        box.append(body_scroll)
        box.append(bottom_box)
        return box

    def refetch_emails(self):
        self._load_emails_from_cache()
        thread = threading.Thread(target=self._sync_emails_thread)
        thread.daemon = True
        thread.start()

    def _load_emails_from_cache(self):
        self.emails = get_all_emails_cached()
        for email in self.emails:
            email["_selected"] = False
        self._clear_email_list()
        self._render_emails(self.emails)
        self._update_selection_label()

    def _sync_emails_thread(self):
        self.updating = True
        update_indicator = self.update_indicator
        if update_indicator is not None:
            GLib.idle_add(update_indicator.set_visible, True)

        updated_emails = self.emails
        try:
            fetch_all_emails_and_store()
            updated_emails = get_all_emails_cached()
        finally:
            GLib.idle_add(self._on_emails_updated, updated_emails)

    def _clear_email_list(self):
        child = self.email_list.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.email_list.remove(child)
            child = next_child

    def _render_emails(self, emails):
        for email in emails:
            is_selected = email.get("_selected", False)
            email_row = makeEmailRow(
                email,
                self.on_email_clicked,
                is_selected=is_selected,
                select_mode=self.select_mode,
                on_selection_changed=self._update_selection_label
            )
            self.email_list.append(email_row)

    def _on_emails_updated(self, emails=None):
        if emails is not None:
            self.emails = emails
            for email in self.emails:
                email["_selected"] = False
        if self.update_indicator:
            self.update_indicator.set_visible(False)
        self.updating = False
        self._clear_email_list()
        print(f"Updated with {len(self.emails)} emails")
        self._render_emails(self.emails)
        self._update_selection_label()
