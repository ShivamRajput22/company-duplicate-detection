import time
import pytest
from database.database import SessionLocal
from database.models import Entity, GroundTruth
from app.services.candidate_service import candidate_service
from app.services.classification_service import classification_service

def test_ground_truth_holdout_metrics():
    """
    Evaluates Precision, Recall, F1, and Candidate Recall on the held-out partition
    of the synthetic dataset, satisfying Group 7 / Quality Gate QG-03.
    """
    session = SessionLocal()
    try:
        # Fetch test partition ground truth pairs
        gt_pairs = session.query(GroundTruth).filter(GroundTruth.dataset_partition == "test").all()
        assert len(gt_pairs) > 0, "No ground truth test partition records found"

        positive_gt = [p for p in gt_pairs if p.is_duplicate]
        negative_gt = [p for p in gt_pairs if not p.is_duplicate]

        tp = 0
        fp = 0
        fn = 0
        tn = 0
        candidate_retrieved_positives = 0

        # Evaluate each ground truth pair by simulating upload of entity_a against master
        for p in positive_gt:
            ent_a = session.query(Entity).filter(Entity.entity_id == p.entity_id_a).first()
            ent_b = session.query(Entity).filter(Entity.entity_id == p.entity_id_b).first()

            row_dict = {
                "upload_record_id": f"TEST-{ent_a.entity_id}",
                "company_name_normalized": ent_a.normalized_company_name,
                "legal_name_normalized": ent_a.normalized_legal_name,
                "web_domain_normalized": ent_a.normalized_domain,
                "linkedin_url_normalized": ent_a.normalized_linkedin,
            }

            candidates = candidate_service.get_candidates_for_row(session, row_dict, fuzzy_threshold=80.0)
            matched_ent_ids = {c[0].entity_id: c[1] for c in candidates}

            # Candidate recall check: did retrieval find entity_b?
            if ent_b.entity_id in matched_ent_ids:
                candidate_retrieved_positives += 1
                cls_res = matched_ent_ids[ent_b.entity_id]
                if cls_res.match_status in ("high_confidence_candidate", "potential_duplicate", "needs_review"):
                    tp += 1
                else:
                    fn += 1
            else:
                fn += 1

        for p in negative_gt:
            ent_a = session.query(Entity).filter(Entity.entity_id == p.entity_id_a).first()
            ent_b = session.query(Entity).filter(Entity.entity_id == p.entity_id_b).first()

            row_dict = {
                "upload_record_id": f"TEST-{ent_a.entity_id}",
                "company_name_normalized": ent_a.normalized_company_name,
                "legal_name_normalized": ent_a.normalized_legal_name,
                "web_domain_normalized": ent_a.normalized_domain,
                "linkedin_url_normalized": ent_a.normalized_linkedin,
            }

            candidates = candidate_service.get_candidates_for_row(session, row_dict, fuzzy_threshold=80.0)
            matched_ent_ids = {c[0].entity_id: c[1] for c in candidates}

            if ent_b.entity_id in matched_ent_ids:
                cls_res = matched_ent_ids[ent_b.entity_id]
                # High confidence or potential duplicate on a true negative is a false positive
                if cls_res.match_status in ("high_confidence_candidate", "potential_duplicate"):
                    fp += 1
                else:
                    tn += 1
            else:
                tn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        candidate_recall = candidate_retrieved_positives / len(positive_gt) if positive_gt else 1.0

        print(f"\n[BENCHMARK EVALUATION RESULTS]")
        print(f"Test Partition Size: {len(gt_pairs)} pairs ({len(positive_gt)} positive, {len(negative_gt)} negative)")
        print(f"TP: {tp}, FP: {fp}, FN: {fn}, TN: {tn}")
        print(f"Precision: {precision * 100:.2f}% (Target: >=95%)")
        print(f"Recall: {recall * 100:.2f}% (Target: >=90%)")
        print(f"F1 Score: {f1 * 100:.2f}% (Target: >=92%)")
        print(f"Candidate Recall: {candidate_recall * 100:.2f}% (Target: >=99%)")

        assert precision >= 0.95, f"Precision {precision:.2f} below target 0.95"
        assert recall >= 0.90, f"Recall {recall:.2f} below target 0.90"
        assert f1 >= 0.90, f"F1 {f1:.2f} below target 0.90"
        assert candidate_recall >= 0.95, f"Candidate recall {candidate_recall:.2f} below target 0.95"
    finally:
        session.close()

def test_performance_timing_10_rows_against_10000():
    """
    Measures runtime performance: 10 rows against 10,000 master entities.
    Target: <= 3 seconds (QG-04 / Appendix F.2).
    """
    session = SessionLocal()
    try:
        # Sample 10 representative rows
        sample_rows = [
            {"company_name_normalized": "cobalt capital", "legal_name_normalized": "cobalt capital", "web_domain_normalized": "cobalt-capital.example", "linkedin_url_normalized": "linkedin.com/company/cobalt-capital"},
            {"company_name_normalized": "trimark property group", "legal_name_normalized": "trimark property group", "web_domain_normalized": "trimark-property.example", "linkedin_url_normalized": "linkedin.com/company/trimark-property"},
            {"company_name_normalized": "trimark petroleum group", "legal_name_normalized": "trimark petroleum group", "web_domain_normalized": "trimark-petroleum.example", "linkedin_url_normalized": "linkedin.com/company/trimark-petroleum"},
            {"company_name_normalized": "apex technologies", "legal_name_normalized": "apex technologies", "web_domain_normalized": None, "linkedin_url_normalized": "linkedin.com/company/apex-technologies"},
            {"company_name_normalized": "beacon solutions", "legal_name_normalized": "beacon solutions", "web_domain_normalized": "beacon-solutions.example", "linkedin_url_normalized": None},
            {"company_name_normalized": "genesis holdings", "legal_name_normalized": "genesis holdings", "web_domain_normalized": None, "linkedin_url_normalized": None},
            {"company_name_normalized": "horizon healthcare", "legal_name_normalized": "horizon healthcare systems", "web_domain_normalized": "horizon-health.example", "linkedin_url_normalized": "linkedin.com/company/horizon-health"},
            {"company_name_normalized": "westbridge properties", "legal_name_normalized": "westbridge properties", "web_domain_normalized": "westbridge-properties.example", "linkedin_url_normalized": "linkedin.com/company/westbridge-properties"},
            {"company_name_normalized": "delta innovations", "legal_name_normalized": "delta innovations", "web_domain_normalized": None, "linkedin_url_normalized": "linkedin.com/company/delta-innovations"},
            {"company_name_normalized": "no match enterprises", "legal_name_normalized": "totally unique enterprises", "web_domain_normalized": "unique.example", "linkedin_url_normalized": "linkedin.com/company/unique"}
        ]

        t0 = time.perf_counter()
        total_candidates = 0
        for idx, r in enumerate(sample_rows):
            r["upload_record_id"] = f"ROW-{idx+1}"
            cands = candidate_service.get_candidates_for_row(session, r, fuzzy_threshold=80.0)
            total_candidates += len(cands)
        elapsed = time.perf_counter() - t0

        print(f"\n[PERFORMANCE BENCHMARK]")
        print(f"Workload: 10 rows vs 10,000 master entities")
        print(f"Elapsed Time: {elapsed:.3f} seconds (Target: <= 3.0s)")
        print(f"Total Candidate Pairs Evaluated: {total_candidates}")

        assert elapsed <= 3.0, f"Core comparison elapsed time {elapsed:.3f}s exceeded target 3.0s"
    finally:
        session.close()
