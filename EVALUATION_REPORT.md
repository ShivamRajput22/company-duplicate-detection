# Benchmark Evaluation & Quality Gates Report

## 1. Executive Summary

This report documents the measured empirical results of the **Hybrid Intelligent Company Duplicate Detection System** evaluated against the synthetic master dataset.

- **Master Dataset:** Exactly 10,000 synthetic company records.
- **Intentional Duplicate Groups:** Exactly 200 groups (425 total records in groups of 2, 3, or 4 records).
- **Hard Negative Scenarios:** Cross-industry look-alikes (`Trimark Property Group` vs `Trimark Petroleum Group`, `Westbridge Capital` vs `Westbridge Logistics`, `Horizon Healthcare` vs `Horizon Aerospace`).
- **Ground Truth Partition:** 178 evaluation pairs in the test partition (176 true duplicate pairs, 2 hard negative control pairs).

---

## 2. Quality Gate Status Matrix (QG-01 to QG-10)

| Quality Gate | Requirement | Measured Result | Status |
|---|---|---|---|
| **QG-01** | All BR-01–BR-15 functional rule tests pass | 15/15 rule tests passed (`tests/test_rules.py`) | **PASSED** |
| **QG-02** | Real Entity ID + correct Legal Name integrity verified; no duplicate export keys | 100% verified across database and exports (`tests/test_exports.py`, `tests/test_e2e_smoke.py`) | **PASSED** |
| **QG-03** | Precision $\ge 95\%$, Recall $\ge 90\%$, F1 $\ge 92\%$, Candidate Recall $\ge 99\%$ | **Precision: 100.00%**, **Recall: 95.45%**, **F1: 97.67%**, **Candidate Recall: 100.00%** | **PASSED** |
| **QG-04** | Measured baseline comparison timing $\le 3.0$ seconds | **0.123 seconds** (10 incoming rows against 10,000 SQLite master entities) | **PASSED** |
| **QG-05** | Full backend + frontend workflows pass, including no-match and error states | Verified in `test_api.py` and `test_e2e_smoke.py`; production bundle built in 5.33s | **PASSED** |
| **QG-06** | No unresolved critical security vulnerabilities; formula injection defended | CSV formula injection sanitization verified with leading quote prefix (`'=cmd|`) | **PASSED** |
| **QG-07** | AI-disabled mode works without provider keys or paid calls | `AI_VERIFICATION_ENABLED=false` by default; all tests pass offline with zero paid requests | **PASSED** |
| **QG-08** | Run retries, review edits, exports and audit history are idempotent/persistent | Append-only audit trail verified in `duplicate_reviews` without mutating master entity | **PASSED** |
| **QG-09** | No duplicate implementations of matching, classification, normalization, or exports | Single authoritative service for normalization, classification, candidate retrieval, review, and export | **PASSED** |
| **QG-10** | All required tests executed; raw results and logs retained | 33 automated tests executed and passing in 6.97s | **PASSED** |

---

## 3. Labeled Holdout Test Metrics

Evaluated on held-out test partition (`tests/test_benchmarks.py`):

```
========================= BENCHMARK EVALUATION RESULTS =========================
Test Partition Size:       178 pairs (176 positive duplicates, 2 negative controls)
True Positives (TP):       168
False Positives (FP):      0
False Negatives (FN):      8 (unusable/corrupted inputs in complex variants)
True Negatives (TN):       2 (Trimark & Westbridge look-alike hard negatives)
--------------------------------------------------------------------------------
Metric                     Observed Value      Target Threshold     Result
--------------------------------------------------------------------------------
Precision                  100.00%             >= 95.00%            PASSED
Recall                     95.45%              >= 90.00%            PASSED
F1 Score                   97.67%              >= 92.00%            PASSED
Candidate Recall           100.00%             >= 99.00%            PASSED
================================================================================
```

---

## 4. Latency & Resource Benchmarks

Evaluated on local reference hardware (Windows 11, Python 3.12, SQLite 3.45):

```
============================ PERFORMANCE BENCHMARK ============================
Workload:                  10 uploaded records vs 10,000 master SQLite entities
Execution Mode:            AI_VERIFICATION_ENABLED=false (deterministic core)
Total Candidate Pairs:     300 pairs evaluated
Elapsed Processing Time:   0.123 seconds (Target: <= 3.0 seconds)
Throughput:                ~81 incoming rows / second against 10,000 master records
================================================================================
```

---

## 5. Client Complaint Regression Verification

1. **AC-01 (Speed):** 0.123s core comparison time eliminates previous tool freezing.
2. **AC-02 (Trimark Look-Alikes):** `Trimark Property Group` and `Trimark Petroleum Group` are identified as `related_name_lead` under separate discovery channel, preventing false duplicate merges while surfacing the look-alike relationship for investigator review.
3. **AC-03 (Entity ID):** Preserves actual `entities.entity_id` across all views.
4. **AC-04 (Adjacent Legal Name):** Authoritative `entities.legal_name` exported immediately adjacent to `entities.entity_id`.
5. **AC-05 (Non-Repeating Duplicates):** `master_summary` export contains exactly one row per master entity ID (zero repeat company rows).
6. **AC-06 (Domain Normalization):** Public Suffix List parsing extracts registered domains so `https://www.example.com/about` and `example.com` match identically, while `example.net` does not.
7. **AC-07 (Empirical Accuracy):** 100.00% Precision and 95.45% Recall measured on labeled synthetic holdout data.
8. **AC-10 (Review Safety):** Review decisions persisted append-only in `duplicate_reviews`. Zero master record updates, deletions, or merges.
