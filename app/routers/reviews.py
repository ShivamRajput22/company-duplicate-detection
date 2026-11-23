from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database.database import get_db
from database.models import MatchCandidate, DuplicateReview
from app.services.review_service import review_service
from app.schemas import ReviewRequest, ReviewResponse

router = APIRouter(prefix="/imports/{run_id}/reviews", tags=["Human Reviews"])

@router.post("", response_model=ReviewResponse)
def submit_review(
    run_id: str,
    req: ReviewRequest,
    db: Session = Depends(get_db)
):
    # Verify candidate belongs to run
    candidate = db.query(MatchCandidate).filter(
        MatchCandidate.candidate_id == req.candidate_id,
        MatchCandidate.run_id == run_id
    ).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found in this run.")

    try:
        review = review_service.save_review_decision(
            session=db,
            candidate_id=req.candidate_id,
            decision=req.decision,
            reviewer=req.reviewer or "human_reviewer",
            reason=req.reason,
            request_id=req.request_id
        )
        return ReviewResponse(
            review_id=review.review_id,
            candidate_id=review.candidate_id,
            reviewer=review.reviewer,
            prior_decision=review.prior_decision,
            new_decision=review.new_decision,
            reason=review.reason,
            reviewed_at=review.reviewed_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save review: {e}")

@router.get("", response_model=List[ReviewResponse])
def get_run_reviews(run_id: str, db: Session = Depends(get_db)):
    # Get all reviews for candidates in this run
    candidates = db.query(MatchCandidate.candidate_id).filter(MatchCandidate.run_id == run_id).all()
    cand_ids = [c[0] for c in candidates]
    if not cand_ids:
        return []

    reviews = db.query(DuplicateReview).filter(
        DuplicateReview.candidate_id.in_(cand_ids)
    ).order_by(DuplicateReview.reviewed_at.desc()).all()

    return [
        ReviewResponse(
            review_id=r.review_id,
            candidate_id=r.candidate_id,
            reviewer=r.reviewer,
            prior_decision=r.prior_decision,
            new_decision=r.new_decision,
            reason=r.reason,
            reviewed_at=r.reviewed_at
        ) for r in reviews
    ]
