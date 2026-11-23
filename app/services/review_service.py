from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from database.models import MatchCandidate, DuplicateReview

def utcnow_str():
    return datetime.now(timezone.utc).isoformat()

VALID_DECISIONS = {"confirmed_duplicate", "not_duplicate", "needs_review"}

class ReviewService:
    @classmethod
    def save_review_decision(
        cls,
        session: Session,
        candidate_id: int,
        decision: str,
        reviewer: str = "human_reviewer",
        reason: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> DuplicateReview:
        """
        Saves a human review decision in append-only fashion.
        Never mutates the entities table.
        """
        if decision not in VALID_DECISIONS:
            raise ValueError(f"Invalid review decision: '{decision}'. Must be one of: {list(VALID_DECISIONS)}")

        candidate = session.query(MatchCandidate).filter(MatchCandidate.candidate_id == candidate_id).first()
        if not candidate:
            raise ValueError(f"Candidate ID {candidate_id} not found.")

        # Check idempotency
        if request_id:
            existing = session.query(DuplicateReview).filter(DuplicateReview.request_id == request_id).first()
            if existing:
                return existing

        # Get latest prior decision
        latest = session.query(DuplicateReview).filter(
            DuplicateReview.candidate_id == candidate_id
        ).order_by(DuplicateReview.reviewed_at.desc()).first()

        prior_decision = latest.new_decision if latest else None

        review = DuplicateReview(
            candidate_id=candidate_id,
            reviewer=reviewer,
            prior_decision=prior_decision,
            new_decision=decision,
            reason=reason,
            request_id=request_id,
            reviewed_at=utcnow_str()
        )
        session.add(review)
        session.commit()
        session.refresh(review)
        return review

    @classmethod
    def get_latest_review(
        cls,
        session: Session,
        candidate_id: int
    ) -> Optional[DuplicateReview]:
        return session.query(DuplicateReview).filter(
            DuplicateReview.candidate_id == candidate_id
        ).order_by(DuplicateReview.reviewed_at.desc()).first()

    @classmethod
    def get_review_history(
        cls,
        session: Session,
        candidate_id: int
    ) -> List[DuplicateReview]:
        return session.query(DuplicateReview).filter(
            DuplicateReview.candidate_id == candidate_id
        ).order_by(DuplicateReview.reviewed_at.desc()).all()

review_service = ReviewService()
