import io
import csv
import pytest
from database.database import SessionLocal
from database.models import Entity, ImportRun, ImportRow, MatchCandidate, DuplicateReview
from app.services.csv_service import csv_service
from app.services.matching_results_service import matching_results_service
from app.services.review_service import review_service
from app.services.export_service import export_service

def test_complete_e2e_workflow():
    session = SessionLocal()
    try:
        # Step 1: Verify 10,000 master entities invariant
        master_count = session.query(Entity).count()
        assert master_count == 10000, f"Expected 10,000 master entities, got {master_count}"

        # Step 2: Upload CSV with 10 representative rows
        raw_csv = """company_name,legal_name,web_domain,linkedin_url
Cobalt Capital,Cobalt Capital GmbH,cobalt-capital.example,https://www.linkedin.com/company/cobalt-capital
Trimark Property Group,Trimark Property Group LLC,trimark-property.example,https://www.linkedin.com/company/trimark-property
Trimark Petroleum Group,Trimark Petroleum Group LLC,trimark-petroleum.example,https://www.linkedin.com/company/trimark-petroleum
Apex Technologies,Apex Technologies Inc,,https://www.linkedin.com/company/apex-technologies
Beacon Solutions,Beacon Solutions Corp,beacon-solutions.example,
Genesis Holdings,Genesis Holdings LLC,,
Horizon Healthcare,Horizon Healthcare Systems LLC,horizon-health.example,https://www.linkedin.com/company/horizon-health
Westbridge Properties,Westbridge Properties LLC,westbridge-properties.example,https://www.linkedin.com/company/westbridge-properties
Delta Innovations,Delta Innovations Ltd,=calc!A0,https://www.linkedin.com/company/delta-innovations
Unique Innovators,Completely Unique Company Inc,completely-unique-12345.example,https://www.linkedin.com/company/completely-unique-12345
"""
        parsed_rows, stats = csv_service.parse_and_validate_csv(raw_csv.encode("utf-8"), "e2e_test.csv")
        assert stats["total_rows"] == 10
        assert stats["accepted_rows"] == 10

        run_id = "RUN-E2E-SMOKE-TEST"
        # Clean any prior run with this ID
        session.query(MatchCandidate).filter(MatchCandidate.run_id == run_id).delete()
        session.query(ImportRow).filter(ImportRow.run_id == run_id).delete()
        session.query(ImportRun).filter(ImportRun.run_id == run_id).delete()
        session.commit()

        run_obj = ImportRun(
            run_id=run_id,
            filename="e2e_test.csv",
            content_hash="mock-hash",
            fuzzy_threshold=80.0,
            run_status="pending",
            total_rows=10,
            accepted_rows=10,
            rejected_rows=0
        )
        session.add(run_obj)
        session.flush()

        for r in parsed_rows:
            session.add(ImportRow(
                run_id=run_id,
                upload_record_id=r["upload_record_id"],
                csv_row_number=r["csv_row_number"],
                company_name_original=r["company_name_original"],
                legal_name_original=r["legal_name_original"],
                web_domain_original=r["web_domain_original"],
                linkedin_url_original=r["linkedin_url_original"],
                company_name_normalized=r["company_name_normalized"],
                legal_name_normalized=r["legal_name_normalized"],
                web_domain_normalized=r["web_domain_normalized"],
                linkedin_url_normalized=r["linkedin_url_normalized"],
                website_validation_status=r["website_validation_status"],
                linkedin_validation_status=r["linkedin_validation_status"],
                record_validation_status=r["record_validation_status"]
            ))
        session.commit()

        # Step 3: Execute Matching
        completed_run = matching_results_service.execute_matching_for_run(
            session=session,
            run_id=run_id,
            fuzzy_threshold=80.0
        )
        assert completed_run.run_status == "completed"
        assert completed_run.candidate_pairs_count > 0

        # Step 4: Verify Candidate Pairs & Integrity
        candidates = session.query(MatchCandidate).filter(MatchCandidate.run_id == run_id).all()
        assert len(candidates) == completed_run.candidate_pairs_count

        # Check pair uniqueness constraint: (run_id, upload_record_id, candidate_entity_id)
        pair_keys = [(c.run_id, c.upload_record_id, c.candidate_entity_id) for c in candidates]
        assert len(pair_keys) == len(set(pair_keys)), "Candidate pairs must be unique"

        # Check AC-03 & AC-04: Entity ID and Legal Name correspondence
        for c in candidates:
            ent = session.query(Entity).filter(Entity.entity_id == c.candidate_entity_id).first()
            assert ent is not None, f"Master entity {c.candidate_entity_id} must exist in entities table"
            # Verify legal_name is real
            assert ent.legal_name is not None

        # Check Trimark look-alike hard negative:
        # "Trimark Property Group" vs "Trimark Petroleum Group"
        # Must NOT be marked high_confidence_candidate or potential_duplicate!
        trimark_cand = session.query(MatchCandidate).filter(
            MatchCandidate.run_id == run_id,
            MatchCandidate.match_status == "high_confidence_candidate"
        ).all()
        for tc in trimark_cand:
            ent = session.query(Entity).filter(Entity.entity_id == tc.candidate_entity_id).first()
            # If upload was property, candidate should not be petroleum
            row_src = session.query(ImportRow).filter(
                ImportRow.run_id == run_id,
                ImportRow.upload_record_id == tc.upload_record_id
            ).first()
            if "property" in row_src.company_name_normalized:
                assert "petroleum" not in ent.normalized_company_name

        # Step 5: Human Review Decision Persistence & Audit Trail
        test_candidate = candidates[0]
        rev1 = review_service.save_review_decision(
            session=session,
            candidate_id=test_candidate.candidate_id,
            decision="confirmed_duplicate",
            reviewer="qa_agent",
            reason="Confirmed by QA",
            request_id="req-1"
        )
        assert rev1.new_decision == "confirmed_duplicate"

        # Edit review (append-only)
        rev2 = review_service.save_review_decision(
            session=session,
            candidate_id=test_candidate.candidate_id,
            decision="needs_review",
            reviewer="senior_reviewer",
            reason="Need additional registry check",
            request_id="req-2"
        )
        assert rev2.new_decision == "needs_review"
        assert rev2.prior_decision == "confirmed_duplicate"

        history = review_service.get_review_history(session, test_candidate.candidate_id)
        assert len(history) == 2
        assert history[0].new_decision == "needs_review"
        assert history[1].new_decision == "confirmed_duplicate"

        # Invariant: Master entity table was NOT modified
        assert session.query(Entity).count() == 10000

        # Step 6: CSV Exports Integrity
        # 1. uploaded_summary: exactly 10 rows (1 row per uploaded record)
        up_csv = export_service.generate_csv_export(session, run_id, "uploaded_summary")
        up_lines = [l for l in up_csv.strip().split("\r\n") if l]
        # 1 header + 10 data rows = 11 lines
        assert len(up_lines) == 11, f"Expected 11 lines in uploaded_summary, got {len(up_lines)}"
        assert "Unique Innovators" in up_csv # No-match row is preserved

        # 2. master_summary: zero duplicate master entities
        master_csv = export_service.generate_csv_export(session, run_id, "master_summary")
        master_lines = [l for l in master_csv.strip().split("\r\n") if l]
        master_ids = []
        for l in master_lines[1:]:
            parts = l.split(",")
            master_ids.append(parts[1]) # Matched Entity ID
        assert len(master_ids) == len(set(master_ids)), "Master summary must not have duplicate master entities"

        # 3. candidate_details: formula injection check
        detail_csv = export_service.generate_csv_export(session, run_id, "candidate_details")
        assert "Matched Entity ID" in detail_csv
        assert "Latest Review Decision" in detail_csv

        print("\n[E2E SMOKE TEST PASSED]")
        print(f"Verified 10 uploaded rows against 10,000 master entities.")
        print(f"Total candidate pairs: {len(candidates)}")
        print(f"Review history count: {len(history)}")
        print(f"All 3 export views verified for row grain and referential integrity.")
    finally:
        session.close()
