from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, ForeignKey,
    DateTime, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.database import Base

def utcnow_str():
    return datetime.now(timezone.utc).isoformat()

class Entity(Base):
    __tablename__ = "entities"

    entity_id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(500), nullable=False)
    legal_name = Column(String(500), nullable=True)
    web_domain = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)

    normalized_company_name = Column(String(500), nullable=True)
    normalized_legal_name = Column(String(500), nullable=True)
    normalized_domain = Column(String(500), nullable=True)
    normalized_linkedin = Column(String(500), nullable=True)

    normalization_version = Column(String(50), nullable=False, default="v1")
    created_at = Column(String(50), nullable=False, default=utcnow_str)

    __table_args__ = (
        Index("idx_entities_norm_domain", "normalized_domain"),
        Index("idx_entities_norm_linkedin", "normalized_linkedin"),
        Index("idx_entities_norm_legal_name", "normalized_legal_name"),
    )

class ImportRun(Base):
    __tablename__ = "import_runs"

    run_id = Column(String(100), primary_key=True)
    filename = Column(String(500), nullable=False)
    content_hash = Column(String(100), nullable=False)
    fuzzy_threshold = Column(Float, nullable=False, default=80.0)
    rule_version = Column(String(50), nullable=False, default="v1")
    algorithm_version = Column(String(50), nullable=False, default="rapidfuzz_ratio")
    normalization_version = Column(String(50), nullable=False, default="v1")
    master_snapshot_id = Column(String(100), nullable=True)
    run_status = Column(String(50), nullable=False, default="pending")  # pending, running, completed, failed
    total_rows = Column(Integer, default=0)
    accepted_rows = Column(Integer, default=0)
    rejected_rows = Column(Integer, default=0)
    candidate_pairs_count = Column(Integer, default=0)
    idempotency_key = Column(String(100), unique=True, nullable=True)
    started_at = Column(String(50), nullable=True)
    completed_at = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    rows = relationship("ImportRow", back_populates="run", cascade="all, delete-orphan")
    candidates = relationship("MatchCandidate", back_populates="run", cascade="all, delete-orphan")

class ImportRow(Base):
    __tablename__ = "import_rows"

    row_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(100), ForeignKey("import_runs.run_id", ondelete="CASCADE"), nullable=False)
    upload_record_id = Column(String(100), nullable=False)
    csv_row_number = Column(Integer, nullable=False)

    company_name_original = Column(Text, nullable=True)
    legal_name_original = Column(Text, nullable=True)
    web_domain_original = Column(Text, nullable=True)
    linkedin_url_original = Column(Text, nullable=True)

    company_name_normalized = Column(Text, nullable=True)
    legal_name_normalized = Column(Text, nullable=True)
    web_domain_normalized = Column(Text, nullable=True)
    linkedin_url_normalized = Column(Text, nullable=True)

    website_validation_status = Column(String(50), nullable=False, default="missing")  # valid, missing, invalid
    linkedin_validation_status = Column(String(50), nullable=False, default="missing") # valid, missing, invalid
    record_validation_status = Column(String(50), nullable=False, default="accepted")  # accepted, rejected
    validation_errors = Column(Text, nullable=True) # JSON list of error messages

    run = relationship("ImportRun", back_populates="rows")

    __table_args__ = (
        UniqueConstraint("run_id", "csv_row_number", name="uq_import_rows_run_csv_row"),
        UniqueConstraint("run_id", "upload_record_id", name="uq_import_rows_run_upload_record_id"),
        Index("idx_import_rows_run_id", "run_id"),
    )

