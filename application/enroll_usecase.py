"""
application/enroll_usecase.py
==============================
Enrollment use case — orchestrates domain repositories, no I/O.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np

from domain.entities import AuditEvent, FaceEmbedding, Role, User
from domain.repositories import AuditRepository, EmbeddingRepository, UserRepository


class EnrollUseCase:

    def __init__(
        self,
        users:      UserRepository,
        embeddings: EmbeddingRepository,
        audit:      AuditRepository,
    ) -> None:
        self._users      = users
        self._embeddings = embeddings
        self._audit      = audit

    def is_enrolled(self, user_id: str) -> bool:
        return self._users.exists(user_id)

    def delete(self, user_id: str) -> None:
        self._embeddings.delete(user_id)
        self._users.delete(user_id)
        self._audit.log(AuditEvent(
            user_id=user_id, event="USER_DELETED",
            success=True, timestamp=datetime.now(), auth_type="system",
        ))

    def execute(
        self,
        user_id: str,
        vectors: list[np.ndarray],
        role:    Role = Role.USER,
    ) -> bool:
        now = datetime.now()
        avg = np.mean(vectors, axis=0)

        self._users.save(User(user_id=user_id, role=role,
                              created_at=now, updated_at=now))
        self._embeddings.save(FaceEmbedding(user_id=user_id,
                                            vector=avg, created_at=now))
        self._audit.log(AuditEvent(
            user_id=user_id, event="ENROLLED",
            success=True, timestamp=now, auth_type="system",
        ))
        return True
