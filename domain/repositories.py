"""
domain/repositories.py
========================
Abstract repository interfaces — the domain's contract with infrastructure.
Concrete implementations live in infrastructure/repositories.py.
"""

from __future__ import annotations
from abc import ABC, abstractmethod

from domain.entities import User, FaceEmbedding, AuditEvent


class UserRepository(ABC):
    @abstractmethod
    def save(self, user: User) -> None: ...

    @abstractmethod
    def find(self, user_id: str) -> User | None: ...

    @abstractmethod
    def find_all(self) -> list[User]: ...

    @abstractmethod
    def delete(self, user_id: str) -> None: ...

    @abstractmethod
    def exists(self, user_id: str) -> bool: ...


class EmbeddingRepository(ABC):
    @abstractmethod
    def save(self, embedding: FaceEmbedding) -> None: ...

    @abstractmethod
    def find(self, user_id: str) -> FaceEmbedding | None: ...

    @abstractmethod
    def delete(self, user_id: str) -> None: ...


class AuditRepository(ABC):
    @abstractmethod
    def log(self, event: AuditEvent) -> None: ...

    @abstractmethod
    def get_events(self, user_id: str | None = None, limit: int = 50) -> list[AuditEvent]: ...

    @abstractmethod
    def verify_event(self, event: AuditEvent) -> bool: ...
