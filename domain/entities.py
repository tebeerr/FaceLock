"""
domain/entities.py
===================
Pure domain entities — no I/O, no framework dependencies.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import numpy as np


class Role(str, Enum):
    ADMIN    = "admin"
    USER     = "user"
    READONLY = "readonly"


@dataclass
class User:
    user_id:    str
    role:       Role
    created_at: datetime
    updated_at: datetime


@dataclass
class FaceEmbedding:
    user_id:    str
    vector:     np.ndarray
    created_at: datetime


@dataclass
class AuthResult:
    user_id:        str
    success:        bool
    distance:       float
    threshold:      float
    timestamp:      datetime
    frames_matched: int = 0
    frames_total:   int = 0

    @property
    def confidence(self) -> float:
        return max(0.0, (1.0 - self.distance) * 100)


@dataclass
class AuditEvent:
    user_id:   str
    event:     str
    success:   bool | None
    timestamp: datetime
    auth_type: str = "system"   # "genuine" | "imposter" | "system"
    hmac:      str = ""
