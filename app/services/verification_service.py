from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.config import settings
from database.models import MatchCandidate, VerificationJob, VerificationEvidence, ApiUsage, Entity
import json
from datetime import datetime, timezone

def utcnow_str():
    return datetime.now(timezone.utc).isoformat()

class VerificationService:
    @classmethod
    def is_enabled(cls) -> bool:
        return bool(settings.AI_VERIFICATION_ENABLED)

    @classmethod
    def run_mock_verification(
        cls,
        session: Session,
        candidate_id: int,
        run_id: str
    ) -> Dict[str, Any]:
        """
        Advisory verification provider (runs safely offline with mock evidence).
        Used when AI verification is triggered, without making paid external calls.
        """
        candidate = session.query(MatchCandidate).filter(MatchCandidate.candidate_id == candidate_id).first()
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found.")

        ent = session.query(Entity).filter(Entity.entity_id == candidate.candidate_entity_id).first()

        # Check job
        job = VerificationJob(
            run_id=run_id,
            candidate_id=candidate_id,
            status="completed",
            retry_count=0,
            estimated_cost_usd=0.005,
            actual_cost_usd=0.0, # Zero paid cost for synthetic demo
            started_at=utcnow_str(),
            completed_at=utcnow_str()
        )
        session.add(job)
        session.flush()

        # Generate advisory relationship
        if candidate.match_status == "high_confidence_candidate":
            rel_type = "same_legal_entity"
            reason = f"Verified matching registry footprint and registered domain '{ent.web_domain if ent else ''}'."
            status = "completed"
        elif candidate.match_status == "potential_duplicate":
            rel_type = "same_legal_entity"
            reason = "High name similarity and complementary business category indicate same legal identity."
            status = "completed"
        elif candidate.match_status == "needs_review":
            rel_type = "related_separate_entities"
            reason = "Conflicting identifiers indicate distinct entities operating under similar corporate branding."
            status = "needs_review"
        else:
            rel_type = "unrelated"
            reason = "External registry comparison finds no corporate connection."
            status = "completed"

        # Update candidate advisory fields
        candidate.ai_verification_status = status
        candidate.ai_relationship_type = rel_type
        candidate.ai_reason = reason

        # Record mock evidence
        evidence = VerificationEvidence(
            job_id=job.job_id,
            candidate_id=candidate_id,
            source_url=f"https://registry.example/entity/{candidate.candidate_entity_id}",
            provenance="Corporate Registry Mock Provider",
            retrieved_at=utcnow_str(),
            evidence_snippet=reason,
            evidence_hash=f"mock-hash-{candidate_id}"
        )
        session.add(evidence)

        # Record usage
        usage = ApiUsage(
            provider="mock_offline_provider",
            model="advisory-analyst-v1",
            request_count=1,
            tokens_used=120,
            cost_usd=0.0,
            created_at=utcnow_str()
        )
        session.add(usage)
        session.commit()

        return {
            "candidate_id": candidate_id,
            "status": status,
            "relationship_type": rel_type,
            "reason": reason,
            "cost_usd": 0.0
        }

verification_service = VerificationService()
