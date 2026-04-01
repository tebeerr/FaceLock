"""
app.py (updated)
=================
Streamlit UI for FaceLock -- integrates SQLite database + background service.
Run with: streamlit run app.py
"""

import streamlit as st
import numpy as np
import cv2
import threading
from PIL import Image

from modules.database import DatabaseManager
from modules.system_controller import SystemController
from authentication import authenticate_from_frame, is_enrolled
from enrollment import enroll_from_frame
from config import (
    APP_TITLE, APP_ICON, DEFAULT_USER,
    DEFAULT_THRESHOLD, MIN_THRESHOLD, MAX_THRESHOLD, INACTIVITY_TIMEOUT
)

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .success-box {
        background-color: #1a3a2a;
        border-left: 5px solid #00ff88;
        padding: 15px; border-radius: 8px; margin: 10px 0;
    }
    .error-box {
        background-color: #3a1a1a;
        border-left: 5px solid #ff4444;
        padding: 15px; border-radius: 8px; margin: 10px 0;
    }
    .info-card {
        background-color: #1e2130;
        padding: 20px; border-radius: 12px; margin: 10px 0;
    }
    .warning-box {
        background-color: #3a3a1a;
        border-left: 5px solid #ffaa00;
        padding: 15px; border-radius: 8px; margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_db() -> DatabaseManager:
    return DatabaseManager()

@st.cache_resource
def get_controller() -> SystemController:
    db         = get_db()
    controller = SystemController(db=db, inactivity_timeout=INACTIVITY_TIMEOUT)
    controller.start()
    return controller

db         = get_db()
controller = get_controller()

with st.sidebar:
    st.title(f"{APP_ICON} FaceLock")
    st.markdown("---")
    username = st.text_input("Username", value=DEFAULT_USER)
    enrolled = is_enrolled(username, db)
    st.markdown(f"**Status:** {'Enrolled' if enrolled else 'Not Enrolled'}")
    status = controller.get_status()
    st.markdown("---")
    st.markdown("### Inactivity Monitor")
    st.progress(status["auto_lock_pct"] / 100)
    st.caption(
        f"Idle: **{status['idle_seconds']}s** / {status['timeout_seconds']}s  |  "
        f"Lock in: **{status['remaining_seconds']}s**"
    )
    svc_color = "Running" if status["service_running"] else "Stopped"
    st.caption(f"Background Service: {svc_color}")
    st.markdown("---")
    page = st.radio("Navigation", [
        "Home",
        "Enroll Face",
        "Authenticate",
        "Lock Session",
        "Settings",
        "Audit Logs",
        "Users"
    ])


if page == "Home":
    st.title("FaceLock -- Biometric Authentication System")
    st.markdown("##### Privacy by Design | Deep Learning Embeddings | 100% Local")
    st.markdown("---")
    stats = db.get_stats()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Enrolled Users", stats["total_users"])
    with col2:
        st.metric("Total Authentications", stats["total_auths"])
    with col3:
        st.metric("Successful", stats["success_auths"])
    with col4:
        st.metric("Failed", stats["failed_auths"])
    st.markdown("---")
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("### System Flow")
        st.markdown("""
        ```
        1. ENROLL
           Camera -> Face detection
           -> 128D embedding -> AES-256 encrypt
           -> Store in SQLite DB

        2. AUTO-LOCK
           Background service monitors inactivity
           -> No user detected for N seconds
           -> LockWorkStation() called

        3. AUTHENTICATE
           Camera -> Detect face
           -> Extract embedding
           -> Decrypt stored embedding
           -> Compare (cosine distance)
           -> Grant or Deny access

        4. AUDIT
           All events logged to SQLite
        ```
        """)
    with col_right:
        st.markdown("### Privacy by Design")
        st.markdown("""
        | GDPR Article | Measure |
        |---|---|
        | Art. 5(1)(c) | Only embeddings stored |
        | Art. 5(1)(e) | Raw images deleted immediately |
        | Art. 5(1)(f) | AES-256 encryption |
        | Art. 17 | Full delete available |
        | Art. 32 | Local processing only |
        """)
    st.markdown("---")
    st.markdown("### Live Status")
    svc = controller.get_status()
    c1, c2, c3 = st.columns(3)
    c1.metric("Idle Time", f"{svc['idle_seconds']}s")
    c2.metric("Lock In", f"{svc['remaining_seconds']}s")
    c3.metric("Session", "Locked" if svc["session_locked"] else "Active")


elif page == "Enroll Face":
    st.title("Face Enrollment")
    st.markdown("Register your face into the encrypted local database.")
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("### Capture Your Face")
        st.info("Look straight at the camera in good lighting.")
        img_file = st.camera_input("Take enrollment photo")
        if img_file:
            img_pil   = Image.open(img_file)
            img_np    = np.array(img_pil)
            frame_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            with st.spinner("Extracting and encrypting face embedding..."):
                result = enroll_from_frame(username, frame_bgr, db)
            with col2:
                st.markdown("### Result")
                if result["success"]:
                    st.markdown(f"""
                    <div class="success-box">
                        <h3>Enrolled Successfully</h3>
                        <p>{result['message']}</p>
                        <p>Embedding encrypted with AES-256</p>
                        <p>Stored in local SQLite database</p>
                        <p>No raw image saved (GDPR compliant)</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.balloons()
                else:
                    st.markdown(f"""
                    <div class="error-box">
                        <h3>Enrollment Failed</h3>
                        <p>{result['message']}</p>
                    </div>
                    """, unsafe_allow_html=True)


elif page == "Authenticate":
    st.title("Face Authentication")
    st.markdown("Verify your identity to unlock the session.")
    st.markdown("---")
    if not is_enrolled(username, db):
        st.warning(f"**{username}** is not enrolled. Go to **Enroll Face** first.")
    else:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("### Scan Your Face")
            st.info("Look at the camera and hold still.")
            img_file = st.camera_input("Take authentication photo")
            if img_file:
                img_pil   = Image.open(img_file)
                img_np    = np.array(img_pil)
                frame_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                with st.spinner("Verifying identity..."):
                    result = authenticate_from_frame(username, frame_bgr, db)
                with col2:
                    st.markdown("### Result")
                    if result["success"]:
                        st.markdown(f"""
                        <div class="success-box">
                            <h3>Access Granted</h3>
                            <p>Welcome back, <strong>{username}</strong></p>
                            <p>Confidence: <strong>{result['confidence']}</strong></p>
                            <p>Distance: <strong>{result['distance']}</strong>
                               (threshold: {db.get_threshold()})</p>
                        </div>
                        """, unsafe_allow_html=True)
                        controller.on_session_unlock(username)
                        st.balloons()
                    else:
                        st.markdown(f"""
                        <div class="error-box">
                            <h3>Access Denied</h3>
                            <p>{result['message']}</p>
                            {f"<p>Distance: <strong>{result['distance']}</strong></p>"
                             if result['distance'] else ""}
                        </div>
                        """, unsafe_allow_html=True)


elif page == "Lock Session":
    st.title("Lock Windows Session")
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Manual Lock")
        st.warning("This will immediately lock your Windows screen.")
        if st.button("Lock Now", type="primary"):
            result = controller.lock_workstation(reason="manual_ui")
            if result["success"]:
                st.success(result["message"])
            else:
                st.error(result["message"])
    with col2:
        st.markdown("### Auto-Lock Status")
        svc = controller.get_status()
        st.markdown(f"""
        <div class="info-card">
            <p>Current idle time: <strong>{svc['idle_seconds']}s</strong></p>
            <p>Auto-lock in: <strong>{svc['remaining_seconds']}s</strong></p>
            <p>Timeout set to: <strong>{svc['timeout_seconds']}s</strong></p>
            <p>Service: {'Running' if svc['service_running'] else 'Stopped'}</p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(svc["auto_lock_pct"] / 100, text="Inactivity progress")


elif page == "Settings":
    st.title("Settings")
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Recognition Threshold")
        st.caption("Lower = stricter matching. Default: 0.45")
        new_threshold = st.slider(
            "Similarity threshold",
            min_value=MIN_THRESHOLD,
            max_value=MAX_THRESHOLD,
            value=db.get_threshold(),
            step=0.01
        )
        if st.button("Save Threshold"):
            db.set_threshold(new_threshold)
            st.success(f"Threshold updated to {new_threshold}")
    with col2:
        st.markdown("### Auto-Lock Timeout")
        st.caption("Seconds of inactivity before session locks automatically.")
        new_timeout = st.slider(
            "Inactivity timeout (seconds)",
            min_value=10,
            max_value=300,
            value=controller.inactivity_timeout,
            step=5
        )
        if st.button("Save Timeout"):
            controller.set_timeout(new_timeout)
            st.success(f"Timeout updated to {new_timeout}s")
    st.markdown("---")
    st.markdown("### Background Service Control")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Start Service"):
            controller.start()
            st.success("Service started.")
    with c2:
        if st.button("Stop Service"):
            controller.stop()
            st.warning("Service stopped.")


elif page == "Audit Logs":
    st.title("Audit Logs")
    st.markdown("All authentication events stored in SQLite database.")
    st.markdown("---")
    filter_user = st.text_input("Filter by user (leave empty for all)", value="")
    logs = db.get_logs(user_id=filter_user if filter_user else None, limit=100)
    st.markdown(f"**{len(logs)} events found**")
    st.markdown("---")
    for log in logs:
        msg = f"[{log['timestamp']}]  [{log['user_id'].upper()}]  {log['event']}"
        if log["success"] is True:
            st.success(msg)
        elif log["success"] is False:
            st.error(msg)
        else:
            st.info(msg)
    if st.button("Clear All Logs"):
        import sqlite3
        with sqlite3.connect("data/facelock.db") as conn:
            conn.execute("DELETE FROM auth_logs")
            conn.commit()
        st.success("Logs cleared.")
        st.rerun()


elif page == "Users":
    st.title("Enrolled Users")
    st.markdown("Manage users stored in the local database.")
    st.markdown("---")
    users = db.get_all_users()
    if not users:
        st.info("No users enrolled yet.")
    else:
        for u in users:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{u}**")
            with col2:
                if st.button(f"Delete", key=f"del_{u}"):
                    db.delete_user(u)
                    st.success(f"User '{u}' deleted (GDPR Art. 17).")
                    st.rerun()
    st.markdown("---")
    stats = db.get_stats()
    st.markdown(f"**Total enrolled:** {stats['total_users']} users")
