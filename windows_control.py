import ctypes
from utils.logger import log

def lock_windows_session(username: str = "unknown") -> dict:
    """
    Lock the Windows workstation.
    Returns status dict for Streamlit to display.
    """
    log("SESSION_LOCKED", user=username)
    try:
        ctypes.windll.user32.LockWorkStation()
        return {"success": True, "message": "Session locked successfully 🔒"}
    except Exception as e:
        return {"success": False, "message": f"Lock failed: {str(e)}"}

def get_lock_status() -> str:
    """
    Returns a readable lock status string.
    (Windows doesn't expose a direct API for this, 
     so we track it via our own logger state.)
    """
    return "Locked 🔒"