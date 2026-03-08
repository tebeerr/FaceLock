import cv2, json, numpy as np
import face_recognition
from utils.key_manager import get_cipher
from utils.logger import log
import os

THRESHOLD    = 0.45
PROFILES_DIR = "profiles"

def load_embedding(username: str) -> np.ndarray:
    cipher   = get_cipher()
    enc_path = os.path.join(PROFILES_DIR, f"{username}.enc")

    if not os.path.exists(enc_path):
        raise FileNotFoundError(f"No profile found for '{username}'. Enroll first.")

    with open(enc_path, "rb") as f:
        decrypted = cipher.decrypt(f.read())

    return np.array(json.loads(decrypted)["embedding"])


def authenticate_from_frame(username: str, frame_bgr) -> dict:
    """
    Authenticate a user from a single captured frame.
    Called by Streamlit after st.camera_input() captures the image.
    Returns: {"success": bool, "message": str, "distance": float}
    """
    try:
        known = load_embedding(username)
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "distance": None}

    log("AUTH_ATTEMPT", user=username)

    rgb       = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    locations = face_recognition.face_locations(rgb)
    encodings = face_recognition.face_encodings(rgb, locations)

    if not encodings:
        log("AUTH_RESULT", user=username, success=False)
        return {
            "success"  : False,
            "message"  : "No face detected in frame. Try again.",
            "distance" : None
        }

    distance = face_recognition.face_distance([known], encodings[0])[0]
    success  = distance < THRESHOLD

    log("AUTH_RESULT", user=username, success=success)

    return {
        "success" : success,
        "message" : "Access Granted ✅" if success else "Access Denied ❌",
        "distance": round(float(distance), 4),
        "confidence": f"{round((1 - distance) * 100, 1)}%"
    }

def is_enrolled(username: str) -> bool:
    """Quick check if a user profile exists."""
    return os.path.exists(os.path.join(PROFILES_DIR, f"{username}.enc"))