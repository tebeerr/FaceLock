"""
oversight/dashboard.py
========================
Human oversight CLI — satisfies EU AI Act Article 14 (human oversight measures).

Capabilities:
  - Live dashboard: enrolled users, recent events, alert detection
  - Log integrity verification via HMAC
  - Manual workstation lock (operator override)
  - Threshold inspection

Usage:
    python oversight/dashboard.py               # full dashboard + integrity check
    python oversight/dashboard.py --verify      # integrity check only
    python oversight/dashboard.py --lock        # manual lock
    python oversight/dashboard.py --events 50   # show last N events
"""

from __future__ import annotations

import argparse
import ctypes
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from domain.entities import AuditEvent
from infrastructure.repositories import SQLiteAuditRepository, SQLiteUserRepository
from config import MATCH_THRESHOLD

_ALERT_FAIL_THRESHOLD = 3      # consecutive failures → alert
_RECENT_WINDOW_S      = 3600  # 1-hour look-back for stats


def _sep(title: str = "") -> None:
    width = 58
    if title:
        pad = (width - len(title) - 2) // 2
        print(f"\n{'─' * pad} {title} {'─' * pad}")
    else:
        print(f"\n{'─' * width}")


def _show_dashboard(audit: SQLiteAuditRepository,
                    users: SQLiteUserRepository,
                    n_events: int) -> None:
    enrolled = users.find_all()
    events   = audit.get_events(limit=max(n_events, 200))
    now      = datetime.now()
    cutoff   = now - timedelta(seconds=_RECENT_WINDOW_S)
    recent   = [e for e in events if e.timestamp >= cutoff]

    success_count = sum(1 for e in recent if e.success is True)
    fail_count    = sum(1 for e in recent if e.success is False)

    _sep("FACELOCK — HUMAN OVERSIGHT DASHBOARD")
    print(f"  Timestamp        : {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Enrolled users   : {len(enrolled)}")
    print(f"  Match threshold  : {MATCH_THRESHOLD}")
    print(f"\n  ── Last 60 minutes ──")
    print(f"  Auth success     : {success_count}")
    print(f"  Auth failed      : {fail_count}")

    # Consecutive failure alert
    streak = 0
    max_streak = 0
    for e in sorted(events, key=lambda x: x.timestamp):
        if e.success is False:
            streak += 1
            max_streak = max(max_streak, streak)
        elif e.success is True:
            streak = 0

    if max_streak >= _ALERT_FAIL_THRESHOLD:
        print(f"\n  [!] ALERT: {max_streak} consecutive authentication failures.")
        print("      Potential brute-force or imposter activity detected.")

    # Enrolled users table
    _sep("ENROLLED USERS")
    if enrolled:
        for u in enrolled:
            print(f"  {u.user_id:<24} role={u.role.value:<10} "
                  f"enrolled={u.created_at.strftime('%Y-%m-%d')}")
    else:
        print("  No users enrolled.")

    # Recent events table
    _sep(f"RECENT EVENTS (last {n_events})")
    shown = events[:n_events]
    if shown:
        for e in shown:
            ok = "OK  " if e.success is True else ("FAIL" if e.success is False else "SYS ")
            print(f"  [{ok}] {e.timestamp.strftime('%H:%M:%S')}  "
                  f"{e.user_id:<20}  {e.event:<24}  type={e.auth_type}")
    else:
        print("  No events recorded.")


def _verify_logs(audit: SQLiteAuditRepository) -> bool:
    _sep("LOG INTEGRITY VERIFICATION")
    events   = audit.get_events(limit=1000)
    signed   = [e for e in events if e.hmac]
    unsigned = [e for e in events if not e.hmac]
    tampered = [e for e in signed if not audit.verify_event(e)]

    print(f"  Total events     : {len(events)}")
    print(f"  Signed entries   : {len(signed)}")
    print(f"  Unsigned entries : {len(unsigned)}  (pre-RBAC legacy rows)")

    if tampered:
        print(f"\n  [!] TAMPERED ENTRIES DETECTED: {len(tampered)}")
        for t in tampered:
            print(f"      {t.timestamp.isoformat()}  {t.user_id}  {t.event}")
        return False
    else:
        print(f"\n  [OK] All {len(signed)} signed entries verified — no tampering detected.")
        return True


def _manual_lock(audit: SQLiteAuditRepository) -> None:
    _sep("MANUAL OVERRIDE")
    audit.log(AuditEvent(
        user_id="oversight-operator", event="MANUAL_LOCK",
        success=True, timestamp=datetime.now(), auth_type="system",
    ))
    ctypes.windll.user32.LockWorkStation()
    print("  Workstation locked by human oversight operator.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FaceLock — Human Oversight Dashboard")
    parser.add_argument("--verify", action="store_true", help="Verify log integrity only")
    parser.add_argument("--lock",   action="store_true", help="Manually lock workstation")
    parser.add_argument("--events", type=int, default=20, help="Number of recent events to show")
    args = parser.parse_args()

    audit_repo = SQLiteAuditRepository()
    users_repo = SQLiteUserRepository()

    if args.lock:
        _manual_lock(audit_repo)
    elif args.verify:
        ok = _verify_logs(audit_repo)
        sys.exit(0 if ok else 1)
    else:
        _show_dashboard(audit_repo, users_repo, args.events)
        print()
        _verify_logs(audit_repo)
        print()
