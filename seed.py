"""Seed reference data. Never creates a default password.

Run:  python -m database.seed
Optionally create the first admin with environment variables
ALGEBRALAB_ADMIN_USER and ALGEBRALAB_ADMIN_PASSWORD (see .env.example).
"""
import os
from typing import Optional

from db import create_user, init_db, session

ROLES = ["student", "teacher", "admin"]
TOPICS = [
    ("left-right-cosets", "Left and Right Cosets"),
    ("lagrange", "Lagrange's Theorem and Its Converse"),
    ("normal-subgroups", "Normal and Non-Normal Subgroups"),
    ("normalizers-centralizers", "Normalizers and Centralizers"),
    ("centre-conjugacy", "Centre and Conjugacy Classes"),
    ("quotient-groups", "Quotient Groups and Cayley Tables"),
    ("quotient-classification", "Classification of Quotient Groups"),
]


def seed_database(path: Optional[str] = None) -> None:
    init_db(path)
    with session(path) as conn:
        conn.executemany("INSERT OR IGNORE INTO roles (name) VALUES (?)", [(r,) for r in ROLES])
        conn.executemany("INSERT OR IGNORE INTO topics (slug, title, position) VALUES (?,?,?)",
                         [(s, t, i + 1) for i, (s, t) in enumerate(TOPICS)])
        user, pw = os.environ.get("ALGEBRALAB_ADMIN_USER"), os.environ.get("ALGEBRALAB_ADMIN_PASSWORD")
        if user and pw:
            exists = conn.execute("SELECT 1 FROM users WHERE username = ?", (user,)).fetchone()
            if not exists:
                create_user(conn, user, pw, role="admin", full_name="Administrator")


if __name__ == "__main__":
    seed_database()
    print("Database initialised and seeded.")
