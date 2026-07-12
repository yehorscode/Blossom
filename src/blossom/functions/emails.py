import json
import os
import sqlite3
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import secretstorage

SCHEMA_NAME = "com.yehors.Blossom"

_conn = None
_db_conn = None

def get_data_dir():
    """~/.local/share/com.yehors.Blossom"""
    data_home = os.getenv("XDG_DATA_HOME",
                         os.path.join(os.path.expanduser("~"), ".local", "share"))
    path = Path(data_home) / "com.yehors.Blossom"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_dir():
    """~/.config/com.yehors.Blossom"""
    config_home = os.getenv("XDG_CONFIG_HOME",
                           os.path.join(os.path.expanduser("~"), ".config"))
    path = Path(config_home) / "com.yehors.Blossom"
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_db_connection():
    global _db_conn
    if _db_conn is None:
        db_path = get_data_dir() / "emails.db"
        _db_conn = sqlite3.connect(str(db_path), check_same_thread=False)
        _db_conn.row_factory = sqlite3.Row
    return _db_conn


def _coerce_email_datetime(value) -> datetime | None:
    raw_value = str(value or "")
    if not raw_value:
        return None

    parsed_value = None
    try:
        parsed_value = parsedate_to_datetime(raw_value)
    except TypeError, ValueError, IndexError, OverflowError:
        parsed_value = None

    if parsed_value is None:
        try:
            parsed_value = datetime.fromisoformat(raw_value)
        except ValueError:
            return None

    if parsed_value.tzinfo is not None:
        parsed_value = parsed_value.astimezone(timezone.utc).replace(tzinfo=None)

    return parsed_value


def _email_sort_key(email: dict) -> datetime:
    return (
        _coerce_email_datetime(email.get("date"))
        or _coerce_email_datetime(email.get("fetched_at"))
        or datetime.min
    )


def init_email_db():
    """Initialize email storage schema."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account TEXT NOT NULL,
            uid TEXT NOT NULL,
            from_addr TEXT,
            read BOOL NOT NULL,
            date TEXT,
            subject TEXT,
            body_plain TEXT,
            body_html TEXT,
            to_addr TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(account, uid)
        )
        """
    )
    try:
        cursor.execute("ALTER TABLE emails ADD COLUMN read BOOL NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS email_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account TEXT NOT NULL,
            uid TEXT NOT NULL,
            part_index INTEGER NOT NULL,
            filename TEXT NOT NULL,
            mime_type TEXT,
            size INTEGER,
            content BLOB NOT NULL,
            content_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(account, uid, part_index)
        )
        """
    )

    try:
        cursor.execute("ALTER TABLE email_attachments ADD COLUMN content_id TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()


def get_connection():
    global _conn
    if _conn is None:
        _conn = secretstorage.dbus_init()
    return _conn


def get_collection():
    return secretstorage.get_default_collection(get_connection())


def _search_attrs(email: str) -> dict:
    return {"schema": SCHEMA_NAME, "email": email}


def _password_attrs(email: str) -> dict:
    return {"schema": SCHEMA_NAME, "email": email, "kind": "password"}

CONFIG_PATH = get_config_dir() / "accounts.json"


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
    if CONFIG_PATH.exists():
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

    with open(CONFIG_PATH, "w") as f:
            json.dump(accounts, f, indent=2)

    for item in list(get_collection().search_items(_search_attrs(email))):
        item.delete()

    return get_collection().create_item(
        label=f"Blossom account {email[:5]}",
        attributes=_password_attrs(email),
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
    if not CONFIG_PATH.exists():
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

    password = get_password(email)
    if not password:
        return None

    return accounts[email] | {"email": email, "password": password}


def get_password(email: str) -> str | None:
    collection = get_collection()
    results = list(collection.search_items(_password_attrs(email)))
    if not results:
        results = list(collection.search_items(_search_attrs(email)))
    if not results:
        return None
    result = results[0]
    if result.is_locked():
        result.unlock()
    return result.get_secret().decode()


def delete_credential(email: str) -> bool:
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
        for item in list(get_collection().search_items({"schema": SCHEMA_NAME})):
            item.delete()
    except Exception:
        return False
    return True


def save_emails(account: str, emails: list[dict]) -> int:
    """Save emails to database, skipping duplicates. Returns count of new emails saved."""
    conn = get_db_connection()
    cursor = conn.cursor()
    saved = 0

    for email in emails:
        read_value = bool(email.get("read", False))
        cursor.execute(
            """
            INSERT OR IGNORE INTO emails (account, uid, from_addr, read, date, subject, body_plain, body_html, to_addr)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account,
                email["uid"],
                email.get("from", ""),
                int(read_value),
                email.get("date", ""),
                email.get("subject", ""),
                email.get("body_plain", ""),
                email.get("body_html", ""),
                email.get("to", ""),
            ),
        )
        if cursor.rowcount > 0:
            saved += 1

        for attachment in email.get("attachments", []):
            content = attachment.get("content", b"")
            if isinstance(content, memoryview):
                content = content.tobytes()
            elif isinstance(content, bytearray):
                content = bytes(content)
            elif not isinstance(content, bytes):
                continue

            cursor.execute(
                """
                INSERT OR IGNORE INTO email_attachments
                (account, uid, part_index, filename, mime_type, size, content, content_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account,
                    email["uid"],
                    int(attachment.get("part_index", 0)),
                    str(attachment.get("filename") or "attachment.bin"),
                    str(attachment.get("mime_type") or "application/octet-stream"),
                    int(attachment.get("size") or len(content)),
                    content,
                    attachment.get("content_id"),
                ),
            )

    conn.commit()
    return saved


def get_email_attachments(account: str, uid: str) -> list[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, part_index, filename, mime_type, size, content, content_id
        FROM email_attachments
        WHERE account = ? AND uid = ?
        ORDER BY part_index ASC
        """,
        (account, uid),
    )
    return [dict(row) for row in cursor.fetchall()]


