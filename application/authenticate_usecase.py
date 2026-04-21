"""
application/authenticate_usecase.py
=====================================
Authentication use case — pure business logic, no webcam I/O.
"""

from __future__ import annotations

from datetime import datetime

import face_recognition
import numpy as np

from domain.entities import AuditEvent, AuthResult
from domain.repositories import AuditRepository, EmbeddingRepository


class AuthenticateUseCase:

    def __init__(
        self,
        embeddings: EmbeddingRepository,
        audit:      AuditRepository,
        threshold:  float,
    ) -> None:
        self._embeddings = embeddings
        self._audit      = audit
        self.threshold   = threshold

    def _load_vector(self, user_id: str) -> np.ndarray:
        stored = self._embeddings.find(user_id)
        if stored is None:
            raise FileNotFoundError(f"User '{user_id}' is not enrolled.")
        return stored.vector

    def distance(self, user_id: str, live_encoding: np.ndarray) -> float:
        known = self._load_vector(user_id)
        return float(face_recognition.face_distance([known], live_encoding)[0])

    def execute(
        self,
        user_id:       str,
        live_encoding: np.ndarray,
        auth_type:     str = "genuine",
    ) -> AuthResult:
        dist    = self.distance(user_id, live_encoding)
        success = dist < self.threshold
        now     = datetime.now()

        self._audit.log(AuditEvent(
            user_id=user_id,
            event="AUTH_SUCCESS" if success else "AUTH_FAILED",
            success=success,
            timestamp=now,
            auth_type=auth_type,
        ))
        return AuthResult(
            user_id=user_id, success=success,
            distance=dist, threshold=self.threshold,
            timestamp=now,
        )
