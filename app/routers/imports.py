import hashlib
import json
import uuid
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from database.database import get_db
from database.models import ImportRun, ImportRow, MatchCandidate, Entity, DuplicateReview
from app.services.csv_service import csv_service, CSVValidationError
from app.services.matching_results_service import matching_results_service
from app.services.export_service import export_service
from app.services.review_service import review_service
from app.schemas import (
    ImportResponse, ImportRowItem, CompareRequest, CompareResponse,
    PaginatedResultsResponse, CandidateItem, CandidateDetailResponse, MetricsResponse
)

router = APIRouter(prefix="/imports", tags=["Imports & Matching"])

def utcnow_str():
    return datetime.now(timezone.utc).isoformat()

@router.post("", response_model=ImportResponse)
async def upload_csv_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")

    file_bytes = await file.read()
    content_hash = hashlib.sha256(file_bytes).hexdigest()

    try:
        parsed_rows, stats = csv_service.parse_and_validate_csv(file_bytes, file.filename)
    except CSVValidationError as e:
        raise HTTPException(status_code=400, detail={"message": e.message, "errors": e.errors})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process CSV: {e}")

    run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"

    import_run = ImportRun(
        run_id=run_id,
        filename=file.filename,
        content_hash=content_hash,
        fuzzy_threshold=80.0,
        run_status="pending",
        total_rows=stats["total_rows"],
        accepted_rows=stats["accepted_rows"],
        rejected_rows=stats["rejected_rows"],
        candidate_pairs_count=0,
        started_at=None,
        completed_at=None
    )
    db.add(import_run)
    db.flush()

    row_objs = []
    for r in parsed_rows:
        row_obj = ImportRow(
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
            record_validation_status=r["record_validation_status"],
            validation_errors=json.dumps(r["validation_errors"])
        )
        row_objs.append(row_obj)

    db.bulk_save_objects(row_objs)
    db.commit()

    return ImportResponse(
        run_id=run_id,
        filename=file.filename,
        content_hash=content_hash,
        total_rows=stats["total_rows"],
        accepted_rows=stats["accepted_rows"],
        rejected_rows=stats["rejected_rows"],
        empty_rows_skipped=stats["empty_rows_skipped"],
        invalid_identifiers=stats["invalid_identifiers"],
        rows=[
            ImportRowItem(
                upload_record_id=r["upload_record_id"],
                csv_row_number=r["csv_row_number"],
                company_name_original=r["company_name_original"],
                legal_name_original=r["legal_name_original"],
                web_domain_original=r["web_domain_original"],
                linkedin_url_original=r["linkedin_url_original"],
                record_validation_status=r["record_validation_status"],
                validation_errors=r["validation_errors"]
            ) for r in parsed_rows
        ]
    )

