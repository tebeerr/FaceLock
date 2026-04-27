"""
facelock_guard.py — Pre-login face verification overlay.

Run at Windows logon via Task Scheduler (0-second delay).
Shows fullscreen blocking overlay, scans face, either:
  - Closes overlay (face OK) → desktop accessible
  - Calls LockWorkStation (face fail / timeout) → Windows lock screen

Usage (standalone):
    python facelock_guard.py --user primary

Usage (compiled exe):
    FaceLockGuard.exe --user primary
"""

import argparse
import ctypes
import logging
import sys
import threading
import time
from pathlib import Path

import cv2
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageTk

import config

# ── Logging ──────────────────────────────────────────────────────────────────

config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(config.LOGS_DIR / 'guard.log'),
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
log = logging.getLogger('guard')


# ── Windows lock ──────────────────────────────────────────────────────────────

def lock_session(reason: str) -> None:
    log.warning('Locking session: %s', reason)
    ctypes.windll.user32.LockWorkStation()


# ── Face recognition (lazy import — heavy) ────────────────────────────────────

def load_stored_embedding(username: str):
    """Load the stored 128D embedding from the encrypted DB."""
    from infrastructure.repositories import SQLiteEmbeddingRepository
    repo = SQLiteEmbeddingRepository()
    embedding = repo.find(username)
    if embedding is None:
        raise ValueError(f'No enrollment found for user: {username}')
    return embedding.vector


def compute_distance(stored, live) -> float:
    import numpy as np
    return float(np.linalg.norm(stored - live))


# ── Overlay window ────────────────────────────────────────────────────────────

