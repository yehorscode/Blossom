import email
import email.utils
import smtplib as smtp
import socket
from datetime import datetime, timezone

from functions.emails import get_all_accounts, get_credentials
from functions.logging import error

smtp_connections: dict[str, smtp.SMTP_SSL] = {}


def _create_connection(account: str) -> smtp.SMTP_SSL:
    credentials = get_credentials(account)
    if credentials is None:
        raise ValueError(f"No credentials found for account: {account}")

    smtp_port = credentials.get("smtp_port")
    try:
        smtp_port = int(smtp_port)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid SMTP port for account: {account}") from exc

    connection = smtp.SMTP_SSL(host=credentials["smtp_server"], port=smtp_port)
    connection.login(
        user=credentials.get("imap_username") or credentials["email"],
        password=credentials["password"],
    )
    return connection


def on_start():
    for account in get_all_accounts():
        try:
            smtp_connections[account] = _create_connection(account)
        except smtp.SMTPConnectError:
            credentials = get_credentials(account)
            if not credentials:
                error(f"No credentials found for account: {account}")
                continue
            error(
                f"Failed to establish a connection for {account} on server {credentials['smtp_server']} and port {credentials['smtp_port']}"
            )
        except socket.gaierror:
            credentials = get_credentials(account)
            if not credentials:
                error(f"No credentials found for account: {account}")
                continue
            error(f"Server {credentials['smtp_server']} is unreachable")
        except socket.timeout:
            credentials = get_credentials(account)
            if not credentials:
                error(f"No credentials found for account: {account}")
                continue
            error(f"Connection to server {credentials['smtp_server']} timed out")
        except Exception as e:
            error(f"{account} unexpected error for login: {e}")


def send_email(message, sender, to_addrs: list[str]) -> tuple[bool, str | None]:
    try:
        if "Date" not in message:
            message["Date"] = email.utils.formatdate()

        connection = smtp_connections.get(sender)
        if connection is None:
            connection = _create_connection(sender)
            smtp_connections[sender] = connection

        refused = connection.send_message(
            msg=message, from_addr=sender, to_addrs=to_addrs
        )
        if refused:
            return False, f"Some recipients were refused: {', '.join(refused.keys())}"
        return True, None
    except smtp.SMTPServerDisconnected:
        connection = _create_connection(sender)
        smtp_connections[sender] = connection
        refused = connection.send_message(
            msg=message, from_addr=sender, to_addrs=to_addrs
        )
        if refused:
            return False, f"Some recipients were refused: {', '.join(refused.keys())}"
        return True, None
    except smtp.SMTPRecipientsRefused as e:
        return False, f"Recipients were refused: {', '.join(e.recipients.keys())}"
    except smtp.SMTPAuthenticationError:
        return False, "SMTP authentication failed."
    except smtp.SMTPConnectError:
        return False, "Failed to connect to SMTP server."
    except (smtp.SMTPException, OSError, ValueError) as e:
        return False, str(e)
