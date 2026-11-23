from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import Entity, GroundTruth
from app.config import settings
from app.schemas import HealthResponse, DatabaseStatsResponse

router = APIRouter(tags=["Health & Database"])

@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    try:
        count = db.query(Entity).count()
        return HealthResponse(
            status="healthy",
            database="connected",
            total_entities=count,
            ai_verification_enabled=settings.AI_VERIFICATION_ENABLED
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {e}")

@router.get("/database/stats", response_model=DatabaseStatsResponse)
def get_database_stats(db: Session = Depends(get_db)):
    try:
        total = db.query(Entity).count()
        with_dom = db.query(Entity).filter(Entity.normalized_domain.isnot(None)).count()
        with_li = db.query(Entity).filter(Entity.normalized_linkedin.isnot(None)).count()
        both_blank = db.query(Entity).filter(
            Entity.normalized_domain.is_(None),
            Entity.normalized_linkedin.is_(None)
        ).count()
        gt_count = db.query(GroundTruth).count()

        return DatabaseStatsResponse(
            total_entities=total,
            entities_with_domain=with_dom,
            entities_with_linkedin=with_li,
            entities_with_both_blank=both_blank,
            ground_truth_pairs_count=gt_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query database stats: {e}")
