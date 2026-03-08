import cv2, json, numpy as np
import face_recognition
from utils.key_manager import get_cipher
from utils.logger import log
import os

PROFILES_DIR = "profiles"

def enroll_from_frame(username: str, frame_bgr) -> dict:
    """
    Enroll a user from a single captured frame (numpy array).
    Called by Streamlit after st.camera_input() captures the image.
    Returns: {"success": bool, "message": str}
    """
    os.makedirs(PROFILES_DIR, exist_ok=True)
    cipher = get_cipher()

    rgb       = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    locations = face_recognition.face_locations(rgb)
    encodings = face_recognition.face_encodings(rgb, locations)

    if not encodings:
        log("ENROLLMENT_FAILED", user=username, success=False)
        return {"success": False, "message": "No face detected. Please try again."}

    embedding = encodings[0].tolist()
    payload   = json.dumps({"user": username, "embedding": embedding}).encode()
    encrypted = cipher.encrypt(payload)

    enc_path = os.path.join(PROFILES_DIR, f"{username}.enc")
    with open(enc_path, "wb") as f:
        f.write(encrypted)

    log("ENROLLMENT_COMPLETE", user=username, success=True)
    return {"success": True, "message": f"'{username}' enrolled successfully ✅"}


def enroll_user_multisample(username: str, frames: list) -> dict:
    """
    Enroll from multiple frames and average embeddings (more accurate).
    frames: list of BGR numpy arrays
    """
    os.makedirs(PROFILES_DIR, exist_ok=True)
    cipher     = get_cipher()
    embeddings = []

    for frame_bgr in frames:
        rgb       = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, locations)
        if encodings:
            embeddings.append(encodings[0])

    if len(embeddings) == 0:
        log("ENROLLMENT_FAILED", user=username, success=False)
        return {"success": False, "message": "No face detected in any frame."}

    avg_embedding = np.mean(embeddings, axis=0).tolist()
    payload       = json.dumps({"user": username, "embedding": avg_embedding}).encode()
    encrypted     = cipher.encrypt(payload)

    enc_path = os.path.join(PROFILES_DIR, f"{username}.enc")
    with open(enc_path, "wb") as f:
        f.write(encrypted)

    log("ENROLLMENT_COMPLETE", user=username, success=True)
    return {
        "success": True,
        "message": f"Enrolled from {len(embeddings)} frames ✅",
        "samples": len(embeddings)
    }