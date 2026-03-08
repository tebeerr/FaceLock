import streamlit as st
import numpy as np
import cv2
from PIL import Image
from authentication import authenticate_from_frame, is_enrolled
from enrollment import enroll_from_frame
from windows_control import lock_windows_session
from utils.logger import log, show_logs
from profiles.student_user import DEFAULT_USER
import os

# ── Page config ─────────────────────────────────────────
st.set_page_config(
    page_title="FaceLock",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ───────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        font-size: 16px;
        font-weight: bold;
    }
    .success-box {
        background-color: #1a3a2a;
        border-left: 5px solid #00ff88;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .error-box {
        background-color: #3a1a1a;
        border-left: 5px solid #ff4444;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .info-card {
        background-color: #1e2130;
        padding: 20px;
        border-radius: 12px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


# ── Sidebar Navigation ───────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/fingerprint.png", width=80)
    st.title("🔐 FaceLock")
    st.markdown("---")

    username = st.text_input("👤 Username", value=DEFAULT_USER.username)

    enrolled_status = "✅ Enrolled" if is_enrolled(username) else "❌ Not Enrolled"
    st.markdown(f"**Status:** {enrolled_status}")
    st.markdown("---")

    page = st.radio("Navigation", [
        "🏠 Home",
        "📸 Enroll Face",
        "🔓 Authenticate",
        "🔒 Lock Session",
        "📜 Audit Logs"
    ])


# ── HOME PAGE ────────────────────────────────────────────
if page == "🏠 Home":
    st.title("🔐 FaceLock — Biometric Authentication System")
    st.markdown("### Privacy by Design | Deep Learning | Local Data Only")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.metric("🔐 Encryption", "AES-128")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.metric("🧠 Model", "128D Embeddings")
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.metric("☁️ Cloud Storage", "None — Local Only")
        st.markdown('</div>', unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.metric("🎯 Threshold", "0.45 distance")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("## How It Works")
    st.markdown("""
```
    1. 📸 ENROLL    → Camera captures your face → converted to 128D vector → encrypted & saved locally
    2. 🔒 LOCK      → Windows session is locked
    3. 🔓 AUTHENTICATE → Camera scans face → compares with stored vector → grants or denies access
    4. 📜 AUDIT LOG → All events recorded with timestamps
```
    """)


# ── ENROLL PAGE ──────────────────────────────────────────
elif page == "📸 Enroll Face":
    st.title("📸 Face Enrollment")
    st.markdown("Take a photo to register your face in the system.")
    st.markdown("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### Step 1 — Capture Your Face")
        st.info("💡 Look straight at the camera. Make sure your face is well lit.")

        img_file = st.camera_input("Take a photo for enrollment")

        if img_file is not None:
            # Convert Streamlit image to OpenCV BGR format
            img_pil   = Image.open(img_file)
            img_np    = np.array(img_pil)
            frame_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

            with st.spinner("Processing face..."):
                result = enroll_from_frame(username, frame_bgr)

            with col2:
                st.markdown("### Step 2 — Result")
                if result["success"]:
                    st.markdown(f"""
                    <div class="success-box">
                        <h3>✅ Enrollment Successful</h3>
                        <p>{result['message']}</p>
                        <p>User: <strong>{username}</strong></p>
                        <p>Data encrypted and stored locally.</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.balloons()
                else:
                    st.markdown(f"""
                    <div class="error-box">
                        <h3>❌ Enrollment Failed</h3>
                        <p>{result['message']}</p>
                    </div>
                    """, unsafe_allow_html=True)


# ── AUTHENTICATE PAGE ────────────────────────────────────
elif page == "🔓 Authenticate":
    st.title("🔓 Face Authentication")
    st.markdown("Capture your face to verify your identity.")
    st.markdown("---")

    if not is_enrolled(username):
        st.warning(f"⚠️ User **{username}** is not enrolled yet. Go to **Enroll Face** first.")
    else:
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("### Scan Your Face")
            st.info("💡 Look at the camera and hold still.")

            img_file = st.camera_input("Take a photo to authenticate")

            if img_file is not None:
                img_pil   = Image.open(img_file)
                img_np    = np.array(img_pil)
                frame_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

                with st.spinner("Verifying identity..."):
                    result = authenticate_from_frame(username, frame_bgr)

                with col2:
                    st.markdown("### Verification Result")

                    if result["success"]:
                        st.markdown(f"""
                        <div class="success-box">
                            <h3>✅ Access Granted</h3>
                            <p>Welcome back, <strong>{username}</strong></p>
                            <p>Confidence: <strong>{result['confidence']}</strong></p>
                            <p>Distance: <strong>{result['distance']}</strong></p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.balloons()
                    else:
                        st.markdown(f"""
                        <div class="error-box">
                            <h3>❌ Access Denied</h3>
                            <p>{result['message']}</p>
                            { f"<p>Distance: <strong>{result['distance']}</strong> (threshold: 0.45)</p>"
                              if result['distance'] else "" }
                        </div>
                        """, unsafe_allow_html=True)


# ── LOCK SESSION PAGE ────────────────────────────────────
elif page == "🔒 Lock Session":
    st.title("🔒 Lock Windows Session")
    st.markdown("---")

    st.warning("⚠️ Clicking the button below will **immediately lock your Windows screen**.")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔒 Lock Session Now", type="primary"):
            result = lock_windows_session(username)
            if result["success"]:
                st.success(result["message"])
            else:
                st.error(result["message"])


# ── AUDIT LOGS PAGE ──────────────────────────────────────
elif page == "📜 Audit Logs":
    st.title("📜 Audit Log")
    st.markdown("All authentication events recorded locally.")
    st.markdown("---")

    LOG_PATH = "profiles/audit.log"

    if not os.path.exists(LOG_PATH):
        st.info("No logs yet. Enroll or authenticate first.")
    else:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

        st.markdown(f"**Total events recorded:** {len(lines)}")
        st.markdown("---")

        # Show logs in reverse (newest first)
        for line in reversed(lines):
            line = line.strip()
            if "SUCCESS" in line:
                st.success(line)
            elif "FAILED" in line or "DENIED" in line:
                st.error(line)
            else:
                st.info(line)

        st.markdown("---")
        if st.button("🗑️ Clear Logs"):
            open(LOG_PATH, "w").close()
            st.success("Logs cleared.")
            st.rerun()