def get_emails_from_db(account: str | None = None) -> list[dict]:
    """Retrieve emails from database, newest first."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if account:
        cursor.execute(
            "SELECT * FROM emails WHERE account = ? ORDER BY date DESC",
            (account,),
        )
    else:
        cursor.execute("SELECT * FROM emails ORDER BY date DESC")

    rows = cursor.fetchall()
    emails = []
    for row in rows:
        email_dict = dict(row)
        # Map DB column names to UI expected keys
        email_dict["from"] = email_dict.pop("from_addr")
        email_dict["to"] = email_dict.pop("to_addr")
        email_dict["read"] = bool(email_dict.get("read", 0))
        email_dict["attachments"] = get_email_attachments(
            str(email_dict["account"]), str(email_dict["uid"])
        )
        emails.append(email_dict)

    emails.sort(key=_email_sort_key, reverse=True)
    return emails


def get_email_by_uid(account: str, uid: str) -> dict | None:
    """Retrieve email by account and uid from db"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM emails WHERE account = ? AND uid = ?",
        (account, uid),
    )
    row = cursor.fetchone()
    if not row:
        return None

    email = dict(row)
    email["from"] = email.pop("from_addr")
    email["to"] = email.pop("to_addr")
    email["read"] = bool(email.get("read", 0))
    email["attachments"] = get_email_attachments(account, uid)
    return email


def set_email_read_state(account: str, uid: str, read: bool) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE emails SET read = ? WHERE account = ? AND uid = ?",
        (int(read), account, uid),
    )
    conn.commit()
    return cursor.rowcount > 0


def fetch_all_emails_and_store() -> int:
    """Fetch and save emails (all)"""
    from blossom.functions.ear import fetch_emails

    total_new = 0
    for account in get_all_accounts():
        try:
            emails = fetch_emails(account)
            new_count = save_emails(account, emails)
            total_new += new_count
        except Exception as e:
            print(f"Error fetching emails for {account}: {e}")
    return total_new


def get_all_emails_cached() -> list[dict]:
    """Get all emails from db, sorted newest first across accounts."""
    accounts = get_all_accounts()
    all_emails = []
    for account in accounts:
        all_emails.extend(get_emails_from_db(account))

    all_emails.sort(key=_email_sort_key, reverse=True)
    return all_emails
