import json
import os

import secretstorage

SCHEMA_NAME = "com.yehors.Blossom"
ATTRIBUTES = [
    "email",
    "imap_server",
    "imap_port",
    "imap_security",
    "imap_username",
    "imap_auth",
    "smtp_server",
    "smtp_port",
    "smtp_security",
    "smtp_auth",
]

_conn = None


def get_connection():
    global _conn
    if _conn is None:
        _conn = secretstorage.dbus_init()
    return _conn


def get_collection():
    return secretstorage.get_default_collection(get_connection())


def _search_attrs(email: str) -> dict:
    return {"schema": SCHEMA_NAME, "email": email}


CONFIG_PATH = "configs/accounts.json"


def save_credentials(
    email,
    password,
    imap_server,
    imap_port,
    imap_security,
    imap_username,
    imap_auth,
    smtp_server,
    smtp_port,
    smtp_security,
    smtp_auth,
):
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            try:
                accounts = json.load(f)
            except json.JSONDecodeError:
                accounts = {}
    else:
        accounts = {}

    accounts[email] = {
        "imap_server": imap_server,
        "imap_port": imap_port,
        "imap_security": imap_security,
        "imap_username": imap_username,
        "imap_auth": imap_auth,
        "smtp_server": smtp_server,
        "smtp_port": smtp_port,
        "smtp_security": smtp_security,
        "smtp_auth": smtp_auth,
    }

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(accounts, f, indent=2)

    return get_collection().create_item(
        label=f"Blossom account {email[:5]}",
        attributes={"schema": SCHEMA_NAME, "email": email},
        secret=password.encode(),
        replace=True,
    )


def iter_items(collection):
    for item_path in collection._collection.get_property("Items"):
        try:
            item = secretstorage.Item(
                collection.connection, item_path, collection.session
            )
            yield item
        except Exception:
            continue


def get_all_accounts() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def get_credentials(email: str) -> dict | None:
    if not os.path.exists(CONFIG_PATH):
        return None
    with open(CONFIG_PATH, "r") as f:
        accounts = json.load(f)
    if email not in accounts:
        return None

    collection = get_collection()
    results = list(collection.search_items(_search_attrs(email)))
    if not results:
        return None

    return accounts[email] | {
        "email": email,
        "password": results[0].get_secret().decode(),
    }


def delete_credentials(email: str) -> bool:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            accounts = json.load(f)
        if email in accounts:
            del accounts[email]
            with open(CONFIG_PATH, "w") as f:
                json.dump(accounts, f, indent=2)

    try:
        results = list(get_collection().search_items(_search_attrs(email)))
        for item in results:
            item.delete()
        return True
    except Exception:
        return False


def delete_all_credentials(sure=False) -> bool:
    if not sure:
        return False
    if os.path.exists(CONFIG_PATH):
        os.remove(CONFIG_PATH)
    try:
        get_collection().delete()
    except Exception:
        return False
    return True


# print(
#     save_credentials(
#         email="test@example.com",
#         password="testpassword",
#         imap_server="imap.example.com",
#         imap_port="993",
#         imap_security="SSL",
#         imap_username="test@example.com",
#         imap_auth="password",
#         smtp_server="smtp.example.com",
#         smtp_port="587",
#         smtp_security="TLS",
#         smtp_auth="password",
#     )
# )
# print(get_all_accounts())
# delete_all_credentials(sure=True)
