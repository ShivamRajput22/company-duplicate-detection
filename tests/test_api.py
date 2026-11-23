import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["total_entities"] == 10000

def test_database_stats_endpoint():
    res = client.get("/api/database/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_entities"] == 10000
    assert data["ground_truth_pairs_count"] > 0

def test_upload_and_compare_workflow():
    # 10 test rows covering domain match, linkedin match, fuzzy fallback, conflicts, look-alikes
    sample_csv = """company_name,legal_name,web_domain,linkedin_url
Cobalt Capital,Cobalt Capital GmbH,cobalt-capital.example,https://www.linkedin.com/company/cobalt-capital
Trimark Property Group,Trimark Property Group LLC,trimark-property.example,https://www.linkedin.com/company/trimark-property
Trimark Petroleum Group,Trimark Petroleum Group LLC,trimark-petroleum.example,https://www.linkedin.com/company/trimark-petroleum
Apex Technologies,Apex Technologies Inc,,https://www.linkedin.com/company/apex-technologies
Beacon Solutions,Beacon Solutions Corp,beacon-solutions.example,
Genesis Holdings,Genesis Holdings LLC,,
Horizon Healthcare,Horizon Healthcare Systems LLC,horizon-health.example,https://www.linkedin.com/company/horizon-health
Westbridge Properties,Westbridge Properties LLC,westbridge-properties.example,https://www.linkedin.com/company/westbridge-properties
Delta Innovations,Delta Innovations Ltd,=cmd|' /C calc'!A0,https://www.linkedin.com/company/delta-innovations
No Match Company,Totally Unique Enterprises Inc,totally-unique-nonexistent.example,https://www.linkedin.com/company/totally-unique-nonexistent
"""
    # 1. Upload CSV
    files = {"file": ("test_companies.csv", io.BytesIO(sample_csv.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/imports", files=files)
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    run_id = upload_data["run_id"]
    assert upload_data["total_rows"] == 10
    assert upload_data["accepted_rows"] == 10

    # 2. Run Comparison
    compare_res = client.post(f"/api/imports/{run_id}/compare", json={"fuzzy_threshold": 80.0})
    assert compare_res.status_code == 200
    compare_data = compare_res.json()
    assert compare_data["run_status"] == "completed"
    assert compare_data["candidate_pairs_count"] > 0

    # 3. Get Results
    results_res = client.get(f"/api/imports/{run_id}/results?page=1&page_size=20")
    assert results_res.status_code == 200
    results_data = results_res.json()
    assert results_data["total_uploaded_rows"] == 10
    assert results_data["total_candidates"] > 0
    candidates = results_data["candidates"]
    assert len(candidates) > 0

    first_cand = candidates[0]
    cand_id = first_cand["candidate_id"]

    # 4. Human Review
    review_res = client.post(
        f"/api/imports/{run_id}/reviews",
        json={
            "candidate_id": cand_id,
            "decision": "confirmed_duplicate",
            "reviewer": "qa_tester",
            "reason": "Verified domain and corporate records match."
        }
    )
    assert review_res.status_code == 200
    review_data = review_res.json()
    assert review_data["new_decision"] == "confirmed_duplicate"

    # Refresh results to verify review decision persisted
    results_res_after = client.get(f"/api/imports/{run_id}/results")
    assert results_res_after.status_code == 200
    updated_cand = next(c for c in results_res_after.json()["candidates"] if c["candidate_id"] == cand_id)
    assert updated_cand["latest_review_decision"] == "confirmed_duplicate"

    # 5. Export Tests (All 3 Views)
    # View A: uploaded_summary
    exp_up = client.get(f"/api/imports/{run_id}/export?type=uploaded_summary")
    assert exp_up.status_code == 200
    assert exp_up.headers["content-type"].startswith("text/csv")
    up_csv_text = exp_up.content.decode("utf-8-sig")
    assert "Upload Record ID" in up_csv_text
    # Invariant: No Match Company must be present in uploaded_summary!
    assert "No Match Company" in up_csv_text
    # Formula injection test: formula string `=cmd|' /C calc'!A0` is sanitized with leading quote `'`
    assert "'=cmd|" in up_csv_text

    # View B: master_summary
    exp_master = client.get(f"/api/imports/{run_id}/export?type=master_summary")
    assert exp_master.status_code == 200
    master_csv_text = exp_master.content.decode("utf-8-sig")
    assert "Matched Entity ID" in master_csv_text
    assert "Matched Legal Name" in master_csv_text
    # Invariant AC-03 & AC-04: Never IMPORT_BATCH, real entity_id with adjacent legal_name
    assert "IMPORT_BATCH" not in master_csv_text
    master_lines = [l for l in master_csv_text.strip().split("\r\n") if l]
    header = master_lines[0].split(",")
    id_idx = header.index('"Matched Entity ID"') if '"Matched Entity ID"' in header else header.index("Matched Entity ID")
    name_idx = header.index('"Matched Legal Name"') if '"Matched Legal Name"' in header else header.index("Matched Legal Name")
    # Verify adjacent
    assert abs(id_idx - name_idx) == 1

    # Verify zero repeated master companies in master_summary (AC-05)
    matched_ids = []
    for l in master_lines[1:]:
        parts = l.split(",")
        matched_ids.append(parts[id_idx])
    assert len(matched_ids) == len(set(matched_ids)), "Master summary must not repeat master entity IDs"

    # View C: candidate_details
    exp_detail = client.get(f"/api/imports/{run_id}/export?type=candidate_details")
    assert exp_detail.status_code == 200
    detail_csv_text = exp_detail.content.decode("utf-8-sig")
    assert "Matched Entity ID" in detail_csv_text
    assert "Name Similarity (%)" in detail_csv_text
    assert "Latest Review Decision" in detail_csv_text


def test_single_page_rows_and_append_only_review_round_trip():
    """Reopening and repeated validation retain raw names, pair IDs and reviews."""
    import csv
    from database.database import SessionLocal
    from database.models import Entity

    with SessionLocal() as session:
        master = session.query(Entity).filter(Entity.normalized_domain.isnot(None)).first()
        entity_id, legal_name = master.entity_id, master.legal_name
        domain, linkedin = master.web_domain, master.linkedin_url
    payload = io.StringIO()
    writer = csv.writer(payload)
    writer.writerow(["company_name", "legal_name", "web_domain", "linkedin_url"])
    writer.writerow(["Original company, Ltd", "'=Original legal name", domain, linkedin])
    writer.writerow(["Unique QA ZXQY987", "Unique QA ZXQY987 Legal", "zxqy987-qa.example", ""])
    writer.writerow(["", "", "invalid domain!", ""])
    imported = client.post("/api/imports", files={"file": ("round_trip.CSV", payload.getvalue().encode(), "text/csv")})
    assert imported.status_code == 200
    run_id = imported.json()["run_id"]
    assert client.post(f"/api/imports/{run_id}/compare", json={"fuzzy_threshold": 80}).status_code == 200
    result = client.get(f"/api/imports/{run_id}/results?page_size=100").json()
    assert result["filename"] == "round_trip.CSV"
    assert result["uploaded_rows"] == imported.json()["rows"]
    assert result["uploaded_rows"][0]["legal_name_original"] == "'=Original legal name"
    assert result["uploaded_rows"][2]["record_validation_status"] == "rejected"
    assert result["uploaded_rows"][2]["validation_errors"]
    assert client.get(f"/api/imports/{run_id}/results?page=2").json()["uploaded_rows"] == []
    candidate = next(c for c in result["candidates"] if c["matched_entity_id"] == entity_id and c["csv_row_number"] == 2)
    assert candidate["matched_legal_name"] == legal_name
    for decision in ["not_duplicate", "needs_review"]:
        review = client.post(f"/api/imports/{run_id}/reviews", json={
            "candidate_id": candidate["candidate_id"], "decision": decision, "reviewer": "regression_test"
        })
        assert review.status_code == 200
    history_before = client.get(f"/api/imports/{run_id}/reviews").json()
    assert [r["new_decision"] for r in history_before] == ["needs_review", "not_duplicate"]
    assert history_before[0]["prior_decision"] == "not_duplicate"
    assert client.post(f"/api/imports/{run_id}/compare", json={"fuzzy_threshold": 80}).status_code == 200
    assert client.post(f"/api/imports/{run_id}/compare", json={"fuzzy_threshold": 85}).status_code == 409
    assert client.get(f"/api/imports/{run_id}/reviews").json() == history_before
    after = client.get(f"/api/imports/{run_id}/results?page_size=100").json()
    assert [c["candidate_id"] for c in after["candidates"]] == [c["candidate_id"] for c in result["candidates"]]
    assert after["uploaded_rows"] == result["uploaded_rows"]
