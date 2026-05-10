import imaplib as imap
import smtplib as smtp
import socket
import threading

import gi

from functions.emails import (
    get_all_accounts,
    get_collection,
    get_credentials,
)

gi.require_version("GLib", "2.0")
from gi.repository import GLib

imap_connections = {}


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
                print(
                    f"Failed to establish a connection for {account} on server {credentials['imap_server']} and port {credentials['imap_port']}"
                )
            except socket.gaierror:
                print(f"Server {credentials['imap_server']} is unreachable")
            except socket.timeout:
                print(f"Connection to server {credentials['imap_server']} timed out")
            except Exception as e:
                print(f"{account} unexpected error for login: {e}")


def fetch_emails(account, callback):
    credentials = get_credentials(account)
    if credentials is None:
        return GLib.Error("No credentials found for account: " + account)
    else:
        print("pass", credentials["password"])


on_start()
fetch_emails("test@test.com", None)
print(imap_connections)