class FaceGuardOverlay:
    """
    Fullscreen always-on-top tkinter window.
    Shows webcam feed, face recognition result, countdown timer.
    Destroys itself on success; calls lock_session() on failure.
    """

    TIMEOUT_SECONDS = 10      # Seconds before lock on no-match
    MATCH_THRESHOLD = config.MATCH_THRESHOLD
    CONSEC_NEEDED   = 5       # Consecutive matching frames to unlock

    def __init__(self, username: str):
        self.username = username
        self.stored_embedding = None

        self.root = tk.Tk()
        self._setup_window()
        self._setup_ui()

        self._cam = None
        self._running = True
        self._consec_matches = 0
        self._no_match_since = None
        self._status = 'initializing'   # initializing | scanning | success | fail

    # ── Window setup ─────────────────────────────────────────────────────────

    def _setup_window(self):
        root = self.root
        root.title('FaceLock')
        root.configure(bg='#0a0a0a')

        # Fullscreen + always on top
        root.attributes('-fullscreen', True)
        root.attributes('-topmost', True)

        # Attempt to grab keyboard focus — prevents most accidental bypasses
        root.grab_set()
        root.focus_force()

        # Intercept Ctrl+Alt+Del is NOT possible from user space.
        # We CAN block Alt+F4, Win key, and Alt+Tab from closing this window:
        root.protocol('WM_DELETE_WINDOW', lambda: None)  # Block close button
        root.bind('<Alt-F4>', lambda e: 'break')
        root.bind('<Alt-Tab>', lambda e: 'break')

    def _setup_ui(self):
        root = self.root
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()

        # Background
        self._canvas = tk.Canvas(root, bg='#0a0a0a', highlightthickness=0)
        self._canvas.pack(fill='both', expand=True)

        # Webcam preview label (centered)
        self._cam_label = tk.Label(root, bg='#0a0a0a')
        self._cam_label.place(relx=0.5, rely=0.42, anchor='center')

        # Status text
        mono = tkfont.Font(family='Consolas', size=18, weight='normal')
        self._status_var = tk.StringVar(value='Initializing camera...')
        self._status_label = tk.Label(
            root, textvariable=self._status_var,
            bg='#0a0a0a', fg='#ffffff',
            font=mono,
        )
        self._status_label.place(relx=0.5, rely=0.72, anchor='center')

        # Timer / confidence bar
        small_mono = tkfont.Font(family='Consolas', size=13)
        self._timer_var = tk.StringVar(value='')
        self._timer_label = tk.Label(
            root, textvariable=self._timer_var,
            bg='#0a0a0a', fg='#666666',
            font=small_mono,
        )
        self._timer_label.place(relx=0.5, rely=0.78, anchor='center')

        # Hint
        hint_font = tkfont.Font(family='Consolas', size=11)
        hint = tk.Label(
            root,
            text='If recognition fails, press Ctrl+Alt+Del to access Windows login.',
            bg='#0a0a0a', fg='#333333',
            font=hint_font,
        )
        hint.place(relx=0.5, rely=0.95, anchor='center')

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        """Start recognition in background thread, run tkinter mainloop."""
        t = threading.Thread(target=self._recognition_loop, daemon=True)
        t.start()
        self.root.mainloop()

    def _recognition_loop(self):
        """Background thread: opens camera, runs face_recognition."""
        import face_recognition
        import numpy as np

        # Load stored embedding
        try:
            self.stored_embedding = load_stored_embedding(self.username)
        except Exception as exc:
            log.error('Failed to load embedding: %s', exc)
            self._update_status('⚠  No enrollment found.', '#ff6b6b')
            time.sleep(3)
            self._do_lock('no_enrollment')
            return

        # Open camera
        self._cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self._cam.isOpened():
            log.error('Camera unavailable')
            self._update_status('⚠  Camera not detected.', '#ff6b6b')
            time.sleep(3)
            self._do_lock('no_camera')
            return

        self._no_match_since = time.time()
        self._update_status('Look at the camera...', '#ffffff')

        while self._running:
            ret, frame = self._cam.read()
            if not ret:
                time.sleep(0.1)
                continue

            # Show camera feed (mirror flip for natural feel)
            frame_rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
            self._update_camera_frame(frame_rgb)

            # Detect + encode face
            small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
            rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            locations = face_recognition.face_locations(rgb_small)

            elapsed = time.time() - self._no_match_since
            remaining = max(0, self.TIMEOUT_SECONDS - elapsed)

            if not locations:
                self._consec_matches = 0
                self._update_timer(f'No face detected  —  locking in {remaining:.0f}s')
                if elapsed >= self.TIMEOUT_SECONDS:
                    self._do_lock('timeout_no_face')
                    return
                continue

            encodings = face_recognition.face_encodings(rgb_small, locations)
            if not encodings:
                continue

            dist = compute_distance(self.stored_embedding, encodings[0])
            confidence = max(0, (1 - dist / self.MATCH_THRESHOLD)) * 100

            if dist <= self.MATCH_THRESHOLD:
                self._consec_matches += 1
                self._no_match_since = time.time()  # reset timeout on any match
                self._update_status(
                    f'✓  Recognized  ({confidence:.0f}%)',
                    '#00ff88'
                )
                self._update_timer(
                    f'Consecutive: {self._consec_matches}/{self.CONSEC_NEEDED}'
                )
                if self._consec_matches >= self.CONSEC_NEEDED:
                    self._do_success()
                    return
            else:
                self._consec_matches = 0
                self._update_status(
                    f'✗  Not recognized  ({confidence:.0f}%)',
                    '#ff6b6b'
                )
                self._update_timer(f'Locking in {remaining:.0f}s')
                if elapsed >= self.TIMEOUT_SECONDS:
                    self._do_lock('timeout_wrong_face')
                    return

        if self._cam:
            self._cam.release()

    # ── UI update helpers (thread-safe via after()) ───────────────────────────

    def _update_status(self, text: str, color: str = '#ffffff'):
        self.root.after(0, lambda: (
            self._status_var.set(text),
            self._status_label.configure(fg=color),
        ))

    def _update_timer(self, text: str):
        self.root.after(0, lambda: self._timer_var.set(text))

    def _update_camera_frame(self, frame_rgb):
        img = Image.fromarray(frame_rgb)
        img = img.resize((480, 360), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self.root.after(0, lambda: (
            self._cam_label.configure(image=photo),
            setattr(self._cam_label, '_photo', photo),  # prevent GC
        ))

    def _do_success(self):
        log.info('Face verified for user=%s — unlocking', self.username)
        self._running = False
        if self._cam:
            self._cam.release()
        self._update_status('✓  Verified — Welcome!', '#00ff88')
        self._update_timer('')
        # Short delay so the green confirmation is visible
        self.root.after(800, self.root.destroy)

    def _do_lock(self, reason: str):
        self._running = False
        if self._cam:
            self._cam.release()
        self._update_status('Session locked.', '#ff6b6b')
        self._update_timer('Enter your PIN or password.')
        self.root.after(1200, lambda: (
            self.root.destroy(),
            lock_session(reason),
        ))


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='FaceLock pre-login guard')
    parser.add_argument('--user', default=config.DEFAULT_USER,
                        help='Username whose embedding to match against')
    args = parser.parse_args()

    log.info('Guard starting for user=%s', args.user)

    overlay = FaceGuardOverlay(username=args.user)
    overlay.run()

    log.info('Guard finished for user=%s', args.user)


if __name__ == '__main__':
    main()
