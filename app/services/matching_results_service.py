import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from database.models import ImportRun, ImportRow, MatchCandidate, Entity, DuplicateReview
from app.services.candidate_service import candidate_service

def utcnow_str():
    return datetime.now(timezone.utc).isoformat()

class MatchingResultsService:
    @classmethod
    def execute_matching_for_run(
        cls,
        session: Session,
        run_id: str,
        fuzzy_threshold: Optional[float] = None
    ) -> ImportRun:
        """
        Executes duplicate matching for all accepted rows in an import run.
        Enforces candidate pair uniqueness: exactly one record per (run_id, upload_record_id, entity_id).
        Transactionally persists candidates and updates run status and metrics.
        """
        run: ImportRun = session.query(ImportRun).filter(ImportRun.run_id == run_id).first()
        if not run:
            raise ValueError(f"Import run '{run_id}' not found.")

        threshold = fuzzy_threshold if fuzzy_threshold is not None else run.fuzzy_threshold
        # A completed run is an immutable matching snapshot. Re-validating must
        # never cascade-delete append-only human reviews or change pair IDs.
        if run.run_status == "completed":
            if threshold != run.fuzzy_threshold:
                raise ValueError("This run is completed. Upload a new CSV to use a different threshold; its review history is preserved.")
            return run
        if run.run_status == "running":
            raise ValueError("This comparison is already running.")
        has_reviews = session.query(DuplicateReview.review_id).join(MatchCandidate).filter(
            MatchCandidate.run_id == run_id
        ).first()
        if has_reviews:
            raise ValueError("This run has review history. Upload a new CSV to compare again.")
        run.fuzzy_threshold = threshold
        run.run_status = "running"
        run.started_at = utcnow_str()
        session.commit()

        try:
            # Delete any existing candidates for idempotency / re-run safety
            session.query(MatchCandidate).filter(MatchCandidate.run_id == run_id).delete()
            session.commit()

            rows = session.query(ImportRow).filter(
                ImportRow.run_id == run_id,
                ImportRow.record_validation_status == "accepted"
            ).order_by(ImportRow.csv_row_number).all()

            candidate_records = []
            seen_pairs = set()

            for row in rows:
                row_dict = {
                    "upload_record_id": row.upload_record_id,
                    "company_name_normalized": row.company_name_normalized,
                    "legal_name_normalized": row.legal_name_normalized,
                    "web_domain_normalized": row.web_domain_normalized,
                    "linkedin_url_normalized": row.linkedin_url_normalized,
                }

                candidates_evaluated = candidate_service.get_candidates_for_row(
                    session=session,
                    row=row_dict,
                    fuzzy_threshold=threshold
                )

                for ent, classification in candidates_evaluated:
                    pair_key = (run_id, row.upload_record_id, ent.entity_id)
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    candidate_obj = MatchCandidate(
                        run_id=run_id,
                        upload_record_id=row.upload_record_id,
                        candidate_entity_id=ent.entity_id,
                        website_match_state=classification.website_match_state,
                        linkedin_match_state=classification.linkedin_match_state,
                        name_similarity_percent=classification.name_similarity_percent,
                        match_methods=json.dumps(classification.match_methods),
                        matched_fields=json.dumps(classification.matched_fields),
                        conflicting_fields=json.dumps(classification.conflicting_fields),
                        match_status=classification.match_status,
                        discovery_type=classification.discovery_type,
                        rationale=classification.rationale,
                        created_at=utcnow_str()
                    )
                    candidate_records.append(candidate_obj)

            if candidate_records:
                session.bulk_save_objects(candidate_records)

            run.candidate_pairs_count = len(candidate_records)
            run.run_status = "completed"
            run.completed_at = utcnow_str()
            session.commit()
            return run
        except Exception as e:
            session.rollback()
            run.run_status = "failed"
            run.error_message = str(e)
            run.completed_at = utcnow_str()
            session.commit()
            raise

matching_results_service = MatchingResultsService()