class MatchCandidate(Base):
    __tablename__ = "match_candidates"

    candidate_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(100), ForeignKey("import_runs.run_id", ondelete="CASCADE"), nullable=False)
    upload_record_id = Column(String(100), nullable=False)
    candidate_entity_id = Column(Integer, ForeignKey("entities.entity_id"), nullable=False)

    website_match_state = Column(String(50), nullable=False)  # MATCH, CONFLICT, UNAVAILABLE
    linkedin_match_state = Column(String(50), nullable=False) # MATCH, CONFLICT, UNAVAILABLE
    name_similarity_percent = Column(Float, nullable=True)    # Null unless fuzzy comparison was evaluated

    match_methods = Column(Text, nullable=False)   # JSON array: ["website", "linkedin", "fuzzy_legal_name"]
    matched_fields = Column(Text, nullable=False)  # JSON array
    conflicting_fields = Column(Text, nullable=False) # JSON array
    match_status = Column(String(100), nullable=False) # high_confidence_candidate, potential_duplicate, needs_review, insufficient_data, not_a_match
    discovery_type = Column(String(50), nullable=False, default="standard") # standard, related_name
    rationale = Column(Text, nullable=False)

    ai_verification_status = Column(String(50), nullable=True)
    ai_relationship_type = Column(String(50), nullable=True)
    ai_reason = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=False, default=utcnow_str)

    run = relationship("ImportRun", back_populates="candidates")
    entity = relationship("Entity")
    reviews = relationship("DuplicateReview", back_populates="candidate", cascade="all, delete-orphan", order_by="desc(DuplicateReview.reviewed_at)")

    __table_args__ = (
        UniqueConstraint("run_id", "upload_record_id", "candidate_entity_id", name="uq_match_candidates_pair"),
        Index("idx_candidates_run_status", "run_id", "match_status"),
        Index("idx_candidates_run_record", "run_id", "upload_record_id"),
    )

class DuplicateReview(Base):
    __tablename__ = "duplicate_reviews"

    review_id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("match_candidates.candidate_id", ondelete="CASCADE"), nullable=False)
    reviewer = Column(String(100), nullable=False, default="human_reviewer")
    prior_decision = Column(String(50), nullable=True)
    new_decision = Column(String(50), nullable=False) # confirmed_duplicate, not_duplicate, needs_review
    reason = Column(Text, nullable=True)
    request_id = Column(String(100), unique=True, nullable=True)
    reviewed_at = Column(String(50), nullable=False, default=utcnow_str)

    candidate = relationship("MatchCandidate", back_populates="reviews")

    __table_args__ = (
        Index("idx_reviews_candidate_time", "candidate_id", "reviewed_at"),
    )

class VerificationJob(Base):
    __tablename__ = "verification_jobs"

    job_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(100), nullable=False)
    candidate_id = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default="pending") # pending, running, completed, needs_review, failed, skipped, budget_exceeded, cancelled
    retry_count = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    actual_cost_usd = Column(Float, default=0.0)
    started_at = Column(String(50), nullable=True)
    completed_at = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

class VerificationEvidence(Base):
    __tablename__ = "verification_evidence"

    evidence_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, nullable=True)
    candidate_id = Column(Integer, nullable=False)
    source_url = Column(String(500), nullable=True)
    provenance = Column(String(200), nullable=True)
    retrieved_at = Column(String(50), nullable=False, default=utcnow_str)
    expires_at = Column(String(50), nullable=True)
    evidence_snippet = Column(Text, nullable=True)
    evidence_hash = Column(String(100), nullable=True)

class ApiUsage(Base):
    __tablename__ = "api_usage"

    usage_id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    request_count = Column(Integer, default=1)
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    created_at = Column(String(50), nullable=False, default=utcnow_str)

class GroundTruth(Base):
    """
    Isolated ground truth labels for synthetic benchmark evaluation only.
    Inference / production code NEVER reads this table.
    """
    __tablename__ = "ground_truth"

    pair_id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id_a = Column(Integer, nullable=False)
    entity_id_b = Column(Integer, nullable=False)
    is_duplicate = Column(Boolean, nullable=False)
    relationship_type = Column(String(50), nullable=False) # same_entity, related_company, unrelated
    scenario_id = Column(String(50), nullable=False)
    label_source = Column(String(100), nullable=False, default="synthetic_generator")
    dataset_partition = Column(String(50), nullable=False, default="test") # dev, val, test

    __table_args__ = (
        UniqueConstraint("entity_id_a", "entity_id_b", name="uq_ground_truth_pair"),
        Index("idx_ground_truth_partition", "dataset_partition"),
    )
