import base64
import html
import re
import threading
from email.utils import parsedate_to_datetime
from pathlib import Path

import gi

from functions.emails import (
    fetch_all_emails_and_store,
    get_all_emails_cached,
    init_email_db,
    set_email_read_state,
)

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
    inner_content_horizontal_split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
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

    selected_tick_box = Gtk.Box()
    if email.get("uid") in getattr(on_clicked_callback, "selected_emails", set()):
        tick = Gtk.Image.new_from_icon_name("checkbox-symbolic")
        selected_tick_box.append(tick)
    inner_content_horizontal_split.append(selected_tick_box)
    inner_content_horizontal_split.append(inner_content)

    em_box.append(inner_content_horizontal_split)
    container.append(em_box)
    if email["attachments"]:
        inner_content.append(attachments_container)
    but = Gtk.Button()
    but.set_child(container)
    if on_clicked_callback:
        but.connect("clicked", lambda btn: on_clicked_callback(email))
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
    except TypeError, ValueError, IndexError, OverflowError:
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
        self.select_mode = False
        self.selected_emails = set()

        def handleSelectMode(self):
            if self.select_mode:
                print("disablign selecting")
                self.select_mode = False
                toolbar_enter_select_mode_content.set_label("Select emails")
                toolbar_enter_select_mode.remove_css_class("suggested-action")
            else:
                print("enablin selectin")
                self.select_mode = True
                toolbar_enter_select_mode_content.set_label("Exit selection")
                toolbar_enter_select_mode.add_css_class("suggested-action")

        scroll_window_parent = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        # toolbar buttons
        toolbar_enter_select_mode = Gtk.Button()
        toolbar_enter_select_mode_content = Adw.ButtonContent(
            icon_name="selection-mode-symbolic",
            label="Select emails"
        )
        toolbar_mark_read = Gtk.Button()
        toolbar_mark_read_content = Adw.ButtonContent(
            icon_name="mail-mark-notjunk-symbolic",
            label="Mark read",
        )
        toolbar_email_delete = Gtk.Button()
        toolbar_email_delete_content = Adw.ButtonContent(
            icon_name="edit-delete-symbolic", label="Delete"
        )
        toolbar_enter_select_mode.set_child(toolbar_enter_select_mode_content)
        toolbar_mark_read.set_child(toolbar_mark_read_content)
        toolbar_email_delete.set_child(toolbar_email_delete_content)
        toolbar_enter_select_mode.connect("clicked", lambda btn: handleSelectMode(self))
        toolbar.append(toolbar_enter_select_mode)
        toolbar.append(toolbar_mark_read)
        toolbar.append(toolbar_email_delete)
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
        if self.selected_email is None:
            return
        if callable(self._on_reply_requested):
            self._on_reply_requested(self.selected_email)

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
        self._clear_email_list()
        self._render_emails(self.emails)

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
            email_row = makeEmailRow(email, self.on_email_clicked)
            self.email_list.append(email_row)

    def _on_emails_updated(self, emails=None):
        if emails is not None:
            self.emails = emails
        if self.update_indicator:
            self.update_indicator.set_visible(False)
        self.updating = False
        self._clear_email_list()
        print(f"Updated with {len(self.emails)} emails")
        self._render_emails(self.emails)
