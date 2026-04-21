# Data Protection Impact Assessment (DPIA)

**Document type**: DPIA per GDPR Article 35  
**Version**: 1.0  
**System**: FaceLock — Biometric Authentication System  
**Date**: 2026-04-21  
**Controller**: Academic institution / individual operator  

---

## 1. Necessity for DPIA

GDPR Article 35(3)(b) requires a DPIA for any "large-scale processing of special categories
of data referred to in Article 9". Biometric data processed for the purpose of uniquely
identifying a natural person is a **special category** under Article 9(1).

FaceLock triggers Article 35 because it processes biometric data (facial embeddings derived
from facial images) to identify individuals.

---

## 2. Description of Processing

| Field | Value |
|---|---|
| **Purpose** | Authenticate the authorised user of a Windows workstation |
| **Data subjects** | Enrolled users (1–N individuals per device) |
| **Data categories** | Biometric data — 128-D facial embedding derived from facial image |
| **Recipients** | None — all processing is local |
| **Retention** | Until the user requests deletion; no automatic expiry |
| **Third-country transfers** | None |
| **Automated decisions** | Yes — session lock/unlock without human decision per-event |

---

## 3. Processing Necessity and Proportionality

### 3.1 Is processing necessary for the purpose?

Yes. The system replaces password-based authentication. To authenticate by face, the
system must store a mathematical representation of the enrolled face.

### 3.2 Is there a less privacy-invasive alternative?

Password authentication requires no biometric data and should be the default. FaceLock
is an optional enhancement. The system defaults to less data (no images, no cloud) and
cannot be configured to collect more without code changes.

### 3.3 Proportionality

| Data element | Collected | Justification |
|---|---|---|
| Raw facial images | **No** | Not required; embedding is sufficient |
| 128-D face embedding | Yes | Minimum necessary for authentication |
| Timestamp of events | Yes | Required for audit trail |
| IP address / device ID | **No** | Not required |

---

## 4. Risk Assessment

### 4.1 Risk Register

| ID | Risk | Likelihood | Severity | Risk Score |
|---|---|---|---|---|
| R1 | Embedding extracted from DB and used to reconstruct face | Low | High | Medium |
| R2 | Key file stolen, embeddings decrypted | Low | High | Medium |
| R3 | Imposter bypasses facial recognition | Low | High | Medium |
| R4 | Session lock fails to trigger | Low | Medium | Low |
| R5 | Audit log tampered to remove evidence of breach | Very Low | High | Low |
| R6 | Replay attack using printed photo | Low | Medium | Low |

### 4.2 Likelihood Rationale

- **R1**: Face reconstruction from 128-D embeddings is computationally infeasible with current
  techniques (embeddings are lossy projections, not invertible transforms)
- **R2**: Key file requires OS-level access to the user account
- **R3**: Mitigated by multi-frame streak requirement (`AUTH_CORRECT_NEEDED = 10`) and
  distance threshold (`MATCH_THRESHOLD = 0.45`)

---

## 5. Measures to Address Risks

| Risk | Measure | Status |
|---|---|---|
| R1 | Non-invertible embedding (dlib ResNet); no raw image stored | Implemented |
| R2 | AES-256-GCM encryption; key file stored outside DB | Implemented |
| R3 | Multi-frame authentication streak (10 frames) | Implemented |
| R4 | `WRONG_FACE_LIMIT` + `NO_FACE_TIMEOUT` dual triggers | Implemented |
| R5 | HMAC-SHA256 signed audit entries; `oversight --verify` | Implemented |
| R6 | Multi-frame streak makes single-frame spoofing ineffective | Implemented |

---

## 6. DPO Consultation

This system processes biometric data on a small scale (single device, 1–5 users typically)
for authentication purposes only. Under GDPR Recital 91, DPO consultation is recommended
but may not be strictly mandatory at this scale. Institutions deploying at larger scale must
conduct formal DPO consultation before deployment.

---

## 7. Conclusion

The residual risk after applying the measures above is **acceptable** for a single-user
authentication system. The processing is necessary, proportionate, and implements
state-of-the-art privacy controls (AES-256-GCM, no image storage, local-only).

Processing may proceed subject to:
1. Explicit informed consent from each enrolled user
2. Documented deletion procedure made available to users
3. Periodic review of residual risks (recommended annually)
