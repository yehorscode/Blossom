import email
import imaplib as imap
import socket
from email.header import decode_header
from typing import Callable

from blossom.functions.emails import (
    get_all_accounts,
    get_credentials,
)
from blossom.functions.logging import error

def delete_emails_from_db(account: str, uids: list[str]) -> bool:
    """
    Delete emails from the local database.

    Args:
        account: Email account identifier
        uids: List of UIDs to delete

    Returns:
        True if successful, False otherwise
    """
    try:
        from functions.emails import get_db_connection

        conn = get_db_connection()
        cursor = conn.cursor()

        # Delete each email by uid
        for uid in uids:
            cursor.execute(
                "DELETE FROM emails WHERE account = ? AND uid = ?",
                (account, uid)
            )

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        error(f"Failed to delete emails from database: {str(e)}")
        return False

# Batch delete utility
def delete_emails_batch(account: str, uids: list[str], folder: str = "INBOX") -> tuple[int, str | None]:
    """
    Delete multiple emails at once by their UIDs.

    Args:
        account: Email account identifier
        uids: List of UIDs to delete
        folder: The folder to delete from (default: INBOX)

    Returns:
        Tuple of (deleted_count: int, error_message: str | None)
    """
    if not uids:
        return 0, None

    credentials = get_credentials(account)
    if credentials is None:
        return 0, f"No credentials found for account: {account}"

    conn = _get_connection(account, credentials)

    try:
        try:
            conn.login(
                user=credentials["imap_username"], password=credentials["password"]
            )
        except imap.IMAP4.error as e:
            if (
                "state AUTH" not in str(e)
                and "already authenticated" not in str(e).lower()
            ):
                raise

        typ, _ = conn.select(folder)
        if typ != "OK":
            return 0, f"Failed to select folder: {folder}"

        deleted_count = 0
        for uid in uids:
            typ, _ = conn.store(uid, "+FLAGS", r"(\Deleted)")
            if typ == "OK":
                deleted_count += 1
            else:
                return deleted_count, f"Failed to mark email {uid} for deletion"

        typ, _ = conn.expunge()
        if typ != "OK":
            return deleted_count, "Failed to expunge deleted emails"

        return deleted_count, None
    except imap.IMAP4.error as e:
        return 0, f"IMAP error: {str(e)}"
    except socket.gaierror:
        return 0, "IMAP server is unreachable"
    except socket.timeout:
        return 0, "Connection to IMAP server timed out"
    except Exception as e:
        return 0, f"Unexpected error deleting emails: {str(e)}"
    finally:
        try:
            conn.close()
        except:
            pass

imap_connections: dict[str, imap.IMAP4_SSL] = {}


def on_start():
    for account in get_all_accounts():
        credentials = get_credentials(account)
        if credentials:
            try:
                connection = imap.IMAP4_SSL(
                    host=credentials["imap_server"], port=credentials["imap_port"]
                )
                imap_connections[account] = connection
            except imap.IMAP4.error:
                error(
                    f"Failed to establish a connection for {account} on server {credentials['imap_server']} and port {credentials['imap_port']}"
                )
            except socket.gaierror:
                error(f"Server {credentials['imap_server']} is unreachable")
            except socket.timeout:
                error(f"Connection to server {credentials['imap_server']} timed out")
            except Exception as e:
                error(f"{account} unexpected error for login: {e}")


def _get_connection(account: str, credentials: dict) -> imap.IMAP4_SSL:
    connection = imap.IMAP4_SSL(
        host=credentials["imap_server"], port=credentials["imap_port"]
    )
    return connection


def _decode_subject(raw_subject: str | None) -> str:
    if not raw_subject:
        return ""
    decoded_subject = []
    for part, encoding in decode_header(raw_subject):
        if isinstance(part, bytes):
            decoded_subject.append(part.decode(encoding or "utf-8", errors="replace"))
        else:
            decoded_subject.append(part)
    return "".join(decoded_subject)


