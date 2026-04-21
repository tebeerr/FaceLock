# EU AI Act Compliance Mapping

**Document type**: EU AI Act Conformity Assessment  
**Version**: 1.0  
**System**: FaceLock — Biometric Authentication System  
**Regulation**: Regulation (EU) 2024/1689 (EU AI Act)  
**Date**: 2026-04-21  

---

## 1. System Classification

### 1.1 Is FaceLock an AI system under the AI Act?

**Yes.** FaceLock uses a machine-learning model (dlib ResNet face embedding network) to
infer identity from camera input. This satisfies Article 3(1) definition of an AI system.

### 1.2 Risk Category Assessment

Under **Annex III, Point 1(a)**, AI systems used for **biometric identification** of
natural persons are classified as **HIGH-RISK** when deployed in specific contexts
(law enforcement, border control, etc.).

For FaceLock deployed as a **personal workstation authentication tool**:

| Factor | Assessment |
|---|---|
| Deployment context | Private personal use, not law enforcement |
| Number of subjects | 1–5 (single-device authentication) |
| Consequential decision | Session lock only — reversible, low-stakes |
| Human oversight | Yes — operator can override via `oversight/dashboard.py` |

**Determination**: FaceLock falls under **limited risk** in personal authentication use.
However, this assessment applies a **high-risk compliance posture voluntarily** to
demonstrate best practice.

---

## 2. Article Compliance Mapping

### Article 9 — Risk Management System

| Requirement | Implementation |
|---|---|
| Identify and analyse risks | DPIA (`report/dpia.md`) |
| Risk mitigation measures | AES-256-GCM, multi-frame auth, HMAC logs |
| Residual risk evaluation | DPIA Section 4–5 |
| Post-deployment monitoring | Audit logs + oversight dashboard |

### Article 10 — Data and Data Governance

| Requirement | Implementation |
|---|---|
| Training/validation data practices | dlib pre-trained on publicly available datasets |
| Data relevance and representativeness | Embeddings captured per-user at enrolment |
| Examination for biases | EER evaluation (`evaluation/evaluate.py`) |
| Data minimisation | No raw images stored; 128-D vectors only |

### Article 13 — Transparency and Provision of Information

| Requirement | Implementation |
|---|---|
| System identifies itself as AI | CLI output labels all decisions with confidence % |
| Information to users | Enrolment prompt explains data collection |
| Intended purpose disclosed | README and enrolment UX |

### Article 14 — Human Oversight

| Requirement | Implementation |
|---|---|
| Human can intervene, interrupt, override | `oversight/dashboard.py --lock` |
| Operator can monitor system behaviour | `oversight/dashboard.py` (live dashboard) |
| Alerts on anomalous behaviour | Consecutive failure alert (≥3 failures) |
| Log integrity verification | `oversight/dashboard.py --verify` |
| Understanding of system capabilities | README, DPIA, this document |

### Article 15 — Accuracy, Robustness, and Cybersecurity

| Requirement | Implementation |
|---|---|
| Accuracy metrics documented | FAR/FRR/EER via `evaluation/evaluate.py` |
| Robustness against errors | Multi-frame streak prevents single-frame spoofing |
| Cybersecurity measures | AES-256-GCM, HMAC logs, RBAC |
| Resilience to adversarial input | `WRONG_FACE_LIMIT` lockout on persistent wrong face |

---

## 3. Prohibited Practices (Article 5)

FaceLock does **not**:

- Perform real-time remote biometric identification in public spaces (Art. 5(1)(d))
- Exploit vulnerabilities of specific groups (Art. 5(1)(b))
- Perform social scoring (Art. 5(1)(c))
- Infer emotions in workplace/educational settings (Art. 5(1)(f))

---

## 4. Conformity Documentation

| Document | Location | Status |
|---|---|---|
| DPIA | `report/dpia.md` | Complete |
| Privacy by Design | `report/privacy_by_design.md` | Complete |
| Technical documentation | `README.md` | Complete |
| Evaluation results | `report/evaluation_results.json` | Generated on eval run |
| Human oversight log | SQLite `auth_logs` table | Live |

---

## 5. Conformity Declaration

FaceLock, as deployed for personal workstation authentication, implements controls
consistent with EU AI Act high-risk requirements on a voluntary basis. The system
processes biometric data locally, maintains tamper-evident logs, provides human
oversight mechanisms, and documents its accuracy characteristics.
