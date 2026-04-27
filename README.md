<div align="center">

# FaceLock

### Biometric Authentication System for Windows

**Local face recognition that guards your Windows session — privately, securely, and entirely on-device.**

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![AES-256-GCM](https://img.shields.io/badge/Encryption-AES--256--GCM-green?logo=letsencrypt)
![Tests](https://img.shields.io/badge/Tests-44%20passed-brightgreen?logo=pytest)
![GDPR](https://img.shields.io/badge/Compliance-GDPR%20%7C%20AI%20Act%20%7C%20ISO%2030107--3-orange)
![Windows](https://img.shields.io/badge/Platform-Windows%2010%2F11-blue?logo=windows)
![Standalone](https://img.shields.io/badge/Standalone-.exe%20via%20PyInstaller-purple?logo=windows)

</div>

---

## What is FaceLock?

FaceLock is a Python application that replaces password-based screen locking with real-time facial recognition. It runs **100% locally** — no cloud, no external servers, no raw image storage.

Face embeddings are extracted from the webcam, encrypted with **AES-256-GCM**, and stored in a local SQLite database. A **guardian loop** continuously monitors who is at the screen and locks the Windows session when the enrolled user is absent or an unrecognised face appears.

FaceLock also includes a **pre-login guard** (`facelock_guard.py`) — a fullscreen overlay that runs at Windows logon via Task Scheduler. It verifies the user's face before granting desktop access and can be compiled into a **standalone `.exe`** with PyInstaller for zero-dependency deployment.

The system is built around a clean **domain → application → infrastructure** architecture, with full audit logging, RBAC roles, tamper-evident log signing, and biometric evaluation metrics (FAR/FRR/EER).

---

## Architecture

```
FaceLock/
├── domain/                      # Pure entities and repository interfaces
│   ├── entities.py              #   User, FaceEmbedding, AuthResult, AuditEvent, Role
│   └── repositories.py          #   Abstract contracts (ABCs)
│
├── application/                 # Business logic — no I/O, no framework deps
│   ├── enroll_usecase.py
│   ├── authenticate_usecase.py
│   └── guardian_usecase.py
│
├── infrastructure/              # Concrete implementations
│   ├── crypto.py                #   AES-256-GCM encrypt / decrypt
│   ├── repositories.py          #   SQLite + RBAC + HMAC-signed audit logs
│   └── session.py               #   Windows session lock via ctypes
│
├── evaluation/                  # Biometric performance metrics
│   ├── metrics.py               #   FAR, FRR, EER computation
│   └── evaluate.py              #   Live webcam evaluation runner
│
├── oversight/                   # AI Act Art.14 — human oversight
│   └── dashboard.py             #   Dashboard, alert detection, log verify, manual lock
│
├── tests/
│   ├── unit/                    #   test_crypto, test_metrics, test_repositories
│   └── integration/             #   test_enroll_auth (full pipeline, no webcam)
│
├── report/
│   ├── privacy_by_design.md     #   GDPR Art.25 compliance statement
│   ├── dpia.md                  #   Data Protection Impact Assessment
│   ├── ai_act_mapping.md        #   EU AI Act Article mapping
│   └── iso_mapping.md           #   ISO 27001 + ISO 30107-3 + ISO 24745
│
├── enroll.py                    # CLI adapter — enrollment
├── authenticate.py              # CLI adapter — authentication
├── facelock.py                  # CLI adapter — guardian loop
├── facelock_guard.py            # Pre-login face verification overlay
├── facelock_guard.spec          # PyInstaller build spec for standalone .exe
├── config.py                    # Centralised settings (frozen-exe aware)
├── migrate_key.py               # One-time Fernet → AES-256-GCM migration
└── run.bat                      # Windows batch launcher
```

### Data flow

```
Webcam → face_recognition (dlib ResNet) → 128-D embedding
                                                │
                                    AES-256-GCM encrypt
                                                │
                                        SQLite (facelock.db)
                                                │
                          HMAC-SHA256 signed audit log entry
```

### Guard flow (pre-login)

```
Windows logon → Task Scheduler → FaceLockGuard.exe
        │
        ▼
Fullscreen overlay blocks desktop
        │
        ▼
Webcam → face match against stored embedding
        │                           │
    ✓ Match (5 frames)        ✗ Timeout (10s)
        │                           │
  Overlay closes             LockWorkStation()
  Desktop accessible         → Windows lock screen
```

---

## Security Model

| Layer | Technology | Detail |
|---|---|---|
| Embedding encryption | AES-256-GCM | 32-byte key, 12-byte random nonce per write, GCM authentication tag |
| Audit log integrity | HMAC-SHA256 | Every log entry signed; verifiable via `oversight --verify` |
| Access control | RBAC | Three roles: `admin`, `user`, `readonly` |
| Key storage | Separate file | `data/facelock.key` — separate from `data/facelock.db` |
| Image retention | None | Frames discarded after embedding extraction (`STORE_RAW_IMAGES = False`) |
| Network | None | Zero outbound connections (`CLOUD_UPLOAD = False`) |

---

## Getting Started

### Prerequisites

- Windows 10 or 11 (64-bit)
- Python 3.11
- Webcam (built-in or USB)
- Visual Studio Build Tools (required by `dlib`)

### Installation

```bash
# Clone
git clone https://github.com/tebeerr/FaceLock.git
cd FaceLock

# Create virtual environment
py -3.11 -m venv facelock_env
facelock_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

> **If `face_recognition` fails**, install the prebuilt dlib wheel first:
> ```bash
> pip install https://github.com/jloh02/dlib/releases/download/v19.22/dlib-19.22.99-cp311-cp311-win_amd64.whl
> pip install face_recognition
> ```

### First-time key migration (existing installations only)

If you used a previous version of FaceLock (Fernet encryption), run once:

```bash
.\run.bat migrate
```

This re-encrypts all stored embeddings under AES-256-GCM and backs up the old key.

---

## Usage

All commands are available through the batch launcher. Run from PowerShell with `.\`:

```powershell
.\run.bat enroll    <username>          # Enroll a face (add --role admin|user|readonly)
.\run.bat start     <username>          # Start the guardian loop
.\run.bat auth      <username>          # Test authentication
.\run.bat users                         # List all enrolled users and roles
.\run.bat eval      <username>          # Run FAR/FRR/EER biometric evaluation
.\run.bat oversight                     # Human oversight dashboard
.\run.bat oversight --verify            # Verify HMAC integrity of all log entries
.\run.bat oversight --lock              # Manually lock the workstation
.\run.bat migrate                       # Upgrade encryption: Fernet → AES-256-GCM
.\run.bat test                          # Run the full test suite (44 tests)
```

Or call Python directly:

```bash
python enroll.py --user alice --role admin
python facelock.py --user alice --silent
python authenticate.py --user alice
python facelock_guard.py --user alice          # Pre-login face guard overlay
python evaluation/evaluate.py --user alice --genuine 20 --imposter 20
python oversight/dashboard.py --verify
```

To build and run the standalone guard executable:

```bash
pyinstaller facelock_guard.spec                # Build .exe to dist/
dist\FaceLockGuard.exe --user alice            # Run without Python
```

---

## How It Works

### Enrollment

```
Webcam → 7 frames captured → face_recognition.face_encodings()
→ 128-D vectors averaged → AES-256-GCM encrypted → SQLite
→ HMAC-signed audit log entry written
```

The user sits in front of the webcam. FaceLock captures `ENROLLMENT_FRAMES` (default 7) frames, averages the 128-dimensional embeddings for a more stable representation, encrypts the result, and stores it. No raw images are ever written to disk.

### Guardian Loop

The core of the system. Runs continuously while the user is logged in:

- **No face detected** for `NO_FACE_TIMEOUT` seconds (default 8) → session locks
- **Wrong face** for `WRONG_FACE_LIMIT` consecutive frames (default 15) → session locks immediately
- **Correct face** → session stays active with live confidence overlay

### Pre-Login Guard

`facelock_guard.py` is a fullscreen, always-on-top overlay designed to run at Windows logon (before the desktop is accessible):

- **Launches via Task Scheduler** at user logon with 0-second delay
- **Blocks the desktop** with a dark overlay — intercepts Alt+F4, Alt+Tab, and window close
- **Scans the webcam** for the enrolled user's face with a live camera feed
- **On match** (5 consecutive frames) → overlay closes, desktop is accessible
- **On timeout** (10 seconds with no match) → calls `LockWorkStation()` and returns to the Windows lock screen
- **Fallback**: user can always press Ctrl+Alt+Del to reach the Windows login screen

```bash
# Run from source
python facelock_guard.py --user alice

# Run as standalone exe (no Python required)
dist\FaceLockGuard.exe --user alice
```

#### Compiling to Standalone `.exe`

FaceLock Guard can be compiled into a single portable executable using PyInstaller:

```bash
pyinstaller facelock_guard.spec
```

The resulting `dist/FaceLockGuard.exe` (~180 MB) bundles Python, OpenCV, dlib, and all dependencies. Copy the `dist/` folder (including `data/` and `logs/`) to any Windows 10/11 machine — no Python installation needed.

### Authentication

Requires `AUTH_CORRECT_NEEDED` consecutive matching frames (default 10) before confirming identity. A single lucky frame is never sufficient.

### Biometric Evaluation

```bash
.\run.bat eval alice
```

Captures genuine samples (enrolled user) then prompts for an imposter (different person). Computes FAR, FRR, and EER across a 500-point threshold sweep. Results saved to `report/evaluation_results.json`.

### Human Oversight Dashboard

```bash
.\run.bat oversight
```

Displays enrolled users, recent auth events, consecutive-failure alerts, and verifies HMAC integrity of all log entries. Satisfies EU AI Act Article 14 (human oversight measures).

---

## Configuration

All settings in `config.py`:

| Setting | Default | Description |
|---|---|---|
| `MATCH_THRESHOLD` | `0.45` | Cosine distance threshold — lower = stricter |
| `NO_FACE_TIMEOUT` | `8` | Seconds without a face before auto-lock |
| `WRONG_FACE_LIMIT` | `15` | Consecutive wrong-face frames before lock |
| `ENROLLMENT_FRAMES` | `7` | Frames averaged during enrollment |
| `AUTH_CORRECT_NEEDED` | `10` | Consecutive correct frames to confirm identity |
| `POLL_INTERVAL_MS` | `100` | Webcam polling rate (10 fps) |
| `SHOW_WINDOW` | `True` | Show live webcam preview |

---

## Testing

```bash
.\run.bat test
```

```
44 passed in 3.24s
```

| Suite | Tests | Coverage |
|---|---|---|
| `tests/unit/test_crypto.py` | 7 | AES-256-GCM roundtrip, nonce randomness, tamper detection, key size validation |
| `tests/unit/test_metrics.py` | 7 | FAR/FRR/EER correctness, edge cases (perfect/full overlap) |
| `tests/unit/test_repositories.py` | 17 | CRUD, RBAC, HMAC signing, encryption opacity |
| `tests/integration/test_enroll_auth.py` | 13 | Full enroll→auth pipeline, imposter rejection, log signing |

No webcam required — integration tests use synthetic 128-D vectors.

---

## Compliance

| Framework | Document | Key claims |
|---|---|---|
| GDPR Art. 25 | `report/privacy_by_design.md` | 7 PbD principles; Art. 5, 9, 17, 25, 32 mapping |
| GDPR Art. 35 | `report/dpia.md` | Full DPIA; risk register; residual risk assessment |
| EU AI Act | `report/ai_act_mapping.md` | Art. 9, 10, 13, 14, 15 mapping; Art. 5 exclusions |
| ISO 27001:2022 | `report/iso_mapping.md` | 13 Annex A control mappings |
| ISO 30107-3:2023 | `report/iso_mapping.md` | PAD Level 2 (temporal frame consistency) |
| ISO 24745:2022 | `report/iso_mapping.md` | Irreversibility, unlinkability, revocability |

---

## Security Notes

- `data/facelock.key` is your AES-256-GCM key — **never commit it** (excluded by `.gitignore`)
- `data/facelock.db` contains encrypted biometric data — **keep it local**
- Both are OS-permission protected; no application can read them without your user account
- Delete a user permanently: `python -c "from application.enroll_usecase import EnrollUseCase; ..."`  
  or re-enroll and overwrite

---

## Academic Context

Developed as part of a university biometric systems module. Demonstrates:

- **Computer vision pipeline** — detection → alignment → 128-D embedding (dlib ResNet)
- **Layered architecture** — domain / application / infrastructure separation
- **Biometric template protection** — AES-256-GCM, no raw storage, key separation
- **Pre-login authentication** — fullscreen guard overlay with standalone `.exe` deployment
- **Performance evaluation** — FAR, FRR, EER with live genuine and imposter capture
- **Regulatory compliance** — GDPR, EU AI Act, ISO 27001, ISO 30107-3
- **Engineering maturity** — 44 automated tests, HMAC-signed audit trail, RBAC

---

<div align="center">

Built with Python · AES-256-GCM · Privacy by Design · Pre-Login Guard · 44 tests green

</div>
