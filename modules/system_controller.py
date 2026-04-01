"""
modules/system_controller.py
==============================
Background service for FaceLock.
Monitors user inactivity and automatically locks the Windows session.
Runs as a persistent background thread alongside the Streamlit UI.
"""

import ctypes
import threading
import time
import ctypes.wintypes
from datetime import datetime
from modules.database import DatabaseManager


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint),
    ]


class SystemController:
    """
    Manages Windows session control and inactivity monitoring.

    Usage:
        controller = SystemController(db, inactivity_timeout=60)
        controller.start()   # starts background thread
        controller.stop()    # stops background thread
    """

    def __init__(self, db: DatabaseManager = None, inactivity_timeout: int = 60):
        self.db                 = db or DatabaseManager()
        self.inactivity_timeout = inactivity_timeout
        self._running           = False
        self._thread            = None
        self._session_locked    = False
        self._lock_callbacks    = []
        self._unlock_callbacks  = []

    # -- Windows Idle Time -----------------------------------------------------

    def get_idle_seconds(self) -> float:
        """Return seconds since last user input using Windows GetLastInputInfo."""
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0

    def check_inactivity(self) -> dict:
        """Check current inactivity status."""
        idle = self.get_idle_seconds()
        return {
            "idle_seconds"      : round(idle, 1),
            "threshold_seconds" : self.inactivity_timeout,
            "should_lock"       : idle >= self.inactivity_timeout,
            "remaining_seconds" : max(0, self.inactivity_timeout - idle),
        }

    # -- Session Control -------------------------------------------------------

    def lock_workstation(self, reason: str = "manual") -> dict:
        """Lock the Windows workstation immediately."""
        try:
            ctypes.windll.user32.LockWorkStation()
            self._session_locked = True
            self.db.log_event("system", f"SESSION_LOCKED:{reason}", success=True)
            print(f"[SYSTEM] Session locked. Reason: {reason}")
            for cb in self._lock_callbacks:
                try:
                    cb(reason)
                except Exception:
                    pass
            return {"success": True, "message": f"Session locked ({reason})"}
        except Exception as e:
            self.db.log_event("system", "SESSION_LOCK_FAILED", success=False)
            return {"success": False, "message": str(e)}

    def on_session_unlock(self, user_id: str = "unknown"):
        """Handle session unlock event after successful face authentication."""
        self._session_locked = False
        self.db.log_event(user_id, "SESSION_UNLOCKED", success=True)
        print(f"[SYSTEM] Session unlocked for user: {user_id}")
        for cb in self._unlock_callbacks:
            try:
                cb(user_id)
            except Exception:
                pass

    def prevent_sleep(self):
        """Prevent Windows from sleeping."""
        ES_CONTINUOUS      = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        )

    # -- Background Service ----------------------------------------------------

    def _background_loop(self):
        """Main loop -- polls inactivity every second and locks when threshold exceeded."""
        print(f"[SERVICE] Background service started. "
              f"Auto-lock after {self.inactivity_timeout}s of inactivity.")

        while self._running:
            try:
                status = self.check_inactivity()
                if status["should_lock"] and not self._session_locked:
                    print(f"[SERVICE] Inactivity detected "
                          f"({status['idle_seconds']}s). Locking session...")
                    self.lock_workstation(reason="inactivity")
                time.sleep(1)
            except Exception as e:
                print(f"[SERVICE] Error in background loop: {e}")
                time.sleep(5)

        print("[SERVICE] Background service stopped.")

    def start(self):
        """Start the background monitoring thread."""
        if self._running:
            print("[SERVICE] Already running.")
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._background_loop,
            daemon=True,
            name="FaceLock-BackgroundService"
        )
        self._thread.start()
        print("[SERVICE] FaceLock background service started.")

    def stop(self):
        """Stop the background monitoring thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        print("[SERVICE] FaceLock background service stopped.")

    def is_running(self) -> bool:
        return self._running

    def set_timeout(self, seconds: int):
        """Update the inactivity timeout at runtime."""
        self.inactivity_timeout = seconds
        self.db.set_threshold(seconds)
        print(f"[SERVICE] Inactivity timeout updated to {seconds}s.")

    def on_lock(self, callback):
        """Register a function to be called when session is locked."""
        self._lock_callbacks.append(callback)

    def on_unlock(self, callback):
        """Register a function to be called when session is unlocked."""
        self._unlock_callbacks.append(callback)

    def get_status(self) -> dict:
        """Return full service status for display in UI."""
        idle = self.get_idle_seconds()
        return {
            "service_running"   : self._running,
            "session_locked"    : self._session_locked,
            "idle_seconds"      : round(idle, 1),
            "timeout_seconds"   : self.inactivity_timeout,
            "remaining_seconds" : max(0, round(self.inactivity_timeout - idle, 1)),
            "auto_lock_pct"     : min(100, int((idle / self.inactivity_timeout) * 100)),
        }
