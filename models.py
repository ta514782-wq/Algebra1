"""SQLite schema for AlgebraLab (kept separate from the UI)."""

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK (name IN ('student','teacher','admin'))
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT UNIQUE,
    full_name TEXT,
    password_hash TEXT NOT NULL,
    role_id INTEGER NOT NULL REFERENCES roles(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_login TEXT
);

CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    body_md TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY,
    uid TEXT NOT NULL UNIQUE,                 -- stable external ID, e.g. COS-0001
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    difficulty TEXT NOT NULL CHECK (difficulty IN ('easy','medium','advanced')),
    question TEXT NOT NULL,
    correct_option INTEGER NOT NULL CHECK (correct_option BETWEEN 0 AND 3),
    reasoning TEXT NOT NULL,                  -- mathematical reasoning / step-by-step
    formula TEXT,
    verification_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (verification_status IN ('pending','verified','rejected')),
    source TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS answer_options (
    id INTEGER PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position BETWEEN 0 AND 3),
    text TEXT NOT NULL,
    explanation TEXT NOT NULL,                -- why correct / why incorrect
    UNIQUE (question_id, position)
);

CREATE TABLE IF NOT EXISTS practice_sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('practice','exam')),
    topic_id INTEGER REFERENCES topics(id),
    num_questions INTEGER NOT NULL,
    time_limit_s INTEGER,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT,
    score INTEGER
);

CREATE TABLE IF NOT EXISTS student_answers (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id),
    chosen_option INTEGER CHECK (chosen_option BETWEEN 0 AND 3),
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0,1)),
    seconds_taken REAL,
    answered_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS examination_results (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL UNIQUE REFERENCES practice_sessions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total INTEGER NOT NULL,
    correct INTEGER NOT NULL,
    percentage REAL NOT NULL,
    seconds_taken REAL
);

CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
    note_id INTEGER REFERENCES notes(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK ((question_id IS NOT NULL) <> (note_id IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS incorrect_answers (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    last_chosen_option INTEGER,
    times_wrong INTEGER NOT NULL DEFAULT 1,
    mastered INTEGER NOT NULL DEFAULT 0 CHECK (mastered IN (0,1)),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, question_id)
);

CREATE TABLE IF NOT EXISTS topic_progress (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    notes_completed INTEGER NOT NULL DEFAULT 0 CHECK (notes_completed IN (0,1)),
    attempted INTEGER NOT NULL DEFAULT 0,
    correct INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, topic_id)
);

CREATE TABLE IF NOT EXISTS learning_activity (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_questions_topic ON questions(topic_id, difficulty);
CREATE INDEX IF NOT EXISTS idx_answers_user ON student_answers(user_id, question_id);
CREATE INDEX IF NOT EXISTS idx_answers_session ON student_answers(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON practice_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_incorrect_user ON incorrect_answers(user_id, mastered);
CREATE INDEX IF NOT EXISTS idx_activity_user ON learning_activity(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON bookmarks(user_id);
"""

TABLES = [
    "roles", "users", "topics", "notes", "questions", "answer_options",
    "practice_sessions", "student_answers", "examination_results", "bookmarks",
    "incorrect_answers", "topic_progress", "learning_activity", "app_settings",
]
