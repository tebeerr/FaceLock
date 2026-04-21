# Privacy by Design — FaceLock

**Document type**: Privacy by Design Statement  
**Version**: 2.0  
**System**: FaceLock — Biometric Authentication System  
**Regulation**: GDPR (EU) 2016/679

---

## 1. Overview

FaceLock implements all seven Privacy by Design (PbD) foundational principles as
defined by Ann Cavoukian (2011) and codified under GDPR Article 25.

---

## 2. Principle Mapping

### 2.1 Proactive not Reactive — Preventive not Remedial

The system was designed from inception to eliminate privacy risks, not patch them
after the fact.  

- No image capture storage path exists in the codebase (`STORE_RAW_IMAGES = False`)
- AES-256-GCM encryption is applied before any data touches the filesystem
- Network calls are architecturally absent (`CLOUD_UPLOAD = False`)

### 2.2 Privacy as the Default Setting

Privacy-protective behaviour requires no configuration; weakening it does.

| Setting | Default | Weakening requires |
|---|---|---|
| Raw image storage | `False` | Code change |
| Cloud upload | `False` | Code change |
| Encryption | AES-256-GCM always | Not possible |
| Local processing | On-device only | Not possible |

### 2.3 Privacy Embedded into Design

Biometric data protection is not a layer on top of the system — it is the system.

- `infrastructure/crypto.py` is the sole entry point for all data persistence
- No code path writes an embedding without first passing through `encrypt()`
- Repository interfaces (`domain/repositories.py`) enforce this contract at compile time

### 2.4 Full Functionality — Positive-Sum, not Zero-Sum

Security and privacy are not traded off:

- AES-256-GCM provides both confidentiality (encryption) and integrity (GCM tag)
- HMAC-SHA256 log signing provides audit integrity without exposing log content
- RBAC provides access control without requiring additional data collection

### 2.5 End-to-End Security — Full Lifecycle Protection

| Lifecycle phase | Control |
|---|---|
| Capture | Frame discarded immediately after embedding extraction |
| Storage | AES-256-GCM encrypted blob, key stored separately |
| Retrieval | Decrypt-use-discard; plaintext never persisted |
| Deletion | `delete_user()` removes users, embeddings, and logs atomically |
| Key rotation | `migrate_key.py` re-encrypts all embeddings under new key |

### 2.6 Visibility and Transparency

- All processing is local and inspectable
- Audit log records every event with timestamp and HMAC signature
- `oversight/dashboard.py` provides human-readable event history to oversight operators

### 2.7 Respect for User Privacy — User-Centric

- Users can delete their own data at any time (`run.bat delete <username>`)
- No data is shared with third parties
- Minimum necessary data: only 128-dimensional float vector, never the face image

---

## 3. GDPR Article Compliance

| Article | Requirement | Implementation |
|---|---|---|
| Art. 5(1)(a) | Lawfulness, fairness, transparency | Local-only processing, explicit enrolment |
| Art. 5(1)(b) | Purpose limitation | Embeddings used only for authentication |
| Art. 5(1)(c) | Data minimisation | 128-D vector only; no images |
| Art. 5(1)(e) | Storage limitation | No retention beyond active session |
| Art. 5(1)(f) | Integrity & confidentiality | AES-256-GCM + HMAC-signed logs |
| Art. 9 | Special category data (biometrics) | Explicit enrolment consent; local only |
| Art. 17 | Right to erasure | `EnrollUseCase.delete()` — atomic full deletion |
| Art. 25 | Privacy by Design and Default | This document |
| Art. 32 | Security of processing | AES-256-GCM; no network; RBAC |

---

## 4. Residual Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Key file theft | Low | High | OS file permissions; key separate from DB |
| Physical camera access | Medium | Medium | `WRONG_FACE_LIMIT` triggers lock |
| Replay attack (photo) | Low | Medium | Multi-frame streak requirement |
| Memory scraping | Very Low | High | Embeddings not logged or printed |
