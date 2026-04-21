"""
infrastructure/repositories.py
================================
SQLite implementations of domain repository interfaces.
  - Embeddings encrypted with AES-256-GCM (infrastructure.crypto)
  - Audit logs signed with HMAC-SHA256 (tamper-evident)
  - Users table carries RBAC role column
  - ALTER TABLE guards handle existing pre-RBAC databases
"""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import pickle
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np

from config import DB_PATH, KEY_PATH
from domain.entities import AuditEvent, FaceEmbedding, Role, User
from domain.repositories import AuditRepository, EmbeddingRepository, UserRepository
from infrastructure import crypto


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get_key() -> bytes:
    return crypto.load_or_create_key(Path(KEY_PATH))


def _sign(key: bytes, user_id: str, event: str,
          success: int | None, timestamp: str, auth_type: str) -> str:
    payload = json.dumps(
        {"user_id": user_id, "event": event,
         "success": success, "timestamp": timestamp, "auth_type": auth_type},
        sort_keys=True,
    ).encode()
    return hmac_mod.new(key, payload, hashlib.sha256).hexdigest()


def _add_column(conn: sqlite3.Connection, table: str, col: str, defn: str) -> None:
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists


# ---------------------------------------------------------------------------
# SQLiteUserRepository
# ---------------------------------------------------------------------------

class SQLiteUserRepository(UserRepository):

    def __init__(self, db_path: str = DB_PATH):
        self._path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id    TEXT PRIMARY KEY,
                    role       TEXT NOT NULL DEFAULT 'user',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()
        with self._connect() as conn:
            _add_column(conn, "users", "role", "TEXT NOT NULL DEFAULT 'user'")

    def save(self, user: User) -> None:
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO users (user_id, role, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    role=excluded.role,
                    updated_at=excluded.updated_at
            """, (user.user_id, user.role.value,
                  user.created_at.isoformat(), user.updated_at.isoformat()))
            conn.commit()

    def find(self, user_id: str) -> User | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT user_id, role, created_at, updated_at FROM users WHERE user_id=?",
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return User(
            user_id=row[0], role=Role(row[1]),
            created_at=datetime.fromisoformat(row[2]),
            updated_at=datetime.fromisoformat(row[3]),
        )

    def find_all(self) -> list[User]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT user_id, role, created_at, updated_at FROM users"
            ).fetchall()
        return [
            User(user_id=r[0], role=Role(r[1]),
                 created_at=datetime.fromisoformat(r[2]),
                 updated_at=datetime.fromisoformat(r[3]))
            for r in rows
        ]

    def delete(self, user_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))
            conn.commit()

    def exists(self, user_id: str) -> bool:
        return self.find(user_id) is not None


# ---------------------------------------------------------------------------
# SQLiteEmbeddingRepository
# ---------------------------------------------------------------------------

class SQLiteEmbeddingRepository(EmbeddingRepository):

    def __init__(self, db_path: str = DB_PATH, key: bytes | None = None):
        self._path = db_path
        self._key  = key or _get_key()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    TEXT NOT NULL UNIQUE,
                    embedding  BLOB NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            # Ensure UNIQUE constraint on user_id for existing tables
            try:
                conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_embeddings_user_id ON embeddings(user_id)")
            except sqlite3.OperationalError:
                pass  # Index already exists or table has duplicates
            # Ensure UNIQUE constraint on user_id for existing tables
            try:
                conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_embeddings_user_id ON embeddings(user_id)")
            except sqlite3.OperationalError:
                pass  # Index already exists or table has duplicates
            conn.commit()

    def save(self, embedding: FaceEmbedding) -> None:
        blob = crypto.encrypt(self._key, pickle.dumps(embedding.vector))
        with self._connect() as conn:
            conn.execute("DELETE FROM embeddings WHERE user_id = ?", (embedding.user_id,))
            conn.execute("""
                INSERT INTO embeddings (user_id, embedding, created_at)
                VALUES (?, ?, ?)
            """, (embedding.user_id, blob, embedding.created_at.isoformat()))
            conn.commit()

    def find(self, user_id: str) -> FaceEmbedding | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT embedding, created_at FROM embeddings WHERE user_id=?",
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        vector = pickle.loads(crypto.decrypt(self._key, bytes(row[0])))
        return FaceEmbedding(
            user_id=user_id, vector=vector,
            created_at=datetime.fromisoformat(row[1]),
        )

    def delete(self, user_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM embeddings WHERE user_id=?", (user_id,))
            conn.commit()


# ---------------------------------------------------------------------------
# SQLiteAuditRepository  — HMAC-SHA256 signed entries
# ---------------------------------------------------------------------------

class SQLiteAuditRepository(AuditRepository):

    def __init__(self, db_path: str = DB_PATH, key: bytes | None = None):
        self._path = db_path
        self._key  = key or _get_key()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS auth_logs (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id   TEXT NOT NULL,
                    event     TEXT NOT NULL,
                    success   INTEGER,
                    auth_type TEXT NOT NULL DEFAULT 'system',
                    timestamp TEXT NOT NULL,
                    hmac      TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.commit()
        with self._connect() as conn:
            _add_column(conn, "auth_logs", "auth_type", "TEXT NOT NULL DEFAULT 'system'")
            _add_column(conn, "auth_logs", "hmac",      "TEXT NOT NULL DEFAULT ''")

    def log(self, event: AuditEvent) -> None:
        ts      = event.timestamp.isoformat()
        success = int(event.success) if event.success is not None else None
        sig     = _sign(self._key, event.user_id, event.event, success, ts, event.auth_type)
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO auth_logs (user_id, event, success, auth_type, timestamp, hmac)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (event.user_id, event.event, success, event.auth_type, ts, sig))
            conn.commit()

    def get_events(self, user_id: str | None = None, limit: int = 50) -> list[AuditEvent]:
        with self._connect() as conn:
            if user_id:
                rows = conn.execute("""
                    SELECT user_id, event, success, auth_type, timestamp, hmac
                    FROM auth_logs WHERE user_id=?
                    ORDER BY timestamp DESC LIMIT ?
                """, (user_id, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT user_id, event, success, auth_type, timestamp, hmac
                    FROM auth_logs ORDER BY timestamp DESC LIMIT ?
                """, (limit,)).fetchall()
        return [
            AuditEvent(
                user_id=r[0], event=r[1],
                success=bool(r[2]) if r[2] is not None else None,
                auth_type=r[3] or "system",
                timestamp=datetime.fromisoformat(r[4]),
                hmac=r[5] or "",
            )
            for r in rows
        ]

    def verify_event(self, event: AuditEvent) -> bool:
        if not event.hmac:
            return False
        success  = int(event.success) if event.success is not None else None
        expected = _sign(self._key, event.user_id, event.event,
                         success, event.timestamp.isoformat(), event.auth_type)
        return hmac_mod.compare_digest(expected, event.hmac)
