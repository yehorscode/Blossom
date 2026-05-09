import threading

import gi

from functions.emails import (
    get_all_accounts,
    get_collection,
    get_credentials,
)

gi.require_version("GLib", "2.0")
from gi.repository import GLib


def fetch_emails(account, callback):
    credentials = get_credentials(account)
    if credentials is None:
        return GLib.Error("No credentials found for account: " + account)
    else:
        print("pass", credentials["password"])


fetch_emails("test@test.com", None)
