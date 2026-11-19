"""Database access layer. Parameterised queries only; no UI imports."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator, Optional

from models import SCHEMA

DEFAULT_PATH = os.environ.get("ALGEBRALAB_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "algebralab.db"))


def get_connection(path: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or DEFAULT_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def session(path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    conn = get_connection(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(path: Optional[str] = None) -> None:
    """Create all tables and indexes (idempotent)."""
    conn = get_connection(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def create_user(conn: sqlite3.Connection, username: str, password: str, role: str = "student",
                full_name: str = "", email: Optional[str] = None) -> int:
    from security import hash_password
    row = conn.execute("SELECT id FROM roles WHERE name = ?", (role,)).fetchone()
    if row is None:
        raise ValueError(f"Unknown role '{role}'. Run seed_database() first.")
    cur = conn.execute(
        "INSERT INTO users (username, email, full_name, password_hash, role_id) VALUES (?,?,?,?,?)",
        (username.strip(), email, full_name, hash_password(password), row["id"]))
    return int(cur.lastrowid)


def authenticate(conn: sqlite3.Connection, username: str, password: str) -> Optional[sqlite3.Row]:
    from security import verify_password
    user = conn.execute(
        "SELECT u.*, r.name AS role FROM users u JOIN roles r ON r.id = u.role_id WHERE u.username = ?",
        (username.strip(),)).fetchone()
    if user and verify_password(password, user["password_hash"]):
        conn.execute("UPDATE users SET last_login = datetime('now') WHERE id = ?", (user["id"],))
        return user
    return None
