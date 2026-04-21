import pytest
import numpy as np
from datetime import datetime

from domain.entities import AuditEvent, FaceEmbedding, Role, User
from infrastructure.crypto import load_or_create_key
from infrastructure.repositories import (
    SQLiteAuditRepository,
    SQLiteEmbeddingRepository,
    SQLiteUserRepository,
)


@pytest.fixture
def db(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def key(tmp_path):
    return load_or_create_key(tmp_path / "test.key")


# ── UserRepository ─────────────────────────────────────────────────────────

class TestUserRepository:

    def test_save_and_find(self, db):
        repo = SQLiteUserRepository(db)
        now  = datetime.now()
        repo.save(User("alice", Role.USER, now, now))
        u = repo.find("alice")
        assert u is not None
        assert u.user_id == "alice"
        assert u.role    == Role.USER

    def test_admin_role_persisted(self, db):
        repo = SQLiteUserRepository(db)
        now  = datetime.now()
        repo.save(User("admin_user", Role.ADMIN, now, now))
        assert repo.find("admin_user").role == Role.ADMIN

    def test_find_all(self, db):
        repo = SQLiteUserRepository(db)
        now  = datetime.now()
        repo.save(User("alice", Role.USER,     now, now))
        repo.save(User("bob",   Role.READONLY, now, now))
        assert len(repo.find_all()) == 2

    def test_delete_removes_user(self, db):
        repo = SQLiteUserRepository(db)
        now  = datetime.now()
        repo.save(User("alice", Role.USER, now, now))
        repo.delete("alice")
        assert repo.find("alice") is None

    def test_exists_true_after_save(self, db):
        repo = SQLiteUserRepository(db)
        now  = datetime.now()
        assert not repo.exists("alice")
        repo.save(User("alice", Role.USER, now, now))
        assert repo.exists("alice")

    def test_save_overwrites_role(self, db):
        repo = SQLiteUserRepository(db)
        now  = datetime.now()
        repo.save(User("alice", Role.USER,  now, now))
        repo.save(User("alice", Role.ADMIN, now, now))
        assert repo.find("alice").role == Role.ADMIN


# ── EmbeddingRepository ────────────────────────────────────────────────────

class TestEmbeddingRepository:

    def test_save_and_find(self, db, key):
        repo   = SQLiteEmbeddingRepository(db, key)
        vector = np.random.rand(128).astype(np.float64)
        repo.save(FaceEmbedding("alice", vector, datetime.now()))
        found  = repo.find("alice")
        assert found is not None
        np.testing.assert_array_almost_equal(found.vector, vector)

    def test_find_returns_none_for_unknown(self, db, key):
        repo = SQLiteEmbeddingRepository(db, key)
        assert repo.find("ghost") is None

    def test_save_overwrites_existing(self, db, key):
        repo = SQLiteEmbeddingRepository(db, key)
        v1   = np.zeros(128)
        v2   = np.ones(128)
        repo.save(FaceEmbedding("alice", v1, datetime.now()))
        repo.save(FaceEmbedding("alice", v2, datetime.now()))
        np.testing.assert_array_equal(repo.find("alice").vector, v2)

    def test_delete_removes_embedding(self, db, key):
        repo = SQLiteEmbeddingRepository(db, key)
        repo.save(FaceEmbedding("alice", np.zeros(128), datetime.now()))
        repo.delete("alice")
        assert repo.find("alice") is None

    def test_encryption_is_opaque(self, db, key):
        import sqlite3
        repo   = SQLiteEmbeddingRepository(db, key)
        vector = np.array([0.1] * 128)
        repo.save(FaceEmbedding("alice", vector, datetime.now()))
        with sqlite3.connect(db) as conn:
            raw = conn.execute(
                "SELECT embedding FROM embeddings WHERE user_id='alice'"
            ).fetchone()[0]
        assert b"0.1" not in bytes(raw)


# ── AuditRepository ────────────────────────────────────────────────────────

class TestAuditRepository:

    def test_log_and_retrieve(self, db, key):
        repo  = SQLiteAuditRepository(db, key)
        event = AuditEvent("alice", "AUTH_SUCCESS", True, datetime.now(), "genuine")
        repo.log(event)
        events = repo.get_events("alice")
        assert len(events) == 1
        assert events[0].event == "AUTH_SUCCESS"

    def test_hmac_verification_passes(self, db, key):
        repo  = SQLiteAuditRepository(db, key)
        event = AuditEvent("alice", "ENROLLED", True, datetime.now(), "system")
        repo.log(event)
        stored = repo.get_events("alice")[0]
        assert repo.verify_event(stored)

    def test_verify_detects_empty_hmac(self, db, key):
        repo  = SQLiteAuditRepository(db, key)
        event = AuditEvent("alice", "ENROLLED", True, datetime.now(), "system")
        event.hmac = ""
        assert not repo.verify_event(event)

    def test_get_all_events_no_filter(self, db, key):
        repo = SQLiteAuditRepository(db, key)
        now  = datetime.now()
        repo.log(AuditEvent("alice", "ENROLLED",     True, now, "system"))
        repo.log(AuditEvent("alice", "AUTH_SUCCESS", True, now, "genuine"))
        repo.log(AuditEvent("bob",   "ENROLLED",     True, now, "system"))
        assert len(repo.get_events()) == 3

    def test_get_events_filtered_by_user(self, db, key):
        repo = SQLiteAuditRepository(db, key)
        now  = datetime.now()
        repo.log(AuditEvent("alice", "AUTH_SUCCESS", True,  now, "genuine"))
        repo.log(AuditEvent("bob",   "AUTH_FAILED",  False, now, "genuine"))
        assert len(repo.get_events("alice")) == 1

    def test_auth_type_persisted(self, db, key):
        repo = SQLiteAuditRepository(db, key)
        repo.log(AuditEvent("alice", "AUTH_FAILED", False, datetime.now(), "imposter"))
        e = repo.get_events("alice")[0]
        assert e.auth_type == "imposter"
