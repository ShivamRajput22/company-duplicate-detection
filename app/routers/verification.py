from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from database.database import get_db
from database.models import MatchCandidate, VerificationJob
from app.services.verification_service import verification_service
from app.schemas import VerifyRequest

router = APIRouter(prefix="/imports/{run_id}", tags=["AI Verification (Optional)"])

@router.post("/verify")
def trigger_verification(
    run_id: str,
    req: VerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Triggers optional advisory evidence verification for a candidate pair.
    Runs mock offline evidence provider without making paid external calls.
    """
    try:
        result = verification_service.run_mock_verification(
            session=db,
            candidate_id=req.candidate_id,
            run_id=run_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {e}")

@router.get("/verification-jobs")
def get_verification_jobs(
    run_id: str,
    db: Session = Depends(get_db)
):
    jobs = db.query(VerificationJob).filter(VerificationJob.run_id == run_id).all()
    return [
        {
            "job_id": j.job_id,
            "candidate_id": j.candidate_id,
            "status": j.status,
            "estimated_cost_usd": j.estimated_cost_usd,
            "actual_cost_usd": j.actual_cost_usd,
            "started_at": j.started_at,
            "completed_at": j.completed_at
        } for j in jobs
    ]
