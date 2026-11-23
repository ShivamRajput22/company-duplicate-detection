export interface CandidateItem {
  candidate_id: number;
  run_id: string;
  upload_record_id: string;
  csv_row_number?: number;
  uploaded_company_name?: string;
  uploaded_legal_name?: string;
  uploaded_domain?: string;
  uploaded_linkedin?: string;

  matched_entity_id: number;
  matched_legal_name?: string;
  matched_company_name?: string;
  matched_domain?: string;
  matched_linkedin?: string;

  match_methods: string[];
  website_match_state: 'MATCH' | 'CONFLICT' | 'UNAVAILABLE';
  linkedin_match_state: 'MATCH' | 'CONFLICT' | 'UNAVAILABLE';
  name_similarity_percent?: number | null;
  match_status: string;
  discovery_type: string;
  matched_fields: string[];
  conflicting_fields: string[];
  rationale: string;

  latest_review_decision?: 'confirmed_duplicate' | 'not_duplicate' | 'needs_review' | null;
  ai_verification_status?: string | null;
  ai_relationship_type?: string | null;
  ai_reason?: string | null;
}

export interface PaginatedResultsResponse {
  filename: string;
  uploaded_rows: ImportRowItem[];
  run_id: string;
  total_candidates: number;
  page: number;
  page_size: number;
  total_pages: number;
  candidates: CandidateItem[];

  total_uploaded_rows: number;
  strong_candidates_count: number;
  potential_fuzzy_count: number;
  needs_review_count: number;
  reviewed_count: number;
}

export interface ImportRowItem {
  upload_record_id: string;
  csv_row_number: number;
  company_name_original?: string;
  legal_name_original?: string;
  web_domain_original?: string;
  linkedin_url_original?: string;
  record_validation_status: string;
  validation_errors?: string[];
}

export interface ImportResponse {
  run_id: string;
  filename: string;
  content_hash: string;
  total_rows: number;
  accepted_rows: number;
  rejected_rows: number;
  empty_rows_skipped: number;
  invalid_identifiers: number;
  rows: ImportRowItem[];
}

export interface CompareResponse {
  run_id: string;
  run_status: string;
  candidate_pairs_count: number;
  fuzzy_threshold: number;
  started_at?: string;
  completed_at?: string;
}

export interface ReviewHistoryItem {
  candidate_id?: number;
  review_id: number;
  reviewer: string;
  prior_decision?: string;
  new_decision: string;
  reason?: string;
  reviewed_at: string;
}

export interface CandidateDetailResponse {
  candidate: CandidateItem;
  review_history: ReviewHistoryItem[];
  verification_evidence: any[];
}

export interface DatabaseStats {
  total_entities: number;
  entities_with_domain: number;
  entities_with_linkedin: number;
  entities_with_both_blank: number;
  ground_truth_pairs_count: number;
}
