# ISO Standards Compliance Mapping

**Document type**: Standards Mapping  
**Version**: 1.0  
**System**: FaceLock — Biometric Authentication System  
**Date**: 2026-04-21  
**Standards**: ISO/IEC 27001:2022, ISO/IEC 30107-3:2023

---

## Part 1 — ISO/IEC 27001:2022 (Information Security Management)

### Annex A Control Mapping

| Control | Title | FaceLock Implementation |
|---|---|---|
| A.5.1 | Information security policies | STORE_RAW_IMAGES=False; CLOUD_UPLOAD=False enforced in config |
| A.5.10 | Acceptable use of information assets | CLI-only access; no shared accounts |
| A.5.33 | Protection of records | HMAC-signed audit logs; tamper detection via `--verify` |
| A.8.2 | Privileged access rights | RBAC: admin / user / readonly roles |
| A.8.3 | Information access restriction | Repository pattern enforces DB access through crypto layer |
| A.8.5 | Secure authentication | AES-256-GCM + HMAC-SHA256; no plaintext credentials |
| A.8.7 | Protection against malware | On-device only; no network surface |
| A.8.11 | Data masking | Embeddings encrypted at rest; confidence % shown, not raw vector |
| A.8.12 | Data leakage prevention | No image storage; no cloud path; no network calls |
| A.8.15 | Logging | Timestamped, HMAC-signed SQLite audit trail |
| A.8.16 | Monitoring activities | `oversight/dashboard.py` — continuous monitoring capability |
| A.8.24 | Use of cryptography | AES-256-GCM (NIST SP 800-38D compliant) |
| A.8.25 | Secure development life cycle | Layered architecture; unit + integration tests |

### Applicability Statement

FaceLock is a single-component authentication system without a network perimeter.
Controls relating to network segmentation (A.8.20, A.8.21) and supplier relationships
(A.5.19–5.22) are not applicable.

---

## Part 2 — ISO/IEC 30107-3:2023 (Biometric Presentation Attack Detection)

### PAD Level Assessment

ISO 30107-3 defines Presentation Attack Detection (PAD) levels based on the attack
potential required to defeat the system.

| PAD Level | Description | FaceLock Status |
|---|---|---|
| Level 0 | No PAD; single-frame acceptance | **Not used** |
| Level 1 | Basic liveness (blink detection) | Not implemented |
| Level 2 | Multi-frame temporal consistency | **Implemented** — `AUTH_CORRECT_NEEDED = 10` consecutive frames |
| Level 3 | Hardware liveness (IR, 3D depth) | Not implemented (requires IR camera) |

FaceLock achieves **PAD Level 2** through temporal frame consistency. A static photograph
cannot satisfy 10 consecutive matching frames in a live video stream with natural variation.

### Attack Vector Coverage

| Attack type | Covered | Mechanism |
|---|---|---|
| Printed photo | Partial | Multi-frame streak; single frame never sufficient |
| Digital screen replay | Partial | Frame-to-frame variance detection |
| 3D mask | Not covered | Requires depth sensor (Level 3) |
| Impersonation | Yes | 0.45 cosine distance threshold |

### Performance Metrics

Metrics are computed using `evaluation/evaluate.py` with live genuine and imposter samples.
Results are stored in `report/evaluation_results.json`.

| Metric | Definition | Target | Measurement method |
|---|---|---|---|
| FAR | False Acceptance Rate | < 1% | Live imposter capture |
| FRR | False Rejection Rate | < 5% | Live genuine capture |
| EER | Equal Error Rate | < 3% | Threshold sweep across genuine/imposter distances |

---

## Part 3 — ISO/IEC 24745:2022 (Biometric Information Protection)

| Requirement | Implementation |
|---|---|
| Irreversibility | dlib embeddings are lossy projections; face cannot be reconstructed |
| Unlinkability | Each device has unique AES-256-GCM key; embeddings not portable |
| Revocability | `EnrollUseCase.delete()` — full atomic deletion |
| Confidentiality | AES-256-GCM at rest; no network transmission |
