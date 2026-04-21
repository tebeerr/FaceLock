"""
infrastructure/session.py
==========================
Windows session control and inactivity monitoring.
Moved from modules/system_controller.py; now depends on domain types only.
"""

from __future__ import annotations

import ctypes
import threading
import time
from datetime import datetime

from domain.entities import AuditEvent
from domain.repositories import AuditRepository
from config import NO_FACE_TIMEOUT


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


class SessionController:

    def __init__(self, audit: AuditRepository, inactivity_timeout: int = NO_FACE_TIMEOUT):
        self._audit    = audit
        self._timeout  = inactivity_timeout
        self._running  = False
        self._thread:  threading.Thread | None = None
        self._locked   = False

    # ------------------------------------------------------------------
    # Windows API helpers
    # ------------------------------------------------------------------

    def idle_seconds(self) -> float:
        lii = _LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(_LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0

    def lock(self, reason: str = "manual", user_id: str = "system") -> None:
        ctypes.windll.user32.LockWorkStation()
        self._locked = True
        self._audit.log(AuditEvent(
            user_id=user_id, event=f"SESSION_LOCKED:{reason}",
            success=True, timestamp=datetime.now(), auth_type="system",
        ))

    def prevent_sleep(self) -> None:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)

    # ------------------------------------------------------------------
    # Inactivity background service
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while self._running:
            try:
                idle = self.idle_seconds()
                if idle >= self._timeout and not self._locked:
                    self.lock(reason="inactivity")
                time.sleep(1)
            except Exception as exc:
                print(f"[SESSION] Loop error: {exc}")
                time.sleep(5)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True,
                                         name="FaceLock-SessionController")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def status(self) -> dict:
        idle = self.idle_seconds()
        return {
            "running":   self._running,
            "locked":    self._locked,
            "idle_s":    round(idle, 1),
            "timeout_s": self._timeout,
            "remaining": max(0.0, round(self._timeout - idle, 1)),
            "pct":       min(100, int(idle / self._timeout * 100)),
        }
