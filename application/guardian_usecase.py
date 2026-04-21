"""
application/guardian_usecase.py
=================================
Guardian use case — frame-level match logic, no webcam/display code.
"""

from __future__ import annotations

import numpy as np
import face_recognition

from domain.entities import AuditEvent
from domain.repositories import AuditRepository, EmbeddingRepository


class GuardianUseCase:

    def __init__(
        self,
        embeddings:       EmbeddingRepository,
        audit:            AuditRepository,
        threshold:        float,
        wrong_face_limit: int,
        no_face_timeout:  float,
    ) -> None:
        self._embeddings      = embeddings
        self._audit           = audit
        self.threshold        = threshold
        self.wrong_face_limit = wrong_face_limit
        self.no_face_timeout  = no_face_timeout

    def load_embedding(self, user_id: str) -> np.ndarray:
        stored = self._embeddings.find(user_id)
        if stored is None:
            raise FileNotFoundError(f"User '{user_id}' is not enrolled.")
        return stored.vector

    def check_frame(
        self,
        known_vector: np.ndarray,
        encodings:    list[np.ndarray],
    ) -> tuple[bool, float]:
        """Return (is_match, best_distance) for the closest detected face."""
        if not encodings:
            return False, 1.0
        distances = face_recognition.face_distance([known_vector], np.array(encodings))
        best_dist = float(np.min(distances))
        return best_dist < self.threshold, best_dist

    def log(self, event: AuditEvent) -> None:
        self._audit.log(event)