def _decode_header_value(raw_value: str | None) -> str:
    if not raw_value:
        return ""
    decoded = []
    for part, encoding in decode_header(raw_value):
        if isinstance(part, bytes):
            decoded.append(part.decode(encoding or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _decode_part_payload(part) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _extract_bodies(msg) -> tuple[str, str]:
    if not msg.is_multipart():
        return _decode_part_payload(msg), ""

    text_plain = ""
    text_html = ""

    for part in msg.walk():
        content_type = part.get_content_type()
        disposition = (part.get("Content-Disposition") or "").lower()
        if "attachment" in disposition or part.get_filename():
            continue
        if content_type == "text/plain" and not text_plain:
            text_plain = _decode_part_payload(part)
        elif content_type == "text/html" and not text_html:
            text_html = _decode_part_payload(part)

    return text_plain, text_html


def _extract_attachments(msg) -> list[dict[str, object]]:
    attachments = []
    for part_index, part in enumerate(msg.walk()):
        disposition = (part.get("Content-Disposition") or "").lower()
        filename_header = part.get_filename()
        content_id = part.get("Content-ID")

        if "attachment" not in disposition and not filename_header and not content_id:
            continue

        payload = part.get_payload(decode=True)
        if payload is None:
            continue

        filename = _decode_header_value(filename_header) or f"attachment-{part_index}"

        if content_id:
            content_id = content_id.strip("<>").strip()

        attachments.append(
            {
                "part_index": part_index,
                "filename": filename,
                "mime_type": part.get_content_type() or "application/octet-stream",
                "size": len(payload),
                "content": payload,
                "content_id": content_id,
            }
        )
    return attachments


def fetch_emails(
    account: str,
    callback: Callable[[list[dict[str, object]]], None] | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    credentials = get_credentials(account)
    if credentials is None:
        raise ValueError("No credentials found for account: " + account)

    conn = _get_connection(account, credentials)

    try:
        try:
            conn.login(
                user=credentials["imap_username"], password=credentials["password"]
            )
        except imap.IMAP4.error as e:
            if (
                "state AUTH" not in str(e)
                and "already authenticated" not in str(e).lower()
            ):
                raise

        typ, _ = conn.select("INBOX", readonly=True)
        if typ != "OK":
            raise RuntimeError("Failed to select INBOX")

        typ, data = conn.search(None, "ALL")
        if typ != "OK":
            raise RuntimeError("Failed to search mailbox")

        uids = data[0].split()[-limit:]
        emails: list[dict[str, object]] = []

        for uid in reversed(uids):
            typ, msg_data = conn.fetch(uid, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue

            if not isinstance(msg_data[0], tuple):
                continue

            raw_msg = msg_data[0][1]
            msg = email.message_from_bytes(raw_msg)
            body_plain, body_html = _extract_bodies(msg)
            attachments = _extract_attachments(msg)

            emails.append(
                {
                    "uid": uid.decode(errors="replace"),
                    "from": msg.get("From", ""),
                    "date": msg.get("Date", ""),
                    "subject": _decode_subject(msg.get("Subject")),
                    "body_plain": body_plain,
                    "body_html": body_html,
                    "to": msg.get("To", ""),
                    "attachments": attachments,
                }
            )

        if callback:
            callback(emails)
        return emails
    finally:
        try:
            conn.close()
        except:
            pass


def delete_email(account: str, uid: str, folder: str = "INBOX") -> tuple[bool, str | None]:
    """
    Delete a single email by UID.

    Args:
        account: Email account identifier
        uid: The UID of the email to delete
        folder: The folder to delete from (default: INBOX)

    Returns:
        Tuple of (success: bool, error_message: str | None)
    """
    credentials = get_credentials(account)
    if credentials is None:
        return False, f"No credentials found for account: {account}"

    conn = _get_connection(account, credentials)

    try:
        try:
            conn.login(
                user=credentials["imap_username"], password=credentials["password"]
            )
        except imap.IMAP4.error as e:
            if (
                "state AUTH" not in str(e)
                and "already authenticated" not in str(e).lower()
            ):
                raise

        typ, _ = conn.select(folder)
        if typ != "OK":
            return False, f"Failed to select folder: {folder}"

        typ, _ = conn.store(uid, "+FLAGS", r"(\Deleted)")
        if typ != "OK":
            return False, f"Failed to mark email {uid} for deletion"

        typ, _ = conn.expunge()
        if typ != "OK":
            return False, "Failed to expunge deleted emails"

        return True, None
    except imap.IMAP4.error as e:
        return False, f"IMAP error: {str(e)}"
    except socket.gaierror:
        return False, "IMAP server is unreachable"
    except socket.timeout:
        return False, "Connection to IMAP server timed out"
    except Exception as e:
        return False, f"Unexpected error deleting email: {str(e)}"
    finally:
        try:
            conn.close()
        except:
            pass


def delete_emails_by_subject(account: str, subject: str, folder: str = "INBOX") -> tuple[bool, str | None]:
    """
    Delete all emails matching a subject line.

    Args:
        account: Email account identifier
        subject: Subject line to match
        folder: The folder to delete from (default: INBOX)

    Returns:
        Tuple of (success: bool, error_message: str | None)
    """
    credentials = get_credentials(account)
    if credentials is None:
        return False, f"No credentials found for account: {account}"

    conn = _get_connection(account, credentials)

    try:
        try:
            conn.login(
                user=credentials["imap_username"], password=credentials["password"]
            )
        except imap.IMAP4.error as e:
            if (
                "state AUTH" not in str(e)
                and "already authenticated" not in str(e).lower()
            ):
                raise

        typ, _ = conn.select(folder)
        if typ != "OK":
            return False, f"Failed to select folder: {folder}"

        typ, data = conn.search(None, f'SUBJECT "{subject}"')
        if typ != "OK":
            return False, f"Failed to search for emails with subject: {subject}"

        uids = data[0].split()
        if not uids:
            return True, f"No emails found with subject: {subject}"

        for uid in uids:
            typ, _ = conn.store(uid, "+FLAGS", r"(\Deleted)")
            if typ != "OK":
                return False, f"Failed to mark email {uid} for deletion"

        typ, _ = conn.expunge()
        if typ != "OK":
            return False, "Failed to expunge deleted emails"

        return True, f"Successfully deleted {len(uids)} email(s)"
    except imap.IMAP4.error as e:
        return False, f"IMAP error: {str(e)}"
    except socket.gaierror:
        return False, "IMAP server is unreachable"
    except socket.timeout:
        return False, "Connection to IMAP server timed out"
    except Exception as e:
        return False, f"Unexpected error deleting emails: {str(e)}"
    finally:
        try:
            conn.close()
        except:
            pass


def delete_emails_by_sender(account: str, sender: str, folder: str = "INBOX") -> tuple[bool, str | None]:
    """
    Delete all emails from a specific sender.

    Args:
        account: Email account identifier
        sender: Sender email address to match
        folder: The folder to delete from (default: INBOX)

    Returns:
        Tuple of (success: bool, error_message: str | None)
    """
    credentials = get_credentials(account)
    if credentials is None:
        return False, f"No credentials found for account: {account}"

    conn = _get_connection(account, credentials)

    try:
        try:
            conn.login(
                user=credentials["imap_username"], password=credentials["password"]
            )
        except imap.IMAP4.error as e:
            if (
                "state AUTH" not in str(e)
                and "already authenticated" not in str(e).lower()
            ):
                raise

        typ, _ = conn.select(folder)
        if typ != "OK":
            return False, f"Failed to select folder: {folder}"

        typ, data = conn.search(None, f'FROM "{sender}"')
        if typ != "OK":
            return False, f"Failed to search for emails from: {sender}"

        uids = data[0].split()
        if not uids:
            return True, f"No emails found from: {sender}"

        for uid in uids:
            typ, _ = conn.store(uid, "+FLAGS", r"(\Deleted)")
            if typ != "OK":
                return False, f"Failed to mark email {uid} for deletion"

        typ, _ = conn.expunge()
        if typ != "OK":
            return False, "Failed to expunge deleted emails"

        return True, f"Successfully deleted {len(uids)} email(s) from {sender}"
    except imap.IMAP4.error as e:
        return False, f"IMAP error: {str(e)}"
    except socket.gaierror:
        return False, "IMAP server is unreachable"
    except socket.timeout:
        return False, "Connection to IMAP server timed out"
    except Exception as e:
        return False, f"Unexpected error deleting emails: {str(e)}"
    finally:
        try:
            conn.close()
        except:
            pass
