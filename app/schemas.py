from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class HealthResponse(BaseModel):
    status: str
    database: str
    total_entities: int
    ai_verification_enabled: bool

class DatabaseStatsResponse(BaseModel):
    total_entities: int
    entities_with_domain: int
    entities_with_linkedin: int
    entities_with_both_blank: int
    ground_truth_pairs_count: int

class ImportRowItem(BaseModel):
    upload_record_id: str
    csv_row_number: int
    company_name_original: Optional[str]
    legal_name_original: Optional[str]
    web_domain_original: Optional[str]
    linkedin_url_original: Optional[str]
    record_validation_status: str
    validation_errors: Optional[List[str]] = None

class ImportResponse(BaseModel):
    run_id: str
    filename: str
    content_hash: str
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    empty_rows_skipped: int
    invalid_identifiers: int
    rows: List[ImportRowItem]

class CompareRequest(BaseModel):
    fuzzy_threshold: Optional[float] = Field(default=80.0, ge=50.0, le=100.0)
    idempotency_key: Optional[str] = None

class CompareResponse(BaseModel):
    run_id: str
    run_status: str
    candidate_pairs_count: int
    fuzzy_threshold: float
    started_at: Optional[str]
    completed_at: Optional[str]

class CandidateItem(BaseModel):
    candidate_id: int
    run_id: str
    upload_record_id: str
    csv_row_number: Optional[int]
    uploaded_company_name: Optional[str]
    uploaded_legal_name: Optional[str]
    uploaded_domain: Optional[str]
    uploaded_linkedin: Optional[str]

    matched_entity_id: int
    matched_legal_name: Optional[str]
    matched_company_name: Optional[str]
    matched_domain: Optional[str]
    matched_linkedin: Optional[str]

    match_methods: List[str]
    website_match_state: str
    linkedin_match_state: str
    name_similarity_percent: Optional[float]
    match_status: str
    discovery_type: str
    matched_fields: List[str]
    conflicting_fields: List[str]
    rationale: str

    latest_review_decision: Optional[str] = None
    ai_verification_status: Optional[str] = None
    ai_relationship_type: Optional[str] = None
    ai_reason: Optional[str] = None

class PaginatedResultsResponse(BaseModel):
    run_id: str
    total_candidates: int
    page: int
    page_size: int
    total_pages: int
    candidates: List[CandidateItem]
    # 5 Summary counts
    total_uploaded_rows: int
    strong_candidates_count: int
    potential_fuzzy_count: int
    needs_review_count: int
    reviewed_count: int

class CandidateDetailResponse(BaseModel):
    candidate: CandidateItem
    review_history: List[Dict[str, Any]]
    verification_evidence: List[Dict[str, Any]]

class ReviewRequest(BaseModel):
    candidate_id: int
    decision: str = Field(..., pattern="^(confirmed_duplicate|not_duplicate|needs_review)$")
    reviewer: Optional[str] = "human_reviewer"
    reason: Optional[str] = None
    request_id: Optional[str] = None

class ReviewResponse(BaseModel):
    review_id: int
    candidate_id: int
    reviewer: str
    prior_decision: Optional[str]
    new_decision: str
    reason: Optional[str]
    reviewed_at: str

class VerifyRequest(BaseModel):
    candidate_id: int

class MetricsResponse(BaseModel):
    run_id: str
    total_rows: int
    accepted_rows: int
    candidate_pairs_count: int
    high_confidence_count: int
    potential_duplicate_count: int
    needs_review_count: int
    reviewed_count: int
    fuzzy_threshold: float
    elapsed_time_seconds: Optional[float] = None
