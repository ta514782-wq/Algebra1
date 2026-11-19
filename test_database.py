import os
import sqlite3
import tempfile

import db, models, security
from seed import seed_database


def fresh():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "t.db")
    seed_database(p)
    return p


def test_all_tables_created():
    p = fresh()
    with db.session(p) as c:
        names = {r["name"] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert set(models.TABLES) <= names


def test_seed_is_idempotent_and_has_seven_topics():
    p = fresh()
    seed_database(p)
    with db.session(p) as c:
        assert c.execute("SELECT COUNT(*) FROM topics").fetchone()[0] == 7
        assert c.execute("SELECT COUNT(*) FROM roles").fetchone()[0] == 3
        assert c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0   # no default account


def test_password_hashing():
    h = security.hash_password("correct horse")
    assert "correct horse" not in h
    assert security.verify_password("correct horse", h)
    assert not security.verify_password("wrong password", h)
    assert security.hash_password("correct horse") != h          # salted
    assert not security.verify_password("x", "garbage")
    try:
        security.hash_password("short")
    except ValueError:
        pass
    else:
        raise AssertionError("short password accepted")


def test_user_creation_and_authentication():
    p = fresh()
    with db.session(p) as c:
        db.create_user(c, "tayyab", "s3cret-pass", role="student")
        assert db.authenticate(c, "tayyab", "s3cret-pass")["role"] == "student"
        assert db.authenticate(c, "tayyab", "nope-nope") is None
        assert db.authenticate(c, "ghost", "s3cret-pass") is None
        stored = c.execute("SELECT password_hash FROM users").fetchone()[0]
        assert stored.startswith("scrypt$")


def test_sql_injection_attempt_is_inert():
    p = fresh()
    with db.session(p) as c:
        db.create_user(c, "alice", "password-1")
        assert db.authenticate(c, "alice' OR '1'='1", "x") is None
        assert c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1


def test_foreign_keys_and_constraints_enforced():
    p = fresh()
    with db.session(p) as c:
        try:
            c.execute("INSERT INTO users (username, password_hash, role_id) VALUES ('x','h',999)")
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("FK not enforced")
        try:
            c.execute("INSERT INTO questions (uid, topic_id, difficulty, question, correct_option, reasoning) "
                      "VALUES ('Q1',1,'impossible','q',0,'r')")
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("difficulty CHECK not enforced")


def test_admin_created_only_from_environment():
    d = tempfile.mkdtemp(); p = os.path.join(d, "a.db")
    os.environ["ALGEBRALAB_ADMIN_USER"] = "root_admin"
    os.environ["ALGEBRALAB_ADMIN_PASSWORD"] = "env-supplied-pw"
    try:
        seed_database(p)
        with db.session(p) as c:
            assert db.authenticate(c, "root_admin", "env-supplied-pw")["role"] == "admin"
    finally:
        del os.environ["ALGEBRALAB_ADMIN_USER"], os.environ["ALGEBRALAB_ADMIN_PASSWORD"]
