<div align="center">

# 🔐 FaceLock
### Biometric Authentication System for Windows

**Local face recognition that locks and unlocks your Windows session — privately, securely, and entirely on-device.**

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![CLI](https://img.shields.io/badge/Interface-CLI-black?logo=windowsterminal)
![SQLite](https://img.shields.io/badge/Database-SQLite-lightblue?logo=sqlite)
![AES-256](https://img.shields.io/badge/Encryption-AES--256-green?logo=letsencrypt)
![GDPR](https://img.shields.io/badge/Compliance-GDPR-orange)
![Windows](https://img.shields.io/badge/Platform-Windows%2010%2F11-blue?logo=windows)

</div>

---

## What is FaceLock?

FaceLock is a Python application that replaces traditional password-based screen locking with real-time facial recognition. It runs locally on your Windows machine — no cloud, no external servers, no raw image storage.

Face embeddings are extracted, encrypted with AES-256, and stored in a local SQLite database. A **guardian loop** continuously monitors the webcam and automatically locks the session when the enrolled user is no longer detected — or when an unrecognized face appears.

> Inspired by privacy-first research initiatives such as **FACEOFF** and **Keyless**, FaceLock is built with **Privacy by Design** principles from the ground up.

---

## How It Works

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   Webcam    │────▶│  Face Detection  │────▶│  128D Embedding     │
│   Capture   │     │  (dlib / OpenCV) │     │  Extraction         │
└─────────────┘     └──────────────────┘     └──────────┬──────────┘
                                                         │
                    ┌──────────────────┐                 ▼
                    │  Windows Session │     ┌─────────────────────┐
                    │  Lock / Unlock   │◀────│  AES-256 Encrypted  │
                    │  (ctypes API)    │     │  SQLite Database    │
                    └──────────────────┘     └─────────────────────┘
```

### 1 · Enrollment (`enroll.py`)
The user captures their face via webcam. FaceLock extracts **5 frames** (configurable), averages them into a single **128-dimensional face embedding**, encrypts it with **AES-256 (Fernet)**, and stores it in a local SQLite database. No raw images are ever saved.

### 2 · Guardian Loop (`facelock.py`)
The core of the system. A real-time webcam loop monitors who is sitting at the computer:
- **No face detected** for 5 seconds → session locks automatically
- **Wrong face detected** for 30 consecutive frames → session locks immediately
- **Correct face detected** → session stays active with a live confidence overlay

### 3 · Authentication (`authenticate.py`)
To verify identity (e.g., after unlocking), the user presents their face. FaceLock requires **10 consecutive matching frames** before confirming identity — preventing spoofing from a single lucky frame.

### 4 · Audit Logging
Every event — enrollment, authentication attempt, guardian start/stop, and lock — is recorded in the SQLite database with timestamps for full traceability.

---

## Features

| Feature | Description |
|---|---|
| 🔒 **AES-256 Encryption** | All face embeddings are encrypted before being written to disk |
| 🗄️ **SQLite Database** | Users, embeddings, and logs stored in a single local file |
| 👁️ **Guardian Loop** | Real-time webcam monitoring — locks on absence or unrecognized face |
| 🛡️ **GDPR Compliant** | No images stored, right to erasure, 100% local processing |
| 🎯 **Adjustable Threshold** | Tune recognition strictness via `config.py` |
| 👥 **Multi-User Support** | Enroll, authenticate, and delete users via CLI |
| 📜 **Audit Trail** | Timestamped event log for every authentication action |
| 🖥️ **CLI + Batch Launcher** | Lightweight command-line interface with `run.bat` for quick access |

---

## Project Structure

```
FaceLock/
├── facelock.py               # Guardian loop — real-time webcam monitor (entry point)
├── enroll.py                 # Face enrollment script
├── authenticate.py           # Face authentication script
├── config.py                 # Centralized settings (thresholds, timeouts, paths)
├── run.bat                   # Windows batch launcher
├── requirements.txt
│
├── modules/
│   ├── __init__.py
│   ├── database.py           # SQLite + AES-256 encryption layer
│   └── system_controller.py  # Inactivity monitor + session lock via Windows API
│
├── data/                     # Auto-created on first launch
│   ├── facelock.db           # Encrypted SQLite database
│   └── facelock.key          # AES-256 key (never commit this)
│
└── logs/                     # Auto-created on first launch
```

---

## Privacy & GDPR Compliance

FaceLock is designed around the principle that **biometric data should never leave the user's device**.

| GDPR Article | Principle | Implementation |
|---|---|---|
| Art. 5(1)(c) | Data Minimisation | Only 128D embeddings stored — no raw images, ever |
| Art. 5(1)(e) | Storage Limitation | Captured frames are discarded immediately after processing |
| Art. 5(1)(f) | Integrity & Confidentiality | AES-256 encryption on all stored biometric data |
| Art. 17 | Right to Erasure | Full user deletion available via the database manager |
| Art. 32 | Security of Processing | 100% local processing — no network calls, no cloud |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Interface | CLI + OpenCV window + `run.bat` launcher |
| Face Detection & Recognition | `face_recognition` (dlib) |
| Encryption | `cryptography` — Fernet / AES-256 |
| Database | SQLite3 (built-in) |
| Session Control | Windows API via `ctypes` |

---

## Getting Started

### Prerequisites

- Windows 10 or 11 (64-bit)
- Python 3.11
- A webcam (built-in or USB)
- Visual Studio Build Tools (required for `dlib`)

### Installation

```bash
# Clone the repository
git clone https://github.com/tebeerr/FaceLock.git
cd FaceLock

# Create a virtual environment with Python 3.11
py -3.11 -m venv facelock_env
facelock_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

> ⚠️ If `face_recognition` fails to install, `dlib` needs to be installed first.
> Use the prebuilt wheel for Python 3.11:
> ```bash
> pip install https://github.com/jloh02/dlib/releases/download/v19.22/dlib-19.22.99-cp311-cp311-win_amd64.whl
> pip install face_recognition
> ```

### Run

**Using the batch launcher:**

```bash
run.bat enroll student_user    # Enroll your face
run.bat start  student_user    # Start the guardian loop
run.bat auth   student_user    # Test authentication
run.bat users                  # List enrolled users
```

**Or directly with Python:**

```bash
python enroll.py --user student_user       # Step 1: Enroll
python facelock.py --user student_user     # Step 2: Start guardian loop
python authenticate.py --user student_user # Optional: Test auth separately
```

On first launch, `data/facelock.db` and `data/facelock.key` are created automatically.

---

## Usage

| Command | Action |
|---|---|
| 📸 `enroll.py --user <name>` | Capture your face and register in the encrypted database |
| 👁️ `facelock.py --user <name>` | Start the guardian loop — locks on absence or wrong face |
| 🔓 `authenticate.py --user <name>` | Verify your identity against the stored embedding |
| 🔇 `facelock.py --user <name> --silent` | Run guardian loop without the webcam preview window |
| 👥 `run.bat users` | List all enrolled users |

---

## Configuration

All settings are centralized in `config.py`:

| Setting | Default | Description |
|---|---|---|
| `MATCH_THRESHOLD` | `0.45` | Cosine distance threshold — lower = stricter matching |
| `NO_FACE_TIMEOUT` | `5` | Seconds without a face before auto-lock |
| `WRONG_FACE_LIMIT` | `30` | Consecutive wrong-face frames before lock |
| `ENROLLMENT_FRAMES` | `5` | Number of frames averaged during enrollment |
| `AUTH_CORRECT_NEEDED` | `10` | Consecutive correct frames needed to authenticate |
| `POLL_INTERVAL_MS` | `100` | Milliseconds between webcam frames (10 fps) |
| `SHOW_WINDOW` | `True` | Show/hide live webcam preview window |

---

## Security Notes

- `data/facelock.key` is your encryption key — **never commit it to version control**
- `data/facelock.db` contains encrypted biometric data — **keep it local**
- Both files are excluded via `.gitignore` by default
- Deleting a user permanently removes all associated data (GDPR Art. 17)

---

## Academic Context

This project was developed as part of a university biometric systems module.
It demonstrates practical implementation of:

- Computer vision pipelines (detection → alignment → embedding)
- Biometric template protection (encryption, no raw storage)
- Windows system integration (session lock via native API)
- Privacy-by-Design architecture (GDPR-inspired)

---

<div align="center">

Built with Python · Secured with AES-256 · Designed for Privacy

</div>