@router.post("/{run_id}/compare", response_model=CompareResponse)
def run_comparison(
    run_id: str,
    req: CompareRequest = CompareRequest(),
    db: Session = Depends(get_db)
):
    run = db.query(ImportRun).filter(ImportRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Import run '{run_id}' not found.")

    threshold = req.fuzzy_threshold if req.fuzzy_threshold is not None else 80.0
    try:
        updated_run = matching_results_service.execute_matching_for_run(
            session=db,
            run_id=run_id,
            fuzzy_threshold=threshold
        )
        return CompareResponse(
            run_id=updated_run.run_id,
            run_status=updated_run.run_status,
            candidate_pairs_count=updated_run.candidate_pairs_count,
            fuzzy_threshold=updated_run.fuzzy_threshold,
            started_at=updated_run.started_at,
            completed_at=updated_run.completed_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Matching execution failed: {e}")

@router.get("/{run_id}/status", response_model=CompareResponse)
def get_run_status(run_id: str, db: Session = Depends(get_db)):
    run = db.query(ImportRun).filter(ImportRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Import run '{run_id}' not found.")
    return CompareResponse(
        run_id=run.run_id,
        run_status=run.run_status,
        candidate_pairs_count=run.candidate_pairs_count,
        fuzzy_threshold=run.fuzzy_threshold,
        started_at=run.started_at,
        completed_at=run.completed_at
    )

@router.get("/{run_id}/results", response_model=PaginatedResultsResponse)
def get_run_results(
    run_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    method: Optional[str] = Query(default=None),
    review_decision: Optional[str] = Query(default=None),
    discovery_type: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    min_similarity: Optional[float] = Query(default=None),
    max_similarity: Optional[float] = Query(default=None),
    db: Session = Depends(get_db)
):
    run = db.query(ImportRun).filter(ImportRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Import run '{run_id}' not found.")

    # Base query for candidates of this run
    query = db.query(MatchCandidate).filter(MatchCandidate.run_id == run_id)

    # Calculate 5 Summary Metric Card Counts
    all_cands = db.query(MatchCandidate).filter(MatchCandidate.run_id == run_id).all()
    total_uploaded = db.query(ImportRow).filter(ImportRow.run_id == run_id).count()

    strong_count = sum(1 for c in all_cands if c.match_status == "high_confidence_candidate")
    fuzzy_count = sum(1 for c in all_cands if c.match_status == "potential_duplicate")
    needs_review_count = sum(1 for c in all_cands if c.match_status == "needs_review")

    # Reviewed pairs count
    cand_ids = [c.candidate_id for c in all_cands]
    reviewed_set = set()
    if cand_ids:
        revs = db.query(DuplicateReview.candidate_id).filter(
            DuplicateReview.candidate_id.in_(cand_ids)
        ).distinct().all()
        reviewed_set = {r[0] for r in revs}
    reviewed_count = len(reviewed_set)

    # Apply Filters
    if status:
        query = query.filter(MatchCandidate.match_status == status)

    if discovery_type:
        query = query.filter(MatchCandidate.discovery_type == discovery_type)

    if method:
        query = query.filter(MatchCandidate.match_methods.like(f"%{method}%"))

    if min_similarity is not None:
        query = query.filter(MatchCandidate.name_similarity_percent >= min_similarity)

    if max_similarity is not None:
        query = query.filter(MatchCandidate.name_similarity_percent <= max_similarity)

    # Search filter q (entity_id or company name)
    if q:
        q_clean = q.strip()
        if q_clean.isdigit():
            query = query.filter(MatchCandidate.candidate_entity_id == int(q_clean))
        else:
            # Join with Entity or ImportRow
            matched_ent_ids = db.query(Entity.entity_id).filter(
                or_(
                    Entity.company_name.like(f"%{q_clean}%"),
                    Entity.legal_name.like(f"%{q_clean}%")
                )
            ).all()
            ent_id_list = [e[0] for e in matched_ent_ids]

            matched_row_ids = db.query(ImportRow.upload_record_id).filter(
                ImportRow.run_id == run_id,
                or_(
                    ImportRow.company_name_original.like(f"%{q_clean}%"),
                    ImportRow.legal_name_original.like(f"%{q_clean}%")
                )
            ).all()
            row_id_list = [r[0] for r in matched_row_ids]

            query = query.filter(
                or_(
                    MatchCandidate.candidate_entity_id.in_(ent_id_list),
                    MatchCandidate.upload_record_id.in_(row_id_list)
                )
            )

    total_filtered = query.count()
    total_pages = (total_filtered + page_size - 1) // page_size if total_filtered > 0 else 1

    # Order deterministically
    candidates = query.order_by(
        MatchCandidate.upload_record_id,
        MatchCandidate.candidate_entity_id
    ).offset((page - 1) * page_size).limit(page_size).all()

    # Pre-fetch entities, rows, and reviews
    ent_ids = [c.candidate_entity_id for c in candidates]
    entities = {e.entity_id: e for e in db.query(Entity).filter(Entity.entity_id.in_(ent_ids)).all()}

    row_ids = [c.upload_record_id for c in candidates]
    rows = {r.upload_record_id: r for r in db.query(ImportRow).filter(ImportRow.run_id == run_id, ImportRow.upload_record_id.in_(row_ids)).all()}

    cand_items = []
    for c in candidates:
        ent = entities.get(c.candidate_entity_id)
        row_src = rows.get(c.upload_record_id)
        latest_rev = review_service.get_latest_review(db, c.candidate_id)

        # Filter by review_decision if passed
        if review_decision:
            cur_dec = latest_rev.new_decision if latest_rev else "pending"
            if cur_dec != review_decision:
                continue

        cand_items.append(
            CandidateItem(
                candidate_id=c.candidate_id,
                run_id=c.run_id,
                upload_record_id=c.upload_record_id,
                csv_row_number=row_src.csv_row_number if row_src else None,
                uploaded_company_name=row_src.company_name_original if row_src else None,
                uploaded_legal_name=row_src.legal_name_original if row_src else None,
                uploaded_domain=row_src.web_domain_original if row_src else None,
                uploaded_linkedin=row_src.linkedin_url_original if row_src else None,
                matched_entity_id=c.candidate_entity_id,
                matched_legal_name=ent.legal_name if ent else None,
                matched_company_name=ent.company_name if ent else None,
                matched_domain=ent.web_domain if ent else None,
                matched_linkedin=ent.linkedin_url if ent else None,
                match_methods=json.loads(c.match_methods) if c.match_methods else [],
                website_match_state=c.website_match_state,
                linkedin_match_state=c.linkedin_match_state,
                name_similarity_percent=c.name_similarity_percent,
                match_status=c.match_status,
                discovery_type=c.discovery_type,
                matched_fields=json.loads(c.matched_fields) if c.matched_fields else [],
                conflicting_fields=json.loads(c.conflicting_fields) if c.conflicting_fields else [],
                rationale=c.rationale,
                latest_review_decision=latest_rev.new_decision if latest_rev else None,
                ai_verification_status=c.ai_verification_status,
                ai_relationship_type=c.ai_relationship_type,
                ai_reason=c.ai_reason
            )
        )

    return PaginatedResultsResponse(
        run_id=run_id,
        total_candidates=total_filtered,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        candidates=cand_items,
        total_uploaded_rows=total_uploaded,
        strong_candidates_count=strong_count,
        potential_fuzzy_count=fuzzy_count,
        needs_review_count=needs_review_count,
        reviewed_count=reviewed_count
    )

@router.get("/{run_id}/candidates/{upload_record_id}/{entity_id}", response_model=CandidateDetailResponse)
def get_candidate_detail(
    run_id: str,
    upload_record_id: str,
    entity_id: int,
    db: Session = Depends(get_db)
):
    candidate = db.query(MatchCandidate).filter(
        MatchCandidate.run_id == run_id,
        MatchCandidate.upload_record_id == upload_record_id,
        MatchCandidate.candidate_entity_id == entity_id
    ).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate pair not found.")

    ent = db.query(Entity).filter(Entity.entity_id == entity_id).first()
    row_src = db.query(ImportRow).filter(
        ImportRow.run_id == run_id,
        ImportRow.upload_record_id == upload_record_id
    ).first()

    history = review_service.get_review_history(db, candidate.candidate_id)
    history_items = [
        {
            "review_id": h.review_id,
            "reviewer": h.reviewer,
            "prior_decision": h.prior_decision,
            "new_decision": h.new_decision,
            "reason": h.reason,
            "reviewed_at": h.reviewed_at
        } for h in history
    ]

    latest_decision = history[0].new_decision if history else None

    item = CandidateItem(
        candidate_id=candidate.candidate_id,
        run_id=candidate.run_id,
        upload_record_id=candidate.upload_record_id,
        csv_row_number=row_src.csv_row_number if row_src else None,
        uploaded_company_name=row_src.company_name_original if row_src else None,
        uploaded_legal_name=row_src.legal_name_original if row_src else None,
        uploaded_domain=row_src.web_domain_original if row_src else None,
        uploaded_linkedin=row_src.linkedin_url_original if row_src else None,
        matched_entity_id=candidate.candidate_entity_id,
        matched_legal_name=ent.legal_name if ent else None,
        matched_company_name=ent.company_name if ent else None,
        matched_domain=ent.web_domain if ent else None,
        matched_linkedin=ent.linkedin_url if ent else None,
        match_methods=json.loads(candidate.match_methods) if candidate.match_methods else [],
        website_match_state=candidate.website_match_state,
        linkedin_match_state=candidate.linkedin_match_state,
        name_similarity_percent=candidate.name_similarity_percent,
        match_status=candidate.match_status,
        discovery_type=candidate.discovery_type,
        matched_fields=json.loads(candidate.matched_fields) if candidate.matched_fields else [],
        conflicting_fields=json.loads(candidate.conflicting_fields) if candidate.conflicting_fields else [],
        rationale=candidate.rationale,
        latest_review_decision=latest_decision,
        ai_verification_status=candidate.ai_verification_status,
        ai_relationship_type=candidate.ai_relationship_type,
        ai_reason=candidate.ai_reason
    )

    return CandidateDetailResponse(
        candidate=item,
        review_history=history_items,
        verification_evidence=[]
    )

@router.get("/{run_id}/export")
def export_results(
    run_id: str,
    type: str = Query(default="candidate_details", description="uploaded_summary | master_summary | candidate_details"),
    db: Session = Depends(get_db)
):
    try:
        csv_content = export_service.generate_csv_export(db, run_id, type)
        filename = f"{run_id}_{type}.csv"
        # Prepend UTF-8 BOM so Excel opens accents / characters cleanly
        csv_bytes = b"\xef\xbb\xbf" + csv_content.encode("utf-8")
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")

@router.get("/{run_id}/metrics", response_model=MetricsResponse)
def get_run_metrics(run_id: str, db: Session = Depends(get_db)):
    run = db.query(ImportRun).filter(ImportRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Import run '{run_id}' not found.")

    cands = db.query(MatchCandidate).filter(MatchCandidate.run_id == run_id).all()
    cand_ids = [c.candidate_id for c in cands]
    reviewed_count = 0
    if cand_ids:
        revs = db.query(DuplicateReview.candidate_id).filter(
            DuplicateReview.candidate_id.in_(cand_ids)
        ).distinct().all()
        reviewed_count = len(revs)

    high_conf = sum(1 for c in cands if c.match_status == "high_confidence_candidate")
    potential_dup = sum(1 for c in cands if c.match_status == "potential_duplicate")
    needs_rev = sum(1 for c in cands if c.match_status == "needs_review")

    elapsed = None
    if run.started_at and run.completed_at:
        try:
            t0 = datetime.fromisoformat(run.started_at)
            t1 = datetime.fromisoformat(run.completed_at)
            elapsed = (t1 - t0).total_seconds()
        except Exception:
            pass

    return MetricsResponse(
        run_id=run.run_id,
        total_rows=run.total_rows,
        accepted_rows=run.accepted_rows,
        candidate_pairs_count=run.candidate_pairs_count,
        high_confidence_count=high_conf,
        potential_duplicate_count=potential_dup,
        needs_review_count=needs_rev,
        reviewed_count=reviewed_count,
        fuzzy_threshold=run.fuzzy_threshold,
        elapsed_time_seconds=elapsed
    )
