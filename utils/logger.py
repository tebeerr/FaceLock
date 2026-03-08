# Audit log
# Records all authentication events to an audit log file
import os
from datetime import datetime

LOG_PATH = "profiles/audit.log"

def log(event: str, user: str = "unknown", success: bool = None):
    """
    Log an event to the audit file.
    
    Examples:
        log("ENROLL", user="alice")
        log("AUTH_ATTEMPT", user="alice", success=True)
        log("SESSION_LOCKED", user="alice")
    """
    os.makedirs("profiles", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if success is True:
        status = "✅ SUCCESS"
    elif success is False:
        status = "❌ FAILED"
    else:
        status = "ℹ️  INFO"

    line = f"[{timestamp}] [{status}] [{user.upper()}] {event}\n"
    
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)
    
    print(f"[LOGGER] {line.strip()}")

def show_logs():
    """Print all audit logs to the console."""
    if not os.path.exists(LOG_PATH):
        print("[LOGGER] No logs yet.")
        return
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        print("\n===== AUDIT LOG =====")
        print(f.read())
        print("=====================")