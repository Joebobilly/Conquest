import os
import sqlite3
from contextlib import contextmanager


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS world_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS land_tiles (
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    owner_user_id INTEGER,
    terrain TEXT NOT NULL,
    PRIMARY KEY (x, y),
    FOREIGN KEY (owner_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS resources (
    user_id INTEGER PRIMARY KEY,
    power INTEGER NOT NULL,
    max_power INTEGER NOT NULL,
    last_tick REAL NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


@contextmanager
def connect(db_path: str):
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def initialize(db_path: str, width: int, height: int) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)

        session_cols = {row["name"] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()}
        if "expires_at" not in session_cols:
            conn.execute("DROP TABLE sessions")
            conn.execute(
                """
                CREATE TABLE sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
                """
            )

        current = conn.execute("SELECT id FROM world_meta WHERE id=1").fetchone()
        if current is None:
            conn.execute(
                "INSERT INTO world_meta (id, width, height) VALUES (1, ?, ?)",
                (width, height),
            )
            conn.executemany(
                "INSERT INTO land_tiles (x, y, owner_user_id, terrain) VALUES (?, ?, NULL, 'land')",
                ((x, y) for y in range(height) for x in range(width)),
            )
        conn.commit()
