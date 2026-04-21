"""
Integration tests: enroll → authenticate pipeline.
Uses synthetic 128-D vectors — no webcam required.
"""

import numpy as np
import pytest
from datetime import datetime

from application.authenticate_usecase import AuthenticateUseCase
from application.enroll_usecase import EnrollUseCase
from domain.entities import Role
from infrastructure.crypto import load_or_create_key
from infrastructure.repositories import (
    SQLiteAuditRepository,
    SQLiteEmbeddingRepository,
    SQLiteUserRepository,
)


def _unit_vec(seed: int, noise: float = 0.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v   = rng.random(128) + rng.random(128) * noise
    return v / np.linalg.norm(v)


@pytest.fixture
def repos(tmp_path):
    key  = load_or_create_key(tmp_path / "test.key")
    path = str(tmp_path / "test.db")
    return (
        SQLiteUserRepository(path),
        SQLiteEmbeddingRepository(path, key),
        SQLiteAuditRepository(path, key),
    )


class TestEnrollFlow:

    def test_enroll_returns_true(self, repos):
        users, embeddings, audit = repos
        uc = EnrollUseCase(users, embeddings, audit)
        assert uc.execute("alice", [_unit_vec(1)] * 5) is True

    def test_user_exists_after_enroll(self, repos):
        users, embeddings, audit = repos
        uc = EnrollUseCase(users, embeddings, audit)
        uc.execute("alice", [_unit_vec(1)] * 5)
        assert users.exists("alice")

    def test_embedding_stored_after_enroll(self, repos):
        users, embeddings, audit = repos
        uc = EnrollUseCase(users, embeddings, audit)
        uc.execute("alice", [_unit_vec(1)] * 5)
        assert embeddings.find("alice") is not None

    def test_audit_log_written_on_enroll(self, repos):
        users, embeddings, audit = repos
        uc     = EnrollUseCase(users, embeddings, audit)
        uc.execute("alice", [_unit_vec(1)] * 5)
        events = audit.get_events("alice")
        assert any(e.event == "ENROLLED" for e in events)

    def test_default_role_is_user(self, repos):
        users, embeddings, audit = repos
        uc = EnrollUseCase(users, embeddings, audit)
        uc.execute("alice", [_unit_vec(1)] * 5)
        assert users.find("alice").role == Role.USER

    def test_admin_role_assigned(self, repos):
        users, embeddings, audit = repos
        uc = EnrollUseCase(users, embeddings, audit)
        uc.execute("alice", [_unit_vec(1)] * 5, role=Role.ADMIN)
        assert users.find("alice").role == Role.ADMIN

    def test_reenroll_overwrites(self, repos):
        users, embeddings, audit = repos
        uc = EnrollUseCase(users, embeddings, audit)
        uc.execute("alice", [_unit_vec(1)] * 5)
        uc.delete("alice")
        uc.execute("alice", [_unit_vec(99)] * 5)
        assert users.exists("alice")


class TestAuthenticateFlow:

    def test_genuine_accepted(self, repos):
        users, embeddings, audit = repos
        base = _unit_vec(42)
        EnrollUseCase(users, embeddings, audit).execute(
            "alice", [base + _unit_vec(i) * 0.001 for i in range(5)]
        )
        result = AuthenticateUseCase(embeddings, audit, 0.45).execute("alice", base)
        assert result.success is True

    def test_imposter_rejected(self, repos):
        users, embeddings, audit = repos
        EnrollUseCase(users, embeddings, audit).execute(
            "alice", [_unit_vec(42)] * 5
        )
        result = AuthenticateUseCase(embeddings, audit, 0.45).execute(
            "alice", _unit_vec(999), auth_type="imposter"
        )
        assert result.success is False

    def test_unenrolled_raises(self, repos):
        users, embeddings, audit = repos
        uc = AuthenticateUseCase(embeddings, audit, 0.45)
        with pytest.raises(FileNotFoundError):
            uc.execute("ghost", _unit_vec(1))

    def test_distance_below_threshold_on_genuine(self, repos):
        users, embeddings, audit = repos
        base = _unit_vec(42)
        EnrollUseCase(users, embeddings, audit).execute("alice", [base] * 5)
        result = AuthenticateUseCase(embeddings, audit, 0.45).execute("alice", base)
        assert result.distance < 0.45

    def test_audit_logs_signed_after_auth(self, repos):
        users, embeddings, audit = repos
        base = _unit_vec(42)
        EnrollUseCase(users, embeddings, audit).execute("alice", [base] * 5)
        AuthenticateUseCase(embeddings, audit, 0.45).execute("alice", base)
        events = audit.get_events("alice")
        assert all(audit.verify_event(e) for e in events)

    def test_auth_type_recorded(self, repos):
        users, embeddings, audit = repos
        base = _unit_vec(42)
        EnrollUseCase(users, embeddings, audit).execute("alice", [base] * 5)
        AuthenticateUseCase(embeddings, audit, 0.45).execute(
            "alice", _unit_vec(999), auth_type="imposter"
        )
        events = audit.get_events("alice")
        auth_events = [e for e in events if "AUTH" in e.event]
        assert any(e.auth_type == "imposter" for e in auth_events)
